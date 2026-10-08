/* cart-pdf.js — writes the PDF behind cart.html's "Download som PDF" directly
 * in the browser (pdfmake), without the print dialog: a cover page, one A4
 * sheet per selected diary page (text, footnotes, clickable name lists, Det
 * Kgl. Bibliotek link) and an appendix with the cart's register entries.
 *
 * ── Why not window.print() any more ──────────────────────────────────────
 * The old route built the whole document as HTML (thousands of absolutely
 * positioned, flexed sections) and handed it to the browser's print engine,
 * which lays out and rasterises a preview of every page before offering
 * "Save as PDF" — minutes for a big cart, with the tab frozen meanwhile. Here
 * the layout is computed straight from the data records (no DOM, no print
 * preview) and the file is saved as soon as it is done.
 *
 * ── Where the work runs ──────────────────────────────────────────────────
 * Laying out and writing thousands of pages takes tens of seconds even
 * without a print engine (pdfmake is synchronous), so it runs in a Web Worker
 * and the page stays responsive; the button shows progress. The site opens
 * from file:// as well as from a server, and file:// pages cannot start a
 * worker from a script file or importScripts() another file — so the worker
 * is a Blob assembled from text: the library source (carried as a string by
 * vendor/pdfmake/pdf-assets.js) plus the source of makeBuilder() below,
 * obtained with Function.prototype.toString(). That is why makeBuilder() is
 * self-contained and DOM-free (a worker has no document): it parses the
 * edition markup with a small tokenizer instead of innerHTML. If a worker
 * cannot be started (blocked, very old browser) the same builder runs on the
 * main thread — slower to respond, same result.
 *
 * ── Data ─────────────────────────────────────────────────────────────────
 * Page data comes from data/diary-print/vol-<roman>.js, produced by
 * scripts/build_mockup/build_diary_print.py and loaded on demand with plain
 * <script> tags (fetch() is blocked under file://); only the volumes the cart
 * needs are loaded. The library + embedded fonts come from
 * vendor/pdfmake/pdf-assets.js (built by scripts/build_mockup/build_pdf_assets.py),
 * loaded on the first click only.
 *
 * Public API:
 *   CartPdf.download(items, opts) → Promise<boolean>
 *       items  Cart.all()
 *       opts   { typeLabel: {type: label}, typeHref: {type: fn(rid)},   (cart.html's
 *                own maps, so links stay identical to the on-screen list)
 *                onStatus: fn(text) }   progress text for the button
 *       Saves the PDF and resolves true; resolves false when the library or the
 *       diary data could not be loaded, so the caller can fall back to the
 *       plain table print. Rejects on an error while building.
 *
 * Every name, id and the KB address is a real link annotation with an
 * absolute URL; the KB address is also visible text.
 */
window.CartPdf = (function () {
  'use strict';

  // ════════════════════════════════════════════════════════════════════════
  // The document builder. Self-contained and DOM-free: its source text is
  // shipped to the worker (see the header), so it may only use its own body
  // and standard globals — no reference to anything outside this function.
  // ════════════════════════════════════════════════════════════════════════
  function makeBuilder() {
    var TYPE_PAGE = { person: 'persons.html', place: 'place.html', work: 'work.html' };
    var OVERVIEW_CAP = 20;

    // Palette (the reference PDF's: wine headings, teal sub-labels, grey lists).
    var WINE = '#7a1f2b', TEAL = '#1d5a5a', BLUE = '#1e5f8c', RULE = '#ddcfbd';
    var GREY = '#666666', DARK = '#222222';

    // A4 geometry in pt (1 mm = 2.8346 pt).
    var MM = 2.8346;
    var PAGE_W = 595.28;
    var PAGE_MARGIN = 14 * MM;
    var CONTENT_W = PAGE_W - 2 * PAGE_MARGIN;
    var TEXT_INDENT = 17 * MM;   // room for the "IV-197-5" line markers
    var DATE_COL = 22 * MM;      // right margin holding the date of a dated entry

    var FONTS = {
      Serif: { normal: 'LiberationSerif-Regular.ttf', bold: 'LiberationSerif-Bold.ttf', italics: 'LiberationSerif-Italic.ttf', bolditalics: 'LiberationSerif-BoldItalic.ttf' },
      Sans: { normal: 'LiberationSans-Regular.ttf', bold: 'LiberationSans-Bold.ttf', italics: 'LiberationSans-Regular.ttf', bolditalics: 'LiberationSans-Bold.ttf' }
    };

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
        more: function (n) { return '… og ' + n + ' flere'; },
        generated: 'Genereret', source: 'Kilde', sourceVal: 'H.C. Andersens dagbøger (Det Kgl. Bibliotek) og sitets tilknyttede registerdata',
        site: 'Websted',
        volume: 'Bind', page: 'side', year: 'Dagbogsår', text: 'Dagbogstekst', lineMarks: 'Linjemarkering',
        notes: 'Fodnoter', related: 'Tilknyttet dagbogsside', kb: 'Kilde: Det Kgl. Bibliotek', sheet: 'Side',
        noText: 'Teksten til denne side er ikke tilgængelig i udskriften.',
        appendix: 'Valgte registerposter', colType: 'Type', colId: 'ID', colTitle: 'Titel', colUrl: 'URL', locale: 'da-DK',
        file: 'HCA-kurv', filePages: function (n) { return n + '-dagbogssider'; }, fileEntries: 'poster',
        stLoadLib: 'Henter PDF-værktøj …', stLoadData: 'Henter dagbogstekster …',
        stBuild: function (i, n) { return 'Sætter siderne op … ' + i.toLocaleString('da-DK') + ' / ' + n.toLocaleString('da-DK'); },
        stWrite: function (sec) { return 'Skriver PDF … ' + sec + ' s'; }
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
        more: function (n) { return '… and ' + n + ' more'; },
        generated: 'Generated', source: 'Source', sourceVal: "H.C. Andersen's diaries (Royal Danish Library) and the site's linked register data",
        site: 'Site',
        volume: 'Volume', page: 'page', year: 'Diary year', text: 'Diary text', lineMarks: 'Line markers',
        notes: 'Footnotes', related: 'Linked to this diary page', kb: 'Source: Royal Danish Library', sheet: 'Page',
        noText: 'The text of this page is not available in the printout.',
        appendix: 'Selected register entries', colType: 'Type', colId: 'ID', colTitle: 'Title', colUrl: 'URL', locale: 'en-GB',
        file: 'HCA-cart', filePages: function (n) { return n + '-diary-pages'; }, fileEntries: 'entries',
        stLoadLib: 'Loading PDF tools …', stLoadData: 'Loading diary texts …',
        stBuild: function (i, n) { return 'Laying out the pages … ' + i.toLocaleString('en-GB') + ' / ' + n.toLocaleString('en-GB'); },
        stWrite: function (sec) { return 'Writing the PDF … ' + sec + ' s'; }
      }
    };

    // Characters the embedded fonts lack. Liberation has everything in the
    // diaries except the pound sign ℔ (U+2114).
    function clean(s) { return String(s == null ? '' : s).replace(/℔/g, 'lb'); }

    var base = '';
    function abs(href) {
      try { return new URL(href, base).href; } catch (e) { return href; }
    }

    // pdfmake splits a text node into words and writes one link annotation per
    // word, so "Meisling, Inger Cathrine (1793–1854)" would carry six — ~300
    // bytes each, which made the file several times larger. noWrap keeps a
    // (short) label as one unit and so one annotation; a long label may still
    // wrap normally.
    var NOWRAP_MAX = 50;
    function lnk(href, text, extra) {
      var o = { text: clean(text), link: abs(href) };
      if (o.text.length <= NOWRAP_MAX) o.noWrap = true;
      if (extra) for (var k in extra) o[k] = extra[k];
      return o;
    }

    // --- the edition markup, parsed without a DOM ------------------------------
    // Vocabulary of data/normalized/diary_html.csv: div.p / div.hdr (+ in1/in2/
    // center/caps/div1), nested <div> verse lines, i (italic, or an empty
    // <i data-n> margin line number), br, aside[role=note], figure/figcaption,
    // span, and rarely ul/li and table/tr/td.
    var ENT = { amp: '&', lt: '<', gt: '>', quot: '"', apos: "'", nbsp: ' ' };
    function decode(s) {
      return s.indexOf('&') < 0 ? s : s.replace(/&(#x[0-9a-f]+|#\d+|[a-z]+);/gi, function (m, e) {
        if (e.charAt(0) === '#') {
          var n = e.charAt(1).toLowerCase() === 'x' ? parseInt(e.slice(2), 16) : parseInt(e.slice(1), 10);
          return n ? String.fromCodePoint(n) : m;
        }
        return ENT.hasOwnProperty(e.toLowerCase()) ? ENT[e.toLowerCase()] : m;
      });
    }
    function attr(attrs, name) {
      var m = new RegExp('(?:^|\\s)' + name + '="([^"]*)"').exec(attrs);
      return m ? decode(m[1]) : null;
    }

    var BLOCK_INNER = { div: 1, li: 1, tr: 1, figcaption: 1, p: 1 };
    var TOP_BLOCK = { div: 'div', figure: 'figure', ul: 'plain', table: 'plain', p: 'div' };

    // → { blocks: [{kind, cls, id, lines: [{runs: [{text, italics?}], mark}]}],
    //     notes: [runs], marks: [labels] }
    function parseMarkup(html, pr) {
      var re = /<(\/?)([a-zA-Z][a-zA-Z0-9]*)([^>]*?)(\/?)>|([^<]+)/g;
      var blocks = [], notes = [], marks = [];
      var stack = [], cur = null, line = null, italic = 0;
      var note = null, noteAt = -1;      // inside <aside role=note>: its runs

      function newLine() { line = { runs: [], mark: null }; cur.lines.push(line); }
      function breakIfNeeded() { if (cur && (line.runs.length || line.mark)) newLine(); }
      function startBlock(kind, cls, id, attrs) {
        cur = { kind: kind, cls: ' ' + (cls || '') + ' ', id: id || '', lines: [] };
        newLine();
        var dn = attrs && attr(attrs, 'data-n');
        if (dn) { line.mark = pr.vol + '-' + pr.page + '-' + dn; marks.push(line.mark); }
        blocks.push(cur);
      }
      function addText(raw) {
        var t = decode(raw).replace(/\s+/g, ' ');
        if (!t) return;
        if (note) { note.push(italic ? { text: clean(t), italics: true } : { text: clean(t) }); return; }
        if (!cur) {
          if (!t.trim()) return;
          startBlock('plain', '', '', '');
        }
        line.runs.push(italic ? { text: clean(t), italics: true } : { text: clean(t) });
      }

      var m;
      while ((m = re.exec(html))) {
        if (m[5] != null) { addText(m[5]); continue; }
        var closing = !!m[1], tag = m[2].toLowerCase(), attrs = m[3] || '', selfClose = !!m[4];

        if (tag === 'br') { if (!closing && cur && !note) newLine(); continue; }

        if (!closing) {
          if (tag === 'aside' && attr(attrs, 'role') === 'note') {
            note = []; noteAt = stack.length; stack.push({ tag: tag });
            continue;
          }
          if (!note && !stack.length && TOP_BLOCK[tag]) {
            startBlock(TOP_BLOCK[tag], attr(attrs, 'class'), attr(attrs, 'id'), attrs);
          } else if (!note && cur) {
            if (BLOCK_INNER[tag] || tag === 'tr') breakIfNeeded();
            else if ((tag === 'td' || tag === 'th') && line.runs.length) line.runs.push({ text: '    ' });
          }
          var isMark = tag === 'i' && attr(attrs, 'data-n') != null;
          if (isMark && !note && cur) {
            line.mark = pr.vol + '-' + pr.page + '-' + attr(attrs, 'data-n');
            marks.push(line.mark);
          }
          if (!selfClose) {
            stack.push({ tag: tag, italic: tag === 'i' && !isMark });
            if (tag === 'i' && !isMark) italic++;
          }
        } else {
          // pop up to the matching open tag (tolerates stray closers)
          for (var k = stack.length - 1; k >= 0; k--) {
            if (stack[k].tag !== tag) continue;
            for (var j = stack.length - 1; j >= k; j--) if (stack[j].italic) italic--;
            stack.length = k;
            break;
          }
          if (note && tag === 'aside' && stack.length === noteAt) {
            notes.push(note); note = null; noteAt = -1;
          } else if (!note && cur) {
            if (BLOCK_INNER[tag] || tag === 'tr') breakIfNeeded();
            if (!stack.length) { cur = null; italic = 0; }
          }
        }
      }
      return { blocks: blocks, notes: notes, marks: marks };
    }

    // Trims the collapsed whitespace at line ends and drops empty lines.
    function tidyLines(lines) {
      var out = [];
      lines.forEach(function (ln) {
        var r = ln.runs;
        while (r.length && !r[0].text.trim()) r.shift();
        while (r.length && !r[r.length - 1].text.trim()) r.pop();
        if (r.length) {
          r[0].text = r[0].text.replace(/^\s+/, '');
          r[r.length - 1].text = r[r.length - 1].text.replace(/\s+$/, '');
        }
        if (r.length || ln.mark) out.push(ln);
      });
      return out;
    }

    function isoToLabel(iso) {
      var m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso);
      return m ? m[3] + '.' + m[2] + '.' + m[1] : iso;
    }

    // One parsed block → one stack node. Lines are grouped from one margin
    // marker to the next (every fifth line), so a page is a few dozen text
    // nodes rather than hundreds.
    function blockNode(b, st, first) {
      var lines = tidyLines(b.lines);
      if (!lines.length) return null;

      if (b.kind === 'figure') {
        return { text: lines.map(function (ln) { return ln.runs.map(function (r) { return r.text; }).join(''); }).join(' '),
          italics: true, alignment: 'center', color: GREY, margin: [0, 8, 0, 4] };
      }

      var isHdr = b.cls.indexOf(' hdr ') >= 0;
      var center = isHdr || b.cls.indexOf(' center ') >= 0;
      var big = b.cls.indexOf(' div1 ') >= 0;
      var indent = b.cls.indexOf(' in2 ') >= 0 ? 2.4 * 10.5 : b.cls.indexOf(' in1 ') >= 0 ? 1.2 * 10.5 : 0;
      var size = big ? 12.9 : isHdr ? 11.3 : 10.5;

      var date = null, m = /^d(\d{4}-\d{2}-\d{2})$/.exec(b.id);
      if (m) {
        date = m[1];
        var lbl = isoToLabel(date);
        if (st.dates.indexOf(lbl) === -1) st.dates.push(lbl);
      }

      // The leading day name of a dated paragraph is indented (edition style).
      if (!isHdr && date && lines[0].runs.length) lines[0].runs.unshift({ text: '    ' });

      var groups = [], g = null;
      lines.forEach(function (ln) {
        if (!g || ln.mark) groups.push(g = { mark: ln.mark, lines: [] });
        g.lines.push(ln);
      });

      var nodes = groups.map(function (grp, gi) {
        var runs = [];
        grp.lines.forEach(function (ln, li) {
          if (li) runs.push({ text: '\n' });
          ln.runs.forEach(function (r) { runs.push(r); });
        });
        var node = {
          text: runs, fontSize: size, lineHeight: 1.28, bold: big,
          alignment: center ? 'center' : 'left', margin: [indent, 0, 0, 0]
        };
        if (gi === 0 && date) {
          node = { columnGap: 0, columns: [node, { width: DATE_COL, text: date, alignment: 'right', font: 'Sans', bold: true, fontSize: 8, color: BLUE, margin: [0, 2, 0, 0] }] };
        }
        if (grp.mark) {
          node = { stack: [
            { text: grp.mark, relativePosition: { x: -TEXT_INDENT, y: 2.2 }, font: 'Sans', bold: true, fontSize: 7.5, color: WINE },
            node
          ] };
        }
        return node;
      });

      return { stack: nodes, unbreakable: nodes.length <= 14, margin: [0, first ? 0 : (isHdr ? 14 : 4.2), 0, 0] };
    }

    function prepareText(html, pr) {
      var parsed = parseMarkup(html, pr);
      var st = { dates: [] }, nodes = [];
      parsed.blocks.forEach(function (b) {
        var n = blockNode(b, st, !nodes.length);
        if (n) nodes.push(n);
      });
      return { nodes: nodes, notes: parsed.notes, marks: parsed.marks, dates: st.dates };
    }

    function yearOf(rec) {
      var m = /(\d{4})/.exec((rec && rec.d) || '');
      return m ? m[1] : '';
    }

    // Name list as comma-separated link runs.
    function nameRuns(ents, type, color) {
      var runs = [];
      ents.forEach(function (e) {
        if (e[0] !== type) return;
        if (runs.length) runs.push({ text: ', ' });
        runs.push(lnk(TYPE_PAGE[type] + '?reg=' + encodeURIComponent(e[1]), e[2], { color: color }));
      });
      return runs;
    }

    function rule() {
      return { canvas: [{ type: 'line', x1: 0, y1: 0, x2: CONTENT_W, y2: 0, lineWidth: 0.75, lineColor: RULE }] };
    }
    function label(text, extra) {
      var runs = [{ text: clean(text).toUpperCase() }];
      if (extra) runs.push({ text: '   ' + clean(extra), font: 'Serif', bold: false, color: '#777777', fontSize: 7.5 });
      return { text: runs, font: 'Sans', bold: true, fontSize: 7.5, color: TEAL, margin: [0, 0, 0, 3] };
    }

    // --- sections --------------------------------------------------------------
    function coverNodes(rows, counts, t) {
      var order = ['diary', 'person', 'place', 'work'];
      var contents = order.filter(function (k) { return counts[k]; }).map(function (k) {
        return counts[k].toLocaleString(t.locale) + ' ' + t.counts[k][counts[k] === 1 ? 0 : 1];
      }).join(' · ');

      var vols = [], years = [];
      rows.forEach(function (r) {
        if (vols.indexOf(r.pr.vol) === -1) vols.push(r.pr.vol);
        var y = yearOf(r.rec);
        if (y) years.push(+y);
      });
      var lo = Math.min.apply(null, years), hi = Math.max.apply(null, years);
      var yrs = years.length ? (lo === hi ? String(lo) : lo + '–' + hi) : '';

      // Union of the names across all pages, most-mentioned first.
      var tally = { person: {}, place: {}, work: {} };
      rows.forEach(function (r) {
        ((r.rec && r.rec.e) || []).forEach(function (e) {
          var b = tally[e[0]];
          if (!b) return;
          (b[e[1]] = b[e[1]] || { rid: e[1], label: e[2], n: 0 }).n++;
        });
      });
      var overview = [];
      [['person', t.persons], ['place', t.places], ['work', t.works]].forEach(function (pair) {
        var list = Object.keys(tally[pair[0]]).map(function (k) { return tally[pair[0]][k]; });
        if (!list.length) return;
        list.sort(function (a, b) { return b.n - a.n || a.label.localeCompare(b.label, 'da'); });
        var runs = [{ text: pair[1] + ': ', bold: true }];
        list.slice(0, OVERVIEW_CAP).forEach(function (x, i) {
          if (i) runs.push({ text: ', ' });
          runs.push(lnk(TYPE_PAGE[pair[0]] + '?reg=' + encodeURIComponent(x.rid), x.label, { color: BLUE }));
          if (x.n > 1) runs.push({ text: ' (' + x.n + ')', color: '#777777', fontSize: 8.5 });
        });
        if (list.length > OVERVIEW_CAP) runs.push({ text: ', ' + t.more(list.length - OVERVIEW_CAP), color: '#777777', fontSize: 8.5 });
        overview.push({ text: runs, fontSize: 9, lineHeight: 1.25, margin: [11, 0, 0, 5] });
      });

      var gen = new Date().toLocaleDateString(t.locale, { day: 'numeric', month: 'long', year: 'numeric' });
      function block(title, body) {
        return [
          { stack: [rule()], margin: [0, 8, 0, 8] },
          { text: title.toUpperCase(), font: 'Sans', bold: true, fontSize: 8, color: WINE, margin: [0, 0, 0, 4] }
        ].concat(body);
      }
      var nodes = [
        { text: t.kicker, font: 'Sans', bold: true, fontSize: 8.5, color: WINE, margin: [0, 0, 0, 17] },
        { text: t.title.toUpperCase(), font: 'Sans', bold: true, fontSize: 26, color: DARK, margin: [0, 0, 0, 8] },
        { text: clean(rows.length ? t.pages(rows.length) : contents), color: GREY, margin: [0, 0, 0, 14] }
      ];
      nodes = nodes.concat(block(t.contents, [{ text: contents, margin: [11, 0, 0, 5] }]));
      if (rows.length) nodes = nodes.concat(block(t.scope, [{ text: t.scopeText(rows.length, vols.join(', '), yrs), margin: [11, 0, 0, 5] }]));
      if (overview.length) nodes = nodes.concat(block(t.overview, overview));
      nodes = nodes.concat(block(t.docinfo, [{
        fontSize: 9, color: GREY,
        text: [
          t.generated + ': ' + gen + '\n',
          t.source + ': ' + t.sourceVal + '\n',
          t.site + ': ',
          lnk('index.html', "HCA's Hvem-hvad-hvor", { color: BLUE })
        ]
      }]));
      return nodes;
    }

    function sheetNodes(r, t) {
      var pr = r.pr, rec = r.rec;
      var pageUrl = 'diary-pages/' + r.rid + '.html';
      var nodes = [];

      nodes.push({
        pageBreak: 'before',
        columns: [
          { text: t.kicker.split(' · ')[0], font: 'Sans', bold: true, fontSize: 7.5, color: WINE },
          { text: t.volume.toUpperCase() + ' ' + pr.vol + ' · ' + t.page.toUpperCase() + ' ' + pr.page, link: abs(pageUrl), noWrap: true, font: 'Sans', bold: true, fontSize: 7.5, color: WINE, alignment: 'right' }
        ]
      });
      nodes.push({ text: t.volume + ' ' + pr.vol + ', ' + t.page + ' ' + pr.page, link: abs(pageUrl), noWrap: true, font: 'Sans', bold: true, fontSize: 17, color: DARK, margin: [0, 8, 0, 3] });

      if (!rec) {
        nodes.push({ text: t.noText, italics: true, color: GREY });
        nodes.push({ text: [lnk(pageUrl, abs(pageUrl), { color: TEAL })], fontSize: 7.5, margin: [0, 6, 0, 0] });
        return nodes;
      }

      var yr = yearOf(rec);
      var prep = rec.h ? prepareText(rec.h, pr) : { nodes: [], notes: [], marks: [], dates: [] };
      var marks = prep.marks.slice(0, 3).join(', ') + (prep.marks.length > 3 ? ' …' : '');

      if (yr) nodes.push({ text: t.year + ': ' + yr, fontSize: 8.5, color: GREY, margin: [0, 0, 0, 5] });
      nodes.push({ stack: [rule()], margin: [0, 5, 0, 8] });

      if (prep.nodes.length) {
        nodes.push(label(t.text, marks ? t.lineMarks + ': ' + marks : ''));
        nodes.push({ stack: prep.nodes, margin: [TEXT_INDENT, 0, 0, 0] });
      } else {
        nodes.push({ text: t.noText, italics: true, color: GREY });
      }

      if (prep.notes.length) {
        var noteRuns = [];
        prep.notes.forEach(function (runs, i) {
          if (i) noteRuns.push({ text: ' · ' });
          runs.forEach(function (x) { noteRuns.push(x); });
        });
        nodes.push({
          unbreakable: true, margin: [0, 12, 0, 0],
          stack: [rule(), { text: '', margin: [0, 3, 0, 0] }, label(t.notes), { text: noteRuns, fontSize: 8.5, color: '#444444', lineHeight: 1.2 }]
        });
      }

      // Name block: Personer / Steder / Værker / Datoer, every name a link.
      function relRow(head, runs) {
        return { columns: [{ width: 48, text: head + ':', font: 'Sans', bold: true, fontSize: 7.8, color: '#333333' }, { width: '*', text: runs }], fontSize: 7.8, lineHeight: 1.15, color: GREY, margin: [0, 0, 0, 3] };
      }
      var rel = [];
      [['person', t.persons], ['place', t.places], ['work', t.works]].forEach(function (pair) {
        var runs = nameRuns(rec.e || [], pair[0], '#555555');
        if (runs.length) rel.push(relRow(pair[1], runs));
      });
      if (prep.dates.length) rel.push(relRow(t.dates, prep.dates.join(', ')));
      nodes.push({
        unbreakable: true, margin: [0, 14, 0, 0],
        stack: [rule(), { text: '', margin: [0, 4, 0, 0] }, label(t.related)].concat(rel)
      });

      // Source line: the KB address is visible text as well as a link.
      nodes.push({
        margin: [0, 6, 0, 0], fontSize: 7.5, color: GREY,
        text: rec.k
          ? [t.kb + ' · ' + t.volume + ' ' + pr.vol + ', ' + t.page + ' ' + pr.page + '\n', lnk(rec.k, rec.k, { color: TEAL })]
          : [lnk(pageUrl, abs(pageUrl), { color: TEAL })]
      });
      return nodes;
    }

    function appendixNodes(register, t) {
      var body = [[t.colType, t.colId, t.colTitle, t.colUrl].map(function (h) {
        return { text: h.toUpperCase(), font: 'Sans', bold: true, fontSize: 7.5, color: '#555555' };
      })];
      register.forEach(function (it) {
        body.push([
          { text: clean(it.typeLabel) },
          lnk(it.href, it.rid),
          lnk(it.href, it.label),
          { text: abs(it.href), fontSize: 7, color: '#555555' }   // visible address; id and title link to it
        ]);
      });
      return [
        { text: t.appendix.toUpperCase() + ' (' + register.length.toLocaleString(t.locale) + ')', font: 'Sans', bold: true, fontSize: 11, color: WINE, margin: [0, 0, 0, 11], pageBreak: 'before' },
        {
          table: { headerRows: 1, widths: [44, 66, '*', 175], body: body },
          fontSize: 8.5,
          layout: {
            hLineWidth: function (i) { return i === 1 ? 0.75 : 0.5; },
            hLineColor: function (i) { return i === 1 ? '#999999' : '#dddddd'; },
            vLineWidth: function () { return 0; },
            paddingTop: function () { return 3; }, paddingBottom: function () { return 3; },
            paddingLeft: function () { return 5; }, paddingRight: function () { return 5; }
          }
        }
      ];
    }

    // payload: { lg, base, counts: {type: n}, rows: [{rid, pr:{vol,page}, rec}],
    //            register: [{typeLabel, rid, label, href}] }
    // → pdfmake document definition. onProgress(done, total) every few pages.
    function build(payload, onProgress) {
      var t = L[payload.lg] || L.da;
      base = payload.base;
      var rows = payload.rows, content = coverNodes(rows, payload.counts, t);
      rows.forEach(function (r, i) {
        var s = sheetNodes(r, t);
        for (var k = 0; k < s.length; k++) content.push(s[k]);
        if (onProgress && (i % 50 === 49 || i === rows.length - 1)) onProgress(i + 1, rows.length);
      });
      if (payload.register.length) content = content.concat(appendixNodes(payload.register, t));

      return {
        pageSize: 'A4',
        pageMargins: [PAGE_MARGIN, PAGE_MARGIN, PAGE_MARGIN, 17 * MM],
        defaultStyle: { font: 'Serif', fontSize: 10.5, color: DARK, lineHeight: 1.2 },
        info: {
          title: clean(t.title + ' — ' + t.kicker.split(' · ')[0]),
          author: 'H.C. Andersen Dagbøger / Det Kgl. Bibliotek',
          subject: t.sourceVal, creator: "HCA's Hvem-hvad-hvor"
        },
        footer: function (page, pages) {
          return {
            margin: [PAGE_MARGIN, 8, PAGE_MARGIN, 0], font: 'Sans', fontSize: 7.5, color: '#777777',
            columns: [
              { text: t.kicker.split(' · ')[0] },
              { text: t.sheet + ' ' + page + ' / ' + pages, alignment: 'right', bold: true, color: WINE }
            ]
          };
        },
        content: content
      };
    }

    return { L: L, FONTS: FONTS, build: build };
  }

  // ════════════════════════════════════════════════════════════════════════
  // Main-thread side: load, assemble the payload, run (worker or inline), save.
  // ════════════════════════════════════════════════════════════════════════
  var B = makeBuilder();
  var ROMAN = ['', 'I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X', 'XI'];

  function lang() { return document.documentElement.lang === 'en' ? 'en' : 'da'; }

  // Directory of mockup/ relative to the page, from this script's own src
  // (cart.html and cart_en.html both sit in mockup/, but stay robust).
  var BASE = (function () {
    var s = document.currentScript;
    var m = s && /^(.*?)js\/cart-pdf\.js(?:[?#].*)?$/.exec(s.getAttribute('src') || '');
    return m ? m[1] : '';
  })();

  // "Pag040194" → { vol: 'IV', page: 194 }
  function parseRid(rid) {
    var m = /^Pag(\d{2})(\d{4})$/.exec(rid);
    if (!m) return null;
    return { vol: ROMAN[parseInt(m[1], 10)] || '?', page: parseInt(m[2], 10) };
  }

  // Plain <script> tags: fetch() is blocked under file://.
  var loading = {};
  function loadScript(src) {
    if (loading[src]) return loading[src];
    loading[src] = new Promise(function (resolve) {
      var s = document.createElement('script');
      s.src = BASE + src;
      s.onload = function () { resolve(true); };
      s.onerror = function () { resolve(false); };
      document.head.appendChild(s);
    });
    return loading[src];
  }
  function loadAssets() {
    return loadScript('vendor/pdfmake/pdf-assets.js').then(function (ok) {
      return ok && typeof window.HCA_PDFMAKE_SRC === 'string' && !!window.HCA_PDF_FONTS;
    });
  }

  // Let the browser repaint the button between steps.
  function tick() { return new Promise(function (res) { setTimeout(res, 0); }); }

  // Source of the worker: the library, then the builder, then the message glue.
  function workerSource() {
    return 'self.window = self;\n' + window.HCA_PDFMAKE_SRC + '\n;(function () {\n' +
      'var B = (' + makeBuilder.toString() + ')();\n' +
      'self.onmessage = function (ev) {\n' +
      '  try {\n' +
      '    pdfMake.addVirtualFileSystem(ev.data.fonts);\n' +
      '    pdfMake.addFonts(B.FONTS);\n' +
      '    var doc = B.build(ev.data.payload, function (i, n) { self.postMessage({ progress: [i, n] }); });\n' +
      '    self.postMessage({ writing: true });\n' +
      '    pdfMake.createPdf(doc).getBlob().then(function (blob) { self.postMessage({ blob: blob }); },\n' +
      '      function (e) { self.postMessage({ error: String(e && e.message || e) }); });\n' +
      '  } catch (e) { self.postMessage({ error: String(e && e.message || e) }); }\n' +
      '};\n' +
      '})();\n';
  }

  // → Promise<Blob>. onStatus(text) is called with progress text.
  function inWorker(payload, t, onStatus) {
    return new Promise(function (resolve, reject) {
      var url, w, started = false, timer = null, t0 = Date.now();
      function done() {
        if (timer) clearInterval(timer);
        if (w) w.terminate();
        if (url) URL.revokeObjectURL(url);
      }
      try {
        url = URL.createObjectURL(new Blob([workerSource()], { type: 'text/javascript' }));
        w = new Worker(url);
      } catch (e) { done(); reject({ noWorker: true, error: e }); return; }

      w.onmessage = function (ev) {
        var d = ev.data;
        started = true;
        if (d.progress) onStatus(t.stBuild(d.progress[0], d.progress[1]));
        else if (d.writing) {
          // pdfmake gives no progress while it lays out and writes; show elapsed time.
          t0 = Date.now();
          onStatus(t.stWrite(0));
          timer = setInterval(function () { onStatus(t.stWrite(Math.round((Date.now() - t0) / 1000))); }, 1000);
        } else if (d.blob) { done(); resolve(d.blob); }
        else { done(); reject(new Error(d.error || 'PDF worker failed')); }
      };
      w.onerror = function (ev) {
        done();
        reject(started ? new Error(ev.message || 'PDF worker failed') : { noWorker: true, error: ev });
      };
      w.postMessage({ payload: payload, fonts: window.HCA_PDF_FONTS });
    });
  }

  // Same work on the main thread (no worker available): the page is
  // unresponsive while it runs, but the result is identical.
  function inline(payload, t, onStatus) {
    if (!window.pdfMake) (0, eval)(window.HCA_PDFMAKE_SRC);   // eslint-disable-line no-eval
    pdfMake.addVirtualFileSystem(window.HCA_PDF_FONTS);
    pdfMake.addFonts(B.FONTS);
    return tick().then(function () {
      var doc = B.build(payload);
      onStatus(t.stWrite(0));
      return tick().then(function () { return pdfMake.createPdf(doc).getBlob(); });
    });
  }

  function save(blob, name) {
    var a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = name;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    setTimeout(function () { URL.revokeObjectURL(a.href); }, 60000);
  }

  function fileName(t, lg, nItems, nDiary) {
    var d = new Date(), pad = function (n) { return (n < 10 ? '0' : '') + n; };
    var stamp = d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate());
    return t.file + '_' + (nDiary ? t.filePages(nDiary) : nItems + '-' + t.fileEntries) + '_' + stamp + '.pdf';
  }

  function download(items, opts) {
    opts = opts || {};
    var lg = lang(), t = B.L[lg];
    var onStatus = function (s) { if (opts.onStatus) opts.onStatus(s); };
    if (!items.length) return Promise.resolve(false);

    var diary = items.filter(function (i) { return i.type === 'diary' && parseRid(i.rid); })
      .sort(function (a, b) { return a.rid < b.rid ? -1 : a.rid > b.rid ? 1 : 0; });
    var vols = [];
    diary.forEach(function (i) { var v = parseRid(i.rid).vol; if (vols.indexOf(v) === -1) vols.push(v); });

    onStatus(t.stLoadLib);
    return tick().then(loadAssets).then(function (ok) {
      if (!ok) return false;
      onStatus(t.stLoadData);
      return Promise.all(vols.map(function (v) { return loadScript('data/diary-print/vol-' + v + '.js'); })).then(function () {
        var data = window.DIARY_PRINT || {};
        var rows = diary.map(function (i) { return { rid: i.rid, pr: parseRid(i.rid), rec: data[i.rid] || null }; });
        // Diary pages in the cart but no print data at all (not built /
        // blocked) → let the caller fall back to the table print.
        if (rows.length && !rows.some(function (r) { return r.rec; })) return false;

        var counts = {};
        items.forEach(function (it) { if (it.type !== 'diary') counts[it.type] = (counts[it.type] || 0) + 1; });
        if (rows.length) counts.diary = rows.length;
        var payload = {
          lg: lg, base: location.href, counts: counts, rows: rows,
          register: items.filter(function (i) { return i.type !== 'diary'; }).map(function (it) {
            var fn = opts.typeHref && opts.typeHref[it.type];
            return { typeLabel: (opts.typeLabel && opts.typeLabel[it.type]) || it.type, rid: it.rid, label: it.label, href: fn ? fn(it.rid) : '#' };
          })
        };

        onStatus(t.stBuild(0, rows.length));
        return inWorker(payload, t, onStatus).catch(function (e) {
          if (e && e.noWorker) return inline(payload, t, onStatus);
          throw e;
        }).then(function (blob) {
          save(blob, fileName(t, lg, items.length, diary.length));
          return true;
        });
      });
    });
  }

  return { download: download };
})();
