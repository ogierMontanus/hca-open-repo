// Tests for the crowd API Worker: OAuth flow, sessions, roles, the
// contributor → editor round trip, and the GitHub storage requests.
// No network: GitHub is a fake `fetch`; storage is the in-memory store.
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { handle } from '../src/index.js';
import { MemoryStore } from '../src/store-memory.js';
import { GithubStore } from '../src/store-github.js';
import { sign, verify, safeReturn, isAdmin } from '../src/auth.js';

const CASES = JSON.parse(fs.readFileSync(new URL('../../../tests/fixtures/crowd_cases.json', import.meta.url), 'utf8'));
const VALID = CASES.cases.find((c) => c.name === 'valid').payload;
const ORIGIN = 'https://ogiermontanus.github.io';
const RETURN = ORIGIN + '/hca-open-repo/mockup/crowd.html';
const SECRET = 'x'.repeat(40);
const ENV = {
  ALLOWED_ORIGINS: ORIGIN + ',http://127.0.0.1:8765', RETURN_PATH_PREFIX: '/', GITHUB_CLIENT_ID: 'cid', GITHUB_CLIENT_SECRET: 'csec',
  SESSION_SECRET: SECRET, ADMINS: '999, EditorLogin'
};
const WORKER = 'https://crowd.example.workers.dev';

const clone = (o) => JSON.parse(JSON.stringify(o));

function ghFetch(user) {
  const calls = [];
  const f = async (url, init) => {
    calls.push({ url: String(url), init });
    if (String(url) === 'https://github.com/login/oauth/access_token') {
      return new Response(JSON.stringify(JSON.parse(init.body).code === 'good' ? { access_token: 'gho_x' } : { error: 'bad_verification_code' }));
    }
    if (String(url) === 'https://api.github.com/user') return new Response(JSON.stringify(user));
    throw new Error('unexpected fetch ' + url);
  };
  f.calls = calls;
  return f;
}

async function login(user, env = ENV, store) {
  const deps = { fetch: ghFetch(user), store };
  const r1 = await handle(new Request(`${WORKER}/auth/login?return=${encodeURIComponent(RETURN)}`), env, deps);
  assert.equal(r1.status, 302);
  const gh = new URL(r1.headers.get('Location'));
  const nonceCookie = r1.headers.get('Set-Cookie').split(';')[0];
  const r2 = await handle(new Request(`${WORKER}/auth/callback?code=good&state=${encodeURIComponent(gh.searchParams.get('state'))}`,
    { headers: { Cookie: nonceCookie } }), env, deps);
  assert.equal(r2.status, 302);
  const loc = r2.headers.get('Location');
  assert.ok(loc.startsWith(RETURN + '#hca_session='), loc);
  return { token: loc.split('#hca_session=')[1], gh, r1, deps };
}

function call(method, path, token, body, store) {
  return handle(new Request(WORKER + '/api/crowd/' + path, {
    method, headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: 'Bearer ' + token } : {}), Origin: ORIGIN },
    body: body === undefined ? undefined : JSON.stringify(body)
  }), ENV, { store });
}

/* ── login flow ─────────────────────────────────────────────────────────── */
test('login redirects to GitHub with a signed state, a nonce cookie and the callback on the Worker', async () => {
  const { gh, r1 } = await login({ id: 1, login: 'anne', name: 'Anne' });
  assert.equal(gh.origin + gh.pathname, 'https://github.com/login/oauth/authorize');
  assert.equal(gh.searchParams.get('client_id'), 'cid');
  assert.equal(gh.searchParams.get('redirect_uri'), WORKER + '/auth/callback');
  assert.equal(gh.searchParams.get('scope'), null);
  const cookie = r1.headers.get('Set-Cookie');
  assert.match(cookie, /HttpOnly/); assert.match(cookie, /Secure/); assert.match(cookie, /SameSite=Lax/); assert.match(cookie, /Path=\/auth/);
  const st = await verify(gh.searchParams.get('state'), SECRET, 'state');
  assert.equal(st.r, RETURN);
});

test('login refuses a return URL outside the allowed origins / path (no open redirect)', async () => {
  for (const bad of ['https://evil.example/x', 'javascript:alert(1)', ORIGIN + '.evil.example/', 'not a url', '']) {
    const r = await handle(new Request(`${WORKER}/auth/login?return=${encodeURIComponent(bad)}`), ENV, {});
    assert.equal(r.status, 400, bad);
  }
  assert.equal(safeReturn(ORIGIN + '/other/', { ...ENV, RETURN_PATH_PREFIX: '/hca-open-repo/' }), null);
  assert.equal(safeReturn(ORIGIN + '/hca-open-repo/a.html#x', { ...ENV, RETURN_PATH_PREFIX: '/hca-open-repo/' }), ORIGIN + '/hca-open-repo/a.html');
});

test('callback: state must match the cookie nonce, be signed, and not be a session token', async () => {
  const deps = { fetch: ghFetch({ id: 1, login: 'a' }) };
  const state = await sign({ k: 'state', n: 'N1', r: RETURN, exp: Math.floor(Date.now() / 1000) + 60 }, SECRET);
  const get = (st, cookie) => handle(new Request(`${WORKER}/auth/callback?code=good&state=${encodeURIComponent(st)}`,
    { headers: cookie ? { Cookie: cookie } : {} }), ENV, deps);
  assert.equal((await get(state, 'hca_oauth=OTHER')).status, 400);          // login CSRF: other browser's nonce
  assert.equal((await get(state, null)).status, 400);                        // no cookie
  assert.equal((await get(state + 'x', 'hca_oauth=N1')).status, 400);       // forged signature
  const sess = await sign({ k: 'session', sub: 'gh-1', exp: Math.floor(Date.now() / 1000) + 60 }, SECRET);
  assert.equal((await get(sess, 'hca_oauth=N1')).status, 400);              // wrong token kind
  const expired = await sign({ k: 'state', n: 'N1', r: RETURN, exp: 1 }, SECRET);
  assert.equal((await get(expired, 'hca_oauth=N1')).status, 400);
  assert.equal(deps.fetch.calls.length, 0, 'GitHub is never contacted for an invalid state');
});

test('callback: a failed code exchange or a denial returns to the page with an error, no session', async () => {
  const { gh } = await login({ id: 1, login: 'a' });
  const state = gh.searchParams.get('state');
  const nonce = (await verify(state, SECRET, 'state')).n;
  const r = await handle(new Request(`${WORKER}/auth/callback?code=bad&state=${encodeURIComponent(state)}`,
    { headers: { Cookie: 'hca_oauth=' + nonce } }), ENV, { fetch: ghFetch({ id: 1, login: 'a' }) });
  assert.equal(r.headers.get('Location'), RETURN + '#hca_error=exchange');
  const d = await handle(new Request(`${WORKER}/auth/callback?error=access_denied&state=${encodeURIComponent(state)}`,
    { headers: { Cookie: 'hca_oauth=' + nonce } }), ENV, {});
  assert.equal(d.headers.get('Location'), RETURN + '#hca_error=denied');
});

test('the GitHub token is not passed on: the session carries only id, login, name, expiry', async () => {
  const { token } = await login({ id: 42, login: 'anne', name: 'Anne Å' });
  const p = await verify(token, SECRET, 'session');
  assert.deepEqual(Object.keys(p).sort(), ['exp', 'iat', 'k', 'login', 'name', 'sub', 'v']);
  assert.equal(p.sub, 'gh-42');
  assert.ok(!token.includes('gho_x'));
});

/* ── sessions and roles ─────────────────────────────────────────────────── */
test('tokens: forged, expired and missing sessions are anonymous; admin routes → 401', async () => {
  const store = new MemoryStore();
  assert.equal((await call('GET', 'admin/submissions', null, undefined, store)).status, 401);
  assert.equal((await call('GET', 'admin/submissions', 'garbage', undefined, store)).status, 401);
  const expired = await sign({ k: 'session', sub: 'gh-999', login: 'x', exp: 5 }, SECRET);
  assert.equal((await call('GET', 'admin/submissions', expired, undefined, store)).status, 401);
  const other = await sign({ k: 'session', sub: 'gh-999', login: 'x', exp: 4e9 }, 'y'.repeat(40));
  assert.equal((await call('GET', 'admin/submissions', other, undefined, store)).status, 401);
  assert.equal((await call('POST', 'submissions', null, clone(VALID), store)).status, 401);
});

test('roles come from ADMINS (id or login) at request time, never from the token', () => {
  assert.equal(isAdmin({ id: 'gh-999', login: 'someone' }, '999'), true);
  assert.equal(isAdmin({ id: 'gh-1', login: 'EditorLogin' }, ' @editorlogin '), true);
  assert.equal(isAdmin({ id: 'gh-1', login: 'anne' }, '999,EditorLogin'), false);
  assert.equal(isAdmin({ id: 'gh-1', login: 'anne' }, ''), false);
});

/* ── round trip ─────────────────────────────────────────────────────────── */
test('contributor submits; another contributor cannot see or touch it; the editor reviews; the contributor sees the outcome', async () => {
  const store = new MemoryStore();
  const anne = (await login({ id: 1, login: 'anne', name: 'Anne' }, ENV, store)).token;
  const bo = (await login({ id: 2, login: 'bo', name: 'Bo' }, ENV, store)).token;
  const ed = (await login({ id: 999, login: 'editor', name: 'Ed' }, ENV, store)).token;

  const created = await call('POST', 'submissions', anne, { ...clone(VALID), context: { area: 'Danmark', doubt: true, level: 'delvist', gaps: ['identity', 'nonsense'] } }, store);
  assert.equal(created.status, 201);
  const sub = (await created.json()).submission;
  assert.match(sub.id, /^CS-\d{8}-[0-9a-f]{6}$/);
  assert.equal(sub.contributor.id, 'gh-1');
  assert.equal(sub.status, 'submitted');
  assert.equal(sub.register_snapshot, undefined, 'snapshot is not echoed to the contributor');

  assert.deepEqual((await (await call('GET', 'mine', bo, undefined, store)).json()).submissions, []);
  assert.equal((await call('PUT', 'submissions/' + sub.id, bo, clone(VALID), store)).status, 403);
  assert.equal((await call('POST', `submissions/${sub.id}/withdraw`, bo, undefined, store)).status, 403);
  assert.equal((await call('GET', 'admin/submissions', anne, undefined, store)).status, 403);
  assert.equal((await call('POST', `admin/submissions/${sub.id}/review`, anne, { action: 'request_changes', note: 'forsøg på selvgodkendelse' }, store)).status, 403);

  const list = await (await call('GET', 'admin/submissions?status=submitted', ed, undefined, store)).json();
  assert.equal(list.submissions.length, 1);
  const detail = await (await call('GET', 'admin/submissions/' + sub.id, ed, undefined, store)).json();
  assert.deepEqual(detail.register, { label: '', description: '', area: 'Danmark', doubt: true, level: 'delvist', gaps: ['identity'] });

  const ask = await call('POST', `admin/submissions/${sub.id}/review`, ed, { action: 'request_changes', note: 'Hvilken folketælling?' }, store);
  assert.equal((await ask.json()).submission.status, 'needs_changes');
  const mine1 = await (await call('GET', 'mine', anne, undefined, store)).json();
  assert.equal(mine1.submissions[0].status, 'needs_changes');
  assert.equal(mine1.submissions[0].review.note, 'Hvilken folketælling?');
  assert.equal(mine1.submissions[0].review.reviewer_id, undefined);

  const revised = await call('PUT', 'submissions/' + sub.id, anne, clone(VALID), store);
  assert.equal(revised.status, 200);
  assert.equal((await revised.json()).submission.revision, 2);

  const decisions = { fields: { 0: { decision: 'accept' }, 1: { decision: 'accept_edited', final_value: '1820' } } };
  const done = await (await call('POST', `admin/submissions/${sub.id}/review`, ed, { decisions }, store)).json();
  assert.equal(done.submission.status, 'approved');
  assert.equal(done.submission.review.reviewer, 'editor');
  assert.equal(done.submission.review.reviewer_id, 'gh-999');
  assert.equal((await call('PUT', 'submissions/' + sub.id, anne, clone(VALID), store)).status, 409, 'decided submissions are closed');

  const stats = await (await call('GET', 'stats', anne, undefined, store)).json();
  assert.equal(stats.approved, 1);
  assert.equal(stats.me.approved_submissions, 1);
  assert.equal(stats.contributors.length, 1);                              // public_credit is true in the fixture

  const dump = await (await call('GET', 'admin/export?format=json', ed, undefined, store)).json();
  assert.equal(dump.schema, 'hca-crowd-export/1');
  assert.equal(dump.submissions[0].history.length >= 3, true);
  assert.equal((await call('GET', 'admin/export?format=xlsx', ed, undefined, store)).status, 501);
  assert.equal((await call('GET', 'admin/export?format=json', anne, undefined, store)).status, 403);
});

test('invalid submissions are rejected with the validation errors; oversized bodies and bad ids too', async () => {
  const store = new MemoryStore();
  const anne = (await login({ id: 1, login: 'anne', name: 'Anne' }, ENV, store)).token;
  const bad = clone(VALID); bad.person_id = 'abc';
  const r = await call('POST', 'submissions', anne, bad, store);
  assert.equal(r.status, 422);
  assert.deepEqual((await r.json()).errors.map((e) => e.code), ['invalid_person_id']);
  const big = clone(VALID); big.comment = 'x'.repeat(300 * 1024);
  assert.equal((await call('POST', 'submissions', anne, big, store)).status, 413);
  assert.equal((await call('PUT', 'submissions/../../etc', anne, clone(VALID), store)).status, 404);
  assert.equal((await call('GET', 'admin/submissions/CS-1', anne, undefined, store)).status, 403);
});

test('a contributor with 30 open submissions is stopped', async () => {
  const store = new MemoryStore();
  const anne = (await login({ id: 1, login: 'anne', name: 'Anne' }, ENV, store)).token;
  for (let i = 0; i < 30; i++) assert.equal((await call('POST', 'submissions', anne, clone(VALID), store)).status, 201);
  assert.equal((await call('POST', 'submissions', anne, clone(VALID), store)).status, 429);
});

/* ── CORS ───────────────────────────────────────────────────────────────── */
test('CORS: only the configured origins get Access-Control-Allow-Origin; preflight answers 204', async () => {
  const pre = await handle(new Request(WORKER + '/api/crowd/mine', { method: 'OPTIONS', headers: { Origin: ORIGIN } }), ENV, {});
  assert.equal(pre.status, 204);
  assert.equal(pre.headers.get('Access-Control-Allow-Origin'), ORIGIN);
  assert.match(pre.headers.get('Access-Control-Allow-Headers'), /Authorization/);
  const evil = await handle(new Request(WORKER + '/api/crowd/health', { headers: { Origin: 'https://evil.example' } }), ENV, {});
  assert.equal(evil.headers.get('Access-Control-Allow-Origin'), null);
  const ok = await handle(new Request(WORKER + '/api/crowd/health', { headers: { Origin: ORIGIN } }), ENV, {});
  assert.deepEqual(await ok.json(), { ok: true, mode: 'api', auth: 'github', schema: 'hca-crowd-submission/1' });
});

/* ── GitHub storage ─────────────────────────────────────────────────────── */
function fakeGithub() {
  const files = new Map(); let n = 0; const log = [];
  const f = async (url, init) => {
    url = String(url); log.push({ url, method: init.method, body: init.body ? JSON.parse(init.body) : null, auth: init.headers.Authorization });
    if (url.endsWith('/graphql')) {
      const tree = (dir) => ({ entries: [...files].filter(([p]) => p.startsWith(dir + '/')).map(([p, v]) => ({ name: p.slice(dir.length + 1), oid: v.sha, object: { text: v.text, isTruncated: false } })) });
      return new Response(JSON.stringify({ data: { repository: { subs: tree('submissions'), cons: tree('contributors') } } }));
    }
    const m = /\/contents\/(.+?)(\?|$)/.exec(url);
    const path = decodeURIComponent(m[1]);
    if (init.method === 'GET') {
      const v = files.get(path);
      return v ? new Response(JSON.stringify({ sha: v.sha, content: Buffer.from(v.text).toString('base64') })) : new Response('{}', { status: 404 });
    }
    const b = JSON.parse(init.body), cur = files.get(path);
    if ((cur ? cur.sha : undefined) !== b.sha) return new Response('{}', { status: cur ? 409 : 422 });
    const v = { sha: 'sha' + (++n), text: Buffer.from(b.content, 'base64').toString('utf8') };
    files.set(path, v);
    return new Response(JSON.stringify({ content: { sha: v.sha } }), { status: cur ? 200 : 201 });
  };
  return { f, files, log };
}

test('GithubStore: create, list via GraphQL, update with the blob sha, stale sha → conflict, UTF-8 survives', async () => {
  const gh = fakeGithub();
  const store = new GithubStore({ token: 'tkn', repo: 'org/data', branch: 'main', fetchImpl: gh.f });
  const sub = { id: 'CS-20261029-abcdef', status: 'submitted', contributor: { id: 'gh-1' }, comment: 'Sønderjylland — æøå' };
  const v1 = await store.saveSubmission(sub, null);
  assert.equal(gh.log[0].method, 'PUT');
  assert.equal(gh.log[0].body.sha, undefined);
  assert.equal(gh.log[0].auth, 'Bearer tkn');
  assert.match(gh.log[0].body.message, /create CS-20261029-abcdef/);
  await assert.rejects(store.saveSubmission(sub, null), { name: 'ConflictError' });      // create over existing
  const listed = await store.listSubmissions();
  assert.equal(listed.length, 1);
  assert.equal(listed[0].data.comment, 'Sønderjylland — æøå');
  assert.equal(listed[0].version, v1);
  const gq = gh.log.find((l) => l.url.endsWith('/graphql'));
  assert.deepEqual([gq.body.variables.subs, gq.body.variables.cons], ['main:submissions', 'main:contributors']);
  const v2 = await store.saveSubmission({ ...sub, status: 'approved' }, v1);
  assert.notEqual(v2, v1);
  await assert.rejects(store.saveSubmission({ ...sub, status: 'rejected' }, v1), { name: 'ConflictError' });   // stale
  assert.equal((await store.getSubmission(sub.id)).data.status, 'approved');
  assert.equal(await store.getSubmission('CS-20261029-000000'), null);
});

test('GithubStore: the service retries a conflicting write against fresh data', async () => {
  const gh = fakeGithub();
  const store = new GithubStore({ token: 'tkn', repo: 'org/data', fetchImpl: gh.f });
  const anne = (await login({ id: 1, login: 'anne', name: 'Anne' }, ENV, store)).token;
  const ed = (await login({ id: 999, login: 'ed', name: 'Ed' }, ENV, store)).token;
  const sid = (await (await call('POST', 'submissions', anne, clone(VALID), store)).json()).submission.id;
  // Someone else writes between the editor's read and write: bump the file once, behind the service's back.
  const orig = store.saveSubmission.bind(store); let bumped = false;
  store.saveSubmission = async (data, version) => {
    if (!bumped) { bumped = true; const cur = await store.getSubmission(sid); await orig({ ...cur.data, updated: 'x' }, cur.version); }
    return orig(data, version);
  };
  const r = await call('POST', `admin/submissions/${sid}/review`, ed, { action: 'request_changes', note: 'Uddyb kilden' }, store);
  assert.equal(r.status, 200);
  assert.equal((await store.getSubmission(sid)).data.status, 'needs_changes');
});

test('GithubStore refuses to start without a token and a well-formed repo', () => {
  assert.throws(() => new GithubStore({ token: '', repo: 'a/b' }));
  assert.throws(() => new GithubStore({ token: 't', repo: '../etc' }));
});
