/* category-catalogue.js — appends a complete, browsable work catalogue to a
 * works-category landing page (billedkunst.html / teater-musik.html /
 * bibliotek.html), below its hand-curated showcase.
 *
 * The page selects its slice by setting two globals before loading this file:
 *   window.CATEGORY_WING   — 'billedkunst.html' | 'teater-musik.html' | 'bibliotek.html'
 *   window.CATEGORY_LABEL  — human label for the result count ('Billedkunst', …)
 *
 * It expects these containers somewhere on the page:
 *   #js-cat-alpha-bar  — alphabet bar (chips generated here)
 *   #js-cat-results    — list container
 *   #js-cat-more       — "Vis flere" button
 *   #js-cat-count      — result-count element
 *
 * Data comes from WORKS_EXTRA (data/works-extra.js). If that global is absent
 * (fresh clone, no build) the script is a no-op and the showcase stands alone.
 */
(function () {
  'use strict';
  var grid = document.getElementById('js-cat-results');
  var wing = window.CATEGORY_WING;
  if (!grid || !wing || typeof WORKS_EXTRA === 'undefined') return;

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c];
    });
  }

  // First letter of the title, skipping leading punctuation/quotes/asterisks
  // common in the register ("*»Bring Hilsen …" → B). "Aa" folds to Å.
  function initialOf(label) {
    var s = (label || '').replace(/^[^0-9A-Za-zÆØÅæøå]+/, '').trim();
    if (!s) return '#';
    if (/^aa/i.test(s)) return 'Å';
    var c = s.charAt(0).toUpperCase();
    return /[A-ZÆØÅ]/.test(c) ? c : '#';
  }

  var ALL = Object.keys(WORKS_EXTRA).reduce(function (acc, rid) {
    var w = WORKS_EXTRA[rid];
    if (w.wing !== wing) return acc;
    acc.push({
      rid: rid, title: w.title || rid,
      meta: [w.author, w.h3, w.year].filter(Boolean).join(' · '),
      refs: w.refs || 0, init: initialOf(w.title)
    });
    return acc;
  }, []);

  var collator = (typeof Intl !== 'undefined' && Intl.Collator)
    ? new Intl.Collator('da') : null;
  function byTitle(a, b) {
    return collator ? collator.compare(a.title, b.title)
                    : (a.title < b.title ? -1 : a.title > b.title ? 1 : 0);
  }
  function byRefs(a, b) { return b.refs - a.refs || byTitle(a, b); }

  var PAGE = 60;
  var letter = null;
  var shown = 0;
  var filtered = ALL.slice().sort(byRefs);
  var label = window.CATEGORY_LABEL || 'registret';
  var countEl = document.getElementById('js-cat-count');
  var moreBtn = document.getElementById('js-cat-more');

  function card(w) {
    return '<a href="work.html?reg=' + esc(w.rid) + '" class="result-card result-card--list" ' +
      'style="display:flex;align-items:baseline;gap:var(--sp4);padding:var(--sp4)">' +
      '<div style="min-width:90px;font-size:0.72rem;font-weight:600;color:var(--color-text-muted);font-family:monospace">' + esc(w.rid) + '</div>' +
      '<div style="flex:1"><div class="result-card__title" style="font-size:0.95rem">' + esc(w.title) + '</div>' +
      (w.meta ? '<div class="result-card__meta">' + esc(w.meta) + '</div>' : '') + '</div>' +
      '<div style="min-width:70px;text-align:right;font-size:0.78rem;color:var(--color-text-muted)">' + w.refs + ' refs.</div></a>';
  }

  function renderMore() {
    var next = filtered.slice(shown, shown + PAGE);
    grid.insertAdjacentHTML('beforeend', next.map(card).join(''));
    shown += next.length;
    moreBtn.style.display = shown < filtered.length ? '' : 'none';
  }

  function apply() {
    filtered = (letter ? ALL.filter(function (w) { return w.init === letter; }) : ALL.slice());
    filtered.sort(letter ? byTitle : byRefs);
    if (countEl) {
      countEl.innerHTML = '<strong>' + filtered.length.toLocaleString('da-DK') + '</strong> poster i ' + esc(label) +
        (letter ? ' &nbsp;<span style="font-weight:400;font-size:0.8rem;color:var(--color-text-muted)">— bogstav ' + letter + '</span>' : '');
    }
    grid.innerHTML = '';
    shown = 0;
    renderMore();
  }

  var bar = document.getElementById('js-cat-alpha-bar');
  if (bar) {
    var present = {};
    ALL.forEach(function (w) { present[w.init] = true; });
    var order = 'ABCDEFGHIJKLMNOPQRSTUVWXYZÆØÅ#'.split('').filter(function (l) { return present[l]; });
    var chips = [{ l: null, t: 'Alle' }].concat(order.map(function (l) { return { l: l, t: l }; }));
    chips.forEach(function (ch) {
      var a = document.createElement('a');
      a.href = '#';
      a.className = 'chip';
      a.textContent = ch.t;
      a.addEventListener('click', function (ev) {
        ev.preventDefault();
        letter = ch.l;
        bar.querySelectorAll('a.chip').forEach(function (x) { x.style.background = ''; x.style.color = ''; });
        a.style.background = 'var(--color-accent)';
        a.style.color = '#fff';
        apply();
      });
      if (ch.l === null) { a.style.background = 'var(--color-accent)'; a.style.color = '#fff'; }
      bar.appendChild(a);
    });
  }

  moreBtn.addEventListener('click', renderMore);
  apply();
})();
