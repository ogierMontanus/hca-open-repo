/* nav.js — layout switcher, facet toggles, facet group collapse */

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

});
