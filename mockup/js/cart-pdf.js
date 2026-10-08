/* cart-pdf.js — builds the printable document behind cart.html's
 * "Download som PDF": a cover page, one A4 sheet per selected diary page
 * (text, footnotes, clickable name lists, Det Kgl. Bibliotek link) and an
 * appendix with the cart's register entries.
 *
 * The page data comes from data/diary-print/vol-<roman>.js, produced by
 * scripts/build_mockup/build_diary_print.py and loaded on demand with plain
 * <script> tags (fetch() is blocked under file://). Only the volumes the cart
 * actually needs are loaded.
 *
 * Public API:
 *   CartPdf.build(items, opts) → Promise<boolean>
 *       items  Cart.all()
 *       opts   { typeLabel: {type: label}, typeHref: {type: fn(rid)} }  (cart.html's
 *               own maps, so links stay identical to the on-screen list)
 *       Fills #js-print-doc and resolves true; resolves false when there is
 *       nothing to build from (no diary pages, or no print data loaded) so the
 *       caller can fall back to the plain table print.
 *   CartPdf.clear()   empties #js-print-doc again (call after printing)
 *
 * Styling lives in css/cart-print.css (print-only; #js-print-doc is hidden on
 * screen). Every name, id and the KB address is a real <a href> with an
 * absolute URL, so the links survive "Save as PDF".
 */
window.CartPdf = (function () {
  'use strict';

  var ROMAN = ['', 'I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X', 'XI'];
  var MONTHS = {
    da: ['januar', 'februar', 'marts', 'april', 'maj', 'juni', 'juli', 'august', 'september', 'oktober', 'november', 'december'],
    en: ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
  };
  var TYPE_PAGE = { person: 'persons.html', place: 'place.html', work: 'work.html' };
  var OVERVIEW_CAP = 20;

  var L = {
    da: {
      kicker: "HCA'S HVEM-HVAD-HVOR · KURV",
      title: 'Valgte dagbogssider',
      pages: function (n) { return n + (n === 1 ? ' dagbogsside' : ' dagbogssider'); },
      contents: 'Kurvens indhold', scope: 'Omfang', overview: 'Samlet oversigt over navne',
      docinfo: 'Dokumentoplysninger',
      scopeText: function (n, vols, yrs) {
        return 'Denne PDF-fil samler ' + n + (n === 1 ? ' dagbogsside' : ' dagbogssider') +
          ' fra bind ' + vols + (yrs ? ' fra perioden ' + yrs : '') + '.';
      },
      counts: { diary: ['dagbogsside', 'dagbogssider'], person: ['person', 'personer'], place: ['sted', 'steder'], work: ['værk', 'værker'] },
      persons: 'Personer', places: 'Steder', works: 'Værker', dates: 'Datoer',
      pagesWord: 'sider', more: function (n) { return '… og ' + n + ' flere'; },
      generated: 'Genereret', source: 'Kilde', sourceVal: "H.C. Andersens dagbøger (Det Kgl. Bibliotek) og sitets tilknyttede registerdata",
      site: 'Websted',
      volume: 'Bind', page: 'side', year: 'Dagbogsår', text: 'Dagbogstekst', lineMarks: 'Linjemarkering',
      notes: 'Fodnoter', related: 'Tilknyttet dagbogsside', kb: 'Kilde: Det Kgl. Bibliotek', sheet: 'Side',
      noText: 'Teksten til denne side er ikke tilgængelig i udskriften.',
      appendix: 'Valgte registerposter', colType: 'Type', colId: 'ID', colTitle: 'Titel', colUrl: 'URL', locale: 'da-DK'
    },
    en: {
      kicker: 'THE HCA WHO-WHAT-WHERE · CART',
      title: 'Selected diary pages',
      pages: function (n) { return n + (n === 1 ? ' diary page' : ' diary pages'); },
      contents: 'Cart contents', scope: 'Scope', overview: 'Overview of names',
      docinfo: 'Document information',
      scopeText: function (n, vols, yrs) {
        return 'This PDF collects ' + n + (n === 1 ? ' diary page' : ' diary pages') +
          ' from volume ' + vols + (yrs ? ', covering ' + yrs : '') + '.';
      },
      counts: { diary: ['diary page', 'diary pages'], person: ['person', 'persons'], place: ['place', 'places'], work: ['work', 'works'] },
      persons: 'Persons', places: 'Places', works: 'Works', dates: 'Dates',
      pagesWord: 'pages', more: function (n) { return '… and ' + n + ' more'; },
      generated: 'Generated', source: 'Source', sourceVal: "H.C. Andersen's diaries (Royal Danish Library) and the site's linked register data",
      site: 'Site',
      volume: 'Volume', page: 'page', year: 'Diary year', text: 'Diary text', lineMarks: 'Line markers',
      notes: 'Footnotes', related: 'Linked to this diary page', kb: 'Source: Royal Danish Library', sheet: 'Page',
      noText: 'The text of this page is not available in the printout.',
      appendix: 'Selected register entries', colType: 'Type', colId: 'ID', colTitle: 'Title', colUrl: 'URL', locale: 'en-GB'
    }
  };

  function lang() { return document.documentElement.lang === 'en' ? 'en' : 'da'; }
  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c];
    });
  }
  function abs(href) {
    try { return new URL(href, location.href).href; } catch (e) { return href; }
  }
  function link(href, text, cls) {
    return '<a' + (cls ? ' class="' + cls + '"' : '') + ' href="' + esc(abs(href)) + '">' + text + '</a>';
  }

  // "Pag040194" → { vol: 'IV', page: 194 }
  function parseRid(rid) {
    var m = /^Pag(\d{2})(\d{4})$/.exec(rid);
    if (!m) return null;
    return { vol: ROMAN[parseInt(m[1], 10)] || '?', volNum: parseInt(m[1], 10), page: parseInt(m[2], 10) };
  }

  // --- loading -----------------------------------------------------------
  var loading = {};
  function loadVolume(vol) {
    if (loading[vol]) return loading[vol];
    loading[vol] = new Promise(function (resolve) {
      var s = document.createElement('script');
      s.src = 'data/diary-print/vol-' + vol + '.js';
      s.onload = function () { resolve(true); };
      s.onerror = function () { resolve(false); };
      document.head.appendChild(s);
    });
    return loading[vol];
  }

  // --- helpers over one page's markup ------------------------------------
  function isoToLabel(iso, t, lg) {
    var m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso);
    return m ? m[3] + '.' + m[2] + '.' + m[1] : iso;
  }

  // Parses the stored markup, prefixes the margin line numbers with the page
  // reference ("IV-197-5"), stamps each dated paragraph with its date, lifts
  // the footnotes out. Returns { textHtml, notesHtml, marks[], dates[] }.
  function prepareText(html, pr) {
    var box = document.createElement('div');
    box.innerHTML = html;
    var notes = [];
    box.querySelectorAll('aside[role="note"]').forEach(function (a) {
      notes.push(a.innerHTML);
      a.parentNode.removeChild(a);
    });
    var marks = [];
    box.querySelectorAll('i[data-n]').forEach(function (i) {
      var lbl = pr.vol + '-' + pr.page + '-' + i.getAttribute('data-n');
      i.setAttribute('data-n', lbl);
      marks.push(lbl);
    });
    var dates = [];
    box.querySelectorAll('div.p[id]').forEach(function (p) {
      var m = /^d(\d{4}-\d{2}-\d{2})$/.exec(p.id);
      if (!m) return;
      p.removeAttribute('id');
      var d = isoToLabel(m[1]);
      if (dates.indexOf(d) === -1) dates.push(d);
      var sp = document.createElement('span');
      sp.className = 'pdf-date';
      sp.textContent = m[1];
      p.insertBefore(sp, p.firstChild);
    });
    return { textHtml: box.innerHTML, notesHtml: notes.join(' · '), marks: marks, dates: dates };
  }

  function namesHtml(ents, type) {
    return ents.filter(function (e) { return e[0] === type; }).map(function (e) {
      return link(TYPE_PAGE[type] + '?reg=' + encodeURIComponent(e[1]), esc(e[2]));
    }).join(', ');
  }

  function yearOf(rec) {
    var m = /(\d{4})/.exec((rec && rec.d) || '');
    return m ? m[1] : '';
  }

  // --- sections ------------------------------------------------------------
  function coverHtml(rows, items, appendixItems, t, lg) {
    var counts = {};
    items.forEach(function (it) { counts[it.type] = (counts[it.type] || 0) + 1; });
    var order = ['diary', 'person', 'place', 'work'];
    var contents = order.filter(function (k) { return counts[k]; }).map(function (k) {
      return counts[k] + ' ' + (t.counts[k][counts[k] === 1 ? 0 : 1]);
    }).join(' · ');

    var vols = [], years = [];
    rows.forEach(function (r) {
      if (vols.indexOf(r.pr.vol) === -1) vols.push(r.pr.vol);
      var y = yearOf(r.rec);
      if (y) years.push(+y);
    });
    var yrs = years.length ? (Math.min.apply(null, years) === Math.max.apply(null, years)
      ? String(years[0]) : Math.min.apply(null, years) + '–' + Math.max.apply(null, years)) : '';

    // Union of the names across all pages, most-mentioned first.
    var tally = { person: {}, place: {}, work: {} };
    rows.forEach(function (r) {
      ((r.rec && r.rec.e) || []).forEach(function (e) {
        var b = tally[e[0]];
        if (!b) return;
        (b[e[1]] = b[e[1]] || { rid: e[1], label: e[2], n: 0 }).n++;
      });
    });
    var overview = '';
    [['person', t.persons], ['place', t.places], ['work', t.works]].forEach(function (pair) {
      var list = Object.keys(tally[pair[0]]).map(function (k) { return tally[pair[0]][k]; });
      if (!list.length) return;
      list.sort(function (a, b) { return b.n - a.n || a.label.localeCompare(b.label, 'da'); });
      var shown = list.slice(0, OVERVIEW_CAP).map(function (x) {
        return link(TYPE_PAGE[pair[0]] + '?reg=' + encodeURIComponent(x.rid), esc(x.label)) +
          (x.n > 1 ? ' <span class="pdf-n">(' + x.n + ')</span>' : '');
      }).join(', ');
      if (list.length > OVERVIEW_CAP) shown += ', <span class="pdf-n">' + esc(t.more(list.length - OVERVIEW_CAP)) + '</span>';
      overview += '<p><b>' + esc(pair[1]) + ':</b> ' + shown + '</p>';
    });

    var d = new Date();
    var gen = d.toLocaleDateString(t.locale, { day: 'numeric', month: 'long', year: 'numeric' });
    var nDiary = rows.length;

    return '<section class="pdf-cover">' +
      '<div class="pdf-kicker">' + esc(t.kicker) + '</div>' +
      '<h1>' + esc(t.title) + '</h1>' +
      '<p class="pdf-sub">' + esc(nDiary ? t.pages(nDiary) : contents) + '</p>' +
      '<div class="pdf-block"><h2>' + esc(t.contents) + '</h2><p>' + esc(contents) + '</p></div>' +
      (nDiary ? '<div class="pdf-block"><h2>' + esc(t.scope) + '</h2><p>' + esc(t.scopeText(nDiary, vols.join(', '), yrs)) + '</p></div>' : '') +
      (overview ? '<div class="pdf-block pdf-overview"><h2>' + esc(t.overview) + '</h2>' + overview + '</div>' : '') +
      '<div class="pdf-block pdf-docinfo"><h2>' + esc(t.docinfo) + '</h2>' +
      '<p>' + esc(t.generated) + ': ' + esc(gen) + '<br>' + esc(t.source) + ': ' + esc(t.sourceVal) + '<br>' +
      esc(t.site) + ': ' + link('index.html', esc("HCA's Hvem-hvad-hvor")) + '</p></div>' +
      '</section>';
  }

  function pageHtml(r, n, total, t) {
    var pr = r.pr, rec = r.rec;
    var pageUrl = 'diary-pages/' + r.rid + '.html';
    var head = '<div class="pdf-head"><span>' + esc(t.kicker.split(' · ')[0]) + '</span>' +
      '<span>' + link(pageUrl, esc(t.volume.toUpperCase() + ' ' + pr.vol + ' · ' + t.page.toUpperCase() + ' ' + pr.page)) + '</span></div>';
    var title = '<h1 class="pdf-title">' + link(pageUrl, esc(t.volume + ' ' + pr.vol + ', ' + t.page + ' ' + pr.page)) + '</h1>';

    if (!rec) {
      return '<section class="pdf-page">' + head + title +
        '<p class="pdf-missing">' + esc(t.noText) + '</p>' +
        '<div class="pdf-foot"><span>' + link(pageUrl, esc(abs(pageUrl))) + '</span><b>' + esc(t.sheet) + ' ' + n + ' / ' + total + '</b></div></section>';
    }

    var yr = yearOf(rec);
    var prep = rec.h ? prepareText(rec.h, pr) : { textHtml: '', notesHtml: '', marks: [], dates: [] };
    var marks = prep.marks.slice(0, 3).join(', ') + (prep.marks.length > 3 ? ' …' : '');

    var related = '';
    [['person', t.persons], ['place', t.places], ['work', t.works]].forEach(function (pair) {
      var h = namesHtml(rec.e || [], pair[0]);
      if (h) related += '<tr><th>' + esc(pair[1]) + ':</th><td>' + h + '</td></tr>';
    });
    if (prep.dates.length) related += '<tr><th>' + esc(t.dates) + ':</th><td>' + esc(prep.dates.join(', ')) + '</td></tr>';

    var kbLine = rec.k
      ? esc(t.kb) + ' · ' + esc(t.volume) + ' ' + esc(pr.vol) + ', ' + esc(t.page) + ' ' + pr.page + '<br>' + link(rec.k, esc(rec.k))
      : link(pageUrl, esc(abs(pageUrl)));

    return '<section class="pdf-page">' + head + title +
      (yr ? '<p class="pdf-year">' + esc(t.year) + ': ' + esc(yr) + '</p>' : '') +
      '<div class="pdf-rule"></div>' +
      (prep.textHtml
        ? '<div class="pdf-label">' + esc(t.text) + (marks ? ' <span class="pdf-marks">' + esc(t.lineMarks) + ': ' + esc(marks) + '</span>' : '') + '</div>' +
          '<div class="entry-text edition-text pdf-text">' + prep.textHtml + '</div>'
        : '<p class="pdf-missing">' + esc(t.noText) + '</p>') +
      (prep.notesHtml ? '<div class="pdf-notes"><div class="pdf-label">' + esc(t.notes) + '</div><div>' + prep.notesHtml + '</div></div>' : '') +
      '<div class="pdf-related"><div class="pdf-label">' + esc(t.related) + '</div>' +
      '<table>' + related + '</table></div>' +
      '<div class="pdf-foot"><span>' + kbLine + '</span><b>' + esc(t.sheet) + ' ' + n + ' / ' + total + '</b></div>' +
      '</section>';
  }

  function appendixHtml(items, t, opts) {
    var rows = items.map(function (it) {
      var fn = opts.typeHref && opts.typeHref[it.type];
      var href = fn ? fn(it.rid) : '#';
      var u = abs(href);
      return '<tr><td>' + esc((opts.typeLabel && opts.typeLabel[it.type]) || it.type) + '</td>' +
        '<td>' + link(href, esc(it.rid)) + '</td>' +
        '<td>' + link(href, esc(it.label)) + '</td>' +
        '<td class="pdf-url">' + link(href, esc(u)) + '</td></tr>';
    }).join('');
    return '<section class="pdf-appendix"><h2>' + esc(t.appendix) + ' (' + items.length + ')</h2>' +
      '<table class="pdf-table"><thead><tr><th>' + esc(t.colType) + '</th><th>' + esc(t.colId) + '</th><th>' +
      esc(t.colTitle) + '</th><th>' + esc(t.colUrl) + '</th></tr></thead><tbody>' + rows + '</tbody></table></section>';
  }

  // --- entry point -----------------------------------------------------
  function build(items, opts) {
    opts = opts || {};
    var lg = lang(), t = L[lg];
    var host = document.getElementById('js-print-doc');
    if (!host) return Promise.resolve(false);

    var diary = items.filter(function (i) { return i.type === 'diary' && parseRid(i.rid); })
      .sort(function (a, b) { return a.rid < b.rid ? -1 : a.rid > b.rid ? 1 : 0; });
    var register = items.filter(function (i) { return i.type !== 'diary'; });
    if (!diary.length) return Promise.resolve(false);

    var vols = [];
    diary.forEach(function (i) { var v = parseRid(i.rid).vol; if (vols.indexOf(v) === -1) vols.push(v); });

    return Promise.all(vols.map(loadVolume)).then(function () {
      var data = window.DIARY_PRINT || {};
      var rows = diary.map(function (i) { return { rid: i.rid, pr: parseRid(i.rid), rec: data[i.rid] || null }; });
      // Nothing loaded at all (data not built / blocked) → let the caller fall back.
      if (!rows.some(function (r) { return r.rec; })) return false;

      var html = coverHtml(rows, items, register, t, lg);
      rows.forEach(function (r, idx) { html += pageHtml(r, idx + 1, rows.length, t); });
      if (register.length) html += appendixHtml(register, t, opts);
      host.innerHTML = html;
      return true;
    });
  }

  function clear() {
    var host = document.getElementById('js-print-doc');
    if (host) host.innerHTML = '';
  }

  return { build: build, clear: clear };
})();
