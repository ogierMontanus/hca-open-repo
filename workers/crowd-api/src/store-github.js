/* store-github.js — contributions stored as JSON files in a PRIVATE GitHub
 * repository (submissions/<id>.json, contributors/<id>.json).
 *
 * Why a repo: every change is a commit (who, when, what — the audit trail the
 * file store keeps in audit.jsonl comes for free), the files diff and can be
 * pulled into data/ with plain git, and nothing but this Worker's token can
 * write to it. Visibility is the repository's: private repo = not public, and
 * contributors never need access to it.
 *
 * Reads: one GraphQL query returns every file's text and blob id (the blob id
 * is the version used for optimistic concurrency). Writes: the Contents API
 * with the blob id as `sha`; a stale or missing sha → ConflictError, which the
 * service retries.
 */
import { ConflictError } from './store-memory.js';

const API = 'https://api.github.com';
const enc = new TextEncoder();
const dec = new TextDecoder();

function toB64(str) {
  const bytes = enc.encode(str);
  let s = '';
  for (let i = 0; i < bytes.length; i += 0x8000) s += String.fromCharCode.apply(null, bytes.subarray(i, i + 0x8000));
  return btoa(s);
}
function fromB64(b64) {
  const b = atob(String(b64).replace(/\s/g, ''));
  const out = new Uint8Array(b.length);
  for (let i = 0; i < b.length; i++) out[i] = b.charCodeAt(i);
  return dec.decode(out);
}

const QUERY = `query($owner:String!,$name:String!,$subs:String!,$cons:String!){
  repository(owner:$owner,name:$name){
    subs: object(expression:$subs){ ... on Tree { entries { name oid object { ... on Blob { text isTruncated } } } } }
    cons: object(expression:$cons){ ... on Tree { entries { name oid object { ... on Blob { text isTruncated } } } } }
  }
}`;

export class GithubStore {
  constructor({ token, repo, branch = 'main', fetchImpl }) {
    if (!token || !/^[A-Za-z0-9-]+\/(?!\.{1,2}$)[\w.-]+$/.test(repo || '')) throw new Error('DATA_TOKEN and DATA_REPO ("owner/name") are required');
    this.token = token;
    [this.owner, this.name] = repo.split('/');
    this.branch = branch;
    this.f = fetchImpl || ((...a) => fetch(...a));
  }

  _headers() {
    return {
      Authorization: 'Bearer ' + this.token, Accept: 'application/vnd.github+json',
      'User-Agent': 'hca-crowd-api', 'X-GitHub-Api-Version': '2022-11-28', 'Content-Type': 'application/json'
    };
  }

  async _req(method, path, body) {
    const r = await this.f(API + path, { method, headers: this._headers(), body: body === undefined ? undefined : JSON.stringify(body) });
    return r;
  }

  async _getFile(path) {
    const r = await this._req('GET', `/repos/${this.owner}/${this.name}/contents/${path}?ref=${encodeURIComponent(this.branch)}`);
    if (r.status === 404) return null;
    if (!r.ok) throw new Error(`GitHub GET ${path}: ${r.status}`);
    const j = await r.json();
    return { data: JSON.parse(fromB64(j.content)), version: j.sha };
  }

  async _putFile(path, data, version, message) {
    const body = { message, content: toB64(JSON.stringify(data, null, 2) + '\n'), branch: this.branch };
    if (version) body.sha = version;
    const r = await this._req('PUT', `/repos/${this.owner}/${this.name}/contents/${path}`, body);
    if (r.status === 409 || r.status === 422) throw new ConflictError();   // stale sha, or create over an existing file
    if (!r.ok) throw new Error(`GitHub PUT ${path}: ${r.status}`);
    const j = await r.json();
    return j.content.sha;
  }

  async _listTrees() {
    const r = await this._req('POST', '/graphql', {
      query: QUERY, variables: { owner: this.owner, name: this.name, subs: `${this.branch}:submissions`, cons: `${this.branch}:contributors` }
    });
    if (!r.ok) throw new Error('GitHub GraphQL: ' + r.status);
    const j = await r.json();
    if (j.errors && !j.data) throw new Error('GitHub GraphQL: ' + JSON.stringify(j.errors).slice(0, 200));
    const repo = (j.data || {}).repository;
    if (!repo) throw new Error('GitHub: repository not found or token has no access');
    return repo;
  }

  async _entries(tree, dir) {
    const out = [];
    for (const e of (tree && tree.entries) || []) {
      if (!e.name.endsWith('.json')) continue;
      let text = e.object && e.object.text;
      if (e.object && (e.object.isTruncated || text == null)) {
        const f = await this._getFile(`${dir}/${e.name}`);           // too large for GraphQL: fetch singly
        if (f) out.push(f);
        continue;
      }
      try { out.push({ data: JSON.parse(text), version: e.oid }); } catch (err) { /* skip a file that is not JSON */ }
    }
    return out;
  }

  async listSubmissions() { return this._entries((await this._listTrees()).subs, 'submissions'); }
  async listContributors() { return this._entries((await this._listTrees()).cons, 'contributors'); }
  getSubmission(id) { return this._getFile(`submissions/${id}.json`); }
  getContributor(id) { return this._getFile(`contributors/${id}.json`); }
  saveSubmission(data, version) {
    return this._putFile(`submissions/${data.id}.json`, data, version,
      `${version ? 'update' : 'create'} ${data.id} (${data.status}) by ${data.contributor.id}`);
  }
  saveContributor(data, version) {
    return this._putFile(`contributors/${data.id}.json`, data, version, `${version ? 'update' : 'register'} contributor ${data.id}`);
  }
}
