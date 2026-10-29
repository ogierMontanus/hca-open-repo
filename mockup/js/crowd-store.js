/* crowd-store.js — where crowd contributions live.
 *
 * Two interchangeable back-ends behind one Promise API, chosen at start-up:
 *
 *   api    a server answers GET api/crowd/health → contributions are stored
 *          there and an editor reviews them there. Two servers speak this API:
 *          the reference server (scripts/crowdsource/server.py, per-browser
 *          tokens) and the GitHub-login Worker (workers/crowd-api; its address
 *          is CROWD_CONFIG.apiBase, people sign in with GitHub and the session
 *          token comes back in the URL fragment #hca_session=…).
 *   local  no server (file://, GitHub Pages): contributions are kept in this
 *          browser's localStorage and travel to the editors as a JSON file
 *          (exportJSON → scripts/crowdsource/export_approved.py --import-json).
 *          Nothing leaves the browser by itself. The same browser can also
 *          review what it holds or imports, so one person can try the whole
 *          workflow without any infrastructure.
 *
 * The review rules (decision → status, final values, conflict detection,
 * badges) are a port of scripts/crowdsource/store.py; tests/js/
 * crowd-store.test.js runs them under Node. Validation is crowd-validate.js.
 *
 * Browser storage can be missing or throw (private windows, blocked site
 * data): every access is wrapped, with an in-memory fallback.
 */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory(root);
  else root.CrowdStore = factory(root);
})(typeof globalThis !== 'undefined' ? globalThis : (typeof self !== 'undefined' ? self : this), function (root) {
  'use strict';

  var LS = 'hca-crowd/v1/';
  var SESSION = 'session';
  /* '' = same origin; otherwise the Worker's origin (read late so tests can set it). */
  function apiBase() {
    var b = root.CROWD_CONFIG && root.CROWD_CONFIG.apiBase;
    return b ? String(b).replace(/\/+$/, '') + '/' : '';
  }
  function API() { return apiBase() + 'api/crowd/'; }
  var mem = {};

  function tax() { return root.CROWD_TAXONOMY; }
  function V() { return root.CrowdValidate || require('./crowd-validate.js'); }

  /* ── storage with fallbacks ───────────────────────────────────────────── */
  function lsGet(key, dflt) {
    try {
      var raw = root.localStorage.getItem(LS + key);
      return raw === null ? (mem[key] !== undefined ? mem[key] : dflt) : JSON.parse(raw);
    } catch (e) { return mem[key] !== undefined ? mem[key] : dflt; }
  }
  function lsSet(key, val) {
    mem[key] = val;
    try { root.localStorage.setItem(LS + key, JSON.stringify(val)); } catch (e) { /* in-memory only */ }
  }
  function lsDel(key) {
    delete mem[key];
    try { root.localStorage.removeItem(LS + key); } catch (e) { /* ignore */ }
  }
  function sessGet(key) {
    try { return root.sessionStorage.getItem(LS + key); } catch (e) { return mem['s:' + key] || null; }
  }
  function sessSet(key, val) {
    mem['s:' + key] = val;
    try {
      if (val === null) root.sessionStorage.removeItem(LS + key); else root.sessionStorage.setItem(LS + key, val);
    } catch (e) { /* ignore */ }
  }

  function nowISO() { return new Date().toISOString().replace(/\.\d+Z$/, 'Z'); }
  function rand(n) {
    var a = new Uint8Array(n), s = '';
    if (root.crypto && root.crypto.getRandomValues) root.crypto.getRandomValues(a);
    else for (var i = 0; i < n; i++) a[i] = Math.floor(Math.random() * 256);
    for (var j = 0; j < n; j++) s += ('0' + a[j].toString(16)).slice(-2);
    return s;
  }
  function today8() { return nowISO().slice(0, 10).replace(/-/g, ''); }
  function clone(o) { return JSON.parse(JSON.stringify(o)); }

  /* ── mode detection ───────────────────────────────────────────────────── */
  var mode = 'local', authMode = '', readyP = null;

  function withTimeout(p, ms) {
    return new Promise(function (resolve, reject) {
      var t = setTimeout(function () { reject(new Error('timeout')); }, ms);
      p.then(function (v) { clearTimeout(t); resolve(v); }, function (e) { clearTimeout(t); reject(e); });
    });
  }

  /* The Worker sends the browser back with #hca_session=<token> (or #hca_error=…).
   * Keep the token and remove the fragment so it is not bookmarked or shared. */
  var authError = '';
  function takeSessionFromHash() {
    try {
      var h = (root.location && root.location.hash) || '';
      var t = /[#&]hca_session=([\w.\-]+)/.exec(h), e = /[#&]hca_error=(\w+)/.exec(h);
      if (!t && !e) return;
      if (t) lsSet(SESSION, t[1]);
      if (e) authError = e[1];
      root.history.replaceState(null, '', root.location.pathname + root.location.search);
    } catch (err) { /* no history API: harmless */ }
  }

  function init() {
    if (readyP) return readyP;
    takeSessionFromHash();
    // file:// cannot reach a same-origin API (and would log a console error trying);
    // a configured remote API can be reached from file:// when it allows the origin.
    if (typeof root.fetch !== 'function' || (!apiBase() && root.location && root.location.protocol === 'file:')) {
      mode = 'local'; return (readyP = Promise.resolve(mode));
    }
    readyP = withTimeout(root.fetch(API() + 'health', { cache: 'no-store' }), 2500)
      .then(function (r) { if (!r.ok) throw new Error('no api'); return r.json(); })
      .then(function (j) {
        mode = (j && j.mode === 'api') ? 'api' : 'local';
        authMode = (mode === 'api' && j.auth === 'github') ? 'github' : '';
        return mode;
      })
      .catch(function () { mode = 'local'; return mode; });
    return readyP;
  }

  /* ── sign-in (GitHub Worker only) ─────────────────────────────────────── */
  function b64urlJson(part) {
    var b = String(part).replace(/-/g, '+').replace(/_/g, '/');
    var bin = root.atob(b + '==='.slice((b.length + 3) % 4));
    return JSON.parse(decodeURIComponent(Array.prototype.map.call(bin, function (c) {
      return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2);
    }).join('')));
  }
  /* For display only — the Worker verifies the signature; no role is read from here. */
  function session() {
    var tok = lsGet(SESSION, null);
    if (!tok) return null;
    try {
      var p = b64urlJson(String(tok).split('.')[0]);
      if (!p || p.exp * 1000 <= Date.now()) { lsDel(SESSION); return null; }
      return { id: p.sub, login: p.login, name: p.name || p.login, expires: p.exp };
    } catch (e) { lsDel(SESSION); return null; }
  }
  var auth = {
    enabled: function () { return authMode === 'github'; },
    session: session,
    loginUrl: function (returnTo) {
      return apiBase() + 'auth/login?return=' + encodeURIComponent(returnTo || String(root.location.href).split('#')[0]);
    },
    logout: function () { lsDel(SESSION); },
    /* 'denied' | 'exchange' | 'profile' once after a failed sign-in, else '' */
    error: function () { var e = authError; authError = ''; return e; }
  };

  /* ── API transport ────────────────────────────────────────────────────── */
  /* GitHub Worker: one session token for contributors and editors alike (the
   * server decides the role). Reference server: a per-browser contributor
   * token, or the editor key typed into the review page. */
  function credential(admin) {
    if (authMode === 'github') return session() ? lsGet(SESSION, null) : null;
    return admin ? sessGet('admin-token') : lsGet('token', null);
  }
  function api(method, path, body, admin) {
    var headers = { 'Content-Type': 'application/json' };
    var tok = credential(admin);
    if (tok) headers.Authorization = 'Bearer ' + tok;
    return root.fetch(API() + path, {
      method: method, headers: headers, cache: 'no-store',
      body: body === undefined ? undefined : JSON.stringify(body)
    }).then(function (r) {
      return r.json().catch(function () { return {}; }).then(function (j) {
        if (!r.ok) { var e = j || {}; e.status = r.status; throw e; }
        return j;
      });
    });
  }

  /* ── profile, drafts ──────────────────────────────────────────────────── */
  function profile() {
    var p = lsGet('profile', { name: '', contact: '', affiliation: '', expertise: '', public_credit: false });
    var se = authMode === 'github' ? session() : null;
    if (se && !p.name) p = Object.assign({}, p, { name: se.name });     // pre-fill from the GitHub profile
    return p;
  }
  function saveProfile(p) {
    var cur = profile();
    Object.keys(p).forEach(function (k) { cur[k] = p[k]; });
    if (!cur.localId) cur.localId = 'C-local-' + rand(4);
    lsSet('profile', cur);
    return cur;
  }
  var draft = {
    get: function (pid) { return lsGet('draft/' + pid, null); },
    set: function (pid, d) { lsSet('draft/' + pid, d); },
    clear: function (pid) { lsDel('draft/' + pid); }
  };

  /* ── local back-end ───────────────────────────────────────────────────── */
  function localSubs() { return lsGet('submissions', []); }
  function saveLocalSubs(list) { lsSet('submissions', list); }

  function stripAttachments(sources) {
    return sources.map(function (s) {
      var c = clone(s); delete c.attachment; return c;
    });
  }

  /* The stored form of a *validated* payload: normalised text, no attachments.
   * Shared with the Worker (workers/crowd-api), so both back-ends store the same shape. */
  function buildCore(payload) {
    return {
      schema: tax().schema, person_id: payload.person_id.trim(), person_label: payload.person_label || '',
      identification: { status: payload.identification.status, summary: V().normalise(payload.identification.summary, true),
                        same_as: payload.identification.status === 'duplicate' ? payload.identification.same_as.trim() : '' },
      overall_confidence: payload.overall_confidence || '',
      fields: payload.fields.map(function (f) {
        return { field: f.field, value: V().normalise(f.value, true), confidence: f.confidence,
                 comment: V().normalise(f.comment, true), sources: f.sources.slice().sort() };
      }),
      sources: stripAttachments(payload.sources).map(function (s) {
        return { type: s.type, citation: V().normalise(s.citation), url: V().normalise(s.url), locator: V().normalise(s.locator),
                 accessed: V().normalise(s.accessed), result: V().normalise(s.result) || 'stoetter', note: V().normalise(s.note, true) };
      }),
      comment: V().normalise(payload.comment, true), consent: true
    };
  }

  function localCreate(payload, editId, ctx) {
    var errs = V().validate(payload, tax());
    if (errs.length) return Promise.reject({ status: 422, error: 'invalid', message: 'Bidraget har fejl.', errors: errs });
    var p = saveProfile(payload.contributor);
    var list = localSubs(), sub;
    var snapshot = Object.assign({}, ctx || {});
    var core = buildCore(payload);
    if (editId) {
      sub = list.filter(function (s) { return s.id === editId; })[0];
      if (!sub) return Promise.reject({ status: 404, error: 'not_found' });
      if (sub.contributor.id !== p.localId) return Promise.reject({ status: 403, error: 'forbidden', message: 'Det er ikke dit bidrag.' });
      if (['submitted', 'needs_changes'].indexOf(sub.status) < 0) {
        return Promise.reject({ status: 409, error: 'conflict', message: 'Kun åbne bidrag kan rettes.' });
      }
      sub.history.push({ ts: nowISO(), actor: p.localId, action: 'revised', revision: sub.revision + 1,
        previous: { identification: sub.identification, overall_confidence: sub.overall_confidence, fields: sub.fields,
                    comment: sub.comment, sources: sub.sources, review: sub.review, revision: sub.revision } });
      Object.keys(core).forEach(function (k) { sub[k] = core[k]; });
      sub.status = 'submitted'; sub.revision += 1; sub.updated = nowISO(); sub.review = null;
    } else {
      sub = Object.assign(core, {
        id: 'CS-' + today8() + '-' + rand(3),
        register_snapshot: snapshot,
        contributor: { id: p.localId, name: payload.contributor.name.trim(), public_credit: !!payload.contributor.public_credit },
        status: 'submitted', revision: 1, created: nowISO(), updated: nowISO(),
        history: [{ ts: nowISO(), actor: p.localId, action: 'submitted' }], review: null, incorporated: null
      });
      list.push(sub);
    }
    saveLocalSubs(list);
    return Promise.resolve({ submission: sub, local: true });
  }

  /* ── review logic (port of FileStore.review) ──────────────────────────── */
  function reviewSub(sub, reviewer, decisions, note, action) {
    var T = tax();
    if (['submitted', 'needs_changes', 'approved', 'partially_approved', 'rejected'].indexOf(sub.status) < 0) {
      throw new Error('cannot review a ' + sub.status + ' contribution');
    }
    if (sub.incorporated) throw new Error('already incorporated into the authoritative data');
    reviewer = (reviewer || '').trim().slice(0, 120) || 'redaktion';
    note = (note || '').trim().slice(0, T.limits.comment);
    var accepted = ['accept', 'accept_edited'];
    if (action === 'request_changes') {
      if (note.length < 5) throw new Error('a note is required when asking for changes');
      sub.status = 'needs_changes';
      sub.review = { reviewer: reviewer, decided: nowISO(), note: note, fields: {}, identification: null };
      sub.history.push({ ts: nowISO(), actor: reviewer, action: 'changes_requested', note: note });
    } else if (action === 'decide' || !action) {
      var fdec = (decisions && decisions.fields) || {}, out = {}, acc = 0, total = 0;
      sub.fields.forEach(function (f, i) {
        var d = fdec[String(i)];
        if (!d || ['accept', 'accept_edited', 'reject'].indexOf(d.decision) < 0) {
          throw new Error('field ' + i + ' (' + f.field + ') has no decision');
        }
        var entry = { decision: d.decision, note: String(d.note || '').trim().slice(0, T.limits.comment) };
        if (d.decision === 'accept_edited') {
          var fv = String(d.final_value || '').trim();
          if (!fv) throw new Error('field ' + i + ': accept_edited needs final_value');
          entry.final_value = fv.slice(0, T.limits.longtext);
        }
        if (accepted.indexOf(d.decision) >= 0) {
          var fc = d.final_confidence || f.confidence;
          if (T.confidence.map(function (c) { return c.key; }).indexOf(fc) < 0) throw new Error('field ' + i + ': bad final_confidence');
          entry.final_confidence = fc; acc++;
        }
        total++; out[String(i)] = entry;
      });
      var ident = null;
      if (['duplicate', 'not_individual', 'unidentifiable'].indexOf(sub.identification.status) >= 0) {
        var idd = (decisions && decisions.identification) || {};
        if (['accept', 'reject'].indexOf(idd.decision) < 0) throw new Error('the identification statement needs a decision');
        ident = { decision: idd.decision, note: String(idd.note || '').trim().slice(0, T.limits.comment) };
        total++; if (idd.decision === 'accept') acc++;
      }
      if (!total) throw new Error('nothing to decide');
      sub.status = acc === total ? 'approved' : (acc === 0 ? 'rejected' : 'partially_approved');
      sub.review = { reviewer: reviewer, decided: nowISO(), note: note, fields: out, identification: ident };
      sub.history.push({ ts: nowISO(), actor: reviewer, action: sub.status, note: note });
    } else throw new Error('unknown action');
    sub.updated = nowISO();
    return sub;
  }

  function conflictsFor(sub, all) {
    var mine = {};
    sub.fields.forEach(function (f) { mine[f.field] = f.value; });
    var out = [];
    all.forEach(function (o) {
      if (o.id === sub.id || o.person_id !== sub.person_id || ['withdrawn', 'rejected'].indexOf(o.status) >= 0) return;
      o.fields.forEach(function (f) {
        if (mine[f.field] !== undefined && f.value.trim().toLowerCase() !== mine[f.field].trim().toLowerCase()) {
          out.push({ submission: o.id, status: o.status, field: f.field, value: f.value, confidence: f.confidence,
                     contributor: o.contributor.name });
        }
      });
    });
    return out;
  }

  /* Per-contributor counts from reviewed work (port of contributor_stats). */
  function computeStats(subs) {
    var T = tax(), strong = {};
    T.sourceTypes.forEach(function (s) { strong[s.key] = s.strong; });
    var agg = {};
    subs.forEach(function (s) {
      var c = s.contributor;
      var a = agg[c.id] || (agg[c.id] = { id: c.id, name: c.name, public_credit: !!c.public_credit, submitted: 0, pending: 0,
        approved_submissions: 0, accepted_fields: 0, persons: {}, sourced: 0, negative: 0, doubt: 0, areas: {} });
      if (s.status === 'withdrawn') return;
      a.submitted++;
      if (s.status === 'submitted' || s.status === 'needs_changes') a.pending++;
      if (s.status === 'approved' || s.status === 'partially_approved') {
        a.approved_submissions++; a.persons[s.person_id] = true;
        var rev = s.review || {};
        Object.keys(rev.fields || {}).forEach(function (k) {
          if (rev.fields[k].decision !== 'reject') a.accepted_fields++;
        });
        if (s.sources.some(function (x) { return x.result === 'stoetter' && strong[x.type]; })) a.sourced++;
        var snap = s.register_snapshot || {};
        if (snap.doubt) a.doubt++;
        if (snap.area) a.areas[snap.area] = (a.areas[snap.area] || 0) + 1;
        if (s.identification.status === 'unidentifiable' && rev.identification && rev.identification.decision === 'accept') a.negative++;
      }
    });
    return Object.keys(agg).map(function (id) {
      var a = agg[id], badges = [];
      var maxArea = Math.max.apply(null, [0].concat(Object.keys(a.areas).map(function (k) { return a.areas[k]; })));
      if (a.approved_submissions >= 1) badges.push('first_accepted');
      if (a.sourced >= 5) badges.push('five_sourced');
      if (a.negative >= 1) badges.push('negative_result');
      if (maxArea >= 5) badges.push('local_expert');
      if (a.doubt >= 1) badges.push('resolved_doubt');
      return { id: a.id, name: a.name, public_credit: a.public_credit, submitted: a.submitted, pending: a.pending,
               approved_submissions: a.approved_submissions, accepted_fields: a.accepted_fields,
               persons: Object.keys(a.persons).length, badges: badges };
    }).sort(function (x, y) { return x.name.localeCompare(y.name, 'da'); });
  }

  function personStatus(subs) {
    var out = {};
    subs.forEach(function (s) {
      var o = out[s.person_id] || (out[s.person_id] = { pending: 0, approved: 0 });
      if (s.status === 'submitted' || s.status === 'needs_changes') o.pending++;
      else if (s.status === 'approved' || s.status === 'partially_approved') o.approved++;
    });
    return out;
  }

  /* A contribution file comes from outside: keep only known keys with forced
   * types, and a status that the recorded decisions actually support. */
  function normaliseImported(s) {
    var T = tax(), str = function (v) { return typeof v === 'string' ? v : ''; };
    var statuses = T.statuses.map(function (x) { return x.key; });
    var c = s.contributor || {};
    var out = {
      schema: T.schema, id: s.id, person_id: str(s.person_id).trim(), person_label: str(s.person_label),
      identification: { status: str(s.identification.status), summary: str(s.identification.summary), same_as: str(s.identification.same_as) },
      overall_confidence: str(s.overall_confidence), fields: s.fields, sources: s.sources, comment: str(s.comment), consent: true,
      register_snapshot: (s.register_snapshot && typeof s.register_snapshot === 'object') ? s.register_snapshot : {},
      contributor: { id: str(c.id) || 'C-import', name: str(c.name).trim(), public_credit: !!c.public_credit },
      status: statuses.indexOf(s.status) >= 0 ? s.status : 'submitted', revision: parseInt(s.revision, 10) || 1,
      created: str(s.created) || nowISO(), updated: str(s.updated) || nowISO(),
      history: Array.isArray(s.history) ? s.history.filter(function (h) { return h && typeof h === 'object'; }) : [],
      review: null, incorporated: null
    };
    var rev = s.review;
    if (rev && typeof rev === 'object' && rev.fields && typeof rev.fields === 'object') {
      out.review = { reviewer: str(rev.reviewer), decided: str(rev.decided), note: str(rev.note), fields: rev.fields,
                     identification: (rev.identification && typeof rev.identification === 'object') ? rev.identification : null };
    }
    var decided = ['approved', 'partially_approved', 'rejected'];
    if (decided.indexOf(out.status) >= 0) {
      var ok = !!out.review && out.fields.every(function (f, i) {
        var d = out.review.fields[String(i)];
        return d && ['accept', 'accept_edited', 'reject'].indexOf(d.decision) >= 0;
      });
      if (ok) {
        var items = out.fields.map(function (f, i) { return out.review.fields[String(i)].decision !== 'reject'; });
        if (['duplicate', 'not_individual', 'unidentifiable'].indexOf(out.identification.status) >= 0) {
          items.push(!!(out.review.identification && out.review.identification.decision === 'accept'));
        }
        out.status = items.every(Boolean) ? 'approved' : (items.some(Boolean) ? 'partially_approved' : 'rejected');
      } else { out.status = 'submitted'; out.review = null; }
    }
    return out;
  }

  /* ── public API ───────────────────────────────────────────────────────── */
  function submit(payload, editId, ctx) {
    if (mode === 'api') {
      var p = editId ? api('PUT', 'submissions/' + editId, payload) : api('POST', 'submissions', payload);
      return p.then(function (r) {
        if (r.contributor && r.contributor.token) { lsSet('token', r.contributor.token); lsSet('cid', r.contributor.id); }
        saveProfile(payload.contributor);
        return r;
      });
    }
    return localCreate(payload, editId, ctx);
  }

  function mine() {
    if (mode === 'api') {
      return credential(false) ? api('GET', 'mine') : Promise.resolve({ submissions: [], me: null });
    }
    var id = profile().localId;
    var subs = localSubs().filter(function (s) { return s.contributor.id === id; });
    var me = computeStats(localSubs()).filter(function (c) { return c.id === id; })[0] || null;
    return Promise.resolve({ submissions: subs, me: me });
  }

  function withdraw(id) {
    if (mode === 'api') return api('POST', 'submissions/' + id + '/withdraw');
    var list = localSubs(), s = list.filter(function (x) { return x.id === id; })[0];
    if (!s) return Promise.reject({ status: 404 });
    if (['submitted', 'needs_changes'].indexOf(s.status) < 0) return Promise.reject({ status: 409, message: 'Kun åbne bidrag kan trækkes tilbage.' });
    s.status = 'withdrawn'; s.updated = nowISO();
    s.history.push({ ts: nowISO(), actor: s.contributor.id, action: 'withdrawn' });
    saveLocalSubs(list);
    return Promise.resolve({ submission: s });
  }

  function stats() {
    if (mode === 'api') return api('GET', 'stats');
    var subs = localSubs().filter(function (s) { return s.status !== 'withdrawn'; });
    var id = profile().localId, all = computeStats(subs);
    return Promise.resolve({
      submissions: subs.length,
      pending: subs.filter(function (s) { return s.status === 'submitted' || s.status === 'needs_changes'; }).length,
      approved: subs.filter(function (s) { return s.status === 'approved' || s.status === 'partially_approved'; }).length,
      persons: Object.keys(subs.reduce(function (m, s) { m[s.person_id] = 1; return m; }, {})).length,
      contributors: all.filter(function (c) { return c.public_credit && c.approved_submissions; }),
      me: all.filter(function (c) { return c.id === id; })[0] || null,
      personStatus: personStatus(subs)
    });
  }

  var admin = {
    /* api mode: needs a token (kept for this tab only); local mode: always allowed. */
    token: function () { return credential(true); },
    setToken: function (t) { sessSet('admin-token', t || null); },
    list: function (filter) {
      filter = filter || {};
      if (mode === 'api') {
        var qs = Object.keys(filter).filter(function (k) { return filter[k]; })
          .map(function (k) { return k + '=' + encodeURIComponent(filter[k]); }).join('&');
        return api('GET', 'admin/submissions' + (qs ? '?' + qs : ''), undefined, true);
      }
      var subs = localSubs().filter(function (s) {
        return (!filter.status || s.status === filter.status) && (!filter.person || s.person_id === filter.person) &&
               (!filter.contributor || s.contributor.id === filter.contributor);
      }).sort(function (a, b) { return a.created < b.created ? 1 : -1; });
      return Promise.resolve({ submissions: subs.map(function (s) {
        return { id: s.id, person_id: s.person_id, person_label: s.person_label, status: s.status, created: s.created,
                 updated: s.updated, revision: s.revision, contributor: s.contributor, incorporated: s.incorporated,
                 identification: s.identification.status, n_fields: s.fields.length };
      }) });
    },
    get: function (id) {
      if (mode === 'api') return api('GET', 'admin/submissions/' + id, undefined, true);
      var all = localSubs(), s = all.filter(function (x) { return x.id === id; })[0];
      return s ? Promise.resolve({ submission: s, conflicts: conflictsFor(s, all), register: s.register_snapshot || {} })
               : Promise.reject({ status: 404 });
    },
    review: function (id, body) {
      if (mode === 'api') return api('POST', 'admin/submissions/' + id + '/review', body, true);
      var list = localSubs(), s = list.filter(function (x) { return x.id === id; })[0];
      if (!s) return Promise.reject({ status: 404 });
      try { reviewSub(s, body.reviewer, body.decisions, body.note, body.action); }
      catch (e) { return Promise.reject({ status: 400, error: 'bad_request', message: e.message }); }
      saveLocalSubs(list);
      return Promise.resolve({ submission: s });
    },
    contributors: function () {
      if (mode === 'api') return api('GET', 'admin/contributors', undefined, true);
      return Promise.resolve({ contributors: computeStats(localSubs()) });
    },
    /* Fetch an attachment (api mode only) as a blob URL — it needs the admin header. */
    attachment: function (sid, file) {
      return root.fetch(API() + 'admin/attachments/' + sid + '/' + encodeURIComponent(file),
        { headers: { Authorization: 'Bearer ' + (credential(true) || '') } })
        .then(function (r) { if (!r.ok) throw new Error('attachment'); return r.blob(); })
        .then(function (b) { return root.URL.createObjectURL(b); });
    },
    download: function (format) {
      return root.fetch(API() + 'admin/export?format=' + format, { headers: { Authorization: 'Bearer ' + (credential(true) || '') } })
        .then(function (r) { if (!r.ok) throw new Error('export ' + r.status); return r.blob(); });
    },
    /* local mode: take in a contribution file sent by a contributor */
    importFile: function (text) {
      var data;
      try { data = JSON.parse(text); } catch (e) { return Promise.reject({ message: 'Filen er ikke gyldig JSON.' }); }
      var incoming = Array.isArray(data) ? data : (data && data.submissions);
      if (!Array.isArray(incoming)) return Promise.reject({ message: 'Filen indeholder ingen bidrag.' });
      var list = localSubs(), added = 0, updated = 0, skipped = [];
      incoming.forEach(function (s) {
        var payload = { person_id: s.person_id, identification: s.identification, overall_confidence: s.overall_confidence,
          fields: s.fields, sources: s.sources, comment: s.comment, consent: true,
          contributor: { name: (s.contributor || {}).name || '' } };
        var errs = V().validate(payload, tax());
        if (errs.length || !/^CS-\d{8}-[0-9a-f]{6}$/.test(s.id || '')) { skipped.push((s && s.id) || '?'); return; }
        s = normaliseImported(s);
        var i = list.map(function (x) { return x.id; }).indexOf(s.id);
        if (i < 0) { list.push(s); added++; }
        else if ((s.revision || 1) > (list[i].revision || 1) || (list[i].status === 'submitted' && s.status !== 'submitted')) {
          list[i] = s; updated++;
        }
      });
      saveLocalSubs(list);
      return Promise.resolve({ added: added, updated: updated, skipped: skipped });
    },
    /* local mode: everything this browser holds, as a file */
    exportJSON: function (onlyMine) {
      var id = profile().localId;
      var subs = localSubs().filter(function (s) { return !onlyMine || s.contributor.id === id; });
      return { schema: 'hca-crowd-export/1', exported: nowISO(), submissions: subs };
    }
  };

  function exportMine() { return admin.exportJSON(true); }

  return {
    init: init, mode: function () { return mode; }, auth: auth, profile: profile, saveProfile: saveProfile, draft: draft,
    submit: submit, mine: mine, withdraw: withdraw, stats: stats, admin: admin, exportMine: exportMine,
    /* exposed for tests and the Worker */ _buildCore: buildCore, _personStatus: personStatus, _reviewSub: reviewSub, _computeStats: computeStats, _conflictsFor: conflictsFor,
    _setMode: function (m, a) { mode = m; authMode = a || ''; }, _normaliseImported: normaliseImported
  };
});
