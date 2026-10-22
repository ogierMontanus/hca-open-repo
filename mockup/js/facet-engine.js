/* facet-engine.js — live filtering for <aside class="facet-panel">.
 *
 * Generalises the faceting core that has been running on the works-category
 * pages (see js/category-catalogue.js): by default OR within a facet group, AND
 * across groups, with adaptive availability — options that would yield nothing
 * get disabled, dimmed, and their counts rewritten to match the live state.
 *
 * The operator between any two active filters can be switched AND/OR in the
 * active-filter bar (js/active-filters.js). Order, operators and evaluation
 * live in js/filter-logic.js (HcaFilter, must load first) and are documented
 * in docs/filter-logic.md; this file only supplies the per-record truth of
 * each term (hits / inRange) and asks HcaFilter to combine them.
 *
 * No dependencies. Plain <script> tag over an in-memory array, because the
 * mockup is opened over file:// where fetch() of JSON is blocked (that is also
 * why the build emits data/*.js assigning globals rather than *.json).
 *
 * ── Markup contract ───────────────────────────────────────────────────────
 *
 *   <div class="facet-group">
 *     <div class="facet-group__header">Land …</div>
 *     <div class="facet-group__body"
 *          data-facet-source="country"      ← enumerate this field's values
 *          data-facet-limit="12"            ← show the top N (by count)
 *          data-facet-empty-label="Uoplyst"
 *          data-facet-more-label="Vis alle"    ← optional, defaults to "Show all"
 *          data-facet-fewer-label="Vis færre"  ← optional, defaults to "Show fewer"
 *          ><!-- rows generated here --></div>
 *   </div>
 *
 * When a field has more distinct values than data-facet-limit, a toggle row
 * is appended ("Vis alle (79)"). Clicking it expands that one facet into an
 * overlay covering most of the viewport, showing every value in a multi-
 * column list, rather than growing the sidebar and pushing the facets below
 * it off screen. A backdrop click, Escape, the toggle itself, or ticking an
 * option all fold it back to the normal-size list — and a value ticked while
 * expanded stays visible in the folded list afterwards even if it falls
 * outside the top-N by frequency, so choosing it is never silently reversed.
 *
 * A generated row carries the predicate:
 *
 *   <input type="checkbox" data-facet="country" data-match="Tyskland">
 *   <input type="checkbox" data-facet="country" data-facet-empty>  ← "Uoplyst"
 *
 * data-match may list several values comma-separated; they combine with OR
 * (so data-match="da,no" reads "Dansk or Norsk"). Hand-written rows using the
 * same attributes work exactly like generated ones.
 *
 * ── Groups awaiting data ──────────────────────────────────────────────────
 *
 * A group marked <div class="facet-group" data-facet-pending> is skipped
 * entirely: it contributes no predicate, so it can neither narrow the result
 * set nor silently drop rows. Use it for facets whose backing data has not
 * been supplied yet — the group stays visible with an honest note instead of
 * being deleted or, worse, filled with invented counts.
 *
 * ── Range groups (year from–to) ───────────────────────────────────────────
 *
 *   <div class="facet-group">
 *     <div class="facet-group__header">Omtaleår …</div>
 *     <div class="facet-group__body"
 *          data-facet-range="years">      ← accessor name; its values are numbers
 *       <input type="number" data-range-from>  —  <input type="number" data-range-to>
 *     </div>
 *   </div>
 *
 * An item passes when ANY of its values for that accessor lies within
 * [from, to] (either bound may be left empty = open). Items with no value
 * at all are excluded while a bound is set — they have nothing to match.
 * A range group is one term in its own group: it combines with the checkbox
 * groups like any other (AND by default), counts as one active facet, is cleared by reset(), and feeds matcher() so page
 * chrome (the alphabet bar) sees it too.
 *
 * ── Usage ─────────────────────────────────────────────────────────────────
 *
 *   var facets = FacetEngine.create({
 *     panel: document.querySelector('.facet-panel'),
 *     items: ALL,
 *     accessors: {
 *       country: function (p) { return p.country; },   // scalar…
 *       person:  function (p) { return p.personRids; } // …or array
 *     },
 *     labels:   { person: function (rid) { return NAMES[rid]; } },
 *     sortKeys: { person: surnameKey },   // tiebreak when counts are equal
 *     fixedOrder: { role: ['A', 'B'] },   // optional: fixed display order
 *     onChange: function (filtered, state) { render(filtered); }  // state.expr: see filter-logic.js
 *   });
 *
 * Returns a controller: .apply() .reset() .state() .setPrefilter(fn)
 * setPrefilter composes an outside constraint (an alphabet bar, a search box)
 * with the facets so the two narrow together instead of overwriting each other.
 */
window.FacetEngine = (function () {
  'use strict';

  var BOX_SEL = 'input[type=checkbox][data-facet]';
  var RANGE_SEL = '[data-facet-range]';
  var RANGE_INPUT_SEL = RANGE_SEL + ' [data-range-from], ' + RANGE_SEL + ' [data-range-to]';

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c];
    });
  }

  function num(n) {
    return typeof n.toLocaleString === 'function' ? n.toLocaleString('da-DK') : String(n);
  }

  function create(opts) {
    opts = opts || {};
    var panel     = opts.panel;
    var items     = opts.items || [];
    var accessors = opts.accessors || {};
    var labels    = opts.labels || {};
    var sortKeys  = opts.sortKeys || {};
    var fixedOrder = opts.fixedOrder || {};
    var onChange  = opts.onChange || function () {};
    if (!panel) return null;

    var prefilter = null;
    var filtered  = items.slice();

    /* ── Value index ────────────────────────────────────────────────────── */

    // Adaptive availability compares every option against every item, so the
    // inner loop runs items × options times — six figures on a register this
    // size. Reading DOM attributes or re-running accessors in there is what
    // makes a facet panel feel sluggish, so both are hoisted out: values are
    // indexed once here, predicates are compiled once per apply() below.
    var FIELDS = [];
    for (var f in accessors) if (accessors.hasOwnProperty(f)) FIELDS.push(f);

    // VALS[i][field] = array of strings. Empty array means "no value", which
    // is what the "Uoplyst" option tests for.
    var VALS = new Array(items.length);
    var INDEX_OF = (typeof Map === 'function') ? new Map() : null;
    for (var i = 0; i < items.length; i++) {
      var rec = {};
      for (var k = 0; k < FIELDS.length; k++) {
        var v = accessors[FIELDS[k]](items[i]);
        if (v == null || v === '') { rec[FIELDS[k]] = []; continue; }
        var arr = Object.prototype.toString.call(v) === '[object Array]' ? v : [v];
        var out = new Array(arr.length);
        for (var m = 0; m < arr.length; m++) out[m] = String(arr[m]);
        rec[FIELDS[k]] = out;
      }
      VALS[i] = rec;
      if (INDEX_OF) INDEX_OF.set(items[i], i);
    }

    function indexOfItem(item) {
      if (INDEX_OF) { var n = INDEX_OF.get(item); return n === undefined ? -1 : n; }
      return items.indexOf(item);
    }

    /* ── Predicates ─────────────────────────────────────────────────────── */

    // One compiled predicate per checkbox: field, wanted values, empty flag.
    // Read from the DOM once, then matched as plain JS.
    function compile(box) {
      return {
        box:   box,
        field: box.getAttribute('data-facet'),
        empty: box.hasAttribute('data-facet-empty'),
        want:  (box.getAttribute('data-match') || '').split(',')
      };
    }

    function hits(idx, p) {
      var vals = VALS[idx][p.field] || [];
      if (p.empty) return vals.length === 0;
      for (var a = 0; a < p.want.length; a++) {
        for (var b = 0; b < vals.length; b++) {
          if (vals[b] === p.want[a]) return true;
        }
      }
      return false;
    }

    // A range group's bounds as numbers, or null while both ends are empty.
    // Reversed bounds (from 1860 to 1840) are swapped rather than silently
    // matching nothing.
    function readRange(el) {
      var host = el.querySelector(RANGE_SEL);
      if (!host) return undefined;               // not a range group
      var fromEl = host.querySelector('[data-range-from]');
      var toEl   = host.querySelector('[data-range-to]');
      var lo = fromEl && fromEl.value !== '' ? parseInt(fromEl.value, 10) : NaN;
      var hi = toEl && toEl.value !== '' ? parseInt(toEl.value, 10) : NaN;
      if (isNaN(lo) && isNaN(hi)) return null;
      if (!isNaN(lo) && !isNaN(hi) && lo > hi) { var t = lo; lo = hi; hi = t; }
      return { field: host.getAttribute('data-facet-range'),
               lo: isNaN(lo) ? -Infinity : lo, hi: isNaN(hi) ? Infinity : hi };
    }

    function inRange(idx, r) {
      var vals = VALS[idx][r.field] || [];
      for (var v = 0; v < vals.length; v++) {
        var n = parseInt(vals[v], 10);
        if (n >= r.lo && n <= r.hi) return true;
      }
      return false;
    }

    // Live groups only — a data-facet-pending group is invisible to the engine.
    function liveGroups() {
      var out = [];
      var els = panel.querySelectorAll('.facet-group');
      for (var g = 0; g < els.length; g++) {
        if (els[g].hasAttribute('data-facet-pending')) continue;
        var gkey = HcaFilter.groupKeyOf(els[g]);
        var rng = readRange(els[g]);
        if (rng !== undefined) {
          if (rng) rng.key = HcaFilter.termKeyOfRange(els[g].querySelector(RANGE_SEL));
          out.push({ el: els[g], key: gkey, preds: [], checked: [], range: rng });
          continue;
        }
        var boxes = els[g].querySelectorAll(BOX_SEL);
        if (!boxes.length) continue;
        var all = [], checked = [];
        for (var j = 0; j < boxes.length; j++) {
          var p = compile(boxes[j]);
          all.push(p);
          if (boxes[j].checked) { p.key = HcaFilter.termKeyOfBox(boxes[j]); checked.push(p); }
        }
        out.push({ el: els[g], key: gkey, preds: all, checked: checked });
      }
      return out;
    }

    // The selection as one HcaFilter expression. Every ticked box and every
    // non-empty range is a term; terms of one facet form a group (OR between
    // them unless the reader changed it), groups are joined AND unless the
    // reader changed it. The order and operators live in HcaFilter.shared so
    // the active-filter bar shows exactly this expression. A group with
    // nothing ticked has no terms and so imposes no constraint.
    //
    // m.cur is the record index the term test currently answers for; set it,
    // then call HcaFilter.evalExpr(m.expr, m.test).
    function model(groups) {
      var active = [], byKey = {};
      for (var g = 0; g < groups.length; g++) {
        var grp = groups[g];
        if (grp.range) {
          active.push({ key: grp.range.key, group: grp.key });
          byKey[grp.range.key] = grp.range;
        }
        for (var j = 0; j < grp.checked.length; j++) {
          active.push({ key: grp.checked[j].key, group: grp.key });
          byKey[grp.checked[j].key] = grp.checked[j];
        }
      }
      HcaFilter.shared.sync(active);
      var m = { groups: groups, expr: HcaFilter.shared.expr(), cur: 0 };
      m.test = function (key) {
        var t = byKey[key];
        return t.want ? hits(m.cur, t) : inRange(m.cur, t);
      };
      return m;
    }

    /* ── Option rendering ───────────────────────────────────────────────── */

    // Build the full innerHTML for one [data-facet-source] body at a given
    // expand/sort state. A pure function: FacetOverlay (js/facet-overlay.js)
    // owns actually painting it, plus the expand/collapse/backdrop/focus/
    // ARIA/sort-toggle mechanics shared with category-catalogue.js's own
    // capped facets.
    function buildHostHtml(host, expanded, sortMode) {
      var field = host.getAttribute('data-facet-source');
      var limit = parseInt(host.getAttribute('data-facet-limit'), 10) || 0;
      var emptyLabel = host.getAttribute('data-facet-empty-label');
      var moreLabel  = host.getAttribute('data-facet-more-label') || 'Show all';
      var fewerLabel = host.getAttribute('data-facet-fewer-label') || 'Show fewer';
      var countSortLabel = host.getAttribute('data-facet-sort-count-label') || 'Count';
      var alphaSortLabel = host.getAttribute('data-facet-sort-alpha-label') || 'A–Z';

      // A re-render (toggling expand/collapse) rebuilds every checkbox from
      // scratch, so read which values are currently ticked first — otherwise
      // folding the overlay back down would silently untick the reader's own
      // selection.
      var checkedVals = {}, checkedEmpty = false;
      var existing = host.querySelectorAll(BOX_SEL);
      for (var e = 0; e < existing.length; e++) {
        if (!existing[e].checked) continue;
        if (existing[e].hasAttribute('data-facet-empty')) { checkedEmpty = true; continue; }
        checkedVals[existing[e].getAttribute('data-match')] = true;
      }

      var counts = {}, empties = 0;
      for (var i = 0; i < items.length; i++) {
        var vals = VALS[i][field] || [];
        if (!vals.length) { empties++; continue; }
        for (var j = 0; j < vals.length; j++) {
          counts[vals[j]] = (counts[vals[j]] || 0) + 1;
        }
      }

      var labelOf = labels[field] || function (v) { return v; };
      var keyOf   = sortKeys[field] || function (v) { return String(v); };
      var rows = Object.keys(counts).map(function (v) {
        return { value: v, label: String(labelOf(v) || v), n: counts[v] };
      });
      // Always compute the count order first — it's what decides *which*
      // values are the top-N when collapsed, regardless of sortMode (an
      // alphabetical top-N wouldn't be "top" in any useful sense). On a
      // tie fall back to the field's sort key, which for person fields is
      // the surname (project convention — CLAUDE.md).
      rows.sort(function (a, b) {
        return b.n - a.n ||
               String(keyOf(a.value)).localeCompare(String(keyOf(b.value)), 'da');
      });
      // A field with a fixedOrder list (e.g. persons.html's thematic
      // Erhvervsgren facet) is shown in that order instead; values missing
      // from the list follow, still by count (Array#sort is stable).
      var order = fixedOrder[field];
      if (order && order.length) {
        var pos = function (v) { var i = order.indexOf(v); return i < 0 ? order.length : i; };
        rows.sort(function (a, b) { return pos(a.value) - pos(b.value); });
      }

      var total = rows.length;
      var visibleRows = rows;
      if (limit && !expanded) {
        visibleRows = rows.slice(0, limit);
        // A value ticked while the overlay was open must not vanish just
        // because it falls outside the top-N once folded back down.
        var shown = {};
        for (var r = 0; r < visibleRows.length; r++) shown[visibleRows[r].value] = true;
        for (var r2 = 0; r2 < rows.length; r2++) {
          if (checkedVals[rows[r2].value] && !shown[rows[r2].value]) visibleRows.push(rows[r2]);
        }
      }

      // sortMode only ever changes the *display order* of whichever rows
      // were already selected above — never which ones. It's a no-op
      // while collapsed (see facet-overlay.js: the sort toggle only shows
      // up expanded).
      var renderRows = visibleRows;
      if (expanded && sortMode === 'alpha') {
        renderRows = visibleRows.slice().sort(function (a, b) {
          return String(keyOf(a.value)).localeCompare(String(keyOf(b.value)), 'da') || b.n - a.n;
        });
      }

      var rowsHtml = renderRows.map(function (r) {
        var checked = checkedVals[r.value] ? ' checked' : '';
        return '<label class="facet-item"><input type="checkbox" data-facet="' +
          esc(field) + '" data-match="' + esc(r.value) + '"' + checked + '>' +
          '<span class="facet-item__label">' + esc(r.label) + '</span>' +
          '<span class="facet-item__count">' + num(r.n) + '</span></label>';
      }).join('');

      // The "Uoplyst" bucket keeps a partially-covered field honest: the
      // items with no value are selectable rather than silently absent.
      // Always last, regardless of sortMode.
      if (emptyLabel && empties) {
        var eChecked = checkedEmpty ? ' checked' : '';
        rowsHtml += '<label class="facet-item"><input type="checkbox" data-facet="' +
          esc(field) + '" data-facet-empty' + eChecked + '>' +
          '<span class="facet-item__label">' + esc(emptyLabel) + '</span>' +
          '<span class="facet-item__count">' + num(empties) + '</span></label>';
      }

      if (!(limit && total > limit)) return rowsHtml;

      if (!expanded) {
        // Trails the visible rows, so the fixed top-N list isn't pushed
        // down by a control most readers won't need every time.
        return rowsHtml + '<button type="button" class="facet-more-toggle" data-facet-more>' +
          esc(moreLabel) + ' (' + num(total) + ') ▾</button>';
      }
      // Expanded: fold-back control and sort switch lead together, in a
      // sticky header, so both stay reachable without scrolling past
      // however many of the (up to) hundred-plus rows the reader has
      // scrolled through.
      var sortToggle =
        '<div class="facet-sort-toggle">' +
          '<button type="button" class="facet-sort-toggle__btn' +
            (sortMode === 'alpha' ? '' : ' facet-sort-toggle__btn--active') +
            '" data-facet-sort="count">' + esc(countSortLabel) + '</button>' +
          '<button type="button" class="facet-sort-toggle__btn' +
            (sortMode === 'alpha' ? ' facet-sort-toggle__btn--active' : '') +
            '" data-facet-sort="alpha">' + esc(alphaSortLabel) + '</button>' +
        '</div>';
      var fewerToggle = '<button type="button" class="facet-more-toggle" data-facet-more>✕ ' +
        esc(fewerLabel) + '</button>';
      return '<div class="facet-overlay-header">' + fewerToggle + sortToggle + '</div>' + rowsHtml;
    }

    // Render one [data-facet-source] body: one row per distinct value of
    // that field, ordered by frequency (or alphabetically once expanded —
    // see buildHostHtml). Counts are computed here and never hand-typed,
    // so a facet cannot drift out of sync with its data.
    function renderHost(host) {
      var group = host.closest ? host.closest('.facet-group') : null;
      if (group && group.hasAttribute('data-facet-pending')) return;
      FacetOverlay.attach(
        host,
        function (expanded, sortMode) { return buildHostHtml(host, expanded, sortMode); },
        // Runs after every repaint, including ones triggered by
        // FacetOverlay's own toggle/backdrop/Escape handling — refreshes
        // dimming/counts for whatever rows just appeared.
        function () { updateAvailability(model(liveGroups())); }
      );
    }

    function renderSources() {
      var hosts = panel.querySelectorAll('[data-facet-source]');
      for (var h = 0; h < hosts.length; h++) renderHost(hosts[h]);
    }

    /* ── Availability ───────────────────────────────────────────────────── */

    // For each option: how many records the result would hold if that value
    // were the facet's only selection, with every other filter AND operator
    // left as the reader set them. With default operators this is the classic
    // "items passing all OTHER groups that have this value". Zero-reach
    // options are disabled and dimmed; ticked ones never are, since unticking
    // them is the way back out.
    function updateAvailability(m) {
      var groups = m.groups, expr = m.expr;
      // The prefilter is the same for every option, so evaluate it once per
      // item rather than once per item per option.
      var pre = new Array(items.length);
      for (var i = 0; i < items.length; i++) {
        pre[i] = !prefilter || prefilter(items[i]);
      }
      var base = null;   // per item: does it pass the whole expression? (lazy)
      for (var g = 0; g < groups.length; g++) {
        var preds = groups[g].preds;
        if (!preds.length) continue;
        var key = groups[g].key;
        var inExpr = HcaFilter.hasGroup(expr, key);
        // Once per item and group (not per option): does the record pass if
        // this facet matches it (r1) / does not match it (r0)? A facet that
        // is not part of the selection yet joins with AND, so r0 is false.
        var pass1 = [], pass0 = [];
        if (!inExpr && !base) {
          base = new Array(items.length);
          for (var q = 0; q < items.length; q++) {
            m.cur = q;
            base[q] = pre[q] && HcaFilter.evalExpr(expr, m.test);
          }
        }
        for (var n = 0; n < items.length; n++) {
          if (!pre[n]) continue;
          if (inExpr) {
            m.cur = n;
            if (HcaFilter.evalExpr(expr, m.test, { force: { key: key, value: true } })) pass1.push(n);
            if (HcaFilter.evalExpr(expr, m.test, { force: { key: key, value: false } })) pass0.push(n);
          } else if (base[n]) {
            pass1.push(n);
          }
        }
        for (var b = 0; b < preds.length; b++) {
          var p = preds[b], count = 0, j;
          for (j = 0; j < pass1.length; j++) {
            if (hits(pass1[j], p)) count++;
          }
          for (j = 0; j < pass0.length; j++) {
            if (!hits(pass0[j], p)) count++;
          }
          var box  = p.box;
          var item = box.closest ? box.closest('.facet-item') : null;
          var cEl  = item ? item.querySelector('.facet-item__count') : null;
          if (cEl) cEl.textContent = num(count);
          var dim = count === 0 && !box.checked;
          box.disabled = dim;
          if (item) {
            item.style.opacity = dim ? '0.4' : '';
            item.style.cursor  = dim ? 'not-allowed' : '';
            item.title = dim ? 'Ingen resultater under de øvrige filtre' : '';
          }
        }
      }
    }

    /* ── Main ───────────────────────────────────────────────────────────── */

    function apply() {
      var groups = liveGroups();
      var m = model(groups);
      filtered = [];
      for (var i = 0; i < items.length; i++) {
        if (prefilter && !prefilter(items[i])) continue;
        m.cur = i;
        if (!HcaFilter.evalExpr(m.expr, m.test)) continue;
        filtered.push(items[i]);
      }
      updateAvailability(m);
      onChange(filtered, state(groups));
      return filtered;
    }

    function state(groups) {
      groups = groups || liveGroups();
      var active = 0;
      for (var i = 0; i < groups.length; i++) {
        active += groups[i].checked.length + (groups[i].range ? 1 : 0);
      }
      // expr = the boolean expression the result was computed from (see
      // js/filter-logic.js); the same object the active-filter bar displays.
      return { active: active, total: items.length, shown: filtered.length,
               expr: HcaFilter.shared.expr() };
    }

    function reset(silent) {
      // Fold back any open overlay first, so nothing is selected any more
      // once the boxes below are cleared, rather than only once the reader
      // next interacts with that particular facet.
      FacetOverlay.collapseAll();
      var boxes = panel.querySelectorAll(BOX_SEL);
      for (var i = 0; i < boxes.length; i++) boxes[i].checked = false;
      var rangeInputs = panel.querySelectorAll(RANGE_INPUT_SEL);
      for (var ri = 0; ri < rangeInputs.length; ri++) rangeInputs[ri].value = '';
      // Nothing is selected any more, so any facet showing a below-the-cutoff
      // value only because it was ticked should fold back to its plain
      // top-N state too.
      renderSources();
      HcaFilter.shared.sync([]);
      if (!silent) apply();
    }

    renderSources();

    // Delegated, so rows generated above (and any added later) are covered
    // without rebinding. Expand/collapse (toggle click, backdrop, Escape) is
    // handled entirely by FacetOverlay itself (js/facet-overlay.js) — a
    // selection inside the overlay does NOT close it, so narrowing down a
    // long list can tick more than one value without reopening each time.
    panel.addEventListener('change', function (ev) {
      var t = ev.target;
      if (t && t.matches && t.matches(BOX_SEL)) apply();
    });
    // Range inputs: re-filter while typing and on the spinner arrows alike.
    panel.addEventListener('input', function (ev) {
      var t = ev.target;
      if (t && t.matches && t.matches(RANGE_INPUT_SEL)) apply();
    });

    // The reader switched an AND/OR in the active-filter bar: same selection,
    // new combination.
    panel.addEventListener('hca:filters-op-change', function () { apply(); });

    // Clear boxes first, then let the page drop its own prefilter state
    // (an active letter, a search term) inside onReset, then render once.
    // Order matters: resetting the panel without clearing the prefilter would
    // leave the list still narrowed while the count claims otherwise.
    var clear = panel.querySelector('.facet-panel__clear');
    if (clear) {
      clear.addEventListener('click', function (ev) {
        ev.preventDefault();
        reset(true);
        if (opts.onReset) opts.onReset();
        apply();
      });
    }

    return {
      apply: apply,
      reset: reset,
      state: function () { return state(); },
      filtered: function () { return filtered; },
      // silent=true stages the change without rendering, so a caller resetting
      // several things at once renders once at the end rather than per step.
      setPrefilter: function (fn, silent) {
        prefilter = fn;
        return silent ? filtered : apply();
      },

      // A snapshot predicate testing the facet selection *only*, ignoring the
      // prefilter. Callers that own the prefilter — an alphabet bar, a search
      // box — need this to answer "where could I go next", which the engine's
      // own output cannot say because it is already prefiltered. Reads the DOM
      // once and closes over the result, so it is safe to run per item.
      matcher: function () {
        var m = model(liveGroups());
        return function (item) {
          var idx = indexOfItem(item);
          if (idx < 0) return false;
          m.cur = idx;
          return HcaFilter.evalExpr(m.expr, m.test);
        };
      }
    };
  }

  return { create: create };
})();
