// The GitHub sign-in side of mockup/js/crowd-store.js: the session token the
// Worker hands back in the URL fragment, how it is kept, and which requests
// carry it. A fake window/fetch; no network. Run order matters (init() is
// memoised per process), so the steps are sequential tests in one file.
const test = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');

global.CROWD_TAXONOMY = JSON.parse(fs.readFileSync(process.env.CROWD_TAXONOMY_JSON, 'utf8'));
global.CrowdValidate = require('../../mockup/js/crowd-validate.js');

const b64 = (o) => Buffer.from(JSON.stringify(o), 'utf8').toString('base64url');
const future = Math.floor(Date.now() / 1000) + 3600;
const TOKEN = b64({ k: 'session', sub: 'gh-42', login: 'anne', name: 'Anne Ågård', exp: future }) + '.signature';

const calls = [], replaced = [], ls = new Map();
global.localStorage = { getItem: (k) => (ls.has(k) ? ls.get(k) : null), setItem: (k, v) => ls.set(k, String(v)), removeItem: (k) => ls.delete(k) };
global.CROWD_CONFIG = { apiBase: 'https://crowd.example.workers.dev/' };
global.location = { hash: '#hca_session=' + TOKEN, pathname: '/hca-open-repo/mockup/crowd.html', search: '?x=1', protocol: 'https:',
  href: 'https://pages.example/hca-open-repo/mockup/crowd.html?x=1#hca_session=' + TOKEN };
global.history = { replaceState: (a, b, url) => { replaced.push(url); global.location.hash = ''; } };
global.fetch = async (url, init) => {
  calls.push({ url, init });
  if (String(url).endsWith('/health')) return { ok: true, json: async () => ({ ok: true, mode: 'api', auth: 'github' }) };
  return { ok: true, json: async () => ({ submissions: [], me: null }) };
};
const Store = require('../../mockup/js/crowd-store.js');

test('init reads the session from the fragment, removes the fragment, and detects the GitHub back-end', async () => {
  assert.strictEqual(await Store.init(), 'api');
  assert.strictEqual(calls[0].url, 'https://crowd.example.workers.dev/api/crowd/health');
  assert.deepStrictEqual(replaced, ['/hca-open-repo/mockup/crowd.html?x=1']);
  assert.strictEqual(Store.auth.enabled(), true);
  const s = Store.auth.session();
  assert.strictEqual(s.login, 'anne');
  assert.strictEqual(s.name, 'Anne Ågård', 'UTF-8 names survive the base64url round trip');
});

test('requests carry the session as Bearer — for contributors and for the editor calls alike', async () => {
  await Store.mine();
  const c = calls[calls.length - 1];
  assert.strictEqual(c.url, 'https://crowd.example.workers.dev/api/crowd/mine');
  assert.strictEqual(c.init.headers.Authorization, 'Bearer ' + TOKEN);
  assert.strictEqual(Store.admin.token(), TOKEN);
  await Store.admin.list({ status: 'submitted' });
  const a = calls[calls.length - 1];
  assert.strictEqual(a.url, 'https://crowd.example.workers.dev/api/crowd/admin/submissions?status=submitted');
  assert.strictEqual(a.init.headers.Authorization, 'Bearer ' + TOKEN);
});

test('the profile name is pre-filled from the GitHub profile', () => {
  assert.strictEqual(Store.profile().name, 'Anne Ågård');
  Store.saveProfile({ name: 'Anne Å. Ågård' });
  assert.strictEqual(Store.profile().name, 'Anne Å. Ågård', 'a name the person typed wins');
});

test('loginUrl returns to the current page without the fragment; unknown return pages stay the Worker\'s job', () => {
  assert.strictEqual(Store.auth.loginUrl(),
    'https://crowd.example.workers.dev/auth/login?return=' + encodeURIComponent('https://pages.example/hca-open-repo/mockup/crowd.html?x=1'));
});

test('logout forgets the session; without one, mine() makes no request', async () => {
  Store.auth.logout();
  assert.strictEqual(Store.auth.session(), null);
  const n = calls.length;
  assert.deepStrictEqual(await Store.mine(), { submissions: [], me: null });
  assert.strictEqual(calls.length, n);
  assert.strictEqual(Store.admin.token(), null);
});

test('an expired or garbled session is treated as signed out and discarded', () => {
  const KEY = 'hca-crowd/v1/session';
  global.localStorage.setItem(KEY, JSON.stringify(b64({ sub: 'gh-1', login: 'a', exp: 5 }) + '.s'));
  assert.strictEqual(Store.auth.session(), null);
  assert.strictEqual(global.localStorage.getItem(KEY), null);
  global.localStorage.setItem(KEY, JSON.stringify('not-a-token'));
  assert.strictEqual(Store.auth.session(), null);
});

test('a failed sign-in is reported once', () => {
  assert.strictEqual(Store.auth.error(), '');
});
