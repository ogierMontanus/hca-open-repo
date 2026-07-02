/* timeline-wire.js — renders the Tidslinje (timeline) view in diaries.html.
 *
 * Depends on TIMELINE_INDEX defined by mockup/data/timeline-index.js,
 * loaded via a plain <script> tag (file://-safe).
 * When that file is absent the timeline button stays hidden.
 *
 * Public API (attached to window):
 *   TimelineWire.render(container)  — populate #timeline-results and return
 *       a controller, or null when no data.
 */
window.TimelineWire = (function () {
  'use strict';

  function hasData() { return typeof TIMELINE_INDEX !== 'undefined'; }

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];
    });
  }

  /* Format YYYY-MM-DD → "2. apr. 1805" (Danish abbreviated).
   * Day or month = 00 means unknown; fall back gracefully. */
  var DA_MONTHS = ['jan.','feb.','mar.','apr.','maj','jun.',
                   'jul.','aug.','sep.','okt.','nov.','dec.'];
  function fmtDate(iso) {
    if (!iso) return '';
    var parts = iso.split('-');
    if (parts.length !== 3) return iso;
    var y = parts[0], m = parseInt(parts[1], 10), d = parseInt(parts[2], 10);
    if (!m) return y;
    var ms = DA_MONTHS[m - 1] || m;
    if (!d) return ms + ' ' + y;
    return d + '. ' + ms + ' ' + y;
  }

  function render(container) {
    if (!container || !hasData()) return null;

    /* Group events by year. */
    var byYear = {};
    var years  = [];
    for (var i = 0; i < TIMELINE_INDEX.length; i++) {
      var ev = TIMELINE_INDEX[i];
      if (!byYear[ev.y]) { byYear[ev.y] = []; years.push(ev.y); }
      byYear[ev.y].push(ev);
    }
    years.sort();

    var html = [];
    for (var yi = 0; yi < years.length; yi++) {
      var y    = years[yi];
      var evts = byYear[y];
      /* Year heading comes from first event that has one. */
      var heading = '';
      for (var ei = 0; ei < evts.length; ei++) {
        if (evts[ei].hda) { heading = evts[ei].hda; break; }
      }

      html.push('<section class="tl-year" id="tl-' + esc(y) + '">');
      html.push('<h2 class="tl-year__label"><span class="tl-year__num">' +
                esc(y) + '</span>');
      if (heading) {
        html.push(' <span class="tl-year__heading">' + esc(heading) + '</span>');
      }
      html.push('</h2>');
      html.push('<ul class="tl-events">');

      for (var ej = 0; ej < evts.length; ej++) {
        var e   = evts[ej];
        var dt  = fmtDate(e.d);
        /* xda/xen may contain HTML markup from the source database. */
        var txt = e.xda || '';
        var ttl = e.tda ? '<strong>' + esc(e.tda) + '</strong> ' : '';
        html.push('<li class="tl-event">');
        if (dt) {
          html.push('<span class="tl-event__date">' + esc(dt) + '</span>');
        }
        html.push('<span class="tl-event__text">' + ttl + txt + '</span>');
        html.push('</li>');
      }

      html.push('</ul></section>');
    }

    container.innerHTML = html.join('');
    return { yearCount: years.length, eventCount: TIMELINE_INDEX.length };
  }

  return { render: render, hasData: hasData };
})();
