/* diary-wire.js — wires register pages to the generated diary pages.
 *
 * Depends on globals defined by data/diary-refs.js and data/diary-index.js,
 * both produced by scripts/build_mockup/build_diary_index.py and loaded with
 * plain <script> tags (file://-safe — fetch() is blocked under file://).
 *
 * When those data files are absent (fresh clone, no build run), every helper
 * is a no-op and the page keeps whatever static sample markup it shipped with.
 *
 * Public API:
 *   DiaryWire.refs(container, regId, opts)  — render diary-reference cards for
 *       one register entry. Returns the {n, e} record, or null if no data.
 *   DiaryWire.list(container, opts)         — render the paginated diaries.html
 *       listing from DIARY_INDEX. Returns the controller, or null if no data.
 */
window.DiaryWire = (function () {
  'use strict';

  var PAGES_DIR = 'diary-pages/';

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  function hasMeta() { return typeof DIARY_META !== 'undefined'; }
  function hasIndex() { return typeof DIARY_INDEX !== 'undefined'; }

  /* pag -> [chip] map, built lazily from DIARY_INDEX when available. */
  var _chips = null;
  function chipsFor(pag) {
    if (!hasIndex()) return [];
    if (!_chips) {
      _chips = {};
      for (var i = 0; i < DIARY_INDEX.length; i++) {
        _chips[DIARY_INDEX[i].h] = DIARY_INDEX[i].c || [];
      }
    }
    return _chips[pag] || [];
  }

  // Checkbox markup for a diary card, added as a sibling of .result-card
  // (never nested inside its link) — same .result-row / .result-card__select
  // contract as every other cart-able list on the site. Always emitted; if
  // js/cart.js hasn't loaded on this page the box is just inert markup, the
  // same degrade-to-nothing the rest of the cart wiring already relies on.
  function selectBox(rid, labelHtml) {
    return '<label class="result-card__select"><input type="checkbox" ' +
      'data-cart-type="diary" data-cart-rid="' + esc(rid) + '" data-cart-label="' + labelHtml + '"></label>';
  }

  function chipHtml(c) {
    var cls = c.t === 'place' ? 'chip chip--place'
            : c.t === 'person' ? 'chip chip--person' : 'chip';
    var style = c.t === 'work'
      ? ' style="font-size:0.68rem;background:var(--color-accent-light);border-color:var(--color-accent);color:var(--color-accent)"'
      : ' style="font-size:0.68rem"';
    if (c.r) {
      var page = c.t === 'place' ? 'place.html'
               : c.t === 'person' ? 'persons.html' : 'work.html';
      return '<a href="' + page + '?reg=' + esc(c.r) + '" class="' + cls +
             ' result-card__chip-link"' + style + '>' + esc(c.l) + '</a>';
    }
    return '<span class="' + cls + '"' + style + '>' + esc(c.l) + '</span>';
  }

  function titleFor(m) {
    return 'Bind ' + esc(m.v || '?') + ', s. ' + esc(m.p || '?');
  }

  var MONTHS_DA = ['januar', 'februar', 'marts', 'april', 'maj', 'juni',
                   'juli', 'august', 'september', 'oktober', 'november', 'december'];

  /* DIARY_META.d as written by build_diary_index.py's short_date():
   *   "24-01-1864"  full date      → "24. januar 1864"
   *   "01-1864"     day unknown    → "januar 1864"
   *   "1864"        month unknown  → "1864"
   * Anything unrecognised is passed through untouched rather than guessed at.
   */
  function formatDate(d) {
    if (!d) return '';
    var full = /^(\d{1,2})-(\d{1,2})-(\d{4})$/.exec(d);
    if (full) {
      var mo = MONTHS_DA[parseInt(full[2], 10) - 1];
      if (mo) return parseInt(full[1], 10) + '. ' + mo + ' ' + full[3];
    }
    var my = /^(\d{1,2})-(\d{4})$/.exec(d);
    if (my) {
      var mo2 = MONTHS_DA[parseInt(my[1], 10) - 1];
      if (mo2) return mo2 + ' ' + my[2];
    }
    return d;
  }

  /* The heading a reader sees on a diary card.
   *
   * The date of the entry is the most useful label, so it wins whenever the
   * page has one. Only vols VI–VII are dated today (751 of 4.544 pages); the
   * remaining volumes fall back to the bibliographic "Bind III, s. 124".
   * Dates for those volumes are to be supplied later in the same structured
   * form, at which point they start appearing here with no code change.
   *
   * The place name is deliberately not used as the heading: it is not what
   * identifies the entry, and it is already shown as a place chip on the card.
   */
  function headingFor(m) {
    m = m || {};
    if (m.d) return esc(formatDate(m.d));
    if (m.y) return esc(m.y);
    return titleFor(m);
  }

  /* --- diary-reference section for one register entry -------------------- */
  function refs(container, regId, opts) {
    opts = opts || {};
    if (!container || typeof DIARY_REFS === 'undefined' || !DIARY_REFS[regId]) {
      return null;  // leave the page's static fallback markup in place
    }
    var rec = DIARY_REFS[regId];
    var shown = 0;
    var step = opts.pageSize || 24;
    var layout = opts.layout || 'list';  // 'list' | 'grid'

    /* List card: heading + bibliographic sub-line + entity chips.
     * When the page is undated the heading already *is* the volume/page
     * reference, so the sub-line drops the repeat and shows only the Pag id. */
    function cardList(pag, chips) {
      var m = (hasMeta() && DIARY_META[pag]) || {};
      var heading = headingFor(m);
      var vp = titleFor(m);
      var sub = (heading === vp) ? esc(pag) : vp + ' &nbsp;·&nbsp; ' + esc(pag);
      var chipMarkup = (chips || []).slice(0, 3).map(chipHtml).join('');
      var href = PAGES_DIR + esc(pag) + '.html';
      return '<div class="result-row">' + selectBox(pag, heading) +
        '<div class="result-card">' +
        '<a href="' + href + '" class="result-card__link" title="Gå til ' + esc(pag) + '"></a>' +
        '<div class="result-card__body">' +
        '<div class="result-card__title">' + heading + '</div>' +
        '<div class="result-card__meta">' + sub + '</div>' +
        '<div class="result-card__chips">' + chipMarkup + '</div></div></div>' +
        '</div>';
    }

    /* Grid card: compact — heading on top, place below. No chips, so the
     * place name is kept here; in the list layout it arrives as a chip. */
    function cardGrid(pag) {
      var m = (hasMeta() && DIARY_META[pag]) || {};
      var heading = headingFor(m);
      var vp = titleFor(m);
      var sub = m.pl ? esc(m.pl) : (heading === vp ? '' : vp);
      var href = PAGES_DIR + esc(pag) + '.html';
      return '<div class="result-row">' + selectBox(pag, heading) +
        '<div class="result-card result-card--compact">' +
        '<a href="' + href + '" class="result-card__link" title="' + esc(m.d ? formatDate(m.d) : pag) + '"></a>' +
        '<div class="result-card__body">' +
        '<div class="result-card__title">' + heading + '</div>' +
        '<div class="result-card__meta">' + sub + '</div>' +
        '</div></div>' +
        '</div>';
    }

    function applyContainerStyle() {
      container.style.gridTemplateColumns = layout === 'grid'
        ? 'repeat(auto-fill,minmax(150px,1fr))'
        : '1fr';
    }

    function render(limit) {
      applyContainerStyle();
      var html = rec.e.slice(0, limit).map(function (p) {
        return layout === 'grid' ? cardGrid(p) : cardList(p, chipsFor(p));
      }).join('');
      container.innerHTML = html;
      shown = Math.min(limit, rec.e.length);
      if (typeof Cart !== 'undefined') Cart.syncCheckboxes(container);
      if (opts.onCount) opts.onCount(shown, rec.n, rec.e.length);
      if (opts.moreBtn) {
        opts.moreBtn.style.display = shown < rec.e.length ? '' : 'none';
      }
    }

    render(Math.min(step, rec.e.length));

    if (opts.moreBtn) {
      opts.moreBtn.addEventListener('click', function () {
        render(Math.min(shown + step, rec.e.length));
      });
    }

    return {
      n: rec.n,
      setLayout: function (newLayout) {
        layout = newLayout;
        render(shown || step);
      }
    };
  }

  /* --- paginated full listing for diaries.html -------------------------- */
  function list(container, opts) {
    opts = opts || {};
    if (!container || !hasIndex()) return null;

    var step = opts.pageSize || 60;
    var filtered = DIARY_INDEX;
    var shown = 0;
    var filterYear = '';  // tracks the active year selection for card highlighting

    function matches(row, q, year) {
      if (year && row.y !== year) return false;
      if (!q) return true;
      q = q.toLowerCase();
      if ((row.pl || '').toLowerCase().indexOf(q) !== -1) return true;
      if ((row.h || '').toLowerCase().indexOf(q) !== -1) return true;
      var cs = row.c || [];
      for (var i = 0; i < cs.length; i++) {
        if ((cs[i].l || '').toLowerCase().indexOf(q) !== -1) return true;
      }
      return false;
    }

    function rowCard(row) {
      var m = { v: row.v, p: row.p, d: row.d, y: row.y, pl: row.pl };
      var chipMarkup = (row.c || []).slice(0, 3).map(chipHtml).join('');
      var href = PAGES_DIR + esc(row.h) + '.html';
      var highlight = filterYear
        ? ' style="outline:2px solid var(--color-accent);outline-offset:-2px"'
        : '';
      var heading = headingFor(m);
      var vp = titleFor(m);
      var sub = (heading === vp) ? esc(row.h) : vp + ' &nbsp;·&nbsp; ' + esc(row.h);
      return '<div class="result-row">' + selectBox(row.h, heading) +
        '<div class="result-card"' + highlight + '>' +
        '<a href="' + href + '" class="result-card__link" title="Gå til ' + esc(row.h) + '"></a>' +
        '<div class="result-card__body">' +
        '<div class="result-card__title">' + heading + '</div>' +
        '<div class="result-card__meta">' + sub + '</div>' +
        '<div class="result-card__chips">' + chipMarkup + '</div></div></div>' +
        '</div>';
    }

    // "Vælg alle" means every currently FILTERED page, not just the ones
    // paginated onto the screen — same convention as every other cart-able
    // list (persons.html, category-catalogue.js). Opt-in via opts.selectAll
    // so pages that don't render the checkbox (the embedded refs() lists)
    // don't pay for wiring they don't use.
    function updateSelectAll() {
      if (!opts.selectAll || typeof Cart === 'undefined') return;
      if (!filtered.length) { opts.selectAll.checked = false; opts.selectAll.indeterminate = false; return; }
      var inCount = 0;
      for (var i = 0; i < filtered.length; i++) if (Cart.has('diary', filtered[i].h)) inCount++;
      opts.selectAll.checked = inCount === filtered.length;
      opts.selectAll.indeterminate = inCount > 0 && inCount < filtered.length;
    }
    if (opts.selectAll) {
      opts.selectAll.addEventListener('change', function () {
        if (opts.selectAll.checked) {
          if (filtered.length > 100 &&
              !confirm('Tilføj alle ' + filtered.length.toLocaleString('da-DK') + ' dagbogssider til kurven?')) {
            opts.selectAll.checked = false;
            return;
          }
          Cart.addMany(filtered.map(function (r) { return { type: 'diary', rid: r.h, label: headingFor(r) }; }));
        } else {
          Cart.removeMany(filtered.map(function (r) { return { type: 'diary', rid: r.h }; }));
        }
        Cart.syncCheckboxes(container);
      });
      if (typeof Cart !== 'undefined') Cart.subscribe(updateSelectAll);
    }

    function render(reset) {
      if (reset) { container.innerHTML = ''; shown = 0; }
      var next = filtered.slice(shown, shown + step);
      container.insertAdjacentHTML('beforeend', next.map(rowCard).join(''));
      shown += next.length;
      if (typeof Cart !== 'undefined') Cart.syncCheckboxes(container);
      if (opts.onCount) opts.onCount(shown, filtered.length, DIARY_INDEX.length);
      if (opts.moreBtn) {
        opts.moreBtn.style.display = shown < filtered.length ? '' : 'none';
      }
      updateSelectAll();
    }

    function applyFilter(q, year) {
      filterYear = year || '';
      filtered = DIARY_INDEX.filter(function (r) { return matches(r, q, year); });
      render(true);
    }

    render(true);
    if (opts.moreBtn) {
      opts.moreBtn.addEventListener('click', function () { render(false); });
    }
    return { applyFilter: applyFilter, years: function () {
      var ys = {};
      for (var i = 0; i < DIARY_INDEX.length; i++) {
        if (DIARY_INDEX[i].y) ys[DIARY_INDEX[i].y] = (ys[DIARY_INDEX[i].y] || 0) + 1;
      }
      return ys;
    } };
  }

  // heading/formatDate are exported so pages rendering their own diary cards
  // (diaries.html's calendar view) label them identically instead of
  // re-deriving the rule and drifting from it.
  return { refs: refs, list: list, heading: headingFor, formatDate: formatDate };
})();
