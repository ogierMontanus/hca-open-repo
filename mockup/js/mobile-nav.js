/* mobile-nav.js — phone behaviour for the facet panel.
 *
 * On phones (see css/mobile.css) the facet panel is a closed "Filtrér" bar
 * above the results; tapping the bar opens the filter groups, and a "Vis N
 * resultater" button at the bottom of the open panel folds it away again.
 * Desktop keeps the always-open sidebar: the toggle is only wired (and the
 * header only announced as a button) while the viewport is narrow.
 *
 * Open/closed is the class .facet-panel--m-open; the panel itself keeps its
 * overflow untouched (iOS Safari sticky + fixed trap — see CLAUDE.md).
 */
(function () {
  'use strict';

  var panel = document.querySelector('.facet-panel');
  if (!panel) return;
  var header = panel.querySelector('.facet-panel__header');
  if (!header) return;

  var EN = (document.documentElement.getAttribute('lang') || '').toLowerCase().indexOf('en') === 0;
  var mq = window.matchMedia ? window.matchMedia('(max-width: 760px)') : null;

  var done = document.createElement('button');
  done.type = 'button';
  done.className = 'facet-panel__done';
  panel.appendChild(done);

  function resultCount() {
    var el = document.querySelector('.results-count strong');
    return el ? el.textContent.trim() : '';
  }
  function labelDone() {
    var n = resultCount();
    done.textContent = EN ? ('Show ' + (n ? n + ' ' : '') + 'results') : ('Vis ' + (n ? n + ' ' : '') + 'resultater');
  }

  function setOpen(open) {
    panel.classList.toggle('facet-panel--m-open', open);
    if (mq && mq.matches) header.setAttribute('aria-expanded', open ? 'true' : 'false');
    if (open) labelDone();
  }
  function isOpen() { return panel.classList.contains('facet-panel--m-open'); }

  function wire() {
    var narrow = !mq || mq.matches;
    if (narrow) {
      header.setAttribute('role', 'button');
      header.setAttribute('tabindex', '0');
      header.setAttribute('aria-expanded', isOpen() ? 'true' : 'false');
    } else {
      header.removeAttribute('role');
      header.removeAttribute('tabindex');
      header.removeAttribute('aria-expanded');
    }
  }
  wire();
  if (mq && mq.addEventListener) mq.addEventListener('change', wire);

  header.addEventListener('click', function (ev) {
    if (mq && !mq.matches) return;
    if (ev.target.closest('.facet-panel__clear')) return;   // "Nulstil" keeps its own job
    setOpen(!isOpen());
  });
  header.addEventListener('keydown', function (ev) {
    if (mq && !mq.matches) return;
    if (ev.target !== header) return;
    if (ev.key === 'Enter' || ev.key === ' ') { ev.preventDefault(); setOpen(!isOpen()); }
  });

  // Keep the button's count live while the panel is open.
  panel.addEventListener('change', function () { setTimeout(labelDone, 0); });
  panel.addEventListener('input', function () { setTimeout(labelDone, 0); });

  done.addEventListener('click', function () {
    setOpen(false);
    var target = document.querySelector('.results-count');
    if (target && target.scrollIntoView) target.scrollIntoView({ behavior: 'smooth', block: 'start' });
  });
})();
