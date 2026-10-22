/* active-filters.js — removable "active filter" chips above the results.
 *
 * Mirrors every filter the reader has applied in the facet panel — ticked
 * facet values, a year range, an active A–Å letter — as a chip with an ×, plus
 * "Ryd alle". Tapping a chip undoes exactly that one filter, so a filter can
 * be removed without reopening the (on phones collapsed) panel.
 *
 * Purely a view over the existing controls: removing a chip unticks the real
 * checkbox / empties the real input and dispatches the same change/input event
 * the user would have, so FacetEngine, category-catalogue.js and the page's own
 * letter bar all react exactly as they do to a direct click.
 *
 * Between every two chips sits an AND/OR dropdown. The order of the chips and
 * the operators are NOT kept here: they are read from — and written to —
 * HcaFilter.shared (js/filter-logic.js), the very object the engines evaluate
 * the result from, so the bar cannot show one operator while another is
 * applied. Chips of the same facet are clustered (a cluster is evaluated as if
 * in parentheses); a muted line spells the whole expression out. Changing a
 * dropdown fires `hca:filters-op-change` on the panel; the engine recomputes
 * and this bar redraws. The letter chip is a page-level prefilter and is
 * always AND: it has no dropdown. Without HcaFilter the bar degrades to plain
 * chips. See docs/filter-logic.md.
 *
 * Opt out with data-active-filters="off" on the .facet-panel (used where the
 * panel's boxes are static and don't filter anything).
 */
(function () {
  'use strict';

  var panel = document.querySelector('.facet-panel');
  if (!panel || panel.getAttribute('data-active-filters') === 'off') return;

  var anchor = null;
  var headers = document.querySelectorAll('.results-header');
  for (var h = 0; h < headers.length; h++) {
    if (!panel.contains(headers[h]) && !headers[h].closest('.side-acc')) { anchor = headers[h]; break; }
  }
  if (!anchor) return;

  var EN = (document.documentElement.getAttribute('lang') || '').toLowerCase().indexOf('en') === 0;
  var T = EN
    ? { group: 'Active filters', remove: 'Remove filter', clear: 'Clear all', letter: 'Letter', from: 'from', to: 'to',
        between: 'Operator between {a} and {b}', logic: 'Search logic', live: 'Filters are combined as: {x}',
        always: 'Always AND (letter filter)' }
    : { group: 'Aktive filtre', remove: 'Fjern filter', clear: 'Ryd alle', letter: 'Bogstav', from: 'fra', to: 'til',
        between: 'Operator mellem {a} og {b}', logic: 'Søgelogik', live: 'Filtrene kombineres som: {x}',
        always: 'Altid AND (bogstavfilter)' };
  // Looked up again on every draw: this script is injected by nav.js and may
  // run before js/filter-logic.js has loaded.
  var F = null;

  var bar = document.createElement('div');
  bar.className = 'active-filters';
  bar.hidden = true;
  bar.setAttribute('role', 'group');
  bar.setAttribute('aria-label', T.group);
  anchor.parentNode.insertBefore(bar, anchor.nextSibling);

  // Announces the combined expression to screen readers when it changes.
  var live = document.createElement('div');
  live.className = 'sr-only';
  live.setAttribute('aria-live', 'polite');
  bar.parentNode.insertBefore(live, bar.nextSibling);

  var title = panel.querySelector('.facet-panel__title');
  var badge = null;
  if (title) {
    badge = document.createElement('span');
    badge.className = 'facet-panel__badge';
    badge.setAttribute('aria-hidden', 'true');
    title.appendChild(badge);
  }

  function groupTitle(el) {
    var grp = el.closest('.facet-group');
    var head = grp && grp.querySelector('.facet-group__header');
    if (!head) return '';
    var clone = head.cloneNode(true);
    var tog = clone.querySelectorAll('.facet-group__toggle');
    for (var i = 0; i < tog.length; i++) tog[i].remove();
    return clone.textContent.replace(/\s+/g, ' ').trim();
  }

  function fire(el, type) {
    el.dispatchEvent(new Event(type, { bubbles: true }));
  }

  // One entry per active filter: { key, group, text, remove() }. `key` is the
  // HcaFilter term key (null for the letter chip, which is not a term).
  function collect() {
    F = window.HcaFilter || null;
    var out = [];
    var boxes = panel.querySelectorAll('input[type=checkbox]:checked');
    for (var i = 0; i < boxes.length; i++) {
      var box = boxes[i];
      if (box.closest('[data-facet-pending]') || !box.closest('.facet-group')) continue;
      var lab = box.closest('label');
      var txt = lab && lab.querySelector('.facet-item__label');
      out.push({
        key: F ? F.termKeyOfBox(box) : null,
        group: groupTitle(box),
        text: ((txt || lab || box).textContent || '').replace(/\s+/g, ' ').trim(),
        remove: (function (b) { return function () { b.checked = false; fire(b, 'change'); }; })(box)
      });
    }
    var ranges = panel.querySelectorAll('[data-facet-range]');
    for (var r = 0; r < ranges.length; r++) {
      var host = ranges[r];
      if (host.closest('[data-facet-pending]')) continue;
      var from = host.querySelector('[data-range-from]');
      var to = host.querySelector('[data-range-to]');
      var lo = from && from.value, hi = to && to.value;
      if (!lo && !hi) continue;
      var text = lo && hi ? (lo === hi ? lo : lo + '–' + hi) : (lo ? T.from + ' ' + lo : T.to + ' ' + hi);
      out.push({
        key: F ? F.termKeyOfRange(host) : null,
        group: groupTitle(host),
        text: text,
        remove: (function (f, t) { return function () {
          if (f) { f.value = ''; fire(f, 'input'); }
          if (t) { t.value = ''; fire(t, 'input'); }
        }; })(from, to)
      });
    }
    var letterBar = document.getElementById('js-alpha-bar');
    if (letterBar) {
      var chips = letterBar.querySelectorAll('a.chip[data-letter]');
      for (var c = 0; c < chips.length; c++) {
        if (chips[c].style.background) {
          out.push({
            key: null,
            letter: true,
            group: T.letter,
            text: chips[c].getAttribute('data-letter'),
            remove: function () {
              var all = letterBar.querySelector('a.chip:not([data-letter])');
              if (all) all.click();
            }
          });
          break;
        }
      }
    }
    return out;
  }

  function esc(s) {
    return String(s).replace(/[&<>"]/g, function (ch) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[ch];
    });
  }

  function chipHtml(it, i) {
    return '<button type="button" class="active-filter" data-i="' + i + '"' +
      (it.key ? ' data-key="' + esc(it.key) + '"' : '') + ' aria-label="' +
      esc(T.remove + ': ' + (it.group ? it.group + ' ' : '') + it.text) + '">' +
      (it.group ? '<span class="active-filter__group">' + esc(it.group) + ':</span>' : '') +
      '<span class="active-filter__text">' + esc(it.text) + '</span>' +
      '<span class="active-filter__x" aria-hidden="true">×</span></button>';
  }

  function opHtml(link, prev, next) {
    var opts = '';
    F.opNames().forEach(function (name) {
      opts += '<option value="' + esc(name) + '"' + (name === link.op ? ' selected' : '') + '>' + esc(name) + '</option>';
    });
    var label = T.between.replace('{a}', prev.group + ' ' + prev.text).replace('{b}', next.group + ' ' + next.text);
    return '<select class="active-filter-op active-filter-op--' + link.level + '" data-level="' + link.level +
      '" data-op-key="' + esc(link.opKey) + '" aria-label="' + esc(label) + '">' + opts + '</select>';
  }

  // The chips that are terms of the filter expression, in expression order,
  // each paired with its place in it; everything else (letter, controls the
  // engine does not know) follows without operators.
  function arrange(items) {
    var byKey = {}, used = {};
    items.forEach(function (it, i) { if (it.key) byKey[it.key] = i; });
    var logic = [];
    (F ? F.shared.snapshot() : []).forEach(function (link) {
      if (byKey[link.key] === undefined) return;
      used[byKey[link.key]] = true;
      logic.push({ i: byKey[link.key], link: link });
    });
    var rest = [];
    items.forEach(function (it, i) { if (!used[i]) rest.push(i); });
    return { logic: logic, rest: rest };
  }

  var lastHtml = null, lastLive = '';
  function refresh() {
    var items = collect();
    if (badge) {
      badge.textContent = items.length;
      badge.className = 'facet-panel__badge' + (items.length ? ' facet-panel__badge--on' : '');
    }
    var arr = arrange(items);
    var html = '', n, prev = null, cluster = false;

    for (n = 0; n < arr.logic.length; n++) {
      var cur = items[arr.logic[n].i], link = arr.logic[n].link;
      if (link.level !== 'term') {                        // a new facet cluster begins
        if (cluster) html += '</span>';
        if (link.level === 'group') html += opHtml(link, prev, cur);
        var several = n + 1 < arr.logic.length && arr.logic[n + 1].link.level === 'term';
        html += '<span class="active-filter-cluster' + (several ? ' active-filter-cluster--multi' : '') + '">';
        cluster = true;
      } else {
        html += opHtml(link, prev, cur);
      }
      html += chipHtml(cur, arr.logic[n].i);
      prev = cur;
    }
    if (cluster) html += '</span>';

    arr.rest.forEach(function (i) {
      var it = items[i];
      if (it.letter && arr.logic.length) {
        html += '<span class="active-filter-op active-filter-op--fixed" title="' + esc(T.always) + '">AND</span>';
      }
      html += chipHtml(it, i);
    });
    if (items.length > 1) {
      html += '<button type="button" class="active-filters__clear" data-clear>' + T.clear + '</button>';
    }

    var formula = '';
    if (F && arr.logic.length > 1) {
      var first = {};
      arr.logic.forEach(function (e) { if (e.link.level !== 'term') first[items[e.i].key] = true; });
      var byKey = {};
      arr.logic.forEach(function (e) { byKey[items[e.i].key] = items[e.i]; });
      formula = F.describe(F.shared.expr(), function (k) {
        var it = byKey[k];
        return it ? (first[k] && it.group ? it.group + ': ' : '') + it.text : k;
      });
      html += '<span class="active-filters__formula"><span class="active-filters__formula-label">' +
        esc(T.logic) + ':</span> ' + esc(formula) + '</span>';
    }

    if (html !== lastHtml) {
      lastHtml = html;
      bar.hidden = items.length === 0;
      // Redrawing would drop keyboard focus from the dropdown that was just used.
      var f = document.activeElement, keep = null;
      if (f && bar.contains(f) && f.classList.contains('active-filter-op')) {
        keep = { level: f.getAttribute('data-level'), key: f.getAttribute('data-op-key') };
      }
      bar.innerHTML = html;
      if (keep) {
        var sels = bar.querySelectorAll('select.active-filter-op');
        for (var s2 = 0; s2 < sels.length; s2++) {
          if (sels[s2].getAttribute('data-level') === keep.level && sels[s2].getAttribute('data-op-key') === keep.key) {
            sels[s2].focus();
            break;
          }
        }
      }
    }
    var liveText = formula ? T.live.replace('{x}', formula) : '';
    if (liveText !== lastLive) { lastLive = liveText; live.textContent = liveText; }
  }

  // Event-driven refresh: after the engine/page handlers (which were attached
  // first) have run — hence the zero-delay timeout.
  var pending = null;
  function later() {
    if (pending) return;
    pending = setTimeout(function () { pending = null; refresh(); }, 0);
  }

  bar.addEventListener('click', function (ev) {
    var clear = ev.target.closest('[data-clear]');
    if (clear) {
      var btn = panel.querySelector('.facet-panel__clear');
      if (btn) btn.click();
      later();
      return;
    }
    var chip = ev.target.closest('.active-filter');
    if (!chip) return;
    // Re-collect: the panel may have repainted since the chips were drawn.
    var all = collect(), item = null, key = chip.getAttribute('data-key');
    if (key) {
      for (var k = 0; k < all.length; k++) if (all[k].key === key) { item = all[k]; break; }
    } else {
      item = all[parseInt(chip.getAttribute('data-i'), 10)];
    }
    if (item) item.remove();
    later();
  });

  // An AND/OR dropdown: record the choice in the shared state, then let the
  // engine recompute (it listens on the panel) and redraw the bar.
  bar.addEventListener('change', function (ev) {
    F = window.HcaFilter || null;
    var sel = ev.target.closest && ev.target.closest('.active-filter-op');
    if (!sel || !F) return;
    var changed = F.shared.setOp(sel.getAttribute('data-level'), sel.getAttribute('data-op-key'), sel.value);
    if (changed) panel.dispatchEvent(new CustomEvent('hca:filters-op-change', { bubbles: true }));
    later();
  });

  panel.addEventListener('change', later);
  panel.addEventListener('input', later);
  panel.addEventListener('click', function (ev) {
    if (ev.target.closest('.facet-panel__clear')) later();
  });
  var letterBarEl = document.getElementById('js-alpha-bar');
  if (letterBarEl) letterBarEl.addEventListener('click', later);
  if (typeof MutationObserver === 'function') {
    new MutationObserver(later).observe(panel, { childList: true, subtree: true });
  }

  // Filters pre-set from the URL (?category=…, ?gender=…) are applied by the
  // page script during load, which may be after this runs.
  refresh();
  window.addEventListener('load', function () { refresh(); setTimeout(refresh, 400); });
})();
