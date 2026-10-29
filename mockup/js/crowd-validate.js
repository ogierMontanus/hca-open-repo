/* crowd-validate.js — client-side twin of scripts/crowdsource/validate.py.
 *
 * Gives the contributor every problem with a submission before it is sent.
 * The server validates again and is the authority; tests/fixtures/
 * crowd_cases.json is run against both implementations so they agree.
 * DOM-free: also loaded by Node (tests/js/crowd-validate.test.js).
 *
 *   CrowdValidate.validate(payload, taxonomy[, todayISO]) → [{path, code, msg}]
 *   CrowdValidate.normalise(str[, multiline])             → trimmed string
 */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.CrowdValidate = factory();
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  var PERSON_ID_RE = /^Reg\d{4,9}$/;
  var DATE_RE = /^(?:ca\.\s)?(\d{4})(?:-(\d{2})(?:-(\d{2}))?)?$/;
  var QID_RE = /^Q[1-9]\d{0,9}$/;
  var URL_RE = /^https?:\/\/[^\s<>"']{3,}$/i;
  var CTRL_RE = /[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]/g;

  function norm(v, multiline) {
    if (v === null || v === undefined) return '';
    var t = String(v).replace(CTRL_RE, '').replace(/\r\n?/g, '\n');
    if (multiline) t = t.replace(/[ \t]+/g, ' ').replace(/\n{3,}/g, '\n\n');
    else t = t.replace(/\s+/g, ' ');
    return t.trim();
  }

  function isoDateValid(y, m, d) {
    var dt = new Date(Date.UTC(y, m - 1, d));
    return dt.getUTCFullYear() === y && dt.getUTCMonth() === m - 1 && dt.getUTCDate() === d;
  }

  function checkDate(value) {
    var m = DATE_RE.exec(value);
    if (!m) return ['invalid_date', 'Brug ÅÅÅÅ, ÅÅÅÅ-MM eller ÅÅÅÅ-MM-DD (evt. med »ca. « foran).'];
    var year = parseInt(m[1], 10);
    if (year < 1000 || year > 1950) return ['implausible_date', 'Året ligger uden for det rimelige (1000–1950) for en person i dagbøgerne.'];
    if (m[2] && (parseInt(m[2], 10) < 1 || parseInt(m[2], 10) > 12)) return ['invalid_date', 'Måneden skal være 01–12.'];
    if (m[3] && !isoDateValid(year, parseInt(m[2], 10), parseInt(m[3], 10))) return ['invalid_date', 'Datoen findes ikke.'];
    return null;
  }

  function yearOf(value) {
    var m = DATE_RE.exec(value || '');
    return m ? parseInt(m[1], 10) : null;
  }

  function validate(payload, tax, todayISO) {
    var errs = [];
    function add(path, code, msg) { errs.push({ path: path, code: code, msg: msg }); }
    var L = tax.limits;
    var today = todayISO || new Date().toISOString().slice(0, 10);
    if (!payload || typeof payload !== 'object' || Array.isArray(payload)) {
      add('', 'invalid', 'Forventede et JSON-objekt.');
      return errs;
    }
    var keys = function (list) { return list.map(function (x) { return x.key; }); };
    var idKeys = keys(tax.identification), confKeys = keys(tax.confidence);
    var typeByKey = {};
    tax.sourceTypes.forEach(function (s) { typeByKey[s.key] = s; });
    var fieldByKey = {};
    tax.fields.forEach(function (f) { fieldByKey[f.key] = f; });

    var personId = norm(payload.person_id);
    if (!PERSON_ID_RE.test(personId)) add('person_id', 'invalid_person_id', 'Mangler et gyldigt person-ID (Reg…).');

    var ident = payload.identification || {};
    var status = norm(ident.status), summary = norm(ident.summary, true), sameAs = norm(ident.same_as);
    if (idKeys.indexOf(status) < 0) add('identification.status', 'required', 'Vælg, hvad dit bidrag drejer sig om.');
    if (summary.length > L.summary) add('identification.summary', 'too_long', 'Højst ' + L.summary + ' tegn.');
    if (status === 'duplicate') {
      if (!PERSON_ID_RE.test(sameAs)) add('identification.same_as', 'required', 'Angiv det Reg-ID, posten er identisk med.');
      else if (sameAs === personId) add('identification.same_as', 'invalid', 'Posten kan ikke være identisk med sig selv.');
    }
    if (status === 'not_individual' && summary.length < 10) {
      add('identification.summary', 'required', 'Forklar kort, hvorfor posten ikke er en enkeltperson.');
    }

    var overall = norm(payload.overall_confidence);
    if ((status === 'identified' || status === 'candidate') && confKeys.indexOf(overall) < 0) {
      add('overall_confidence', 'required', 'Angiv, hvor sikker du er på identifikationen som helhed.');
    }
    if (overall && confKeys.indexOf(overall) < 0) add('overall_confidence', 'invalid', 'Ukendt sikkerhedsgrad.');

    // sources
    var srcIn = Array.isArray(payload.sources) ? payload.sources : [];
    var sources = [];
    if (!srcIn.length) add('sources', 'required', 'Angiv mindst én kilde. Uden kilde kan bidraget ikke vurderes.');
    if (srcIn.length > L.max_sources) add('sources', 'too_many', 'Højst ' + L.max_sources + ' kilder.');
    var nAtt = 0;
    srcIn.slice(0, L.max_sources).forEach(function (s, i) {
      var p = 'sources[' + i + ']';
      s = (s && typeof s === 'object') ? s : {};
      var type = norm(s.type), citation = norm(s.citation), url = norm(s.url), locator = norm(s.locator);
      var accessed = norm(s.accessed), result = norm(s.result) || 'stoetter';
      var spec = typeByKey[type];
      if (!spec) add(p + '.type', 'required', 'Vælg kildetype.');
      if (citation.length < 5) add(p + '.citation', 'required', 'Skriv en kildehenvisning (hvad er kilden, hvem/hvor/hvornår).');
      else if (citation.length > L.citation) add(p + '.citation', 'too_long', 'Højst ' + L.citation + ' tegn.');
      if (url && !URL_RE.test(url)) add(p + '.url', 'invalid_url', 'Linket skal begynde med http:// eller https://.');
      if (url.length > L.url) add(p + '.url', 'too_long', 'Højst ' + L.url + ' tegn.');
      if (locator.length > L.locator) add(p + '.locator', 'too_long', 'Højst ' + L.locator + ' tegn.');
      if (spec && spec.needsUrl && !url) add(p + '.url', 'required', 'Denne kildetype kræver et link.');
      if (['arkiv', 'tryk', 'billede', 'pdf'].indexOf(type) >= 0 && !url && !locator) {
        add(p + '.locator', 'required', 'Angiv enten et link eller en præcis henvisning (side, folio, opslag, filnavn).');
      }
      if (accessed) {
        if (!/^\d{4}-\d{2}-\d{2}$/.test(accessed) || !isoDateValid(+accessed.slice(0, 4), +accessed.slice(5, 7), +accessed.slice(8, 10))) {
          add(p + '.accessed', 'invalid_date', 'Brug ÅÅÅÅ-MM-DD.');
        } else if (accessed > today) add(p + '.accessed', 'future_date', 'Opslagsdatoen ligger i fremtiden.');
      }
      if (keys(tax.sourceResults).indexOf(result) < 0) add(p + '.result', 'invalid', 'Ukendt resultat.');
      if (s.attachment) {
        var a = s.attachment;
        if (!tax.attachmentTypes[(a.type || '').toLowerCase()]) add(p + '.attachment', 'bad_type', 'Kun PNG, JPG, WebP, GIF og PDF kan vedhæftes.');
        else if (nAtt >= L.max_attachments) add(p + '.attachment', 'too_many', 'Højst ' + L.max_attachments + ' vedhæftninger i alt.');
        else {
          nAtt++;
          if (a.bytes && a.bytes > L.attachment_bytes) {
            add(p + '.attachment', 'too_big', 'Vedhæftningen er over ' + Math.floor(L.attachment_bytes / 1048576) +
              ' MB. Læg den et sted og angiv linket i stedet.');
          }
        }
      }
      sources.push({ type: type, result: result });
    });

    // fields
    var fIn = Array.isArray(payload.fields) ? payload.fields : [];
    var seen = {}, fields = [];
    if (fIn.length > L.max_fields) add('fields', 'too_many', 'For mange felter.');
    fIn.slice(0, L.max_fields).forEach(function (f, i) {
      var p = 'fields[' + i + ']';
      f = (f && typeof f === 'object') ? f : {};
      var key = norm(f.field), spec = fieldByKey[key];
      if (!spec) { add(p + '.field', 'invalid', 'Ukendt felt.'); return; }
      if (seen[key]) add(p + '.field', 'duplicate', 'Feltet er angivet to gange.');
      seen[key] = true;
      var kind = spec.kind;
      var value = norm(f.value, kind === 'longtext');
      var conf = norm(f.confidence), comment = norm(f.comment, true);
      var refs = Array.isArray(f.sources) ? f.sources.filter(function (r) { return typeof r === 'number' && r % 1 === 0; }) : [];
      if (!value) add(p + '.value', 'required', 'Udfyld værdien, eller fjern feltet.');
      else {
        var limit = kind === 'longtext' ? L.longtext : L.text;
        if (value.length > limit) add(p + '.value', 'too_long', 'Højst ' + limit + ' tegn.');
        if (kind === 'date') {
          var bad = checkDate(value);
          if (bad) add(p + '.value', bad[0], bad[1]);
        } else if (kind === 'select') {
          if (key === 'gender' && tax.genderValues.indexOf(value) < 0) add(p + '.value', 'invalid', 'Vælg en af de angivne værdier.');
        } else if (kind === 'qid' && !QID_RE.test(value)) {
          add(p + '.value', 'invalid_qid', 'Et Wikidata-nummer ser ud som Q12345.');
        } else if (kind === 'url_or_id' && /^(http|www)/i.test(value) && !URL_RE.test(value)) {
          add(p + '.value', 'invalid_url', 'Linket skal begynde med http:// eller https://.');
        }
      }
      if (confKeys.indexOf(conf) < 0) add(p + '.confidence', 'required', 'Angiv sikkerhedsgrad for feltet.');
      if (comment.length > L.comment) add(p + '.comment', 'too_long', 'Højst ' + L.comment + ' tegn.');
      if (!refs.length) add(p + '.sources', 'required', 'Knyt mindst én kilde til feltet.');
      else if (refs.some(function (r) { return r < 0 || r >= sources.length; })) {
        add(p + '.sources', 'invalid', 'Henviser til en kilde, der ikke findes.');
      } else if (conf === 'certain' || conf === 'probable') {
        var backing = refs.filter(function (r) {
          var sp = typeByKey[sources[r].type];
          return sp && sp.strong && sources[r].result === 'stoetter';
        });
        if (!backing.length) {
          add(p + '.sources', 'weak_sources',
            '»Sikker« og »Sandsynlig« kræver en kilde, der understøtter feltet og ikke kun er personlig viden. ' +
            'Vælg »Forslag«, eller tilføj en kilde.');
        }
      }
      fields.push({ field: key, value: value });
    });
    var byKey = {};
    fields.forEach(function (f) { byKey[f.field] = f.value; });
    var by = yearOf(byKey.birth_date), dy = yearOf(byKey.death_date);
    if (by && dy && dy < by) add('fields', 'death_before_birth', 'Dødsåret ligger før fødselsåret.');
    if ((status === 'identified' || status === 'candidate' || status === 'partial') && !fields.length) {
      add('fields', 'required', 'Udfyld mindst ét felt, eller vælg en anden type bidrag.');
    }
    if (status === 'unidentifiable' && !sources.some(function (s) { return s.result === 'intet_fund'; })) {
      add('sources', 'required_negative',
        'Et »søgt uden resultat« skal dokumentere, hvor du har søgt: marker mindst én kilde som »Søgt, intet fund«.');
    }

    if (norm(payload.comment, true).length > L.comment) add('comment', 'too_long', 'Højst ' + L.comment + ' tegn.');

    var c = payload.contributor || {};
    var name = norm(c.name);
    if (name.length < 2) add('contributor.name', 'required', 'Skriv dit navn, så bidraget kan krediteres.');
    [['name', L.name], ['contact', L.contact], ['affiliation', L.contact], ['expertise', L.contact]].forEach(function (pair) {
      if (norm(c[pair[0]]).length > pair[1]) add('contributor.' + pair[0], 'too_long', 'Højst ' + pair[1] + ' tegn.');
    });
    if (payload.consent !== true) add('consent', 'required', 'Du skal acceptere vilkårene (CC BY 4.0 med navngivelse).');
    return errs;
  }

  return { validate: validate, normalise: norm, checkDate: checkDate };
});
