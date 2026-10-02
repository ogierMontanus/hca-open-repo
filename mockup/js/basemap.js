/* basemap.js — offline vector basemap for every Leaflet map in the mockup.
 *
 * Replaces remote raster tiles (CARTO began serving "API KEY REQUIRED"
 * tiles in 2026-10). Draws Natural Earth land, lakes, rivers and national
 * borders from data vendored in vendor/basemap/ (built by
 * scripts/build_mockup/build_basemap.py), so the maps need no tile server
 * and work under file:// as well as on GitHub Pages.
 *
 *   world  layer (1:50m) — loaded up front, shown at zoom < DETAIL_ZOOM
 *   europe layer (1:10m) — injected on first zoom >= DETAIL_ZOOM
 *
 * Usage: HcaBasemap.addTo(map) right after L.map(...). Requires
 * vendor/basemap/basemap-world.js to be loaded first.
 */
(function () {
  'use strict';

  var DETAIL_ZOOM = 5;
  var MAX_ZOOM = 10;   // Natural Earth 1:10m gets blobby beyond this.
  // Must match EUROPE_BBOX in build_basemap.py ([[S, W], [N, E]]).
  var EUROPE_BOUNDS = L.latLngBounds([[26, -26], [72.5, 52]]);

  var STYLE = {
    sea:     '#dde8ee',
    land:    { fill: true, fillColor: '#f5f2ea', fillOpacity: 1, stroke: true, color: '#b8c7cf', weight: 0.6 },
    lakes:   { fill: true, fillColor: '#dde8ee', fillOpacity: 1, stroke: true, color: '#b8c7cf', weight: 0.5 },
    rivers:  { color: '#a8c3d2', weight: 0.9, opacity: 0.9 },
    borders: { color: '#a59a92', weight: 0.8, dashArray: '3 2', opacity: 0.9 }
  };

  var ATTRIBUTION = 'Kortdata: <a href="https://www.naturalearthdata.com/" ' +
    'target="_blank" rel="noopener noreferrer">Natural Earth</a>';

  // Resolve vendor/basemap/ relative to this script, so pages in any
  // directory (mockup/, web/) can share it.
  var here = (document.currentScript && document.currentScript.src) || '';
  var VENDOR = here ? here.replace(/js\/basemap\.js(\?.*)?$/, 'vendor/basemap/') : 'vendor/basemap/';

  function layerGroup(data, renderer) {
    var opts = function (style) {
      return { style: function () { return style; }, renderer: renderer, interactive: false, pane: 'hcaBasemap' };
    };
    return L.layerGroup([
      L.geoJSON(data.land, opts(STYLE.land)),
      L.geoJSON(data.lakes, opts(STYLE.lakes)),
      L.geoJSON(data.rivers, opts(STYLE.rivers)),
      L.geoJSON(data.borders, opts(STYLE.borders))
    ]);
  }

  function loadScript(src, cb) {
    var s = document.createElement('script');
    s.src = src;
    s.onload = cb;
    s.onerror = function () { cb(new Error('basemap: could not load ' + src)); };
    document.head.appendChild(s);
  }

  function addTo(map) {
    map.setMaxZoom(MAX_ZOOM);
    map.getContainer().style.background = STYLE.sea;
    if (!map.getPane('hcaBasemap')) {
      map.createPane('hcaBasemap').style.zIndex = 200;   // below overlays (400) and markers (600)
    }
    var renderer = L.canvas({ pane: 'hcaBasemap', padding: 0.5 });
    map.attributionControl.addAttribution(ATTRIBUTION);

    var world = window.HCA_BASEMAP_WORLD ? layerGroup(window.HCA_BASEMAP_WORLD, renderer) : null;
    var europe = null;
    var loading = false, failed = false;

    function update() {
      var detail = map.getZoom() >= DETAIL_ZOOM;
      if (detail && !europe && !window.HCA_BASEMAP_EUROPE && !loading && !failed) {
        loading = true;
        loadScript(VENDOR + 'basemap-europe.js', function (err) {
          loading = false;
          if (err) { failed = true; return; }   // world layer stays on
          update();
        });
      }
      if (detail && !europe && window.HCA_BASEMAP_EUROPE) {
        europe = layerGroup(window.HCA_BASEMAP_EUROPE, renderer);
      }
      // The detail layer is clipped to EUROPE_BOUNDS, so the world layer
      // stays on whenever the view reaches outside it (it would otherwise
      // show doubled coastlines under the detail layer).
      var showEurope = detail && !!europe;
      var showWorld = !showEurope || !EUROPE_BOUNDS.contains(map.getBounds());
      toggle(world, showWorld);
      toggle(europe, showEurope);
    }

    function toggle(layer, on) {
      if (!layer) return;
      if (on && !map.hasLayer(layer)) layer.addTo(map);
      if (!on && map.hasLayer(layer)) map.removeLayer(layer);
    }

    map.on('zoomend moveend', update);
    map.whenReady(update);
    return map;
  }

  window.HcaBasemap = { addTo: addTo, MAX_ZOOM: MAX_ZOOM };
})();
