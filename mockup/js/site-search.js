/* site-search.js — shared typeahead for every search bar on the site.
 *
 * Reads the global SEARCH_INDEX (data/search-index.js, sorted by ref count
 * desc) and attaches the same autocomplete dropdown to:
 *
 *   - the landing hero input (#landing-search-input), reusing the
 *     pre-rendered #landing-typeahead container, with autofocus; and
 *   - every header search input (.search-input) on the inner pages and
 *     generated diary pages, creating a dropdown under the search form.
 *
 * One data source, one ranking, one set of ?reg=… deep-links everywhere —
 * so the landing page and the header bars behave identically ("same
 * origin" for suggestions).
 *
 * Behaviour:
 *   - on focus + empty: the top-N most-referenced entities ("Populære")
 *   - as the user types: live-filtered prefix-first matches, highlighted
 *   - ↑/↓ navigate · Enter open · Esc dismiss · click open
 *
 * Degrades silently to a plain text field when SEARCH_INDEX is absent
 * (fresh clone before the build runs).
 */
(function () {
  'use strict';

  var INDEX = (typeof SEARCH_INDEX !== 'undefined' && Array.isArray(SEARCH_INDEX))
    ? SEARCH_INDEX : [];

  var TYPE_HREF  = { p: 'person.html', s: 'place.html', w: 'work.html' };
  var TYPE_LABEL = { p: 'Person', s: 'Sted', w: 'Værk' };
  var POPULAR_N = 8;
  var RESULT_N  = 20;

  function fold(s) {
    return (s || '').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '');
  }

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  function hrefFor(row, prefix) {
    return (prefix || '') + (TYPE_HREF[row.t] || '#') + '?reg=' + encodeURIComponent(row.r);
  }

  function highlight(label, fq) {
    if (!fq) return escapeHtml(label);
    var pos = fold(label).indexOf(fq);
    if (pos < 0) return escapeHtml(label);
    return escapeHtml(label.slice(0, pos))
      + '<mark>' + escapeHtml(label.slice(pos, pos + fq.length)) + '</mark>'
      + escapeHtml(label.slice(pos + fq.length));
  }

  function matchesFor(query) {
    if (!INDEX.length) return [];
    if (!query) return INDEX.slice(0, POPULAR_N);
    var fq = fold(query);
    var out = [];
    for (var i = 0; i < INDEX.length && out.length < RESULT_N * 4; i++) {
      var pos = fold(INDEX[i].l).indexOf(fq);
      if (pos < 0) continue;
      out.push({ row: INDEX[i], pos: pos });
    }
    out.sort(function (a, b) {
      var ap = a.pos === 0 ? 0 : 1, bp = b.pos === 0 ? 0 : 1;
      return ap - bp;   // prefix matches first; INDEX order (refs desc) within
    });
    return out.slice(0, RESULT_N).map(function (x) { return x.row; });
  }

  /* Attach the typeahead behaviour to one input + dropdown pair.
   * `prefix` is prepended to every href so header bars on diary pages
   * (in a subdirectory) still point at the root-level detail pages. */
  function attach(input, drop, opts) {
    opts = opts || {};
    if (input.dataset.typeaheadOn) return;
    input.dataset.typeaheadOn = '1';

    var prefix = opts.prefix || '';
    var activeIdx = -1;
    var currentRows = [];

    function render(query) {
      currentRows = matchesFor(query);
      activeIdx = -1;

      if (!INDEX.length) {
        drop.innerHTML = '<div class="typeahead__empty">Søgeindekset er ikke bygget endnu.</div>';
        drop.classList.add('typeahead--open');
        return;
      }
      if (!currentRows.length) {
        drop.innerHTML = '<div class="typeahead__empty">Ingen registerposter matcher &ldquo;'
          + escapeHtml(query) + '&rdquo;.</div>';
        drop.classList.add('typeahead--open');
        return;
      }

      var fq = fold(query);
      var heading = query
        ? '<div class="typeahead__heading">' + currentRows.length + ' forslag</div>'
        : '<div class="typeahead__heading">Populære registerposter</div>';

      drop.innerHTML = heading + currentRows.map(function (row, i) {
        var t = row.t || 'w';
        return '<a class="typeahead__item" data-idx="' + i + '" href="'
          + escapeHtml(hrefFor(row, prefix)) + '" role="option">'
          + '<span class="typeahead__type typeahead__type--' + t + '">' + (TYPE_LABEL[t] || '') + '</span>'
          + '<span class="typeahead__label">' + highlight(row.l, fq) + '</span>'
          + '<span class="typeahead__count">' + (row.c || 0) + ' ref.</span>'
          + '</a>';
      }).join('');
      drop.classList.add('typeahead--open');
    }

    function close() { drop.classList.remove('typeahead--open'); activeIdx = -1; }

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

    // Optional hover-to-preview: the landing hero opens its "Populære"
    // curtain on mouseover instead of auto-opening on load, and retracts
    // it when the pointer leaves — unless the field has been focused. Keeps
    // the first-visit view uncluttered while the suggestions stay one
    // hover (or click) away.
    if (opts.hoverOpen) {
      var hoverHost = input.form || input;
      hoverHost.addEventListener('mouseenter', function () { render(input.value.trim()); });
      hoverHost.addEventListener('mouseleave', function () {
        if (document.activeElement !== input) close();
      });
    }

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
          window.location.href = hrefFor(currentRows[activeIdx], prefix);
        } else if (currentRows.length === 1) {
          e.preventDefault();
          window.location.href = hrefFor(currentRows[0], prefix);
        }
      } else if (e.key === 'Escape') {
        close(); input.blur();
      }
    });

    document.addEventListener('mousedown', function (e) {
      if (!drop.contains(e.target) && e.target !== input) close();
    });

    var form = input.form;
    if (form) form.addEventListener('submit', function (e) {
      e.preventDefault(); render(input.value.trim());
    });

    if (opts.autofocus) {
      requestAnimationFrame(function () { try { input.focus(); } catch (_) {} });
    }
  }

  /* Resolve the path prefix back to the mockup root from the current
   * document, so a header bar on diary-pages/Pag*.html links to
   * ../person.html rather than person.html. site-search.js is loaded from
   * "<root>/js/site-search.js"; derive <root> from this script's own URL. */
  function rootPrefix() {
    var s = document.currentScript
      || document.querySelector('script[src$="js/site-search.js"]')
      || document.querySelector('script[src*="site-search.js"]');
    if (!s) return '';
    var here = location.href.replace(/[?#].*$/, '');
    var hereDir = here.slice(0, here.lastIndexOf('/') + 1);
    var root = s.src.replace(/js\/site-search\.js.*$/, '');
    if (hereDir === root) return '';
    // Compute relative steps from hereDir up to root (root is an ancestor).
    if (hereDir.indexOf(root) === 0) {
      var rest = hereDir.slice(root.length).replace(/\/+$/, '');
      var depth = rest ? rest.split('/').length : 0;
      return new Array(depth + 1).join('../');
    }
    return root;  // fallback: absolute base
  }

  function init() {
    var prefix = rootPrefix();

    var landing = document.getElementById('landing-search-input');
    if (landing) {
      var ld = document.getElementById('landing-typeahead');
      if (ld) attach(landing, ld, { hoverOpen: true, prefix: prefix });
    }

    var inputs = document.querySelectorAll('.search-input');
    for (var i = 0; i < inputs.length; i++) {
      var inp = inputs[i];
      if (inp.id === 'landing-search-input') continue;
      var host = inp.form || inp.parentNode;
      if (!host) continue;
      host.style.position = 'relative';
      var d = document.createElement('div');
      d.className = 'typeahead';
      d.setAttribute('role', 'listbox');
      d.setAttribute('aria-label', 'Forslag');
      host.appendChild(d);
      attach(inp, d, { prefix: prefix });
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
