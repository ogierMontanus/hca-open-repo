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
  // Diacritics fold so accented forms file under the right bucket instead
  // of falling into "#":
  //   ä→æ, ö→ø, ü→y (Danish convention; ü is articulated as y in Danish)
  //   ß→s; generic accents (é, à, ñ, ç, î …) collapse to their base letter
  //   via NFD strip of combining marks. æ/ø/å have no decomposition and
  //   pass through.
  function initialOf(label) {
    var s = (label || '')
      .replace(/ä/g, 'æ').replace(/Ä/g, 'Æ')
      .replace(/ö/g, 'ø').replace(/Ö/g, 'Ø')
      .replace(/ü/g, 'y').replace(/Ü/g, 'Y')
      .replace(/ß/g, 's');
    // Keep Latin-1 accented letters (À–ÿ) in the keep-set so the
    // punctuation strip doesn't also eat a leading accented char like
    // "*»École" → that would lose the É before the NFD fold below.
    s = s.replace(/^[^0-9A-Za-zÆØÅæøåÀ-ÿ]+/, '').trim();
    if (!s) return '#';
    if (/^aa/i.test(s)) return 'Å';
    var c = s.charAt(0).toUpperCase();
    if (/[A-ZÆØÅ]/.test(c)) return c;
    // Generic accents fall through to NFD strip: é→E, ç→C, ñ→N, î→I, …
    // Å/å are handled above — they NFD-decompose to A/a + combining ring.
    if (c.normalize) {
      var folded = c.normalize('NFD').replace(/[\u0300-\u036f]/g, '');
      if (/[A-Z]/.test(folded.charAt(0))) return folded.charAt(0);
    }
    return '#';
  }

  var ALL = Object.keys(WORKS_EXTRA).reduce(function (acc, rid) {
    var w = WORKS_EXTRA[rid];
    if (w.wing !== wing) return acc;
    acc.push({
      rid: rid, title: w.title || rid,
      meta: [w.author, w.h3, w.year].filter(Boolean).join(' · '),
      refs: w.refs || 0, init: initialOf(w.title),
      h2: w.h2 || '', h3: w.h3 || ''
    });
    return acc;
  }, []);

  // Faceted filtering — read state from the sibling .facet-panel on every
  // render. Each H2/H3 checkbox carries data-h2 and/or data-h3 naming the
  // exact WORKS_EXTRA value it filters on. Within a .facet-group the
  // predicates combine with OR; across groups with AND; an empty group
  // (no boxes ticked) imposes no constraint. Static counts on facet items
  // are left as starting totals — dynamic count updates are deferred.
  function readFacetGroups() {
    var groups = [];
    document.querySelectorAll('.facet-panel .facet-group').forEach(function (g) {
      var boxes = g.querySelectorAll('input[type=checkbox][data-h2], input[type=checkbox][data-h3]');
      if (!boxes.length) return;
      var preds = [];
      for (var i = 0; i < boxes.length; i++) {
        var b = boxes[i];
        if (!b.checked) continue;
        preds.push({
          h2: b.getAttribute('data-h2') || null,
          h3: b.getAttribute('data-h3') || null
        });
      }
      if (preds.length) groups.push(preds);
    });
    return groups;
  }

  function passesFacets(w, groups) {
    for (var i = 0; i < groups.length; i++) {
      var preds = groups[i];
      var ok = false;
      for (var j = 0; j < preds.length; j++) {
        var p = preds[j];
        if ((p.h2 == null || w.h2 === p.h2) && (p.h3 == null || w.h3 === p.h3)) {
          ok = true; break;
        }
      }
      if (!ok) return false;
    }
    return true;
  }

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
    var groups = readFacetGroups();
    filtered = ALL.filter(function (w) {
      if (letter && w.init !== letter) return false;
      return passesFacets(w, groups);
    });
    filtered.sort(letter ? byTitle : byRefs);
    var activeFacets = groups.reduce(function (n, g) { return n + g.length; }, 0);
    var anyActive = activeFacets > 0 || letter !== null;
    showcaseEls.forEach(function (el) { el.style.display = anyActive ? 'none' : ''; });
    if (countEl) {
      var note = '';
      if (letter) note += ' &nbsp;<span style="font-weight:400;font-size:0.8rem;color:var(--color-text-muted)">— bogstav ' + letter + '</span>';
      if (activeFacets) note += ' &nbsp;<span style="font-weight:400;font-size:0.8rem;color:var(--color-text-muted)">— ' + activeFacets + ' facet' + (activeFacets === 1 ? '' : 'ter') + '</span>';
      countEl.innerHTML = '<strong>' + filtered.length.toLocaleString('da-DK') + '</strong> poster i ' + esc(label) + note;
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

  // The curated showcase sits directly inside the browse-layout main column,
  // above the catalogue block. When the reader narrows by H2/H3 or by letter,
  // the showcase becomes noise (it doesn't react to facets) and pushes the
  // filtered list below the fold. Hide the showcase header + grid (direct
  // children of the main column) whenever any filter is active; the
  // catalogue's own .cat-block wrapper stays visible alongside the sticky
  // facet-panel.
  var showcaseEls = document.querySelectorAll(
    '.browse-layout > div > .results-header, .browse-layout > div > .result-grid'
  );

  // Wire facet checkboxes for live filtering.
  var facetBoxes = document.querySelectorAll(
    '.facet-panel input[type=checkbox][data-h2], .facet-panel input[type=checkbox][data-h3]'
  );
  facetBoxes.forEach(function (cb) { cb.addEventListener('change', apply); });

  // Wire the Nulstil button to clear all facet checkboxes + reset to "Alle".
  var clearBtn = document.querySelector('.facet-panel__clear');
  if (clearBtn) {
    clearBtn.addEventListener('click', function () {
      facetBoxes.forEach(function (cb) { cb.checked = false; });
      letter = null;
      if (bar) {
        bar.querySelectorAll('a.chip').forEach(function (x, i) {
          x.style.background = i === 0 ? 'var(--color-accent)' : '';
          x.style.color = i === 0 ? '#fff' : '';
        });
      }
      apply();
    });
  }

  apply();
})();
