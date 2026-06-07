/* landing-search.js — typeahead for the landing-page search bar.
 *
 * Reads the global SEARCH_INDEX (loaded from data/search-index.js — sorted
 * by ref count desc) and surfaces:
 *
 *   - on focus + empty: the top-N most-referenced entities ("Populære")
 *   - as the user types: live-filtered prefix + substring matches with
 *     the matched range highlighted
 *
 * Each row links to person.html | place.html | work.html with ?reg=<id>.
 * Keyboard: ↑/↓ navigate, Enter open, Esc dismiss.
 *
 * Falls back silently when search-index.js is missing (fresh clone,
 * before the build runs) — the input still works as a plain text field.
 */
(function () {
  'use strict';

  var input  = document.getElementById('landing-search-input');
  var drop   = document.getElementById('landing-typeahead');
  var form   = input && input.form;
  if (!input || !drop) return;

  // Autofocus the search bar so users can start typing immediately.
  // Defer one frame so the browser's restored-scroll doesn't fight us.
  requestAnimationFrame(function () { try { input.focus(); } catch (_) {} });

  var INDEX = (typeof SEARCH_INDEX !== 'undefined' && Array.isArray(SEARCH_INDEX))
    ? SEARCH_INDEX
    : [];

  var TYPE_HREF = {
    p: 'person.html',
    s: 'place.html',
    w: 'work.html'
  };
  var TYPE_LABEL = { p: 'Person', s: 'Sted', w: 'Værk' };

  var POPULAR_N = 8;
  var RESULT_N  = 20;
  var activeIdx = -1;
  var currentRows = [];

  function hrefFor(row) {
    var base = TYPE_HREF[row.t] || '#';
    return base + '?reg=' + encodeURIComponent(row.r);
  }

  // Case- and diacritic-insensitive fold. Danish chars (æ/ø/å) stay as
  // themselves so typing "København" still matches; otherwise standard
  // NFD-strip handles accented Latin characters.
  function fold(s) {
    return (s || '')
      .toLowerCase()
      .normalize('NFD')
      .replace(/[̀-ͯ]/g, '');
  }

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  function highlight(label, foldedQuery) {
    if (!foldedQuery) return escapeHtml(label);
    var folded = fold(label);
    var pos = folded.indexOf(foldedQuery);
    if (pos < 0) return escapeHtml(label);
    // The folded string preserves character count for the alphabet
    // present in the corpus, so indices line up with the original label.
    return escapeHtml(label.slice(0, pos))
      + '<mark>' + escapeHtml(label.slice(pos, pos + foldedQuery.length)) + '</mark>'
      + escapeHtml(label.slice(pos + foldedQuery.length));
  }

  function matchesFor(query) {
    if (!INDEX.length) return [];
    if (!query) return INDEX.slice(0, POPULAR_N);

    var fq = fold(query);
    var out = [];
    for (var i = 0; i < INDEX.length && out.length < RESULT_N * 4; i++) {
      var row = INDEX[i];
      var pos = fold(row.l).indexOf(fq);
      if (pos < 0) continue;
      out.push({ row: row, pos: pos });
    }
    // Prefer prefix matches; within the same bucket, INDEX order
    // (refs desc) already does the right thing.
    out.sort(function (a, b) {
      var ap = a.pos === 0 ? 0 : 1;
      var bp = b.pos === 0 ? 0 : 1;
      if (ap !== bp) return ap - bp;
      return 0;
    });
    return out.slice(0, RESULT_N).map(function (x) { return x.row; });
  }

  function render(query) {
    var rows = matchesFor(query);
    currentRows = rows;
    activeIdx = -1;

    if (!INDEX.length) {
      drop.innerHTML = '<div class="typeahead__empty">Søgeindekset er ikke bygget endnu. Kør <code>python scripts/build_mockup/build_search_index.py</code>.</div>';
      drop.classList.add('typeahead--open');
      return;
    }

    if (!rows.length) {
      drop.innerHTML = '<div class="typeahead__empty">Ingen registerposter matcher &ldquo;'
        + escapeHtml(query) + '&rdquo;.</div>';
      drop.classList.add('typeahead--open');
      return;
    }

    var fq = fold(query);
    var heading = query
      ? '<div class="typeahead__heading">' + rows.length + ' forslag</div>'
      : '<div class="typeahead__heading">Populære registerposter</div>';

    var html = heading + rows.map(function (row, i) {
      var t = row.t || 'w';
      return '<a class="typeahead__item" data-idx="' + i + '" href="' + escapeHtml(hrefFor(row)) + '" role="option">'
        + '<span class="typeahead__type typeahead__type--' + t + '">' + (TYPE_LABEL[t] || '') + '</span>'
        + '<span class="typeahead__label">' + highlight(row.l, fq) + '</span>'
        + '<span class="typeahead__count">' + (row.c || 0) + ' ref.</span>'
        + '</a>';
    }).join('');

    drop.innerHTML = html;
    drop.classList.add('typeahead--open');
  }

  function close() {
    drop.classList.remove('typeahead--open');
    activeIdx = -1;
  }

  function setActive(i) {
    var items = drop.querySelectorAll('.typeahead__item');
    if (!items.length) return;
    activeIdx = ((i % items.length) + items.length) % items.length;
    items.forEach(function (el, j) {
      el.classList.toggle('typeahead__item--active', j === activeIdx);
    });
    var el = items[activeIdx];
    if (el && el.scrollIntoView) el.scrollIntoView({ block: 'nearest' });
  }

  input.addEventListener('focus', function () { render(input.value.trim()); });
  input.addEventListener('input', function () { render(input.value.trim()); });

  input.addEventListener('keydown', function (e) {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      if (!drop.classList.contains('typeahead--open')) render(input.value.trim());
      setActive(activeIdx + 1);
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setActive(activeIdx - 1);
    } else if (e.key === 'Enter') {
      if (activeIdx >= 0 && currentRows[activeIdx]) {
        e.preventDefault();
        window.location.href = hrefFor(currentRows[activeIdx]);
      } else if (currentRows.length === 1) {
        e.preventDefault();
        window.location.href = hrefFor(currentRows[0]);
      }
    } else if (e.key === 'Escape') {
      close();
      input.blur();
    }
  });

  // Hide when clicking elsewhere.
  document.addEventListener('mousedown', function (e) {
    if (!drop.contains(e.target) && e.target !== input) close();
  });

  // Defensive: form has onsubmit="return false", but if anything ever
  // triggers a submit, just open the dropdown for the current query.
  if (form) form.addEventListener('submit', function (e) {
    e.preventDefault();
    render(input.value.trim());
  });
})();
