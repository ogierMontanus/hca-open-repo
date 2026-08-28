/* entity-refs.js — cross-entity lookups shared by work.html, person.html,
 * place.html (and any future detail page that needs to navigate between
 * entity types). Builds reverse indexes from the global *_EXTRA dicts
 * loaded by the per-entity-data scripts.
 *
 * Public API (window.EntityRefs):
 *   personRid(name)          → 'RegNNNN' | null
 *   placeRid(label)          → 'RegNNNN' | null
 *   workRid(title)           → 'RegNNNN' | null
 *   personHref(name)         → 'persons.html?reg=…' | 'persons.html'
 *   placeHref(label)         → 'place.html?reg=…'  | 'place.html'
 *   workHref(title)          → 'work.html?reg=…'   | 'work.html'
 *   personHrefByRid(rid)     → trivial wrapper for callers that already know the rid
 *   placeHrefByRid(rid)      → same
 *   workHrefByRid(rid)       → same
 *   worksByAuthor(personRid) → array of {rid, title, h2, h3, ...} works whose
 *                              author name resolves to this person
 *   worksAtPlace(placeRid)   → array of works whose title parenthetical
 *                              contains this place's label
 *   nameKey(s)               → canonical "surname|initials" key (exposed
 *                              so callers can do their own lookups too)
 *
 * Degrades gracefully when any *_EXTRA global is absent: lookups simply
 * return null / empty arrays.
 */
window.EntityRefs = (function () {
  'use strict';

  var _PLACE_LABEL_REG = {};
  var _PERSON_LABEL_REG = {};
  var _PERSON_PREFIX_REG = {};   // matches "Dickens, Charles" → "Dickens, Charles (1812–1870)"
  var _PERSON_KEY_REG = {};      // surname+initials canonical key → rid
  var _PERSON_KEY_REFS = {};     // refs behind each key (collision tiebreak)
  var _WORK_TITLE_REG = {};
  var _WORK_TITLE_REFS = {};

  /* Canonical "surname|initials" key so an author written
     "Firstname Lastname" (e.g. "Chr. E. F. Weyse", "H. C. ANDERSEN")
     matches a register label in "Lastname, Firstname" order (e.g.
     "Weyse, C. E. F. (1774–1842)"). */
  function nameKey(s) {
    if (!s) return null;
    s = s.split(/[\(\（\[]/)[0].trim();           // drop dates / brackets
    if (!s) return null;
    var surname, given;
    if (s.indexOf(',') !== -1) {
      var parts = s.split(',');
      surname = parts[0];
      given = parts.slice(1).join(' ');
    } else {
      var toks = s.split(/\s+/).filter(Boolean);
      if (!toks.length) return null;
      surname = toks[toks.length - 1];
      given = toks.slice(0, -1).join(' ');
    }
    // ä→æ, ö→ø, ü→y (Danish convention; ü is articulated as y in Danish) —
    // same fold already used for alphabet-bar bucketing (category-
    // catalogue.js/places.html/persons.html's initialOf()), applied here
    // too so an author string spelled the German way ("Adam
    // Oehlenschläger", 2 works) still resolves to the person register's
    // own "Oehlenschlæger, Adam" entry (spelled with æ throughout, ~60
    // works). Must run BEFORE the NFD strip below: NFD decomposes ä into
    // "a" + a combining diaeresis that the next line then deletes,
    // collapsing it to plain "a" and missing the register's æ entirely —
    // whereas æ itself has no NFD decomposition and passes through
    // unchanged, so without this substitution the two spellings fold to
    // different keys instead of the same one.
    var fold = function (x) {
      return x
        .replace(/ä/g, 'æ').replace(/Ä/g, 'Æ')
        .replace(/ö/g, 'ø').replace(/Ö/g, 'Ø')
        .replace(/ü/g, 'y').replace(/Ü/g, 'Y')
        .toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '');
    };
    var sk = fold(surname).replace(/[^a-zæøå]/g, '');
    if (!sk) return null;
    var inits = fold(given).split(/[\s.]+/).filter(Boolean)
      .map(function (t) { return t[0]; }).filter(Boolean).sort().join('');
    return sk + '|' + inits;
  }

  if (typeof PLACES_EXTRA !== 'undefined') {
    for (var rid1 in PLACES_EXTRA) {
      var v1 = PLACES_EXTRA[rid1];
      if (v1 && v1.label) _PLACE_LABEL_REG[v1.label] = rid1;
    }
  }
  if (typeof PERSONS_EXTRA !== 'undefined') {
    for (var rid2 in PERSONS_EXTRA) {
      var v2 = PERSONS_EXTRA[rid2];
      if (!v2 || !v2.label) continue;
      _PERSON_LABEL_REG[v2.label] = rid2;
      var m = v2.label.match(/^(.+?)\s*[\(\（]/);
      if (m) _PERSON_PREFIX_REG[m[1].trim()] = rid2;
      var k = nameKey(v2.label);
      if (k) {
        var refs2 = v2.refs || 0;
        if (!(k in _PERSON_KEY_REG) || refs2 > _PERSON_KEY_REFS[k]) {
          _PERSON_KEY_REG[k] = rid2;
          _PERSON_KEY_REFS[k] = refs2;
        }
      }
    }
  }
  if (typeof WORKS_EXTRA !== 'undefined') {
    for (var rid3 in WORKS_EXTRA) {
      var v3 = WORKS_EXTRA[rid3];
      if (!v3 || !v3.title) continue;
      var refs3 = v3.refs || 0;
      if (!(v3.title in _WORK_TITLE_REG) || refs3 > _WORK_TITLE_REFS[v3.title]) {
        _WORK_TITLE_REG[v3.title] = rid3;
        _WORK_TITLE_REFS[v3.title] = refs3;
      }
    }
  }

  // WORKS_EXTRA.author sometimes carries a Danish genitive ("Dorothea
  // Melchiors [Portræt]" -> the register's "Melchior, Dorothea") rather
  // than the bare surname a BILLEDKUNST portrait credit usually gives —
  // person_derived apparently kept the possessive form as written on 9
  // works checked by hand (2026-08-28 probe), all portraits of named
  // 19th-century Copenhagen family members, none a false match against
  // an unrelated person. Only tried as a fallback, after every other
  // lookup above has already failed, and only strips a trailing s from
  // the LAST token (the surname position) — a genuinely s-ending surname
  // (Dickens, Jones-style) still resolves normally on the first, unmodified
  // attempt and never reaches this branch at all.
  function genitiveStrippedRid(name) {
    var toks = name.trim().split(/\s+/);
    var last = toks[toks.length - 1];
    if (last.length < 3 || !/s$/i.test(last)) return null;
    var stripped = toks.slice(0, -1).concat(last.slice(0, -1)).join(' ');
    var k = nameKey(stripped);
    return k ? (_PERSON_KEY_REG[k] || null) : null;
  }

  function personRid(name) {
    if (!name) return null;
    var r = _PERSON_LABEL_REG[name] || _PERSON_PREFIX_REG[name];
    if (!r) {
      var k = nameKey(name);
      if (k) r = _PERSON_KEY_REG[k];
    }
    if (!r) r = genitiveStrippedRid(name);
    return r || null;
  }
  function placeRid(label) { return label ? (_PLACE_LABEL_REG[label] || null) : null; }
  function workRid(title)  { return title ? (_WORK_TITLE_REG[title]   || null) : null; }

  function personHref(name)  { var r = personRid(name);  return r ? 'persons.html?reg=' + r : 'persons.html'; }
  function placeHref(label)  { var r = placeRid(label);  return r ? 'place.html?reg='  + r : 'place.html';  }
  function workHref(title)   { var r = workRid(title);   return r ? 'work.html?reg='   + r : 'work.html';   }
  function personHrefByRid(r){ return r ? 'persons.html?reg=' + r : 'persons.html'; }
  function placeHrefByRid(r) { return r ? 'place.html?reg='  + r : 'place.html';  }
  function workHrefByRid(r)  { return r ? 'work.html?reg='   + r : 'work.html';   }

  /* Lazy index of works keyed by resolved-author person rid.
     Walks WORKS_EXTRA once on first call. */
  var _worksByPersonRid = null;
  function worksByAuthor(personRidArg) {
    if (!personRidArg || typeof WORKS_EXTRA === 'undefined') return [];
    if (!_worksByPersonRid) {
      _worksByPersonRid = {};
      for (var rid in WORKS_EXTRA) {
        var w = WORKS_EXTRA[rid];
        if (!w || !w.author) continue;
        var pr = personRid(w.author);
        if (!pr) continue;
        var entry = Object.assign({ rid: rid }, w);
        (_worksByPersonRid[pr] = _worksByPersonRid[pr] || []).push(entry);
      }
    }
    return _worksByPersonRid[personRidArg] || [];
  }

  /* Lazy index of works keyed by place rid, derived from the work title's
     parentheticals — e.g. "Den mediceiske Venus (Uffizi, Firenze)" attaches
     to Firenze. Each comma-separated piece inside each parens group is
     tried against _PLACE_LABEL_REG; the first hit wins for that group. */
  var _worksByPlaceRid = null;
  function buildWorksByPlace() {
    _worksByPlaceRid = {};
    if (typeof WORKS_EXTRA === 'undefined') return;
    for (var rid in WORKS_EXTRA) {
      var w = WORKS_EXTRA[rid];
      if (!w || !w.title) continue;
      var parens = w.title.match(/\(([^()]+)\)/g);
      if (!parens) continue;
      var seen = {};
      for (var i = 0; i < parens.length; i++) {
        var inner = parens[i].slice(1, -1);
        var pieces = inner.split(',');
        for (var j = 0; j < pieces.length; j++) {
          var lab = pieces[j].trim();
          if (!lab) continue;
          var prid = _PLACE_LABEL_REG[lab];
          if (!prid || seen[prid]) continue;
          seen[prid] = true;
          var entry = Object.assign({ rid: rid }, w);
          (_worksByPlaceRid[prid] = _worksByPlaceRid[prid] || []).push(entry);
          break;
        }
      }
    }
  }
  function worksAtPlace(placeRidArg) {
    if (!placeRidArg) return [];
    if (!_worksByPlaceRid) buildWorksByPlace();
    return _worksByPlaceRid[placeRidArg] || [];
  }

  return {
    nameKey: nameKey,
    personRid: personRid, placeRid: placeRid, workRid: workRid,
    personHref: personHref, placeHref: placeHref, workHref: workHref,
    personHrefByRid: personHrefByRid,
    placeHrefByRid: placeHrefByRid,
    workHrefByRid: workHrefByRid,
    worksByAuthor: worksByAuthor,
    worksAtPlace: worksAtPlace
  };
})();
