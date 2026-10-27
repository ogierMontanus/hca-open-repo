/* timeline-wire.js — the Tidstavle companion track ("ledsagespor") for the
 * diary views.
 *
 * Depends on the global TIMELINE from data/timeline.js, produced by
 * scripts/build_mockup/build_timeline.py from
 * data/HCA_Tidstavler_bind_1-10_*.xlsx and loaded with a plain <script> tag
 * (file://-safe). When that file is absent every helper degrades to "no
 * data": has() is false and the renderers return empty strings.
 *
 * An entry (see build_timeline.py for the full shape):
 *   { i, v, a, b, pa, pb, q, k, x, p, u, o, n }
 *   a/b   first/last day, ISO, inclusive    k  ophold | rejse | begivenhed
 *   x     description: a string, or an array of strings and
 *         [text, 'p'|'s'|'w', id] spans (place | person | work in the register)
 *
 * Public API (window.TimelineWire):
 *   has()                       → bool
 *   years()                     → [firstYear, lastYear] covered
 *   onDay(iso)                  → entries covering that day, most specific first
 *   inMonth(year, month0)       → entries overlapping that month, by start date
 *   dayInfo(iso)                → { n, stay, event, label } for calendar cells
 *   companion(iso, opts)        → small HTML block for a diary card
 *   plain(iso)                  → text-only summary (table cell, tooltips)
 *   mount(el, entries, opts)    → render the track into el (with "show all")
 *   label(entry)                → "1.–10. nov. 1845"
 */
window.TimelineWire = (function () {
  'use strict';

  var EN = document.documentElement.lang === 'en';

  var T = {
    title:     EN ? 'Chronology'                    : 'Tidstavle',
    entries:   EN ? ['entry', 'entries']            : ['post', 'poster'],
    showAll:   EN ? 'Show all'                      : 'Vis alle',
    showLess:  EN ? 'Show fewer'                    : 'Vis færre',
    source:    EN ? 'Chronology'                    : 'Tidstavle',
    page:      EN ? 'p.'                            : 's.',
    newTab:    EN ? ' (opens in a new tab)'         : ' (åbner i nyt faneblad)',
    original:  EN ? 'Original date: '               : 'Original datoangivelse: ',
    invalid:   EN ? 'invalid calendar date in the printed source' : 'ugyldig kalenderdato i den trykte kilde',
    kind:      EN ? { ophold: 'Stay', rejse: 'Journey', begivenhed: 'Event' }
                  : { ophold: 'Ophold', rejse: 'Rejse', begivenhed: 'Begivenhed' },
    qual:      EN ? { ca: 'c.', sommer: 'summer', 'årets slutning': 'end of the year' }
                  : { ca: 'ca.', sommer: 'sommer', 'årets slutning': 'årets slutning' },
    attrib:    EN ? 'Source: the printed chronologies (Tidstavler) of the diary edition, vols. 1–10, Royal Danish Library.'
                  : 'Kilde: tidstavlerne i dagbogsudgaven, bind 1–10, Det Kgl. Bibliotek.',
    months:    EN ? ['Jan.', 'Feb.', 'Mar.', 'Apr.', 'May', 'Jun.', 'Jul.', 'Aug.', 'Sep.', 'Oct.', 'Nov.', 'Dec.']
                  : ['jan.', 'feb.', 'mar.', 'apr.', 'maj', 'jun.', 'jul.', 'aug.', 'sep.', 'okt.', 'nov.', 'dec.']
  };

  // place.html / work.html serve both languages; persons has an _en twin.
  var PAGE = { p: 'place.html', s: EN ? 'persons_en.html' : 'persons.html', w: 'work.html' };
  var REF_CLASS = { p: 'tl-ref tl-ref--place', s: 'tl-ref tl-ref--person', w: 'tl-ref tl-ref--work' };

  function has() { return typeof TIMELINE !== 'undefined' && TIMELINE.length > 0; }

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  /* ── dates ───────────────────────────────────────────────────────────── */

  function parts(iso) {
    return { y: +iso.slice(0, 4), m: +iso.slice(5, 7), d: +iso.slice(8, 10) };
  }

  function dayNo(iso) { var p = parts(iso); return Date.UTC(p.y, p.m - 1, p.d) / 86400000; }

  function label(e) {
    var A = parts(e.a), B = parts(e.b), mo = T.months;
    var out;
    if (e.pa === 'y' && e.pb === 'y') {
      out = A.y === B.y ? String(A.y) : A.y + '–' + B.y;
    } else if (e.pa !== 'd' && e.pb !== 'd') {
      out = (A.y === B.y && A.m === B.m) ? mo[A.m - 1] + ' ' + A.y
          : (A.y === B.y) ? mo[A.m - 1] + '–' + mo[B.m - 1] + ' ' + A.y
          : mo[A.m - 1] + ' ' + A.y + ' – ' + mo[B.m - 1] + ' ' + B.y;
    } else if (e.a === e.b) {
      out = A.d + '. ' + mo[A.m - 1] + ' ' + A.y;
    } else if (A.y === B.y && A.m === B.m) {
      out = A.d + '.–' + B.d + '. ' + mo[A.m - 1] + ' ' + A.y;
    } else if (A.y === B.y) {
      out = A.d + '. ' + mo[A.m - 1] + ' – ' + B.d + '. ' + mo[B.m - 1] + ' ' + A.y;
    } else {
      out = A.d + '. ' + mo[A.m - 1] + ' ' + A.y + ' – ' + B.d + '. ' + mo[B.m - 1] + ' ' + B.y;
    }
    (e.q || []).forEach(function (q) {
      if (q === 'ca') out = T.qual.ca + ' ' + out;
      else if (q !== 'ugyldig') out += ' (' + (T.qual[q] || q) + ')';
    });
    return out;
  }

  /* ── lookups ─────────────────────────────────────────────────────────── */

  var _sorted = null;   // entries by start date, built once
  var _days = {};       // iso → entries covering it
  var _span = null;     // entry → length in days

  function ensure() {
    if (_sorted || !has()) return;
    _sorted = TIMELINE.slice().sort(function (x, y) {
      return x.a < y.a ? -1 : x.a > y.a ? 1 : (x.b < y.b ? -1 : x.b > y.b ? 1 : 0);
    });
    _span = {};
    TIMELINE.forEach(function (e) { _span[e.i] = dayNo(e.b) - dayNo(e.a) + 1; });
  }

  // Most specific first: a one-day event outranks the month-long stay it
  // happened in; among equals, journey legs and stays outrank events.
  function rank(x, y) {
    var s = _span[x.i] - _span[y.i];
    if (s) return s;
    var kx = x.k === 'begivenhed' ? 1 : 0, ky = y.k === 'begivenhed' ? 1 : 0;
    return kx - ky || (x.i < y.i ? -1 : 1);
  }

  function onDay(iso) {
    if (!has() || !iso) return [];
    ensure();
    if (_days[iso]) return _days[iso];
    var hit = [];
    for (var i = 0; i < _sorted.length; i++) {
      var e = _sorted[i];
      if (e.a > iso) break;
      if (e.b >= iso) hit.push(e);
    }
    hit.sort(rank);
    return (_days[iso] = hit);
  }

  function inMonth(year, month0) {
    if (!has()) return [];
    ensure();
    var mm = ('0' + (month0 + 1)).slice(-2);
    var first = year + '-' + mm + '-01';
    var last = year + '-' + mm + '-31';
    return _sorted.filter(function (e) { return e.a <= last && e.b >= first; });
  }

  function years() {
    if (!has()) return null;
    ensure();
    var lo = _sorted[0].a.slice(0, 4), hi = _sorted[0].b.slice(0, 4);
    _sorted.forEach(function (e) { if (e.b.slice(0, 4) > hi) hi = e.b.slice(0, 4); });
    return [+lo, +hi];
  }

  function yearHasAny(year) {
    if (!has()) return false;
    ensure();
    return _sorted.some(function (e) { return e.a.slice(0, 4) <= String(year) && e.b.slice(0, 4) >= String(year); });
  }

  /* What a calendar cell needs to know: is there a stay/journey covering the
   * day (draws a bar), is there an event dated exactly that day (a dot), and
   * a tooltip/aria text. */
  function dayInfo(iso) {
    var es = onDay(iso);
    if (!es.length) return null;
    var stay = es.filter(function (e) { return e.k !== 'begivenhed'; });
    var event = es.filter(function (e) { return e.k === 'begivenhed' && e.a === e.b; });
    return { n: es.length, stay: stay.length > 0, event: event.length > 0, label: plain(iso) };
  }

  /* ── rendering ───────────────────────────────────────────────────────── */

  function plainText(e) {
    if (typeof e.x === 'string') return e.x;
    return e.x.map(function (s) { return typeof s === 'string' ? s : s[0]; }).join('');
  }

  function textHtml(e, linkClass) {
    if (typeof e.x === 'string') return esc(e.x);
    return e.x.map(function (s) {
      if (typeof s === 'string') return esc(s);
      return '<a class="' + REF_CLASS[s[1]] + (linkClass ? ' ' + linkClass : '') + '" href="' +
        PAGE[s[1]] + '?reg=' + encodeURIComponent(s[2]) + '">' + esc(s[0]) + '</a>';
    }).join('');
  }

  // Provenance link to the printed page at Det Kgl. Bibliotek: small, muted,
  // new tab (docs/external-links.md).
  function sourceHtml(e) {
    var txt = T.source + ' ' + T.page + ' ' + esc(e.p || '');
    if (!e.u) return '<span class="tl-item__src">' + txt + '</span>';
    return '<a class="external-link tl-item__src" href="' + esc(e.u) + '" target="_blank" rel="noopener noreferrer">' +
      txt + '<span class="external-link__icon" aria-hidden="true">↗</span>' +
      '<span class="sr-only">' + T.newTab + '</span></a>';
  }

  function itemHtml(e, opts) {
    opts = opts || {};
    // On a day view a one-day entry needs no date; a stay shows its span.
    var showWhen = !(opts.day && e.a === e.b && e.a === opts.day && e.pa === 'd');
    var when = '';
    if (showWhen) {
      var lab = esc(label(e));
      // In month view the date is a button that selects the first day shown.
      var target = opts.pickDay ? (e.a >= opts.pickDay[0] ? e.a : opts.pickDay[0]) : '';
      when = target && target <= opts.pickDay[1]
        ? '<button type="button" class="tl-item__when tl-item__when--btn" data-tl-day="' + target + '">' + lab + '</button>'
        : '<span class="tl-item__when">' + lab + '</span>';
    }
    var notes = [];
    if (e.o && e.o.replace(/[\s.]/g, '') !== '') notes.push(T.original + esc(e.o));
    if ((e.q || []).indexOf('ugyldig') !== -1) notes.push(T.invalid);
    var note = notes.length
      ? ' <span class="tl-item__note" title="' + notes.join(' · ').replace(/<[^>]+>/g, '') + '">ⓘ</span>' : '';
    return '<li class="tl-item tl-item--' + e.k + '">' +
      '<span class="tl-item__kind">' + T.kind[e.k] + '</span>' + when +
      '<span class="tl-item__text">' + textHtml(e) + note + '</span>' + sourceHtml(e) + '</li>';
  }

  /* Render the track into `el`. opts: { day, pickDay:[first,last], limit }.
   * Long lists (a month view) start collapsed to `limit` items. */
  function mount(el, entries, opts) {
    opts = opts || {};
    if (!el || !has()) return;
    if (!entries.length) { el.innerHTML = ''; return; }
    var limit = opts.limit || 12;
    var n = entries.length;
    var head = '<h4 class="tl-track__title">' + T.title +
      ' <span class="tl-track__count">· ' + n + ' ' + T.entries[n === 1 ? 0 : 1] + '</span></h4>';
    var items = entries.map(function (e) { return itemHtml(e, opts); });
    var more = n > limit
      ? '<button type="button" class="tl-track__more" aria-expanded="false">' + T.showAll + ' (' + n + ')</button>' : '';
    el.innerHTML = '<section class="tl-track" aria-label="' + T.title + '">' + head +
      '<ul class="tl-list' + (n > limit ? ' tl-list--collapsed' : '') + '" data-limit="' + limit + '">' +
      items.join('') + '</ul>' + more +
      '<p class="tl-track__attrib">' + T.attrib + '</p></section>';
    var btn = el.querySelector('.tl-track__more');
    if (btn) {
      btn.addEventListener('click', function () {
        var ul = el.querySelector('.tl-list');
        var open = ul.classList.toggle('tl-list--collapsed') === false;
        btn.setAttribute('aria-expanded', open ? 'true' : 'false');
        btn.textContent = open ? T.showLess : T.showAll + ' (' + n + ')';
      });
    }
  }

  /* Small block for a diary card: the stay/journey leg for that date plus
   * any event dated that exact day. Links sit above the card's overlay link. */
  function companion(iso, opts) {
    opts = opts || {};
    var es = onDay(iso);
    if (!es.length) return '';
    var stay = es.filter(function (e) { return e.k !== 'begivenhed'; })[0];
    var events = es.filter(function (e) { return e.k === 'begivenhed' && e.a === iso && e.b === iso; });
    var show = (stay ? [stay] : []).concat(events.slice(0, stay ? 1 : 2));
    var rest = es.length - show.length;
    if (!show.length) show = [es[0]]; rest = es.length - show.length;
    return '<div class="tl-companion"><span class="tl-companion__tag">' + T.title + '</span>' +
      show.map(function (e) {
        return '<span class="tl-companion__line">' + textHtml(e, 'result-card__chip-link') + '</span>';
      }).join('') +
      (rest > 0 ? '<span class="tl-companion__more">+' + rest + '</span>' : '') + '</div>';
  }

  function plain(iso) {
    var es = onDay(iso);
    if (!es.length) return '';
    var stay = es.filter(function (e) { return e.k !== 'begivenhed'; })[0];
    var events = es.filter(function (e) { return e.k === 'begivenhed' && e.a === iso && e.b === iso; });
    return (stay ? [stay] : []).concat(events.slice(0, 1)).map(plainText).join(' · ');
  }

  return { has: has, years: years, yearHasAny: yearHasAny, onDay: onDay, inMonth: inMonth,
           dayInfo: dayInfo, companion: companion, plain: plain, mount: mount,
           label: label, itemHtml: itemHtml, plainText: plainText };
})();
