/* cart.js — cross-page "select entries, download them" cart.
 *
 * Lets a reader tick individual result cards on a list page (persons.html,
 * places.html, …) and collect them into a cart, reviewed and printed from
 * cart.html. No accounts, no server, no cookies — see "Why sessionStorage,
 * not cookies or a login" below.
 *
 * ── Storage ──────────────────────────────────────────────────────────────
 *
 * sessionStorage['hca-cart-v1'] = {t, items: [{type, rid, label, by}, …]}
 * (t = save time; a bare array from older builds is still read), in selection
 * order. Mirrored into window.name — see "Bridge across directories" below.
 * sessionStorage, not localStorage: it survives normal
 * browsing (clicking between persons.html and places.html in one tab) but
 * clears when the tab closes, which is exactly "remember my selection for
 * this visit" without drifting into "remember it forever" — the explicit
 * request was to avoid a login/remembered-across-sessions system, and
 * sessionStorage gives up that persistence for free rather than needing to
 * be told not to.
 *
 * Why sessionStorage, not cookies: tested directly against this project's
 * primary deployment target (a page opened via file://, not a server) —
 * `document.cookie` comes back empty immediately after being set on a
 * file:// page in Chromium; cookies do not work there at all. sessionStorage
 * does: it persists correctly across navigation between different file://
 * pages in the same tab (round-tripped a æøå test value successfully) and,
 * just as importantly, does NOT carry over to a new tab — sessionStorage is
 * tab-scoped by design, so opening persons.html in a second tab starts a
 * fresh, empty cart there rather than sharing state. That is a real,
 * expected limitation worth knowing about, not a bug: the cart follows one
 * browser tab's navigation history, not "the reader" as an identity.
 *
 * ── Ownership (`by`) ─────────────────────────────────────────────────────
 * Adding a person/place/work adds a BUNDLE: the entity plus every diary page
 * that mentions it (and, for a person, their attributed works). Bundles
 * overlap — Bremer and Dickens share diary pages — so every item records who
 * put it there: `by` holds '*' for an explicit pick and owner keys
 * ('person|Reg0042200') for bundle members. Removing anything deletes that
 * item and drops its key from every other item's `by`; an item whose `by`
 * becomes empty goes too. So un-ticking Bremer removes the pages only Bremer
 * brought in, keeps those Dickens (or the reader, explicitly) also holds, and
 * it works on cart.html, where the diary data isn't loaded at all.
 *
 * ── Bridge across directories ───────────────────────────────────────────
 * Some browsers (Firefox) give file:// pages one storage area per directory,
 * so mockup/ and mockup/diary-pages/ had separate carts. Every save also
 * writes window.name ("hca-cart:" + JSON), which survives navigation within
 * the tab whatever the origin; load() takes whichever copy is newer. A new
 * tab still starts empty, as before.
 *
 * ── Public API (window.Cart) ────────────────────────────────────────────
 *   add(type, rid, label)        add one entry explicitly (label is cached
 *   remove(type, rid)             so cart.html can list entries without every
 *   toggle(type, rid, label)      *_EXTRA data file loaded). remove() also
 *                                  releases everything the entry owned
 *   has(type, rid)                → boolean
 *   all()                         → [{type, rid, label, by}, …] insertion order
 *   count()
 *   clear()
 *   addMany(items)                bulk add/remove, one storage write each —
 *   removeMany(items)             for "select all" over hundreds of rows
 *   addBundle(type, rid, label)   entry + its diary pages (+ works, persons)
 *   bundleSize(type, rid)         → number of items a bundle brings along
 *   selectBundles(ents, on)       "Vælg alle" engine: add/remove the bundles of
 *                                  [{type, rid, label}], with a counted confirm
 *                                  above 100 new items; → false if declined
 *   relatedFor(type, rid)         → the bundle members (diary pages, works)
 *   subscribe(fn)                 fn() runs after every mutation, from any
 *                                  source (this tab's own UI, or a storage
 *                                  event from another tab — see below)
 *   wireCheckboxes()              delegates .result-card__select clicks;
 *                                  call once per page, after DOMContentLoaded.
 *                                  A person/place/work checkbox selects the
 *                                  bundle; a diary checkbox just the page
 *   syncCheckboxes(root)          re-paint checkboxes + the --in-cart
 *                                  highlight under `root` (default: document)
 *                                  from current cart state — call after any
 *                                  render that inserts fresh cards
 *   mountBadge(el)                fills el with a live "🛒 Kurv (N)" /
 *                                   "🛒 Cart (N)" link — cart.html or
 *                                   cart_en.html, read from
 *                                   document.documentElement.lang (see
 *                                   isEnglish() below), so every page shows
 *                                   the badge in its own interface language
 *                                   without needing to say so itself
 *   mountToggle(el, type, rid,    fills el with a live "+ Tilføj til kurv" /
 *               label)             "✓ I kurven" ("+ Add to cart" / "✓ In
 *                                   cart" in English) button — for detail
 *                                   pages with one entity and no result list.
 *                                   Same bundle rule as the list checkboxes
 *
 * ── Markup contract ─────────────────────────────────────────────────────
 *   <div class="result-row">
 *     <label class="result-card__select">
 *       <input type="checkbox" data-cart-type="person" data-cart-rid="Reg…">
 *     </label>
 *     <a class="result-card" href="…">…</a>
 *   </div>
 * The checkbox is a SIBLING of the card link, not nested inside it — a
 * <label>/<input> inside an <a> still needs its own click cancelled to stop
 * the browser from also following the link, which is a real but avoidable
 * source of bugs; keeping them siblings sidesteps it rather than working
 * around it.
 */
window.Cart = (function () {
  'use strict';

  var KEY = 'hca-cart-v1';
  var NAME_PREFIX = 'hca-cart:';
  var EXPLICIT = '*';

  // Directory prefix of mockup/ relative to the current page, taken from this
  // script's own src ("../js/cart.js" on diary-pages/*.html → "../"). The
  // badge links to cart.html, which lives in mockup/, so a bare 'cart.html'
  // 404s from the diary-pages/ subfolder.
  var BASE = (function () {
    var s = document.currentScript;
    var m = s && /^(.*?)js\/cart\.js(?:[?#].*)?$/.exec(s.getAttribute('src') || '');
    return m ? m[1] : '';
  })();
  var subscribers = [];

  function safeStorage() {
    try {
      var t = '__cart_probe__';
      sessionStorage.setItem(t, '1');
      sessionStorage.removeItem(t);
      return sessionStorage;
    } catch (e) {
      return null;
    }
  }
  var storage = safeStorage();

  // cart.js itself is shared, unlocalized markup/logic loaded by every
  // page; the *_en.html pages set <html lang="en">, which is the one
  // reliable, already-present signal for which language to paint in.
  function isEnglish() {
    return document.documentElement.lang === 'en';
  }

  // The two copies, each as {t, items}; null when absent or unreadable.
  function readStore() {
    if (!storage) return null;
    try {
      var raw = storage.getItem(KEY);
      if (!raw) return null;
      var v = JSON.parse(raw);
      return Array.isArray(v) ? { t: 0, items: v } : (v && Array.isArray(v.items) ? v : null);
    } catch (e) { return null; }
  }
  function readName() {
    try {
      var n = window.name || '';
      if (n.indexOf(NAME_PREFIX) !== 0) return null;
      var v = JSON.parse(n.slice(NAME_PREFIX.length));
      return v && Array.isArray(v.items) ? v : null;
    } catch (e) { return null; }
  }

  function load() {
    var a = readStore(), b = readName();
    var win = !a ? b : !b ? a : (b.t > a.t ? b : a);
    var map = {};
    if (!win) return map;
    for (var i = 0; i < win.items.length; i++) {
      var it = win.items[i];
      if (!it || !it.type || !it.rid) continue;
      map[it.type + '|' + it.rid] = {
        type: it.type, rid: it.rid, label: it.label || it.rid,
        by: (Array.isArray(it.by) && it.by.length) ? it.by.slice() : [EXPLICIT]
      };
    }
    // The window.name copy was newer (another directory's storage wrote it):
    // adopt it into this directory's storage too.
    if (win === b && storage) {
      try { storage.setItem(KEY, JSON.stringify(b)); } catch (e) { /* see save() */ }
    }
    return map;
  }

  var warnedQuota = false;
  function save(map) {
    var arr = [];
    for (var k in map) if (map.hasOwnProperty(k)) arr.push(map[k]);
    var json = JSON.stringify({ t: Date.now(), items: arr });
    try { window.name = NAME_PREFIX + json; } catch (e) { /* ignore */ }
    if (!storage) return;
    try {
      storage.setItem(KEY, json);
    } catch (e) {
      // Quota exceeded: the cart still works on this page (state is in
      // memory, and window.name carries it on), but say so once instead of
      // losing the selection silently.
      if (!warnedQuota) {
        warnedQuota = true;
        try {
          window.alert(isEnglish()
            ? 'The cart is too large for the browser\'s storage and may be lost in a new tab. Consider removing entries.'
            : 'Kurven er for stor til browserens lager og kan gå tabt i et nyt faneblad. Overvej at fjerne poster.');
        } catch (e2) { /* dialogs blocked */ }
      }
    }
  }

  var state = load();

  function notify() {
    for (var i = 0; i < subscribers.length; i++) {
      try { subscribers[i](); } catch (e) { /* one bad subscriber shouldn't break the rest */ }
    }
  }

  function key(type, rid) { return type + '|' + rid; }

  // --- mutations without save/notify, so bulk operations write once --------
  function put(type, rid, label, owner) {
    var k = key(type, rid);
    var it = state[k];
    var isNew = !it;
    if (isNew) it = state[k] = { type: type, rid: rid, label: label || rid, by: [] };
    if (it.by.indexOf(owner) === -1) it.by.push(owner);
    return isNew;
  }
  // Delete `k` and release everything it owned (see "Ownership" above).
  // Scans the state rather than recomputing bundles, so it also works where
  // the diary data isn't loaded (cart.html).
  // Takes a list so "Vælg alle" off over thousands of entities is one pass
  // over the state per round, not one per entity.
  function drop(keys) {
    var freed = {}, any = false;
    keys.forEach(function (k) {
      if (state.hasOwnProperty(k)) { delete state[k]; freed[k] = 1; any = true; }
    });
    while (any) {
      var next = {};
      any = false;
      for (var kk in state) {
        if (!state.hasOwnProperty(kk)) continue;
        var it = state[kk];
        var kept = it.by.filter(function (o) { return !freed[o]; });
        if (kept.length === it.by.length) continue;
        it.by = kept;
        if (!kept.length) { delete state[kk]; next[kk] = 1; any = true; }
      }
      freed = next;
    }
  }
  function putBundle(type, rid, label) {
    put(type, rid, label, EXPLICIT);
    var owner = key(type, rid);
    relatedFor(type, rid).forEach(function (r) { put(r.type, r.rid, r.label, owner); });
  }

  // --- public mutations ---------------------------------------------------
  function add(type, rid, label) { put(type, rid, label, EXPLICIT); save(state); notify(); }
  function remove(type, rid) { drop([key(type, rid)]); save(state); notify(); }
  function toggle(type, rid, label) {
    if (has(type, rid)) remove(type, rid); else add(type, rid, label);
  }
  function has(type, rid) { return state.hasOwnProperty(key(type, rid)); }
  function all() {
    var out = [];
    for (var k in state) if (state.hasOwnProperty(k)) out.push(state[k]);
    return out;
  }
  function count() { return Object.keys(state).length; }
  function clear() { state = {}; save(state); notify(); }

  function addMany(items) {
    for (var i = 0; i < items.length; i++) put(items[i].type, items[i].rid, items[i].label, EXPLICIT);
    save(state);
    notify();
  }
  function removeMany(items) {
    drop(items.map(function (it) { return key(it.type, it.rid); }));
    save(state);
    notify();
  }

  function addBundle(type, rid, label) { putBundle(type, rid, label); save(state); notify(); }

  // How many NEW items selecting these entities' bundles would add, by kind.
  function countNew(ents) {
    var seen = {}, c = { total: 0, entities: 0, diary: 0, work: 0 };
    function note(type, rid, isEntity) {
      var k = key(type, rid);
      if (seen[k] || state.hasOwnProperty(k)) return;
      seen[k] = 1;
      c.total++;
      if (isEntity) c.entities++; else if (type === 'diary') c.diary++; else c.work++;
    }
    ents.forEach(function (e) {
      note(e.type, e.rid, true);
      relatedFor(e.type, e.rid).forEach(function (r) { note(r.type, r.rid, false); });
    });
    return c;
  }

  var NOUNS = {
    da: { person: ['person', 'personer'], place: ['sted', 'steder'], work: ['værk', 'værker'] },
    en: { person: ['person', 'persons'], place: ['place', 'places'], work: ['work', 'works'] }
  };
  function confirmText(c, type) {
    var en = isEnglish(), lg = en ? 'en' : 'da';
    var f = function (n) { return n.toLocaleString(en ? 'en-GB' : 'da-DK'); };
    var nouns = NOUNS[lg][type] || (en ? ['entry', 'entries'] : ['post', 'poster']);
    var parts = [];
    if (c.entities) parts.push(f(c.entities) + ' ' + nouns[c.entities === 1 ? 0 : 1]);
    if (c.diary) parts.push(f(c.diary) + (en ? ' diary pages' : ' dagbogssider'));
    if (c.work) parts.push(f(c.work) + (en ? (type === 'work' ? ' more works' : ' works') : (type === 'work' ? ' flere værker' : ' værker')));
    var last = parts.pop();
    var list = parts.length ? parts.join(', ') + (en ? ' and ' : ' og ') + last : last;
    return (en ? 'Add ' : 'Tilføj ') + list + (en ? ' to the cart?' : ' til kurven?');
  }

  // "Vælg alle" (and a single tick) for persons/places/works: each entity
  // with its bundle. Returns false when the reader declines the confirmation.
  function selectBundles(ents, on) {
    if (on) {
      var c = countNew(ents);
      if (c.total > 100 && !window.confirm(confirmText(c, ents.length ? ents[0].type : ''))) return false;
      ents.forEach(function (e) { putBundle(e.type, e.rid, e.label); });
    } else {
      drop(ents.map(function (e) { return key(e.type, e.rid); }));
    }
    save(state);
    notify();
    return true;
  }
  function bundleSize(type, rid) { return relatedFor(type, rid).length; }

  function subscribe(fn) { subscribers.push(fn); }

  // Another tab writing to the same sessionStorage-backed cart would fire a
  // 'storage' event here — doesn't happen in practice since sessionStorage
  // is tab-scoped (see module docstring), but reloading state defensively on
  // any external storage change costs nothing and protects against a future
  // switch to a shared store.
  window.addEventListener('storage', function (ev) {
    if (ev.key === KEY) { state = load(); notify(); }
  });
  // Back/forward cache: a restored page would otherwise keep the in-memory
  // cart from before the reader changed it on another page of the tab.
  // Also repaint every checkbox after "back": the browser's form-state
  // restoration can re-tick boxes from the earlier visit, after our render.
  window.addEventListener('pageshow', function (ev) {
    if (ev.persisted) { state = load(); notify(); }
    setTimeout(function () { syncCheckboxes(); }, 0);
  });

  // window.name follows the tab to other sites too. Don't hand the cart to a
  // site the reader leaves for in this tab (most external links open a new
  // tab anyway — docs/external-links.md — but footers etc. don't): clear it
  // when an off-site link is followed in place. The storage copy remains.
  document.addEventListener('click', function (ev) {
    var a = ev.target && ev.target.closest ? ev.target.closest('a[href]') : null;
    if (!a || (a.target && a.target !== '_self')) return;
    var proto = a.protocol, host = a.host;
    if ((proto === 'http:' || proto === 'https:') && (location.protocol === 'file:' || host !== location.host)) {
      try { if ((window.name || '').indexOf(NAME_PREFIX) === 0) window.name = ''; } catch (e) { /* ignore */ }
    }
  }, true);

  function paintCheckbox(cb) {
    var type = cb.getAttribute('data-cart-type');
    var rid = cb.getAttribute('data-cart-rid');
    var checked = has(type, rid);
    cb.checked = checked;
    var row = cb.closest('.result-row');
    if (row) row.classList.toggle('result-row--in-cart', checked);
  }

  function syncCheckboxes(root) {
    (root || document).querySelectorAll('.result-card__select input[data-cart-rid]').forEach(paintCheckbox);
  }
  // Every change repaints every rendered checkbox on the page — a bundle
  // added by the detail button or a list tick changes many items at once
  // (e.g. the embedded Dagbogsreferencer boxes), not just the one clicked.
  subscribe(function () { syncCheckboxes(); });

  // A ticked person/place/work brings its bundle, exactly like the detail
  // page's button — one rule, so list and detail never disagree. A diary
  // page is just itself.
  function wireCheckboxes() {
    document.addEventListener('change', function (ev) {
      var cb = ev.target;
      if (!cb.matches || !cb.matches('.result-card__select input[data-cart-rid]')) return;
      var type = cb.getAttribute('data-cart-type');
      var rid = cb.getAttribute('data-cart-rid');
      var label = cb.getAttribute('data-cart-label') || rid;
      if (type === 'diary') toggle(type, rid, label);
      else if (has(type, rid)) remove(type, rid);
      else selectBundles([{ type: type, rid: rid, label: label }], true);
      paintCheckbox(cb);
    });
  }

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c];
    });
  }

  function mountBadge(el) {
    if (!el) return;
    function paint() {
      var n = count();
      var en = isEnglish();
      el.innerHTML = '<a href="' + esc(BASE) + (en ? 'cart_en.html' : 'cart.html') + '" class="cart-badge' +
        (n ? ' cart-badge--active' : '') + '">' +
        (en ? '🛒 Cart' : '🛒 Kurv') + (n ? ' <span class="cart-badge__count">' + n + '</span>' : '') + '</a>';
    }
    subscribe(paint);
    paint();
  }

  // Plain-text cart label for a diary page — same precedence as
  // DiaryWire.heading (date, else year, else "Bind V, s. P"), minus the HTML
  // escaping, since the label is stored as text.
  function diaryLabel(pag) {
    var m = (typeof DIARY_META !== 'undefined' && DIARY_META[pag]) || {};
    if (m.d) {
      if (typeof DiaryWire !== 'undefined' && DiaryWire.formatDate) return DiaryWire.formatDate(m.d);
      // List pages don't load diary-wire.js; same "24. januar 1864" form, so
      // a page's label doesn't depend on where it was added from.
      var full = /^(\d{1,2})-(\d{1,2})-(\d{4})$/.exec(m.d);
      var mo = full && ['januar', 'februar', 'marts', 'april', 'maj', 'juni', 'juli', 'august',
        'september', 'oktober', 'november', 'december'][parseInt(full[2], 10) - 1];
      return mo ? parseInt(full[1], 10) + '. ' + mo + ' ' + full[3] : m.d;
    }
    if (m.y) return m.y;
    return 'Bind ' + (m.v || '?') + ', s. ' + (m.p || '?');
  }

  // Every diary page mentioning rid: DIARY_REFS[rid].e is capped at 60, the
  // rest lives in diary-refs-overflow.js. Read directly (not via DiaryWire)
  // so list pages need only the two data files, not diary-wire.js.
  function diaryPagesFor(rid) {
    var rec = (typeof DIARY_REFS !== 'undefined' && DIARY_REFS[rid]) || null;
    if (!rec) return [];
    var more = (typeof DIARY_REFS_OVERFLOW !== 'undefined' && DIARY_REFS_OVERFLOW[rid]) || [];
    return more.length ? rec.e.concat(more) : rec.e;
  }

  // Everything that travels with a person/place/work when it goes in the
  // cart: EVERY diary page that mentions it — so the cart and PDF always hold
  // the primary source, not just a register stub — and, for a person, every
  // work attributed to them in the register. Empty for a diary page, and
  // when the page lacks the data files (the entity then goes in alone).
  function relatedFor(type, rid) {
    var out = [];
    if (type === 'diary') return out;
    diaryPagesFor(rid).forEach(function (pag) {
      out.push({ type: 'diary', rid: pag, label: diaryLabel(pag) });
    });
    if (type === 'person' && typeof EntityRefs !== 'undefined') {
      EntityRefs.worksByAuthor(rid).forEach(function (w) {
        out.push({ type: 'work', rid: w.rid, label: w.title });
      });
    }
    return out;
  }

  // A single-entity "add to cart" affordance for detail pages that show one
  // item, not a list — persons.html?reg=…, place.html, work.html, and the
  // generated diary-pages/*.html — where there is no row of results to put a
  // checkbox next to. Mirrors mountBadge's self-painting pattern.
  function mountToggle(el, type, rid, label) {
    if (!el) return;
    var n = bundleSize(type, rid);
    function paint() {
      var inCart = has(type, rid);
      var en = isEnglish();
      var suffix = n ? (en ? ' (+' + n + ' related)' : ' (+' + n + ' tilknyttede)') : '';
      el.innerHTML = '<button type="button" class="cart-toggle-btn' +
        (inCart ? ' cart-toggle-btn--active' : '') + '">' +
        (en
          ? (inCart ? '✓ In cart' : '+ Add to cart' + suffix)
          : (inCart ? '✓ I kurven' : '+ Tilføj til kurv' + suffix)) + '</button>';
      el.querySelector('button').addEventListener('click', function () {
        if (type === 'diary') toggle(type, rid, label);
        else if (has(type, rid)) remove(type, rid);
        else selectBundles([{ type: type, rid: rid, label: label }], true);
      });
    }
    subscribe(paint);
    paint();
  }

  return {
    add: add, remove: remove, toggle: toggle, has: has, all: all, count: count, clear: clear,
    addMany: addMany, removeMany: removeMany, subscribe: subscribe,
    addBundle: addBundle, bundleSize: bundleSize, selectBundles: selectBundles, relatedFor: relatedFor,
    wireCheckboxes: wireCheckboxes, syncCheckboxes: syncCheckboxes, mountBadge: mountBadge,
    mountToggle: mountToggle,
    storageAvailable: !!storage
  };
})();
