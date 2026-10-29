/* service.js — what the API does, independent of HTTP and of where files live.
 * Mirrors scripts/crowdsource/store.py + server.py (docs/crowdsourcing.md §5, §8),
 * with identity from a GitHub login instead of a per-browser token.
 *
 * `user` = {id: "gh-<number>", login, name, admin}; set by index.js from a
 * verified session. Contributors may only touch their own submissions; the
 * `admin*` methods and review are refused for anyone else.
 */
import { taxonomy as T, Validate, Store } from './rules.js';
import { ConflictError } from './store-memory.js';

const ID_RE = /^CS-\d{8}-[0-9a-f]{6}$/;
const MAX_OPEN_PER_USER = 30;
const OPEN = ['submitted', 'needs_changes'];

export class HttpError extends Error {
  constructor(status, code, message, extra) {
    super(message); this.status = status; this.code = code; this.extra = extra || {};
  }
}

const now = () => new Date().toISOString().replace(/\.\d+Z$/, 'Z');
const str = (v, max) => (typeof v === 'string' ? v : '').slice(0, max);
const hex = (n) => [...crypto.getRandomValues(new Uint8Array(n))].map((b) => b.toString(16).padStart(2, '0')).join('');

async function retry(fn, tries = 4) {
  for (let i = 0; ; i++) {
    try { return await fn(); } catch (e) {
      if (!(e instanceof ConflictError)) throw e;
      if (i >= tries - 1) throw new HttpError(409, 'conflict', 'Posten blev ændret samtidigt — prøv igen.');
    }
  }
}

/** What a contributor may see of a submission (store.py public_view). */
export function publicView(sub) {
  const out = {};
  Object.keys(sub).forEach((k) => { if (k !== 'history' && k !== 'register_snapshot') out[k] = sub[k]; });
  if (sub.review) {
    out.review = {};
    Object.keys(sub.review).forEach((k) => { if (k !== 'reviewer_id') out.review[k] = sub.review[k]; });
  }
  return out;
}

function cleanContext(c) {
  c = c && typeof c === 'object' ? c : {};
  const levels = T.levels.map((l) => l.key), gaps = T.gaps.map((g) => g.key);
  return {
    label: str(c.label, 300), description: str(c.description, 1000), area: str(c.area, 80), doubt: c.doubt === true,
    level: levels.includes(c.level) ? c.level : '', gaps: Array.isArray(c.gaps) ? c.gaps.filter((g) => gaps.includes(g)).slice(0, 20) : []
  };
}

export class CrowdService {
  constructor(store) { this.store = store; }

  _requireAdmin(user) {
    if (!user) throw new HttpError(401, 'login_required', 'Log ind for at fortsætte.');
    if (!user.admin) throw new HttpError(403, 'admin_required', 'Din konto er ikke redaktør.');
  }
  _requireUser(user) {
    if (!user) throw new HttpError(401, 'login_required', 'Log ind for at fortsætte.');
  }
  _id(sid) {
    if (!ID_RE.test(sid || '')) throw new HttpError(404, 'not_found', 'Findes ikke.');
    return sid;
  }
  async _load(sid) {
    const rec = await this.store.getSubmission(this._id(sid));
    if (!rec) throw new HttpError(404, 'not_found', 'Findes ikke.');
    return rec;
  }
  async _all() { return (await this.store.listSubmissions()).map((r) => r.data); }

  /* ── public ───────────────────────────────────────────────────────────── */
  health() { return { ok: true, mode: 'api', auth: 'github', schema: T.schema }; }

  async me(user) {
    this._requireUser(user);
    return { id: user.id, login: user.login, name: user.name, role: user.admin ? 'admin' : 'contributor' };
  }

  async stats(user) {
    const subs = (await this._all()).filter((s) => s.status !== 'withdrawn');
    const profiles = new Map((await this.store.listContributors()).map((r) => [r.data.id, r.data]));
    const rows = Store._computeStats(subs).map((c) => ({
      ...c, affiliation: (profiles.get(c.id) || {}).affiliation || '', expertise: (profiles.get(c.id) || {}).expertise || ''
    }));
    return {
      submissions: subs.length,
      pending: subs.filter((s) => OPEN.includes(s.status)).length,
      approved: subs.filter((s) => ['approved', 'partially_approved'].includes(s.status)).length,
      persons: new Set(subs.map((s) => s.person_id)).size,
      contributors: rows.filter((c) => c.public_credit && c.approved_submissions).map(({ expertise, ...c }) => c),
      me: (user && rows.find((c) => c.id === user.id)) || null,
      personStatus: Store._personStatus(subs)
    };
  }

  /* ── contributor ──────────────────────────────────────────────────────── */
  async mine(user) {
    this._requireUser(user);
    const all = await this._all();
    const me = Store._computeStats(all.filter((s) => s.status !== 'withdrawn')).find((c) => c.id === user.id) || null;
    return { submissions: all.filter((s) => s.contributor.id === user.id).map(publicView), me };
  }

  _validated(payload) {
    const errors = Validate.validate(payload, T);
    if (errors.length) throw new HttpError(422, 'invalid', 'Bidraget har fejl.', { errors });
  }

  async _saveProfile(user, c) {
    await retry(async () => {
      const cur = await this.store.getContributor(user.id);
      const data = {
        ...(cur ? cur.data : { created: now() }), id: user.id, login: user.login, github_name: user.name || '',
        name: Validate.normalise(c.name), contact: Validate.normalise(c.contact), affiliation: Validate.normalise(c.affiliation),
        expertise: Validate.normalise(c.expertise), public_credit: !!c.public_credit, updated: now()
      };
      await this.store.saveContributor(data, cur ? cur.version : null);
    });
  }

  async create(user, payload) {
    this._requireUser(user);
    this._validated(payload);
    const all = await this._all();
    if (all.filter((s) => s.contributor.id === user.id && OPEN.includes(s.status)).length >= MAX_OPEN_PER_USER) {
      throw new HttpError(429, 'too_many_open', `Du har ${MAX_OPEN_PER_USER} åbne bidrag. Vent på gennemgang, før du sender flere.`);
    }
    await this._saveProfile(user, payload.contributor);
    const core = Store._buildCore(payload);
    const sub = {
      ...core,
      id: 'CS-' + now().slice(0, 10).replace(/-/g, '') + '-' + hex(3),
      register_snapshot: cleanContext(payload.context),
      contributor: { id: user.id, name: Validate.normalise(payload.contributor.name), public_credit: !!payload.contributor.public_credit },
      status: 'submitted', revision: 1, created: now(), updated: now(),
      history: [{ ts: now(), actor: user.id, action: 'submitted' }], review: null, incorporated: null
    };
    await this.store.saveSubmission(sub, null);
    return { submission: publicView(sub) };
  }

  async update(user, sid, payload) {
    this._requireUser(user);
    this._validated(payload);
    const sub = await retry(async () => {
      const { data: sub, version } = await this._load(sid);
      if (sub.contributor.id !== user.id) throw new HttpError(403, 'forbidden', 'Det er ikke dit bidrag.');
      if (!OPEN.includes(sub.status)) throw new HttpError(409, 'conflict', 'Kun åbne bidrag kan rettes.');
      const core = Store._buildCore(payload);
      sub.history.push({
        ts: now(), actor: user.id, action: 'revised', revision: sub.revision + 1,
        previous: { identification: sub.identification, overall_confidence: sub.overall_confidence, fields: sub.fields,
                    comment: sub.comment, sources: sub.sources, review: sub.review, revision: sub.revision }
      });
      ['identification', 'overall_confidence', 'fields', 'comment', 'sources', 'person_label'].forEach((k) => { sub[k] = core[k]; });
      sub.contributor = { id: user.id, name: Validate.normalise(payload.contributor.name), public_credit: !!payload.contributor.public_credit };
      sub.status = 'submitted'; sub.revision += 1; sub.updated = now(); sub.review = null;
      await this.store.saveSubmission(sub, version);
      return sub;
    });
    await this._saveProfile(user, payload.contributor);
    return { submission: publicView(sub) };
  }

  async withdraw(user, sid) {
    this._requireUser(user);
    const sub = await retry(async () => {
      const { data: sub, version } = await this._load(sid);
      if (sub.contributor.id !== user.id) throw new HttpError(403, 'forbidden', 'Det er ikke dit bidrag.');
      if (!OPEN.includes(sub.status)) throw new HttpError(409, 'conflict', 'Kun åbne bidrag kan trækkes tilbage.');
      sub.status = 'withdrawn'; sub.updated = now();
      sub.history.push({ ts: now(), actor: user.id, action: 'withdrawn' });
      await this.store.saveSubmission(sub, version);
      return sub;
    });
    return { submission: publicView(sub) };
  }

  /* ── editor ───────────────────────────────────────────────────────────── */
  async adminList(user, q) {
    this._requireAdmin(user);
    let subs = await this._all();
    if (q.status) subs = subs.filter((s) => s.status === q.status);
    if (q.person) subs = subs.filter((s) => s.person_id === q.person);
    if (q.contributor) subs = subs.filter((s) => s.contributor.id === q.contributor);
    subs.sort((a, b) => (a.created < b.created ? 1 : -1));
    return {
      submissions: subs.map((s) => ({
        id: s.id, person_id: s.person_id, person_label: s.person_label, status: s.status, created: s.created, updated: s.updated,
        revision: s.revision, contributor: s.contributor, incorporated: s.incorporated,
        identification: s.identification.status, n_fields: s.fields.length
      }))
    };
  }

  async adminGet(user, sid) {
    this._requireAdmin(user);
    const { data: sub } = await this._load(sid);
    const all = await this._all();
    const prof = await this.store.getContributor(sub.contributor.id);
    return { submission: sub, conflicts: Store._conflictsFor(sub, all), contributor: prof ? prof.data : {}, register: sub.register_snapshot || {} };
  }

  async review(user, sid, body) {
    this._requireAdmin(user);
    body = body && typeof body === 'object' ? body : {};
    const sub = await retry(async () => {
      const { data: sub, version } = await this._load(sid);
      try {
        Store._reviewSub(sub, user.login, body.decisions || {}, body.note, body.action || 'decide');
      } catch (e) {
        throw new HttpError(/^cannot review|already incorporated/.test(e.message) ? 409 : 400,
          /^cannot review|already incorporated/.test(e.message) ? 'conflict' : 'bad_request', e.message);
      }
      sub.review.reviewer_id = user.id;
      await this.store.saveSubmission(sub, version);
      return sub;
    });
    return { submission: sub };
  }

  async contributors(user) {
    this._requireAdmin(user);
    const subs = await this._all();
    const profiles = new Map((await this.store.listContributors()).map((r) => [r.data.id, r.data]));
    return {
      contributors: Store._computeStats(subs).map((c) => ({
        ...c, affiliation: (profiles.get(c.id) || {}).affiliation || '', expertise: (profiles.get(c.id) || {}).expertise || ''
      }))
    };
  }

  /** Everything, in the file format `export_approved.py --import-json` reads. */
  async dump(user) {
    this._requireAdmin(user);
    return { schema: 'hca-crowd-export/1', exported: now(), submissions: await this._all() };
  }
}
