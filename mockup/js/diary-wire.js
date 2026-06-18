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

  function chipHtml(c) {
    var cls = c.t === 'place' ? 'chip chip--place'
            : c.t === 'person' ? 'chip chip--person' : 'chip';
    var style = c.t === 'work'
      ? ' style="font-size:0.68rem;background:var(--color-accent-light);border-color:var(--color-accent);color:var(--color-accent)"'
      : ' style="font-size:0.68rem"';
    if (c.r) {
      var page = c.t === 'place' ? 'place.html'
               : c.t === 'person' ? 'person.html' : 'work.html';
      return '<a href="' + page + '?reg=' + esc(c.r) + '" class="' + cls +
             ' result-card__chip-link"' + style + '>' + esc(c.l) + '</a>';
    }
    return '<span class="' + cls + '"' + style + '>' + esc(c.l) + '</span>';
  }

  function titleFor(m) {
    return 'Bind ' + esc(m.v || '?') + ', s. ' + esc(m.p || '?');
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

    /* "Rom, 18. oktober 1833" — the heading a reader sees in the diary. */
    function headingFor(m) {
      if (m.pl && m.d) return esc(m.pl) + ', ' + esc(m.d);
      if (m.pl) return esc(m.pl);
      return titleFor(m);
    }

    /* List card: heading + bibliographic sub-line + entity chips. */
    function cardList(pag, chips) {
      var m = (hasMeta() && DIARY_META[pag]) || {};
      var heading = headingFor(m);
      var sub = titleFor(m) + ' &nbsp;·&nbsp; ' + esc(pag);
      var chipMarkup = (chips || []).slice(0, 3).map(chipHtml).join('');
      var href = PAGES_DIR + esc(pag) + '.html';
      return '<div class="result-card">' +
        '<a href="' + href + '" class="result-card__link" title="Gå til ' + esc(pag) + '"></a>' +
        '<div class="result-card__body">' +
        '<div class="result-card__title">' + heading + '</div>' +
        '<div class="result-card__meta">' + sub + '</div>' +
        '<div class="result-card__chips">' + chipMarkup + '</div></div></div>';
    }

    /* Grid card: compact — date on top, place name below. No chips. */
    function cardGrid(pag) {
      var m = (hasMeta() && DIARY_META[pag]) || {};
      var place = m.pl ? esc(m.pl) : titleFor(m);
      var date = esc(m.d || m.y || '—');
      var href = PAGES_DIR + esc(pag) + '.html';
      return '<div class="result-card result-card--compact">' +
        '<a href="' + href + '" class="result-card__link" title="' + esc(m.d || pag) + '"></a>' +
        '<div class="result-card__body">' +
        '<div class="result-card__meta">' + date + '</div>' +
        '<div class="result-card__title">' + place + '</div>' +
        '</div></div>';
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
      return '<div class="result-card"' + highlight + '>' +
        '<a href="' + href + '" class="result-card__link" title="Gå til ' + esc(row.h) + '"></a>' +
        '<div class="result-card__body">' +
        '<div class="result-card__title">' + titleFor(m) + '</div>' +
        '<div class="result-card__meta">' + (row.d || row.y || '—') + ' · ' + esc(row.h) + '</div>' +
        '<div class="result-card__chips">' + chipMarkup + '</div></div></div>';
    }

    function render(reset) {
      if (reset) { container.innerHTML = ''; shown = 0; }
      var next = filtered.slice(shown, shown + step);
      container.insertAdjacentHTML('beforeend', next.map(rowCard).join(''));
      shown += next.length;
      if (opts.onCount) opts.onCount(shown, filtered.length, DIARY_INDEX.length);
      if (opts.moreBtn) {
        opts.moreBtn.style.display = shown < filtered.length ? '' : 'none';
      }
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

  return { refs: refs, list: list };
})();
