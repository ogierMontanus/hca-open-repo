/* Storage contract used by service.js — and an in-memory implementation for
 * tests and `wrangler dev` without a data repository.
 *
 *   listSubmissions()              → [{data, version}]
 *   getSubmission(id)              → {data, version} | null
 *   saveSubmission(data, version)  → new version; version null = create.
 *                                    Throws ConflictError if it changed meanwhile.
 *   listContributors()             → [{data, version}]
 *   getContributor(id)             → {data, version} | null
 *   saveContributor(data, version) → new version
 */
export class ConflictError extends Error {
  constructor(msg = 'The record changed while it was being saved') { super(msg); this.name = 'ConflictError'; }
}

export class MemoryStore {
  constructor() { this.subs = new Map(); this.cons = new Map(); this.n = 0; }

  _list(m) { return [...m.values()].map((r) => ({ data: structuredClone(r.data), version: r.version })); }
  _get(m, id) { const r = m.get(id); return r ? { data: structuredClone(r.data), version: r.version } : null; }
  _save(m, data, version) {
    const cur = m.get(data.id);
    if ((cur ? cur.version : null) !== (version || null)) throw new ConflictError();
    const v = 'v' + (++this.n);
    m.set(data.id, { data: structuredClone(data), version: v });
    return v;
  }

  async listSubmissions() { return this._list(this.subs); }
  async getSubmission(id) { return this._get(this.subs, id); }
  async saveSubmission(data, version) { return this._save(this.subs, data, version); }
  async listContributors() { return this._list(this.cons); }
  async getContributor(id) { return this._get(this.cons, id); }
  async saveContributor(data, version) { return this._save(this.cons, data, version); }
}
