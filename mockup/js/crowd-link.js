/* crowd-link.js — the crowdsourcing entry point on persons.html?reg=…
 *
 * Adds to the detail sidebar (a) editor-approved contributions as a separate,
 * attributed "tilføjet" block (the register's own text is never overwritten —
 * docs/data-model/person-editorial-emendations.md) and (b) an invitation to
 * contribute. Needs data/crowd-approved.js (tiny; the queue is not loaded).
 * Silent when the page is the list view or the person is unknown.
 */
(function () {
  'use strict';
  var reg = new URLSearchParams(location.search).get('reg');
  var sb = document.getElementById('js-detail-sidebar');
  if (!reg || !sb || typeof PERSONS_EXTRA === 'undefined' || !PERSONS_EXTRA[reg]) return;

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  var fields = window.CROWD_FIELD_LABELS || {}, conf = window.CROWD_CONF_LABELS || {};
  var claims = (window.CROWD_APPROVED || {})[reg] || [];
  var html = '';

  if (claims.length) {
    html += '<div class="info-block info-block--enriched crowd-block"><div class="info-block__header">Bidrag fra frivillige' +
      '<span class="info-block__tag">tilføjet</span></div><div class="info-block__body">' +
      '<p style="font-size:0.76rem;color:var(--color-text-muted);line-height:1.5;margin:0 0 10px">' +
      'Oplysninger fra bidragydere, gennemgået af redaktionen. De supplerer registret og erstatter det ikke.</p>' +
      claims.filter(function (c) { return c.f !== 'identification'; }).map(function (c) {
        return '<div class="crowd-claim"><strong>' + esc(fields[c.f] || c.f) + ':</strong> ' + esc(c.v) +
          ' <span class="crowd-conf crowd-conf--' + esc(c.c) + '">' + esc(conf[c.c] || c.c) + '</span>' +
          '<br><span style="font-size:0.74rem;color:var(--color-text-muted)">' + esc(c.by) + ' · ' + esc(c.d) +
          (c.s ? ' · ' + esc(c.s.length > 140 ? c.s.slice(0, 140) + '…' : c.s) : '') + '</span></div>';
      }).join('') + '</div></div>';
  }

  html += '<div class="info-block crowd-block"><div class="info-block__header">Kender du noget til personen?</div><div class="info-block__body">' +
    '<p style="font-size:0.8rem;color:var(--color-text-muted);line-height:1.5;margin:0 0 10px">' +
    'Mangler der navn, årstal eller sted? Slægtsforskere og lokalkendte kan bidrage med dokumenterede oplysninger.</p>' +
    '<a href="crowd-contribute.html?reg=' + encodeURIComponent(reg) + '" style="font-size:0.86rem;font-weight:600">Bidrag til identifikationen →</a></div></div>';

  sb.insertAdjacentHTML('beforeend', html);
})();
