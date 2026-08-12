/* table-view.js — shared sortable "Tabel" view, the same pattern cart.html
 * established for its own Liste/Tabel switcher, generalized for reuse across
 * every register listing (persons.html, places.html, the works wings via
 * category-catalogue.js, diaries.html, nation.html).
 *
 * TableView.create(container, columns, opts) → { render(items) }
 *
 * A column is:
 *   { key,                 — identifies the column; also the sort key
 *     label,                — header text (escaped)
 *     value(item) -> string — plain-text cell content (escaped for you)
 *     html(item)  -> string — raw HTML cell content (overrides value; you
 *                             escape whatever needs it); use for links/badges
 *     sortValue(item) -> string|number — comparison key; falls back to
 *                             value(item) or item[key]
 *     sortable: false        — omit the sort affordance (default true)
 *     numeric: true          — right-align + tabular-nums (also implies a
 *                             numeric rather than collated compare when no
 *                             explicit sortValue is given)
 *     className               — extra class on every <td> in this column
 *   }
 *
 * opts: { tableClass, initialSort, initialDir, emptyHtml }
 */
window.TableView = (function () {
  'use strict';

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c];
    });
  }

  var collator = (typeof Intl !== 'undefined' && Intl.Collator)
    ? new Intl.Collator('da') : null;
  function collate(a, b) {
    return collator ? collator.compare(a, b) : (a < b ? -1 : a > b ? 1 : 0);
  }

  function create(container, columns, opts) {
    opts = opts || {};
    var tableClass = opts.tableClass || 'data-table';
    var sortKey = opts.initialSort || (columns[0] && columns[0].key);
    var sortDir = opts.initialDir || 'asc';
    var lastItems = [];

    function colByKey(key) {
      for (var i = 0; i < columns.length; i++) if (columns[i].key === key) return columns[i];
      return null;
    }

    function sortArrow(key) {
      if (sortKey !== key) return '<span class="' + tableClass + '__sort-arrow">↕</span>';
      return '<span class="' + tableClass + '__sort-arrow">' + (sortDir === 'asc' ? '↑' : '↓') + '</span>';
    }

    function theadHtml() {
      return '<tr>' + columns.map(function (c) {
        var cls = [c.numeric ? tableClass + '__num' : null, c.className || null]
          .filter(Boolean).join(' ');
        var clsAttr = cls ? ' class="' + cls + '"' : '';
        if (c.sortable === false) {
          return '<th' + clsAttr + '>' + esc(c.label || '') + '</th>';
        }
        var state = sortKey === c.key ? (sortDir === 'asc' ? 'ascending' : 'descending') : 'none';
        return '<th data-sort="' + esc(c.key) + '" aria-sort="' + state + '"' + clsAttr + '>' +
          esc(c.label || '') + ' ' + sortArrow(c.key) + '</th>';
      }).join('') + '</tr>';
    }

    function cellHtml(c, item) {
      if (c.html) return c.html(item);
      var v = c.value ? c.value(item) : item[c.key];
      return esc(v == null ? '' : v);
    }

    function rowHtml(item) {
      return '<tr>' + columns.map(function (c) {
        var cls = [c.numeric ? tableClass + '__num' : null, c.className || null]
          .filter(Boolean).join(' ');
        return '<td' + (cls ? ' class="' + cls + '"' : '') + '>' + cellHtml(c, item) + '</td>';
      }).join('') + '</tr>';
    }

    function sortValueOf(c, item) {
      if (c.sortValue) return c.sortValue(item);
      if (c.value) return c.value(item);
      return item[c.key];
    }

    function sorted(items) {
      var c = colByKey(sortKey);
      if (!c) return items.slice();
      return items.slice().sort(function (a, b) {
        var av = sortValueOf(c, a), bv = sortValueOf(c, b);
        var r;
        if (typeof av === 'number' || typeof bv === 'number') {
          r = (av == null ? -Infinity : av) - (bv == null ? -Infinity : bv);
        } else {
          r = collate(String(av == null ? '' : av), String(bv == null ? '' : bv));
        }
        return sortDir === 'asc' ? r : -r;
      });
    }

    function render(items) {
      lastItems = items;
      if (!items.length) {
        container.innerHTML = opts.emptyHtml || '';
        return;
      }
      container.innerHTML = '<table class="' + tableClass + '"><thead>' + theadHtml() +
        '</thead><tbody>' + sorted(items).map(rowHtml).join('') + '</tbody></table>';
      if (opts.afterRender) opts.afterRender(container);
    }

    container.addEventListener('click', function (ev) {
      var th = ev.target.closest('th[data-sort]');
      if (!th) return;
      var key = th.getAttribute('data-sort');
      if (sortKey === key) { sortDir = sortDir === 'asc' ? 'desc' : 'asc'; }
      else { sortKey = key; sortDir = 'asc'; }
      render(lastItems);
    });

    return { render: render };
  }

  return { create: create };
})();
