/* place-stats.js — fills the place counts on the landing page from
   data/places-stats.js (PLACE_STATS, written by build_places_extra.py), so
   they follow the register instead of being typed by hand. Every span keeps
   its static text as a fallback for a fresh clone without the build.

   <span data-place-stat="total">2.433</span>      places in the register
   <span data-place-stat="geocoded">2.421</span>   places with coordinates
   <span data-place-stat="diaryRefs">18.737</span> place mentions in the diaries */
(function () {
  'use strict';
  if (typeof PLACE_STATS === 'undefined') return;
  var en = (document.documentElement.getAttribute('lang') || '').toLowerCase().indexOf('en') === 0;
  var els = document.querySelectorAll('[data-place-stat]');
  for (var i = 0; i < els.length; i++) {
    var n = PLACE_STATS[els[i].getAttribute('data-place-stat')];
    if (typeof n === 'number') els[i].textContent = n.toLocaleString(en ? 'en-US' : 'da-DK');
  }
})();
