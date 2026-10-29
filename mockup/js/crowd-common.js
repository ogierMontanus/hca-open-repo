/* crowd-common.js — helpers shared by crowd.html, crowd-contribute.html,
 * crowd-review.html and the crowd block on persons.html.
 *
 * Needs data/crowd-queue.js (CROWD_TAXONOMY, CROWD_QUEUE, CROWD_KB_LINKS).
 * Everything that reaches the DOM goes through esc() — values come from
 * register data, from URLs and from contributors (docs/security.md).
 */
window.CrowdUI = (function () {
  'use strict';

  var T = window.CROWD_TAXONOMY || { levels: [], gaps: [], bases: [], confidence: [], identification: [],
    fields: [], sourceTypes: [], sourceResults: [], statuses: [], badges: [], mentionBuckets: [] };

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  var collator = (typeof Intl !== 'undefined' && Intl.Collator) ? new Intl.Collator('da') : { compare: function (a, b) { return a < b ? -1 : a > b ? 1 : 0; } };

  function find(list, key) {
    for (var i = 0; i < list.length; i++) if (list[i].key === key) return list[i];
    return null;
  }
  function label(list, key, fallback) {
    var it = find(list, key);
    return it ? it.da : (fallback !== undefined ? fallback : key);
  }

  var MONTHS = ['januar', 'februar', 'marts', 'april', 'maj', 'juni', 'juli', 'august', 'september', 'oktober', 'november', 'december'];
  /* '1860-03-12' → '12. marts 1860'; '1860' → '1860'; anything else untouched. */
  function fmtDate(iso) {
    var m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso || '');
    if (m) return parseInt(m[3], 10) + '. ' + MONTHS[parseInt(m[2], 10) - 1] + ' ' + m[1];
    return iso || '';
  }
  function fmtStamp(iso) {
    var m = /^(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2})/.exec(iso || '');
    return m ? fmtDate(m[1]) + ' kl. ' + m[2] : (iso || '');
  }

  var ROMAN = ['', 'I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X', 'XI'];
  /* 'Pag040141' → 'Bind IV, s. 141' (the page id is Pag{vol:02d}{page:04d}). */
  function pageLabel(pag) {
    var m = /^Pag(\d{2})(\d{4})$/.exec(pag || '');
    return m ? 'Bind ' + (ROMAN[parseInt(m[1], 10)] || m[1]) + ', s. ' + parseInt(m[2], 10) : (pag || '');
  }

  /* Surname as the register spells it: the part before the first comma,
   * without a trailing "se:" pointer or parenthesis. */
  function surnameOf(labelText) {
    var s = String(labelText || '').replace(/,?\s*\bse\s*:.*$/i, '').replace(/\s*\([^)]*\)\s*$/, '');
    return s.split(',')[0].trim();
  }

  /* Link into the generated diary page — the page is not copied into the
   * interface. `anchorDate` (YYYY-MM-DD) jumps to the dated entry in which
   * the surname was found; the #:~:text= directive additionally highlights
   * the name in browsers that support text fragments, and is ignored by the
   * rest. Internal links open in the same tab (docs/external-links.md §1). */
  function diaryHref(pag, anchorDate, name) {
    var frag = anchorDate ? '#d' + anchorDate : '#';
    if (name) frag += ':~:text=' + encodeURIComponent(name);
    return 'diary-pages/' + pag + '.html' + (frag === '#' ? '' : frag);
  }

  /* External link per docs/external-links.md: new tab, noopener noreferrer,
   * ↗ marker, screen-reader notice. */
  function externalLink(url, text, cls) {
    return '<a class="external-link' + (cls ? ' ' + cls : '') + '" href="' + esc(url) +
      '" target="_blank" rel="noopener noreferrer">' + esc(text) +
      '<span class="external-link__icon" aria-hidden="true">↗</span>' +
      '<span class="sr-only"> (åbner i nyt faneblad)</span></a>';
  }
  function safeUrl(u) { return /^https?:\/\//i.test(u || '') ? u : ''; }

  function levelBadge(key) {
    return '<span class="crowd-badge crowd-badge--' + esc(key) + '">' + esc(label(T.levels, key)) + '</span>';
  }
  function gapChips(gaps, max) {
    gaps = gaps || [];
    var shown = max ? gaps.slice(0, max) : gaps;
    var html = shown.map(function (g) {
      return '<span class="crowd-gap crowd-gap--' + esc(g) + '">' + esc(label(T.gaps, g)) + '</span>';
    }).join('');
    if (max && gaps.length > max) html += '<span class="crowd-gap crowd-gap--more">+' + (gaps.length - max) + '</span>';
    return html;
  }
  function statusPill(status) {
    return '<span class="crowd-status crowd-status--' + esc(status) + '">' + esc(label(T.statuses, status)) + '</span>';
  }
  function confPill(conf) {
    return '<span class="crowd-conf crowd-conf--' + esc(conf) + '">' + esc(label(T.confidence, conf)) + '</span>';
  }

  /* The queue record of a person, or null (documented persons are not queued). */
  var _byId = null;
  function queueRecord(id) {
    if (!_byId) {
      _byId = {};
      (window.CROWD_QUEUE || []).forEach(function (r) { _byId[r.id] = r; });
    }
    return _byId[id] || null;
  }

  function badgeInfo(key) { return find(T.badges, key); }
  function badgesHtml(keys) {
    return (keys || []).map(function (k) {
      var b = badgeInfo(k);
      return b ? '<span class="crowd-award" title="' + esc(b.desc) + '">' + esc(b.da) + '</span>' : '';
    }).join('');
  }

  function download(filename, text, type) {
    var blob = text instanceof Blob ? text : new Blob([text], { type: type || 'application/json' });
    var url = URL.createObjectURL(blob);
    var a = document.createElement('a');
    a.href = url; a.download = filename;
    document.body.appendChild(a); a.click(); document.body.removeChild(a);
    setTimeout(function () { URL.revokeObjectURL(url); }, 1000);
  }

  /* Banner telling the reader which back-end holds their contributions. */
  function modeNote(mode) {
    if (mode === 'api') {
      return '<strong>Forbundet til redaktionens server.</strong> Dine bidrag gemmes dér og gennemgås af en redaktør, før noget indgår i registret.';
    }
    return '<strong>Lokal prøvetilstand.</strong> Der er ingen server forbundet, så dine bidrag gemmes kun i denne browser. ' +
      'Når du er færdig, henter du dem som en fil og sender den til redaktionen — se »Mine bidrag«.';
  }

  /* Sign-in box for the GitHub Worker; '' with any other back-end. The login
   * link is a same-tab navigation on purpose: the OAuth round trip returns to
   * this page (an exception to the new-tab rule for external links). */
  function authBox(S) {
    if (!S.auth.enabled()) return '';
    var se = S.auth.session(), err = S.auth.error();
    var msg = err ? '<p class="crowd-err" role="alert">Login mislykkedes' + (err === 'denied' ? ' (adgang afvist hos GitHub)' : '') + '. Prøv igen.</p>' : '';
    if (se) {
      return '<p class="crowd-auth">Logget ind som <strong>' + esc(se.name) + '</strong> <span class="crowd-dim">(' + esc(se.login) + ' på GitHub)</span> · ' +
        '<button type="button" class="crowd-link" data-auth="logout">Log ud</button></p>' + msg;
    }
    return '<div class="crowd-auth">' + msg + '<a class="crowd-btn crowd-btn--primary" href="' + esc(S.auth.loginUrl()) + '">Log ind med GitHub</a> ' +
      '<span class="crowd-dim">Kræver en gratis GitHub-konto. Vi gemmer kun dit navn, brugernavn og id — aldrig din adgangskode.</span></div>';
  }
  document.addEventListener('click', function (ev) {
    var t = ev.target;
    if (t && t.getAttribute && t.getAttribute('data-auth') === 'logout' && window.CrowdStore) {
      window.CrowdStore.auth.logout(); window.location.reload();
    }
  });

  return {
    authBox: authBox, T: T, esc: esc, collator: collator, find: find, label: label, fmtDate: fmtDate, fmtStamp: fmtStamp,
    pageLabel: pageLabel, surnameOf: surnameOf, diaryHref: diaryHref, externalLink: externalLink, safeUrl: safeUrl,
    levelBadge: levelBadge, gapChips: gapChips, statusPill: statusPill, confPill: confPill,
    queueRecord: queueRecord, badgesHtml: badgesHtml, badgeInfo: badgeInfo, download: download, modeNote: modeNote
  };
})();
