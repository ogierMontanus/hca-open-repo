/* auth.js — signed tokens (sessions and OAuth state) with WebCrypto.
 *
 * Token = base64url(JSON payload) + "." + base64url(HMAC-SHA256). The secret
 * lives only in the Worker. The payload is readable by anyone who holds the
 * token (it is only signed), so it carries nothing private: id, login, name,
 * expiry. The *role* is deliberately not in it — it is derived from the
 * ADMINS setting on every request, so removing an editor takes effect at once.
 */
const enc = new TextEncoder();
const dec = new TextDecoder();

export function b64urlEncode(bytes) {
  let s = '';
  for (let i = 0; i < bytes.length; i += 0x8000) s += String.fromCharCode.apply(null, bytes.subarray(i, i + 0x8000));
  return btoa(s).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}

export function b64urlDecode(str) {
  const b = atob(String(str).replace(/-/g, '+').replace(/_/g, '/'));
  const out = new Uint8Array(b.length);
  for (let i = 0; i < b.length; i++) out[i] = b.charCodeAt(i);
  return out;
}

function key(secret, usage) {
  return crypto.subtle.importKey('raw', enc.encode(secret), { name: 'HMAC', hash: 'SHA-256' }, false, usage);
}

export async function sign(payload, secret) {
  if (!secret || secret.length < 32) throw new Error('SESSION_SECRET must be at least 32 characters');
  const body = b64urlEncode(enc.encode(JSON.stringify(payload)));
  const mac = await crypto.subtle.sign('HMAC', await key(secret, ['sign']), enc.encode(body));
  return body + '.' + b64urlEncode(new Uint8Array(mac));
}

/** → payload, or null if malformed / forged / expired. `kind` must match. */
export async function verify(token, secret, kind, nowSec = Math.floor(Date.now() / 1000)) {
  if (typeof token !== 'string' || !secret || secret.length < 32) return null;
  const parts = token.split('.');
  if (parts.length !== 2 || !parts[0] || !parts[1]) return null;
  let ok = false, payload;
  try {
    ok = await crypto.subtle.verify('HMAC', await key(secret, ['verify']), b64urlDecode(parts[1]), enc.encode(parts[0]));
    payload = JSON.parse(dec.decode(b64urlDecode(parts[0])));
  } catch (e) { return null; }
  if (!ok || !payload || typeof payload !== 'object') return null;
  if (payload.k !== kind) return null;               // a state token can never be used as a session
  if (typeof payload.exp !== 'number' || payload.exp <= nowSec) return null;
  return payload;
}

export function randomId(bytes = 16) {
  return b64urlEncode(crypto.getRandomValues(new Uint8Array(bytes)));
}

export function parseCookies(header) {
  const out = {};
  String(header || '').split(';').forEach((p) => {
    const i = p.indexOf('=');
    if (i > 0) out[p.slice(0, i).trim()] = p.slice(i + 1).trim();
  });
  return out;
}

/** Administrators: numeric GitHub ids (`123456`, `gh-123456`) or logins. */
export function isAdmin(user, adminsSetting) {
  const list = String(adminsSetting || '').split(',')
    .map((x) => x.trim().replace(/^@/, '').toLowerCase()).filter(Boolean);
  const id = String(user.id || '').replace(/^gh-/, '');
  return list.includes(id) || list.includes(String(user.login || '').toLowerCase());
}

export function allowedOrigins(env) {
  return String(env.ALLOWED_ORIGINS || '').split(',').map((s) => s.trim().replace(/\/+$/, '')).filter(Boolean);
}

/** Where a finished login may send the browser: an allowed origin, under the
 * configured path prefix. Anything else → null (no open redirect). */
export function safeReturn(raw, env) {
  let u;
  try { u = new URL(raw); } catch (e) { return null; }
  if (u.protocol !== 'https:' && u.protocol !== 'http:') return null;
  if (!allowedOrigins(env).includes(u.origin)) return null;
  if (!u.pathname.startsWith(env.RETURN_PATH_PREFIX || '/')) return null;
  u.hash = '';
  return u.toString();
}
