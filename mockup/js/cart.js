/* cart.js — cross-page "select entries, download them" cart.
 *
 * Lets a reader tick individual result cards on a list page (persons.html,
 * places.html, …) and collect them into a cart, reviewed and printed from
 * cart.html. No accounts, no server, no cookies — see "Why sessionStorage,
 * not cookies or a login" below.
 *
 * ── Storage ──────────────────────────────────────────────────────────────
 *
 * sessionStorage['hca-cart-v1'] = JSON array of {type, rid, label}, in
 * selection order. sessionStorage, not localStorage: it survives normal
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
 * ── Public API (window.Cart) ────────────────────────────────────────────
 *   add(type, rid, label)        add one entry (label is cached so
 *   remove(type, rid)             cart.html can list entries without every
 *   toggle(type, rid, label)      *_EXTRA data file loaded)
 *   has(type, rid)                → boolean
 *   all()                         → [{type, rid, label}, …] insertion order
 *   count()
 *   clear()
 *   addMany(items)                bulk add/remove, one storage write each —
 *   removeMany(items)             for "select all" over hundreds of rows
 *   subscribe(fn)                 fn() runs after every mutation, from any
 *                                  source (this tab's own UI, or a storage
 *                                  event from another tab — see below)
 *   wireCheckboxes()              delegates .result-card__select clicks;
 *                                  call once per page, after DOMContentLoaded
 *   syncCheckboxes(root)          re-paint checkboxes + the --in-cart
 *                                  highlight under `root` (default: document)
 *                                  from current cart state — call after any
 *                                  render that inserts fresh cards
 *   mountBadge(el)                fills el with a live "Kurv (N)" link
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

  function load() {
    if (!storage) return {};
    try {
      var raw = storage.getItem(KEY);
      if (!raw) return {};
      var arr = JSON.parse(raw);
      var map = {};
      for (var i = 0; i < arr.length; i++) map[arr[i].type + '|' + arr[i].rid] = arr[i];
      return map;
    } catch (e) {
      return {};
    }
  }
  function save(map) {
    if (!storage) return;
    var arr = [];
    for (var k in map) if (map.hasOwnProperty(k)) arr.push(map[k]);
    try { storage.setItem(KEY, JSON.stringify(arr)); } catch (e) { /* quota or disabled — cart just won't persist */ }
  }

  var state = load();

  function notify() {
    for (var i = 0; i < subscribers.length; i++) {
      try { subscribers[i](); } catch (e) { /* one bad subscriber shouldn't break the rest */ }
    }
  }

  function key(type, rid) { return type + '|' + rid; }

  function add(type, rid, label) {
    state[key(type, rid)] = { type: type, rid: rid, label: label || rid };
    save(state);
    notify();
  }
  function remove(type, rid) {
    delete state[key(type, rid)];
    save(state);
    notify();
  }
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
    for (var i = 0; i < items.length; i++) {
      state[key(items[i].type, items[i].rid)] = { type: items[i].type, rid: items[i].rid, label: items[i].label || items[i].rid };
    }
    save(state);
    notify();
  }
  function removeMany(items) {
    for (var i = 0; i < items.length; i++) delete state[key(items[i].type, items[i].rid)];
    save(state);
    notify();
  }

  function subscribe(fn) { subscribers.push(fn); }

  // Another tab writing to the same sessionStorage-backed cart would fire a
  // 'storage' event here — doesn't happen in practice since sessionStorage
  // is tab-scoped (see module docstring), but reloading state defensively on
  // any external storage change costs nothing and protects against a future
  // switch to a shared store.
  window.addEventListener('storage', function (ev) {
    if (ev.key === KEY) { state = load(); notify(); }
  });

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

  function wireCheckboxes() {
    document.addEventListener('change', function (ev) {
      var cb = ev.target;
      if (!cb.matches || !cb.matches('.result-card__select input[data-cart-rid]')) return;
      var type = cb.getAttribute('data-cart-type');
      var rid = cb.getAttribute('data-cart-rid');
      var label = cb.getAttribute('data-cart-label') || rid;
      toggle(type, rid, label);
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
      el.innerHTML = '<a href="cart.html" class="cart-badge' + (n ? ' cart-badge--active' : '') + '">' +
        '🛒 Kurv' + (n ? ' <span class="cart-badge__count">' + n + '</span>' : '') + '</a>';
    }
    subscribe(paint);
    paint();
  }

  return {
    add: add, remove: remove, toggle: toggle, has: has, all: all, count: count, clear: clear,
    addMany: addMany, removeMany: removeMany, subscribe: subscribe,
    wireCheckboxes: wireCheckboxes, syncCheckboxes: syncCheckboxes, mountBadge: mountBadge,
    storageAvailable: !!storage
  };
})();
