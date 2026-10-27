/* kort-routes.js — Andersen's journeys on kort.html, from the Tidstavle.
 *
 * Every journey leg ("Fra Weimar til Jena", "Fra Rom over Albano, Velletri
 * til Neapel") whose text names two or more register places becomes a line
 * through those places, in text order. The lines are an optional layer
 * (checkbox) with a year filter; colour runs from blue (earliest year) to
 * orange (latest). Needs TimelineWire (data/timeline.js, js/timeline-wire.js)
 * and the PLACES_EXTRA coordinates; with either missing, the controls stay
 * hidden and the map is exactly what it was.
 *
 * Public API: KortRoutes.init(map, placesExtra) → { show(yearOrAll) } | null
 *
 * A hop longer than MAX_HOP_KM is dropped: with ~2,400 places a homonym
 * mismatch would otherwise draw a line across the continent.
 */
window.KortRoutes = (function () {
  'use strict';

  var EN = document.documentElement.lang === 'en';
  var T = EN
    ? { all: 'All years', legs: 'journey legs', year: 'Year', source: 'Chronology p.', newTab: ' (opens in a new tab)' }
    : { all: 'Alle år', legs: 'rejseled', year: 'År', source: 'Tidstavle s.', newTab: ' (åbner i nyt faneblad)' };
  var MAX_HOP_KM = 4500;

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  function init(map, places) {
    var ctl = document.getElementById('kort-routes-ctl');
    if (!ctl || typeof TimelineWire === 'undefined' || !TimelineWire.has() || !places) return null;

    // Build the lines once.
    var lines = [];
    TimelineWire.legs().forEach(function (leg) {
      var pts = [];
      leg.stops.forEach(function (st) {
        var p = places[st[1]];
        if (!p || typeof p.lat !== 'number' || typeof p.lon !== 'number') return;
        var last = pts[pts.length - 1];
        if (last && last.rid === st[1]) return;
        pts.push({ rid: st[1], ll: [p.lat, p.lon] });
      });
      for (var i = 1; i < pts.length; i++) {
        if (map.distance(pts[i - 1].ll, pts[i].ll) / 1000 > MAX_HOP_KM) { pts = []; break; }
      }
      if (pts.length >= 2) lines.push({ e: leg.e, year: +leg.e.a.slice(0, 4), ll: pts.map(function (q) { return q.ll; }) });
    });
    if (!lines.length) return null;

    var years = {};
    lines.forEach(function (l) { years[l.year] = (years[l.year] || 0) + 1; });
    var yearList = Object.keys(years).sort();
    var y0 = +yearList[0], y1 = +yearList[yearList.length - 1];

    function colour(y) {
      var t = y1 === y0 ? 0 : (y - y0) / (y1 - y0);
      return 'hsl(' + Math.round(210 - 190 * t) + ',72%,42%)';
    }

    var layer = L.featureGroup();
    var box = document.getElementById('kort-routes-on');
    var sel = document.getElementById('kort-routes-year');
    var count = document.getElementById('kort-routes-count');
    yearList.forEach(function (y) {
      var o = document.createElement('option');
      o.value = y; o.textContent = y + ' (' + years[y] + ')';
      sel.appendChild(o);
    });
    var allOpt = document.createElement('option');
    allOpt.value = ''; allOpt.textContent = T.all;
    sel.insertBefore(allOpt, sel.firstChild);
    sel.value = '';

    function popup(l) {
      var e = l.e;
      return '<strong>' + esc(TimelineWire.label(e)) + '</strong><br>' + TimelineWire.textHtml(e) +
        (e.u ? '<br><a class="external-link" href="' + esc(e.u) + '" target="_blank" rel="noopener noreferrer">' +
          T.source + ' ' + esc(e.p) + '<span class="external-link__icon" aria-hidden="true">↗</span>' +
          '<span class="sr-only">' + T.newTab + '</span></a>' : '');
    }

    function draw() {
      layer.clearLayers();
      var y = sel.value, shown = 0;
      lines.forEach(function (l) {
        if (y && String(l.year) !== y) return;
        var pl = L.polyline(l.ll, { color: colour(l.year), weight: 3, opacity: 0.8 });
        pl.bindPopup(popup(l));
        pl.on('mouseover', function () { pl.setStyle({ weight: 6, opacity: 1 }); });
        pl.on('mouseout', function () { pl.setStyle({ weight: 3, opacity: 0.8 }); });
        layer.addLayer(pl);
        shown++;
      });
      count.textContent = shown + ' ' + T.legs;
      return shown;
    }

    function setOn(on, fit) {
      box.checked = on;
      sel.disabled = !on;
      if (on) {
        draw();
        map.addLayer(layer);
        if (fit && sel.value) map.fitBounds(layer.getBounds(), { padding: [24, 24] });
      } else {
        map.removeLayer(layer);
        count.textContent = '';
      }
    }

    box.addEventListener('change', function () { setOn(box.checked, false); });
    sel.addEventListener('change', function () { draw(); if (sel.value) map.fitBounds(layer.getBounds(), { padding: [24, 24] }); });

    ctl.hidden = false;
    sel.disabled = true;

    // Deep link: #routes=all | #routes=1846
    var m = /(?:^|&)routes=(all|\d{4})/.exec((location.hash || '').replace(/^#/, ''));
    if (m) {
      if (m[1] !== 'all' && years[m[1]]) sel.value = m[1];
      setOn(true, true);
    }
    return { show: function (y) { sel.value = y || ''; setOn(true, true); } };
  }

  return { init: init };
})();
