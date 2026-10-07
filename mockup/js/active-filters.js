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
 * letter bar all react exactly as they do to a direct click. Nothing here keeps
 * filter state of its own.
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
    ? { group: 'Active filters', remove: 'Remove filter', clear: 'Clear all', letter: 'Letter', from: 'from', to: 'to' }
    : { group: 'Aktive filtre', remove: 'Fjern filter', clear: 'Ryd alle', letter: 'Bogstav', from: 'fra', to: 'til' };

  var bar = document.createElement('div');
  bar.className = 'active-filters';
  bar.hidden = true;
  bar.setAttribute('role', 'group');
  bar.setAttribute('aria-label', T.group);
  anchor.parentNode.insertBefore(bar, anchor.nextSibling);

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

  // One entry per active filter: { group, text, remove() }.
  function collect() {
    var out = [];
    var boxes = panel.querySelectorAll('input[type=checkbox]:checked');
    for (var i = 0; i < boxes.length; i++) {
      var box = boxes[i];
      if (box.closest('[data-facet-pending]') || !box.closest('.facet-group')) continue;
      var lab = box.closest('label');
      var txt = lab && lab.querySelector('.facet-item__label');
      out.push({
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

  var last = null;
  function refresh() {
    var items = collect();
    var sig = items.map(function (i) { return i.group + '\u0001' + i.text; }).join('\u0002');
    if (badge) {
      badge.textContent = items.length;
      badge.className = 'facet-panel__badge' + (items.length ? ' facet-panel__badge--on' : '');
    }
    if (sig === last) return;
    last = sig;
    bar.hidden = items.length === 0;
    var html = '';
    for (var i = 0; i < items.length; i++) {
      html += '<button type="button" class="active-filter" data-i="' + i + '" aria-label="' +
        esc(T.remove + ': ' + (items[i].group ? items[i].group + ' ' : '') + items[i].text) + '">' +
        (items[i].group ? '<span class="active-filter__group">' + esc(items[i].group) + ':</span>' : '') +
        '<span class="active-filter__text">' + esc(items[i].text) + '</span>' +
        '<span class="active-filter__x" aria-hidden="true">×</span></button>';
    }
    if (items.length > 1) {
      html += '<button type="button" class="active-filters__clear" data-clear>' + T.clear + '</button>';
    }
    bar.innerHTML = html;
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
    var item = collect()[parseInt(chip.getAttribute('data-i'), 10)];
    if (item) item.remove();
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
