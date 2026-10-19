// Run with:  node --test workers/report-issue/
import test from 'node:test';
import assert from 'node:assert/strict';
import worker, { validate, buildIssueBody } from './worker.js';

const ORIGIN = 'https://ogiermontanus.github.io';
const ENV = { GITHUB_TOKEN: 'ghp_test' };

// 1x1 PNG
const PNG = 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==';

const good = () => ({
  name: 'Anna Jensen',
  email: 'anna@example.dk',
  title: 'Kortet viser forkert sted',
  description: 'Odense ligger i Jylland på kortet.',
  pageUrl: 'https://ogiermontanus.github.io/hca-open-repo/mockup/kort.html',
  userAgent: 'Mozilla/5.0',
  viewport: '1280x720',
  lang: 'da',
});

function post(body, headers = {}) {
  return new Request('https://worker.test/', {
    method: 'POST',
    headers: { Origin: ORIGIN, 'Content-Type': 'application/json', ...headers },
    body: typeof body === 'string' ? body : JSON.stringify(body),
  });
}

/** Replace global fetch with a recorder that answers like GitHub. */
function mockGithub(handler) {
  const calls = [];
  const original = globalThis.fetch;
  globalThis.fetch = async (url, init = {}) => {
    const call = { url: String(url), method: init.method, body: init.body ? JSON.parse(init.body) : null };
    calls.push(call);
    const r = handler(call);
    return new Response(JSON.stringify(r.body ?? {}), { status: r.status ?? 200 });
  };
  return { calls, restore: () => { globalThis.fetch = original; } };
}

test('validate: accepts a good report', () => {
  const r = validate(good());
  assert.equal(r.name, 'Anna Jensen');
  assert.equal(r.screenshot, null);
});

test('validate: rejects missing name, bad email, short description', () => {
  assert.throws(() => validate({ ...good(), name: '  ' }), { code: 'invalid_name' });
  assert.throws(() => validate({ ...good(), email: 'not-an-email' }), { code: 'invalid_email' });
  assert.throws(() => validate({ ...good(), email: 'a b@c.dk' }), { code: 'invalid_email' });
  assert.throws(() => validate({ ...good(), description: 'kort' }), { code: 'invalid_description' });
});

test('validate: screenshot must really be the declared image type', () => {
  assert.equal(validate({ ...good(), screenshot: { type: 'image/png', data: PNG } }).screenshot.ext, 'png');
  assert.throws(() => validate({ ...good(), screenshot: { type: 'image/jpeg', data: PNG } }), { code: 'invalid_screenshot' });
  assert.throws(() => validate({ ...good(), screenshot: { type: 'image/svg+xml', data: PNG } }), { code: 'invalid_screenshot' });
  assert.throws(() => validate({ ...good(), screenshot: { type: 'image/png', data: 'not base64!' } }), { code: 'invalid_screenshot' });
});

test('buildIssueBody: defangs @mentions and markdown in user text', () => {
  const r = validate({ ...good(), name: 'Eve *bold* @octocat', description: 'ping @octocat and <script>' });
  const body = buildIssueBody(r, null, new Date('2026-10-19T12:00:00Z'));
  assert.ok(!body.includes('@octocat'), 'raw mention must not survive');
  assert.ok(body.includes('Eve \\*bold\\*'));
  assert.ok(body.includes('`anna@example.dk`'));
  assert.ok(body.includes('2026-10-19T12:00:00.000Z'));
});

test('POST without screenshot creates one labelled issue', async () => {
  const gh = mockGithub(() => ({ status: 201, body: { number: 42, html_url: 'https://github.com/o/r/issues/42' } }));
  try {
    const res = await worker.fetch(post(good()), ENV);
    assert.equal(res.status, 201);
    assert.deepEqual(await res.json(), { ok: true, number: 42, url: 'https://github.com/o/r/issues/42', screenshot: true });
    assert.equal(res.headers.get('Access-Control-Allow-Origin'), ORIGIN);
    assert.equal(gh.calls.length, 1);
    assert.match(gh.calls[0].url, /\/repos\/ogierMontanus\/hca-open-repo\/issues$/);
    assert.equal(gh.calls[0].body.title, '[Fejlrapport] Kortet viser forkert sted');
    assert.deepEqual(gh.calls[0].body.labels, ['brugerrapport']);
  } finally { gh.restore(); }
});

test('POST with screenshot commits it to the branch and links it in the issue', async () => {
  const gh = mockGithub((c) => {
    if (c.method === 'GET' && /git\/ref\/heads\/report-screenshots/.test(c.url)) return { status: 404 };
    if (c.method === 'GET' && /git\/ref\/heads\/main/.test(c.url)) return { body: { object: { sha: 'abc123' } } };
    if (c.method === 'GET') return { body: { default_branch: 'main' } };
    if (c.method === 'POST' && /git\/refs$/.test(c.url)) return { status: 201 };
    if (c.method === 'PUT') return { status: 201, body: { content: { download_url: 'https://raw.githubusercontent.com/o/r/report-screenshots/x.png' } } };
    return { status: 201, body: { number: 7, html_url: 'https://github.com/o/r/issues/7' } };
  });
  try {
    const res = await worker.fetch(post({ ...good(), screenshot: { type: 'image/png', data: PNG } }), ENV);
    assert.equal(res.status, 201);
    const put = gh.calls.find((c) => c.method === 'PUT');
    assert.equal(put.body.branch, 'report-screenshots');
    assert.equal(put.body.content, PNG);
    assert.match(put.url, /contents\/screenshots\/\d{4}\/\d{2}\/\d{14}-[0-9a-f]{8}\.png$/);
    const issue = gh.calls.at(-1);
    assert.ok(issue.body.body.includes('![Skærmbillede fra brugeren](https://raw.githubusercontent.com/o/r/report-screenshots/x.png)'));
    assert.deepEqual(gh.calls.find((c) => /git\/refs$/.test(c.url)).body, { ref: 'refs/heads/report-screenshots', sha: 'abc123' });
  } finally { gh.restore(); }
});

test('screenshot upload failure still files the issue and says so', async () => {
  const gh = mockGithub((c) => {
    if (c.url.includes('/git/ref/')) return { body: {} };
    if (c.method === 'PUT') return { status: 500 };
    return { status: 201, body: { number: 8, html_url: 'u' } };
  });
  try {
    const res = await worker.fetch(post({ ...good(), screenshot: { type: 'image/png', data: PNG } }), ENV);
    const out = await res.json();
    assert.equal(res.status, 201);
    assert.equal(out.screenshot, false);
    assert.ok(gh.calls.at(-1).body.body.includes('kunne ikke gemmes'));
  } finally { gh.restore(); }
});

test('rejects foreign origins and missing origin without touching GitHub', async () => {
  const gh = mockGithub(() => ({ status: 201, body: {} }));
  try {
    for (const origin of ['https://evil.example', undefined]) {
      const req = new Request('https://worker.test/', { method: 'POST', headers: origin ? { Origin: origin } : {}, body: JSON.stringify(good()) });
      const res = await worker.fetch(req, ENV);
      assert.equal(res.status, 403);
      assert.equal(res.headers.get('Access-Control-Allow-Origin'), null);
    }
    assert.equal(gh.calls.length, 0);
  } finally { gh.restore(); }
});

test('honeypot is answered with success but files nothing', async () => {
  const gh = mockGithub(() => ({ status: 201, body: {} }));
  try {
    const res = await worker.fetch(post({ ...good(), website: 'http://spam.example' }), ENV);
    assert.equal(res.status, 200);
    assert.equal(gh.calls.length, 0);
  } finally { gh.restore(); }
});

test('validation errors are 400 with a code; bad JSON too; GET is 405', async () => {
  const gh = mockGithub(() => ({ status: 201, body: {} }));
  try {
    let res = await worker.fetch(post({ ...good(), email: 'x' }), ENV);
    assert.equal(res.status, 400);
    assert.equal((await res.json()).error, 'invalid_email');
    res = await worker.fetch(post('{nope'), ENV);
    assert.equal(res.status, 400);
    res = await worker.fetch(new Request('https://worker.test/'), ENV);
    assert.equal(res.status, 405);
    assert.equal(gh.calls.length, 0);
  } finally { gh.restore(); }
});

test('preflight answers for the allowed origin; GitHub failure maps to 502', async () => {
  let res = await worker.fetch(new Request('https://worker.test/', { method: 'OPTIONS', headers: { Origin: ORIGIN } }), ENV);
  assert.equal(res.status, 204);
  assert.equal(res.headers.get('Access-Control-Allow-Origin'), ORIGIN);

  const gh = mockGithub(() => ({ status: 403, body: { message: 'secret detail' } }));
  try {
    res = await worker.fetch(post(good()), ENV);
    assert.equal(res.status, 502);
    assert.ok(!(await res.text()).includes('secret detail'), 'GitHub error text must not leak');
  } finally { gh.restore(); }
});

test('missing token is reported as not_configured', async () => {
  const res = await worker.fetch(post(good()), {});
  assert.equal(res.status, 500);
  assert.equal((await res.json()).error, 'not_configured');
});
