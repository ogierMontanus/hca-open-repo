/* facet-engine.js — live filtering for <aside class="facet-panel">.
 *
 * Generalises the faceting core that has been running on the works-category
 * pages (see js/category-catalogue.js): OR within a facet group, AND across
 * groups, with adaptive availability — options that would yield nothing get
 * disabled, dimmed, and their counts rewritten to match the live state.
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
 *     onChange: function (filtered) { render(filtered); }
 *   });
 *
 * Returns a controller: .apply() .reset() .state() .setPrefilter(fn)
 * setPrefilter composes an outside constraint (an alphabet bar, a search box)
 * with the facets so the two narrow together instead of overwriting each other.
 */
window.FacetEngine = (function () {
  'use strict';

  var BOX_SEL = 'input[type=checkbox][data-facet]';

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

    // Live groups only — a data-facet-pending group is invisible to the engine.
    function liveGroups() {
      var out = [];
      var els = panel.querySelectorAll('.facet-group');
      for (var g = 0; g < els.length; g++) {
        if (els[g].hasAttribute('data-facet-pending')) continue;
        var boxes = els[g].querySelectorAll(BOX_SEL);
        if (!boxes.length) continue;
        var all = [], checked = [];
        for (var j = 0; j < boxes.length; j++) {
          var p = compile(boxes[j]);
          all.push(p);
          if (boxes[j].checked) checked.push(p);
        }
        out.push({ el: els[g], preds: all, checked: checked });
      }
      return out;
    }

    // OR inside a group, AND between groups. A group with nothing ticked
    // imposes no constraint at all.
    function passes(idx, groups, skipEl) {
      for (var g = 0; g < groups.length; g++) {
        var grp = groups[g];
        if (grp.el === skipEl || !grp.checked.length) continue;
        var ok = false;
        for (var j = 0; j < grp.checked.length; j++) {
          if (hits(idx, grp.checked[j])) { ok = true; break; }
        }
        if (!ok) return false;
      }
      return true;
    }

    /* ── Option rendering ───────────────────────────────────────────────── */

    // Only one facet body can be expanded into the overlay at a time, and a
    // shared backdrop element is created lazily on first use.
    var expandedHost = null;
    var backdropEl   = null;

    function ensureBackdrop() {
      if (backdropEl) return backdropEl;
      backdropEl = document.createElement('div');
      backdropEl.className = 'facet-backdrop';
      backdropEl.setAttribute('hidden', '');
      document.body.appendChild(backdropEl);
      backdropEl.addEventListener('click', collapseExpanded);
      return backdropEl;
    }

    // Render one [data-facet-source] body: one row per distinct value of
    // that field, ordered by frequency. Counts are computed here and never
    // hand-typed, so a facet cannot drift out of sync with its data.
    function renderHost(host) {
      var group = host.closest ? host.closest('.facet-group') : null;
      if (group && group.hasAttribute('data-facet-pending')) return;

      var field = host.getAttribute('data-facet-source');
      var limit = parseInt(host.getAttribute('data-facet-limit'), 10) || 0;
      var emptyLabel = host.getAttribute('data-facet-empty-label');
      var moreLabel  = host.getAttribute('data-facet-more-label') || 'Show all';
      var fewerLabel = host.getAttribute('data-facet-fewer-label') || 'Show fewer';
      var expanded = host === expandedHost;

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
      // Frequency first; on a tie fall back to the field's sort key, which
      // for person fields is the surname (project convention — CLAUDE.md).
      rows.sort(function (a, b) {
        return b.n - a.n ||
               String(keyOf(a.value)).localeCompare(String(keyOf(b.value)), 'da');
      });

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

      var rowsHtml = visibleRows.map(function (r) {
        var checked = checkedVals[r.value] ? ' checked' : '';
        return '<label class="facet-item"><input type="checkbox" data-facet="' +
          esc(field) + '" data-match="' + esc(r.value) + '"' + checked + '>' +
          '<span class="facet-item__label">' + esc(r.label) + '</span>' +
          '<span class="facet-item__count">' + num(r.n) + '</span></label>';
      }).join('');

      // The "Uoplyst" bucket keeps a partially-covered field honest: the
      // items with no value are selectable rather than silently absent.
      if (emptyLabel && empties) {
        var eChecked = checkedEmpty ? ' checked' : '';
        rowsHtml += '<label class="facet-item"><input type="checkbox" data-facet="' +
          esc(field) + '" data-facet-empty' + eChecked + '>' +
          '<span class="facet-item__label">' + esc(emptyLabel) + '</span>' +
          '<span class="facet-item__count">' + num(empties) + '</span></label>';
      }

      var html;
      if (limit && total > limit) {
        var toggle = expanded
          ? '<button type="button" class="facet-more-toggle" data-facet-more>✕ ' + esc(fewerLabel) + '</button>'
          : '<button type="button" class="facet-more-toggle" data-facet-more>' + esc(moreLabel) + ' (' + num(total) + ') ▾</button>';
        // Expanded: the fold-back control leads, so it's reachable without
        // scrolling past however many of the (up to) hundred-plus rows the
        // reader has scrolled through. Collapsed: it trails the visible rows.
        html = expanded ? toggle + rowsHtml : rowsHtml + toggle;
      } else {
        html = rowsHtml;
      }
      host.innerHTML = html;
      if (group) group.classList.toggle('facet-group--expanded', expanded);
      // The overlay covers most of the viewport, so mark it as a dialog for
      // assistive tech — cleared again once folded back to a normal list.
      if (expanded) {
        var headerEl = group ? group.querySelector('.facet-group__header') : null;
        host.setAttribute('role', 'dialog');
        host.setAttribute('aria-modal', 'true');
        if (headerEl) host.setAttribute('aria-label', headerEl.textContent.replace(/[▲▾]/g, '').trim());
      } else {
        host.removeAttribute('role');
        host.removeAttribute('aria-modal');
        host.removeAttribute('aria-label');
      }
    }

    function renderSources() {
      var hosts = panel.querySelectorAll('[data-facet-source]');
      for (var h = 0; h < hosts.length; h++) renderHost(hosts[h]);
    }

    // Whichever direction the overlay just moved, focus lands on the toggle
    // button that reappears in the freshly-rendered host — keyboard users
    // never lose their place, regardless of whether a click, Escape, a
    // backdrop click, or a selection triggered the fold-back.
    function focusToggle(host) {
      var btn = host.querySelector('[data-facet-more]');
      if (btn) btn.focus();
    }

    function collapseExpanded() {
      if (!expandedHost) return;
      var host = expandedHost;
      expandedHost = null;
      renderHost(host);
      updateAvailability(liveGroups());
      if (backdropEl) backdropEl.setAttribute('hidden', '');
      focusToggle(host);
    }

    function expandHost(host) {
      if (expandedHost && expandedHost !== host) collapseExpanded();
      expandedHost = host;
      renderHost(host);
      updateAvailability(liveGroups());
      ensureBackdrop().removeAttribute('hidden');
      focusToggle(host);
    }

    /* ── Availability ───────────────────────────────────────────────────── */

    // For each option: how many items would remain if it were ticked, given
    // the prefilter and every OTHER group's current selection. Zero-reach
    // options are disabled and dimmed; ticked ones never are, since unticking
    // them is the way back out.
    function updateAvailability(groups) {
      // The prefilter is the same for every option, so evaluate it once per
      // item rather than once per item per option.
      var pre = new Array(items.length);
      for (var i = 0; i < items.length; i++) {
        pre[i] = !prefilter || prefilter(items[i]);
      }
      for (var g = 0; g < groups.length; g++) {
        // "All other groups" is also constant within a group — precompute
        // which items survive them, then each option only tests itself.
        var base = [];
        for (var n = 0; n < items.length; n++) {
          if (pre[n] && passes(n, groups, groups[g].el)) base.push(n);
        }
        var preds = groups[g].preds;
        for (var b = 0; b < preds.length; b++) {
          var p = preds[b], count = 0;
          for (var j = 0; j < base.length; j++) {
            if (hits(base[j], p)) count++;
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
      filtered = [];
      for (var i = 0; i < items.length; i++) {
        if (prefilter && !prefilter(items[i])) continue;
        if (!passes(i, groups, null)) continue;
        filtered.push(items[i]);
      }
      updateAvailability(groups);
      onChange(filtered, state(groups));
      return filtered;
    }

    function state(groups) {
      groups = groups || liveGroups();
      var active = 0;
      for (var i = 0; i < groups.length; i++) active += groups[i].checked.length;
      return { active: active, total: items.length, shown: filtered.length };
    }

    function reset(silent) {
      var boxes = panel.querySelectorAll(BOX_SEL);
      for (var i = 0; i < boxes.length; i++) boxes[i].checked = false;
      // Nothing is selected any more, so any facet showing a below-the-cutoff
      // value only because it was ticked (or left expanded to the overlay)
      // should fold back to its plain top-N state too.
      expandedHost = null;
      if (backdropEl) backdropEl.setAttribute('hidden', '');
      renderSources();
      if (!silent) apply();
    }

    renderSources();

    // Delegated, so rows generated above (and any added later) are covered
    // without rebinding.
    panel.addEventListener('change', function (ev) {
      var t = ev.target;
      if (!(t && t.matches && t.matches(BOX_SEL))) return;
      var host = t.closest ? t.closest('[data-facet-source]') : null;
      apply();
      // A selection made inside the overlay folds it back to the normal-size
      // list — renderHost (inside collapseExpanded) already keeps the just-
      // ticked value visible even below the top-N cutoff.
      if (expandedHost && host === expandedHost) collapseExpanded();
    });

    // Expand/collapse toggle for facets with more values than their
    // data-facet-limit. Delegated for the same reason as the change handler.
    panel.addEventListener('click', function (ev) {
      var t = ev.target;
      var btn = t && t.closest ? t.closest('[data-facet-more]') : null;
      if (!btn) return;
      ev.preventDefault();
      var host = btn.closest('[data-facet-source]');
      if (!host) return;
      if (host === expandedHost) collapseExpanded();
      else expandHost(host);
    });

    // Escape closes the overlay the same way a backdrop click does.
    document.addEventListener('keydown', function (ev) {
      if (ev.key === 'Escape' && expandedHost) collapseExpanded();
    });

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
        var groups = liveGroups();
        return function (item) {
          var idx = indexOfItem(item);
          return idx >= 0 && passes(idx, groups, null);
        };
      }
    };
  }

  return { create: create };
})();
