/* hca-crowd-api — GitHub OAuth proxy + the /api/crowd/ API of the crowd pages.
 *
 * Login (the static pages cannot hold the OAuth client secret, hence this Worker):
 *
 *   page ──► GET /auth/login?return=<page url>
 *            signed state + nonce cookie ──► github.com/login/oauth/authorize
 *   github ─► GET /auth/callback?code&state
 *            state + cookie checked, code → token → GET /user (token is then
 *            discarded; nothing of GitHub's is kept), our own session minted
 *   ──► 302 <page url>#hca_session=<token>      (fragment: never sent to a server or logged)
 *
 * API calls then carry `Authorization: Bearer <session>`. See README.md.
 */
import { sign, verify, randomId, parseCookies, isAdmin, allowedOrigins, safeReturn } from './auth.js';
import { CrowdService, HttpError } from './service.js';
import { MemoryStore } from './store-memory.js';
import { GithubStore } from './store-github.js';

const SESSION_TTL = 7 * 24 * 3600;
const STATE_TTL = 600;
const MAX_BODY = 256 * 1024;                       // no attachments through this API
const SID = '(CS-\\d{8}-[0-9a-f]{6})';

let memoryStore;                                   // dev fallback, one per isolate

function makeStore(env, deps) {
  if (deps.store) return deps.store;
  if (env.DATA_REPO) return new GithubStore({ token: env.DATA_TOKEN, repo: env.DATA_REPO, branch: env.DATA_BRANCH || 'main', fetchImpl: deps.fetch });
  return (memoryStore = memoryStore || new MemoryStore());
}

function cors(request, env) {
  const origin = request.headers.get('Origin');
  if (!origin || !allowedOrigins(env).includes(origin)) return {};
  return {
    'Access-Control-Allow-Origin': origin, Vary: 'Origin',
    'Access-Control-Allow-Methods': 'GET, POST, PUT, OPTIONS',
    'Access-Control-Allow-Headers': 'Authorization, Content-Type', 'Access-Control-Max-Age': '600'
  };
}

function json(obj, status, headers) {
  return new Response(JSON.stringify(obj), {
    status: status || 200,
    headers: { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff', ...headers }
  });
}

function redirect(url, extra) {
  return new Response(null, { status: 302, headers: { Location: url, 'Cache-Control': 'no-store', 'Referrer-Policy': 'no-referrer', ...extra } });
}

function text(status, msg) {
  return new Response(msg, { status, headers: { 'Content-Type': 'text/plain; charset=utf-8', 'Cache-Control': 'no-store' } });
}

/* ── login ──────────────────────────────────────────────────────────────── */
async function login(request, env) {
  if (!env.GITHUB_CLIENT_ID || !env.SESSION_SECRET) return text(500, 'Login is not configured on this server.');
  const url = new URL(request.url);
  const ret = safeReturn(url.searchParams.get('return'), env);
  if (!ret) return text(400, 'return must be a page of this site.');
  const nonce = randomId();
  const exp = Math.floor(Date.now() / 1000) + STATE_TTL;
  const state = await sign({ k: 'state', n: nonce, r: ret, exp }, env.SESSION_SECRET);
  const gh = new URL('https://github.com/login/oauth/authorize');
  gh.searchParams.set('client_id', env.GITHUB_CLIENT_ID);
  gh.searchParams.set('redirect_uri', url.origin + '/auth/callback');
  gh.searchParams.set('state', state);
  gh.searchParams.set('allow_signup', 'true');          // no scope: public profile only
  return redirect(gh.toString(), {
    'Set-Cookie': `hca_oauth=${nonce}; Max-Age=${STATE_TTL}; Path=/auth; HttpOnly; Secure; SameSite=Lax`
  });
}

async function callback(request, env, deps) {
  const url = new URL(request.url);
  const clear = 'hca_oauth=; Max-Age=0; Path=/auth; HttpOnly; Secure; SameSite=Lax';
  const st = await verify(url.searchParams.get('state'), env.SESSION_SECRET, 'state');
  const cookie = parseCookies(request.headers.get('Cookie')).hca_oauth;
  if (!st || !cookie || cookie !== st.n) return new Response('Login failed: the sign-in link has expired or was opened in another browser. Start again from the site.', { status: 400, headers: { 'Set-Cookie': clear, 'Content-Type': 'text/plain; charset=utf-8' } });
  const back = (frag) => redirect(st.r + '#' + frag, { 'Set-Cookie': clear });

  const code = url.searchParams.get('code');
  if (url.searchParams.get('error') || !code) return back('hca_error=denied');

  const f = deps.fetch || ((...a) => fetch(...a));
  try {
    const tr = await f('https://github.com/login/oauth/access_token', {
      method: 'POST', headers: { Accept: 'application/json', 'Content-Type': 'application/json', 'User-Agent': 'hca-crowd-api' },
      body: JSON.stringify({ client_id: env.GITHUB_CLIENT_ID, client_secret: env.GITHUB_CLIENT_SECRET, code, redirect_uri: url.origin + '/auth/callback' })
    });
    const tj = await tr.json();
    if (!tj.access_token) return back('hca_error=exchange');
    const ur = await f('https://api.github.com/user', {
      headers: { Authorization: 'Bearer ' + tj.access_token, Accept: 'application/vnd.github+json', 'User-Agent': 'hca-crowd-api' }
    });
    const u = await ur.json();
    if (!ur.ok || !u.id || !u.login) return back('hca_error=profile');
    const iat = Math.floor(Date.now() / 1000);
    const session = await sign({ k: 'session', v: 1, sub: 'gh-' + u.id, login: u.login, name: u.name || u.login, iat, exp: iat + SESSION_TTL }, env.SESSION_SECRET);
    return back('hca_session=' + session);
  } catch (e) {
    return back('hca_error=exchange');
  }
}

/* ── API ────────────────────────────────────────────────────────────────── */
async function currentUser(request, env) {
  const h = request.headers.get('Authorization') || '';
  if (!/^bearer /i.test(h)) return null;
  const s = await verify(h.slice(7).trim(), env.SESSION_SECRET, 'session');
  if (!s || !/^gh-\d+$/.test(s.sub)) return null;
  const user = { id: s.sub, login: String(s.login), name: String(s.name || s.login) };
  user.admin = isAdmin(user, env.ADMINS);              // role from current settings, not from the token
  return user;
}

async function body(request) {
  const raw = await request.text();
  if (raw.length > MAX_BODY) throw new HttpError(413, 'too_large', 'Bidraget er for stort.');
  try { return raw ? JSON.parse(raw) : {}; } catch (e) { throw new HttpError(400, 'bad_request', 'Forventede JSON.'); }
}

async function api(request, env, deps, route, q) {
  const svc = new CrowdService(makeStore(env, deps));
  const m = request.method;
  if (m === 'GET' && route === 'health') return svc.health();
  const user = await currentUser(request, env);
  if (m === 'GET' && route === 'me') return svc.me(user);
  if (m === 'GET' && route === 'stats') return svc.stats(user);
  if (m === 'GET' && route === 'mine') return user ? svc.mine(user) : { submissions: [], me: null };
  if (m === 'POST' && route === 'submissions') return [await svc.create(user, await body(request)), 201];
  let r = new RegExp('^submissions/' + SID + '$').exec(route);
  if (r && m === 'PUT') return svc.update(user, r[1], await body(request));
  r = new RegExp('^submissions/' + SID + '/withdraw$').exec(route);
  if (r && m === 'POST') return svc.withdraw(user, r[1]);

  if (route.startsWith('admin/')) {
    svc._requireAdmin(user);                           // before routing: unknown admin routes leak nothing either
    const sub = route.slice(6);
    if (m === 'GET' && sub === 'submissions') return svc.adminList(user, q);
    r = new RegExp('^submissions/' + SID + '$').exec(sub);
    if (r && m === 'GET') return svc.adminGet(user, r[1]);
    r = new RegExp('^submissions/' + SID + '/review$').exec(sub);
    if (r && m === 'POST') return svc.review(user, r[1], await body(request));
    if (m === 'GET' && sub === 'contributors') return svc.contributors(user);
    if (m === 'GET' && sub === 'export') {
      if ((q.format || 'json') !== 'json') throw new HttpError(501, 'format', 'Hent JSON og kør export_approved.py --import-json (TSV/Excel bygges lokalt).');
      return svc.dump(user);
    }
  }
  throw new HttpError(404, 'not_found', 'Ukendt rute.');
}

export async function handle(request, env, deps = {}) {
  const url = new URL(request.url);
  const headers = cors(request, env);
  if (request.method === 'OPTIONS') return new Response(null, { status: 204, headers });
  try {
    if (url.pathname === '/auth/login' && request.method === 'GET') return await login(request, env);
    if (url.pathname === '/auth/callback' && request.method === 'GET') return await callback(request, env, deps);
    if (url.pathname.startsWith('/api/crowd/')) {
      const route = url.pathname.slice('/api/crowd/'.length).replace(/\/+$/, '');
      const q = Object.fromEntries(url.searchParams);
      const out = await api(request, env, deps, route, q);
      return Array.isArray(out) ? json(out[0], out[1], headers) : json(out, 200, headers);
    }
    return json({ error: 'not_found', message: 'Ukendt rute.' }, 404, headers);
  } catch (e) {
    if (e instanceof HttpError) return json({ error: e.code, message: e.message, ...e.extra }, e.status, headers);
    console.error('crowd api error', e && e.message);
    return json({ error: 'server_error', message: 'Uventet serverfejl.' }, 500, headers);
  }
}

export default { fetch: (request, env) => handle(request, env) };
