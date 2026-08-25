/* nav.js — layout switcher, facet toggles, facet group collapse,
   and bootstrap of the shared header-search typeahead. */

/* Load the search index + typeahead engine on every page that ships the
   header search bar. nav.js is the one script included site-wide, so doing
   it here lights up all inner pages (and the generated diary pages) without
   editing each file. Paths are resolved from nav.js's own URL so it works
   both at the mockup root and from the diary-pages/ subdirectory. */
(function bootstrapSearch() {
  if (!document.querySelector('.search-input')) return;  // no header bar here
  var self = document.currentScript
    || document.querySelector('script[src$="js/nav.js"]')
    || document.querySelector('script[src*="nav.js"]');
  var base = self ? self.src.replace(/js\/nav\.js.*$/, '') : '';

  function addScript(src, onload) {
    var s = document.createElement('script');
    s.src = src;
    s.async = false;            // preserve execution order (index before engine)
    if (onload) s.onload = onload;
    s.onerror = onload || null; // engine still attaches (degrades) if index 404s
    document.head.appendChild(s);
  }

  // Index first, then the engine — the engine reads the global at load time.
  addScript(base + 'data/search-index.js', function () {
    addScript(base + 'js/site-search.js');
  });
})();

document.addEventListener('DOMContentLoaded', function () {

  /* Layout switcher */
  document.querySelectorAll('.layout-switcher__btn').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var grid = document.querySelector('.result-grid');
      if (!grid) return;
      document.querySelectorAll('.layout-switcher__btn').forEach(function (b) {
        b.classList.remove('layout-switcher__btn--active');
      });
      btn.classList.add('layout-switcher__btn--active');
      var layout = btn.dataset.layout;
      grid.classList.remove('result-grid--list');
      if (layout === 'list') grid.classList.add('result-grid--list');
    });
  });

  /* Facet item click — toggle checkbox and active class */
  document.querySelectorAll('.facet-item').forEach(function (item) {
    item.addEventListener('click', function (e) {
      if (e.target.tagName === 'INPUT') return;
      var cb = item.querySelector('input[type="checkbox"]');
      if (!cb) return;
      cb.checked = !cb.checked;
      item.classList.toggle('facet-item--active', cb.checked);
    });
    var cb = item.querySelector('input[type="checkbox"]');
    if (cb && cb.checked) item.classList.add('facet-item--active');
  });

  /* Facet group collapse */
  document.querySelectorAll('.facet-group__header').forEach(function (header) {
    header.addEventListener('click', function () {
      var body = header.nextElementSibling;
      var tog = header.querySelector('.facet-group__toggle');
      if (!body) return;
      var hidden = body.style.display === 'none';
      body.style.display = hidden ? '' : 'none';
      if (tog) tog.textContent = hidden ? '▲' : '▼';
    });
  });

  /* Tab switcher */
  document.querySelectorAll('.tab-btn').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var group = btn.closest('.tabs');
      if (!group) return;
      group.querySelectorAll('.tab-btn').forEach(function (b) {
        b.classList.remove('tab-btn--active');
      });
      btn.classList.add('tab-btn--active');
    });
  });

  /* Fold toggle — "Vis N flere" / "Vis færre". Delegated (not bound per
     button) so it also covers buttons added after DOMContentLoaded, e.g.
     nation.html's client-rendered lists. See the .fold-toggle CSS comment
     in css/style.css for the markup contract. */
  document.addEventListener('click', function (ev) {
    var btn = ev.target.closest('.fold-toggle');
    if (!btn) return;
    var target = document.getElementById(btn.getAttribute('data-target'));
    if (!target) return;
    var willShow = target.hidden;
    target.hidden = !willShow;
    btn.textContent = willShow ? btn.getAttribute('data-less') : btn.getAttribute('data-more');
  });

});
