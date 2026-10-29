/* crowd-form.js — crowd-contribute.html?reg=Reg…[&edit=CS-…]
 *
 * A structured contribution about ONE register person: what the contributor
 * has found (identification status, field values), how sure they are (a
 * grade and a comment per field), and what it rests on (sources — each field
 * must point at at least one). The diary pages themselves are never copied
 * here: the sidebar links into them (entry anchor + name highlight) and to
 * the Royal Library's facsimile.
 *
 * Validation is crowd-validate.js (same rules as the server's validate.py).
 * Drafts autosave to this browser only; nothing is sent until "Send bidrag".
 */
(function () {
  'use strict';

  var U = window.CrowdUI, T = U.T, S = window.CrowdStore, V = window.CrowdValidate, esc = U.esc;
  var $ = function (id) { return document.getElementById(id); };

  var params = new URLSearchParams(location.search);
  var pid = (params.get('reg') || '').trim();
  var editId = params.get('edit') || '';

  var P = (typeof PERSONS_EXTRA !== 'undefined' && PERSONS_EXTRA[pid]) || null;
  var REC = U.queueRecord(pid);
  var LABEL = (REC && REC.l) || (P && P.label) || '';
  var DESC = (P && P.description) || (REC && REC.ds) || '';
  var SURNAME = U.surnameOf(LABEL);
  var APPROVED = (window.CROWD_APPROVED || {})[pid] || [];

  if (!pid || !LABEL) {
    $('js-main').innerHTML = '<div class="crowd-sec"><h2>Personen blev ikke fundet</h2><p>Vælg en person i ' +
      '<a href="crowd.html">arbejdskøen</a>, eller åbn siden fra en persons side i <a href="persons.html">personregistret</a>.</p></div>';
    return;
  }
  document.title = LABEL + ' — Bidrag — HCA\'s Hvem-hvad-hvor';
  $('js-crumb').textContent = pid;
  $('js-h1').textContent = LABEL;

  /* ── state ────────────────────────────────────────────────────────────── */
  var state = blank();
  var live = false;             // re-validate on every change once a send was attempted
  var fieldOrder = T.fields.map(function (f) { return f.key; });

  function blank() {
    var p = S.profile();
    return {
      ident: { status: '', summary: '', same_as: '' }, overall: '', fields: {}, sources: [newSource()], comment: '',
      contributor: { name: p.name || '', contact: p.contact || '', affiliation: p.affiliation || '',
                     expertise: p.expertise || '', public_credit: !!p.public_credit },
      consent: false
    };
  }
  function newSource() {
    return { type: '', citation: '', url: '', locator: '', accessed: '', result: 'stoetter', note: '' };
  }

  /* gaps → the fields they invite */
  var wanted = {};
  (REC ? REC.g : []).forEach(function (g) {
    var gap = U.find(T.gaps, g);
    if (gap) gap.fields.forEach(function (f) { wanted[f] = true; });
  });

  /* ── what the register says (read-only hint per field) ────────────────── */
  function registerSays(key) {
    if (!P) return '';
    var natLabels = (typeof NATIONALITY_LABELS !== 'undefined' && NATIONALITY_LABELS) || {};
    switch (key) {
      case 'surname': return SURNAME;
      case 'birth_date': return P.born || '';
      case 'death_date': return P.died || '';
      case 'description': return P.description || '';
      case 'nationality': return (P.nationalities || []).map(function (k) { return natLabels[k] || k; }).join(', ');
      case 'gender': return P.gender ? P.gender + ' (afledt)' : '';
      case 'role_bucket': return (P.roles || []).join('; ') + ((P.roles || []).length ? ' (afledt)' : '');
      default: return '';
    }
  }

  /* ── rendering ────────────────────────────────────────────────────────── */
  function fieldInput(f, val) {
    var id = 'f-' + f.key, path = 'fields.' + f.key + '.value', v = esc(val || '');
    var common = ' id="' + id + '" data-f="' + f.key + '" data-k="value" data-path="' + path + '"';
    if (f.kind === 'longtext') return '<textarea' + common + ' rows="3">' + v + '</textarea>';
    if (f.kind === 'select' && f.key === 'gender') {
      return '<select' + common + '><option value=""></option>' + T.genderValues.map(function (g) {
        return '<option' + (g === val ? ' selected' : '') + '>' + esc(g) + '</option>'; }).join('') + '</select>';
    }
    if (f.key === 'role_bucket') {
      return '<select' + common + '><option value=""></option>' + (window.CROWD_ROLE_BUCKETS || []).map(function (b) {
        return '<option' + (b === val ? ' selected' : '') + '>' + esc(b) + '</option>'; }).join('') + '</select>';
    }
    var ph = f.kind === 'date' ? ' placeholder="ÅÅÅÅ-MM-DD"' : f.kind === 'qid' ? ' placeholder="Q12345"' : '';
    var list = f.key === 'nationality' ? ' list="dl-nat"' : '';
    return '<input type="text"' + common + ' value="' + v + '"' + ph + list + ' autocomplete="off">';
  }

  function fieldRow(f) {
    var st = state.fields[f.key] || {};
    var filled = !!(st.value && st.value.trim());
    var says = registerSays(f.key);
    var help = f.key === 'wikidata' ? 'Slå personen op på wikidata.org og skriv Q-nummeret. Redaktionen kontrollerer det.' :
      f.key === 'birth_date' || f.key === 'death_date' ? 'Skriv det, du kan dokumentere: kun år er fint. »ca. 1820« er tilladt.' : '';
    return '<div class="crowd-fld' + (wanted[f.key] ? ' crowd-fld--wanted' : '') + (filled ? ' crowd-fld--filled' : '') + '" data-row="' + f.key + '">' +
      '<div class="crowd-fld__head"><label class="crowd-field-label" for="f-' + f.key + '">' + esc(f.da) + '</label>' +
      (says ? '<span class="crowd-fld__reg">Registret: ' + esc(says) + '</span>' : '') + '</div>' +
      fieldInput(f, st.value) + (help ? '<p class="crowd-help">' + esc(help) + '</p>' : '') +
      '<div class="crowd-fld__meta">' +
        '<div><div class="crowd-field-label">Hvor sikker er du?</div><div class="crowd-conf-choice">' +
          T.confidence.map(function (c) {
            return '<label title="' + esc(c.guidance) + '"><input type="radio" name="conf-' + f.key + '" data-f="' + f.key + '" data-k="confidence" value="' + c.key + '"' +
              (st.confidence === c.key ? ' checked' : '') + '> ' + esc(c.da) + '</label>';
          }).join('') + '<span class="crowd-err-slot" data-path="fields.' + f.key + '.confidence"></span></div></div>' +
        '<div><div class="crowd-field-label">Kilde(r) til dette felt</div><div class="crowd-fld__srcs" data-srcs-for="' + f.key + '"></div>' +
          '<span class="crowd-err-slot" data-path="fields.' + f.key + '.sources"></span></div>' +
        '<div class="crowd-fld__cmt"><label class="crowd-field-label" for="c-' + f.key + '">Kommentar til feltet (valgfri)</label>' +
          '<textarea id="c-' + f.key + '" data-f="' + f.key + '" data-k="comment" rows="2" placeholder="Fx: fødselsåret følger af folketællingen 1860; navnet staves Peter i kirkebogen.">' + esc(st.comment || '') + '</textarea></div>' +
      '</div></div>';
  }

  function identSection() {
    var s = state.ident;
    var html = '<h2>1 · Hvad vil du bidrage med?</h2><div class="crowd-radios" role="radiogroup" aria-label="Type af bidrag">' +
      T.identification.map(function (i) {
        return '<label class="crowd-radio' + (s.status === i.key ? ' crowd-radio--on' : '') + '"><input type="radio" name="ident" data-id="status" value="' + i.key + '"' +
          (s.status === i.key ? ' checked' : '') + '><span>' + esc(i.da) + '</span></label>';
      }).join('') + '</div><span class="crowd-err-slot" data-path="identification.status"></span>';
    html += '<div id="js-ident-extra">' + identExtra() + '</div>';
    return html;
  }
  function identExtra() {
    var s = state.ident, h = '';
    if (!s.status) return '';
    if (s.status === 'duplicate') {
      h += '<div class="crowd-sub-block" style="margin-top:var(--sp4)"><label class="crowd-lbl" for="i-same">Samme person som (Reg-ID)</label>' +
        '<input type="text" id="i-same" data-id="same_as" data-path="identification.same_as" value="' + esc(s.same_as) + '" placeholder="Reg0012345">' +
        '<p class="crowd-help">Find ID\'et i adresselinjen på den anden persons side (?reg=…).</p></div>';
    }
    var lbl = s.status === 'not_individual' ? 'Hvorfor er posten ikke en enkeltperson?' :
      s.status === 'unidentifiable' ? 'Hvad har du søgt efter, og hvor? (hjælper næste person)' : 'Kort fortælling om identifikationen (valgfri)';
    h += '<div style="margin-top:var(--sp4)"><label class="crowd-lbl" for="i-sum">' + lbl + '</label>' +
      '<textarea id="i-sum" data-id="summary" data-path="identification.summary" rows="3">' + esc(s.summary) + '</textarea></div>';
    if (s.status === 'identified' || s.status === 'candidate') {
      h += '<div style="margin-top:var(--sp4)"><div class="crowd-field-label">Hvor sikker er du på identifikationen som helhed?</div><div class="crowd-conf-choice">' +
        T.confidence.map(function (c) {
          return '<label title="' + esc(c.guidance) + '"><input type="radio" name="overall" data-id="overall" value="' + c.key + '"' + (s.overall === c.key ? ' checked' : '') + '> ' + esc(c.da) +
            ' <span class="crowd-dim">— ' + esc(c.guidance) + '</span></label>';
        }).join('') + '</div><span class="crowd-err-slot" data-path="overall_confidence"></span></div>';
    }
    return h;
  }

  function fieldsSection() {
    var firstWanted = T.fields.filter(function (f) { return wanted[f.key]; });
    var rest = T.fields.filter(function (f) { return !wanted[f.key]; });
    var html = '<h2>2 · Oplysninger</h2><p class="crowd-lede">Udfyld kun det, du kan dokumentere. Når et felt har en værdi, vælger du en sikkerhedsgrad og peger på mindst én kilde. ' +
      (firstWanted.length ? 'De fremhævede felter er dem, registret mangler.' : '') + '</p>';
    html += '<div class="crowd-fields" id="js-fields">' + firstWanted.map(fieldRow).join('') + '</div>';
    if (rest.length) {
      var anyFilledRest = rest.some(function (f) { return state.fields[f.key] && state.fields[f.key].value; });
      html += '<details class="crowd-more-fields"' + (!firstWanted.length || anyFilledRest ? ' open' : '') + '><summary>' + (firstWanted.length ? 'Flere felter' : 'Felter') +
        ' (' + rest.length + ')</summary><div class="crowd-fields">' + rest.map(fieldRow).join('') + '</div></details>';
    }
    html += '<datalist id="dl-nat">' + (window.CROWD_NATIONALITIES || []).map(function (n) { return '<option value="' + esc(n) + '">'; }).join('') + '</datalist>';
    html += '<span class="crowd-err-slot" data-path="fields"></span>';
    return html;
  }

  function sourceCard(s, i) {
    var path = 'sources[' + i + ']';
    var att = '';
    if (S.mode() === 'api') {
      att = '<div class="crowd-src__att"><label class="crowd-lbl" for="s-att-' + i + '">Vedhæft billede eller PDF (valgfri, højst 4 MB)</label>' +
        '<input type="file" id="s-att-' + i + '" data-s="' + i + '" data-k="attachment" accept="image/png,image/jpeg,image/webp,image/gif,application/pdf">' +
        (s.attachment ? '<p class="crowd-help">Vedhæftet: ' + esc(s.attachment.name) + ' (' + Math.round((s.attachment.bytes || 0) / 1024) + ' kB)</p>' : '') +
        (s.attachedFile ? '<p class="crowd-help">Tidligere vedhæftet: ' + esc(s.attachedFile) + '</p>' : '') +
        '<span class="crowd-err-slot" data-path="' + path + '.attachment"></span></div>';
    }
    return '<div class="crowd-src" data-src="' + i + '"><div class="crowd-src__title"><span>Kilde ' + (i + 1) + '</span>' +
      (state.sources.length > 1 ? '<button type="button" class="crowd-link" data-remove-src="' + i + '">Fjern</button>' : '') + '</div>' +
      '<div class="crowd-row">' +
        '<div><label class="crowd-lbl" for="s-type-' + i + '">Type</label><select id="s-type-' + i + '" data-s="' + i + '" data-k="type" data-path="' + path + '.type">' +
          '<option value=""></option>' + T.sourceTypes.map(function (t) { return '<option value="' + t.key + '"' + (s.type === t.key ? ' selected' : '') + '>' + esc(t.da) + '</option>'; }).join('') + '</select></div>' +
        '<div><label class="crowd-lbl" for="s-res-' + i + '">Resultat</label><select id="s-res-' + i + '" data-s="' + i + '" data-k="result" data-path="' + path + '.result">' +
          T.sourceResults.map(function (r) { return '<option value="' + r.key + '"' + (s.result === r.key ? ' selected' : '') + '>' + esc(r.da) + '</option>'; }).join('') + '</select></div>' +
      '</div>' +
      '<div style="margin-bottom:var(--sp3)"><label class="crowd-lbl" for="s-cit-' + i + '">Kildehenvisning</label>' +
        '<input type="text" id="s-cit-' + i + '" data-s="' + i + '" data-k="citation" data-path="' + path + '.citation" value="' + esc(s.citation) + '" placeholder="Fx: Folketælling 1860, Slagelse Sogn, husstand 14 — eller: Dansk Biografisk Leksikon, 3. udg., bd. 4, s. 211">' +
        '<p class="crowd-help">Hvad er kilden, og hvor står oplysningen? En fremmed skal kunne finde den igen.</p></div>' +
      '<div class="crowd-row">' +
        '<div><label class="crowd-lbl" for="s-url-' + i + '">Link (foretrækkes)</label><input type="text" id="s-url-' + i + '" inputmode="url" data-s="' + i + '" data-k="url" data-path="' + path + '.url" value="' + esc(s.url) + '" placeholder="https://…"></div>' +
        '<div><label class="crowd-lbl" for="s-loc-' + i + '">Side, folio, opslag eller filnavn</label><input type="text" id="s-loc-' + i + '" data-s="' + i + '" data-k="locator" data-path="' + path + '.locator" value="' + esc(s.locator) + '" placeholder="s. 211 / skærmbillede-2026-10-29.png"></div>' +
        '<div><label class="crowd-lbl" for="s-acc-' + i + '">Opslået den</label><input type="text" id="s-acc-' + i + '" data-s="' + i + '" data-k="accessed" data-path="' + path + '.accessed" value="' + esc(s.accessed) + '" placeholder="ÅÅÅÅ-MM-DD"></div>' +
      '</div>' + att +
      '<div style="margin-top:var(--sp3)"><label class="crowd-lbl" for="s-note-' + i + '">Note til kilden (valgfri)</label>' +
        '<textarea id="s-note-' + i + '" data-s="' + i + '" data-k="note" rows="2">' + esc(s.note) + '</textarea></div></div>';
  }

  function sourcesSection() {
    return '<h2>3 · Kilder</h2><p class="crowd-lede">Uden kilde kan en redaktør ikke vurdere bidraget. Link til en webside, database eller et digitaliseret dokument, eller henvis præcist til et billede, skærmbillede, en PDF eller en trykt publikation. ' +
      'Har du søgt uden resultat, så tilføj kilden og vælg »Søgt, intet fund«.</p>' +
      '<div class="crowd-srcs" id="js-srcs">' + state.sources.map(sourceCard).join('') + '</div>' +
      '<p style="margin-top:var(--sp4)"><button type="button" class="crowd-btn" id="js-add-src"' + (state.sources.length >= T.limits.max_sources ? ' disabled' : '') + '>+ Tilføj kilde</button></p>' +
      '<span class="crowd-err-slot" data-path="sources"></span>';
  }

  function whoSection() {
    var c = state.contributor;
    return '<h2>4 · Kommentar og kreditering</h2>' +
      '<label class="crowd-lbl" for="o-comment">Fri kommentar til redaktionen (valgfri)</label>' +
      '<textarea id="o-comment" data-o="comment" data-path="comment" rows="3" placeholder="Alt, der ikke passer i felterne: tvivl, alternative læsninger, hvad du ikke nåede at undersøge.">' + esc(state.comment) + '</textarea>' +
      '<div class="crowd-row" style="margin-top:var(--sp5)">' +
        '<div><label class="crowd-lbl" for="c-name">Dit navn</label><input type="text" id="c-name" data-c="name" data-path="contributor.name" value="' + esc(c.name) + '" autocomplete="name"></div>' +
        '<div><label class="crowd-lbl" for="c-contact">E-mail (valgfri, vises aldrig)</label><input type="text" id="c-contact" data-c="contact" data-path="contributor.contact" value="' + esc(c.contact) + '" autocomplete="email"></div>' +
        '<div><label class="crowd-lbl" for="c-aff">Tilknytning (valgfri)</label><input type="text" id="c-aff" data-c="affiliation" data-path="contributor.affiliation" value="' + esc(c.affiliation) + '" placeholder="Fx slægtsforening eller lokalarkiv"></div>' +
        '<div><label class="crowd-lbl" for="c-exp">Egne, lokale kendskabsområder (valgfri)</label><input type="text" id="c-exp" data-c="expertise" data-path="contributor.expertise" value="' + esc(c.expertise) + '" placeholder="Fx Slagelse, Sorø, Nordslesvig"></div>' +
      '</div>' +
      '<label class="crowd-radio" style="margin-top:var(--sp3)"><input type="checkbox" data-c="public_credit"' + (c.public_credit ? ' checked' : '') + '><span>Nævn mig ved navn som bidragyder, når mit bidrag er godkendt.</span></label>' +
      '<label class="crowd-radio" style="margin-top:var(--sp2)"><input type="checkbox" data-o="consent" data-path="consent"' + (state.consent ? ' checked' : '') + '><span>Jeg accepterer, at oplysningerne udgives under <strong>CC BY 4.0</strong> (som resten af materialet), med navngivelse af mig, hvis jeg har ønsket det.</span></label>' +
      '<span class="crowd-err-slot" data-path="consent"></span>';
  }

  function renderAll() {
    var restored = state._restored ? '<div class="crowd-note crowd-note--warn">Din kladde fra ' + esc(U.fmtStamp(state._restored)) + ' er genoprettet. <button type="button" class="crowd-link" id="js-discard">Start forfra</button></div>' : '';
    $('js-main').innerHTML = '<div class="crowd-form" id="js-form">' + restored +
      '<div class="crowd-note" role="status">' + U.modeNote(S.mode()) + '</div>' +
      '<section class="crowd-sec crowd-person"><p class="crowd-dim" style="margin:0">Registerpost</p><h2 class="crowd-person__name">' + esc(LABEL) + '</h2>' +
        '<p class="crowd-person__desc">' + (DESC ? esc(DESC) : '<span class="crowd-dim">Ingen beskrivelse i registret</span>') + '</p>' +
        (REC ? '<div class="crowd-card__tags">' + U.levelBadge(REC.lv) + (REC.fl ? '<span class="crowd-badge crowd-badge--fleeting">Flygtig omtale</span>' : '') + '</div>' +
          '<div class="crowd-card__gaps">' + U.gapChips(REC.g) + '</div>' : '') +
        (editId ? '<p class="crowd-note crowd-note--warn" style="margin-top:var(--sp3)">Du retter bidrag ' + esc(editId) + '. Når du sender igen, erstatter den nye version den gamle, og redaktionen vurderer det på ny.</p>' : '') +
      '</section>' +
      '<section class="crowd-sec" id="sec-ident">' + identSection() + '</section>' +
      '<section class="crowd-sec" id="sec-fields">' + fieldsSection() + '</section>' +
      '<section class="crowd-sec" id="sec-srcs">' + sourcesSection() + '</section>' +
      '<section class="crowd-sec" id="sec-who">' + whoSection() + '</section>' +
      '<div id="js-errors"></div>' +
      '<div class="crowd-actions"><button type="button" class="crowd-btn crowd-btn--primary" id="js-send">Send bidrag</button>' +
        '<span class="crowd-saved" id="js-saved">Kladden gemmes automatisk i denne browser.</span></div></div>';
    refreshFieldSources();
  }

  /* source check-lists inside each filled field */
  function srcLabel(s, i) {
    var t = U.label(T.sourceTypes, s.type, '');
    var c = (s.citation || '').trim();
    return 'Kilde ' + (i + 1) + (t ? ' (' + t.split(' (')[0] + ')' : '') + (c ? ': ' + c.slice(0, 50) + (c.length > 50 ? '…' : '') : '');
  }
  function refreshFieldSources() {
    document.querySelectorAll('[data-srcs-for]').forEach(function (box) {
      var key = box.getAttribute('data-srcs-for');
      var chosen = (state.fields[key] && state.fields[key].sources) || [];
      box.innerHTML = state.sources.map(function (s, i) {
        return '<label><input type="checkbox" data-f="' + key + '" data-k="source" value="' + i + '"' + (chosen.indexOf(i) >= 0 ? ' checked' : '') + '> <span>' + esc(srcLabel(s, i)) + '</span></label>';
      }).join('');
    });
  }

  /* ── sidebar ──────────────────────────────────────────────────────────── */
  function dateOfMeta(meta) {
    if (!meta) return '';
    if (meta.d) {
      var m = /^(\d{2})-(\d{2})-(\d{4})$/.exec(meta.d);
      if (m) return U.fmtDate(m[3] + '-' + m[2] + '-' + m[1]);
      var my = /^(\d{2})-(\d{4})$/.exec(meta.d);
      if (my) return ['', 'januar', 'februar', 'marts', 'april', 'maj', 'juni', 'juli', 'august', 'september', 'oktober', 'november', 'december'][parseInt(my[1], 10)] + ' ' + my[2];
      return meta.d;
    }
    return meta.y || '';
  }

  function renderSide() {
    var anchors = {};
    if (REC) REC.m.forEach(function (m) { anchors[m[0]] = m[1]; });
    var pages = (window.DiaryWire && DiaryWire.pagesFor(pid)) || (REC ? REC.m.map(function (m) { return m[0]; }) : []);
    var meta = (typeof DIARY_META !== 'undefined') ? DIARY_META : {};
    var kb = window.CROWD_KB_LINKS || {};
    var all = pages.length;
    var showN = 8;
    function mention(pag) {
      var m = meta[pag] || {};
      var when = dateOfMeta(m);
      var links = '<a href="' + esc(U.diaryHref(pag, anchors[pag] || '', SURNAME)) + '">Åbn dagbogssiden</a>' +
        (kb[pag] ? U.externalLink(kb[pag], 'Læs siden hos Det Kgl. Bibliotek') : '');
      return '<div class="crowd-mention"><strong>' + esc(U.pageLabel(pag)) + '</strong>' +
        '<span class="crowd-dim">' + esc(when) + (m.pl ? ' · ' + esc(m.pl) : '') + (anchors[pag] ? ' · navnet står i posten for ' + esc(U.fmtDate(anchors[pag])) : '') + '</span>' +
        '<span class="crowd-mention__links">' + links + '</span></div>';
    }
    var html = '<div class="info-block"><div class="info-block__header">Registerets oplysninger</div><div class="info-block__body"><table class="info-table">' +
      '<tr><td>ID</td><td style="font-family:monospace">' + esc(pid) + '</td></tr>' +
      '<tr><td>Navn</td><td>' + esc(LABEL) + '</td></tr>' +
      (REC && REC.c ? '<tr><td>Formodet land</td><td>' + esc(REC.c) + ' <span class="crowd-basis">' + esc(U.label(T.bases, REC.cb, '')) + '</span></td></tr>' : '') +
      (REC && REC.lc && REC.lc !== REC.c ? '<tr><td>Formodet sted</td><td>' + esc(REC.lc) + ' <span class="crowd-basis">' + esc(U.label(T.bases, REC.lb, '')) + '</span></td></tr>' : '') +
      (P && P.nationalities && P.nationalities.length ? '<tr><td>Nationalitet</td><td>' + esc(P.nationalities.map(function (k) { return ((typeof NATIONALITY_LABELS !== 'undefined' && NATIONALITY_LABELS[k]) || k); }).join(', ')) + '</td></tr>' : '') +
      '</table><p style="margin-top:var(--sp3);font-size:0.8rem"><a href="persons.html?reg=' + esc(pid) + '">Personsiden</a></p></div></div>';

    html += '<div class="info-block"><div class="info-block__header">Omtaler i dagbøgerne <span class="info-block__tag">' + all + '</span></div><div class="info-block__body" id="js-mentions">' +
      (pages.length ? pages.slice(0, showN).map(mention).join('') : '<p class="crowd-dim">Ingen dagbogssider med transskriberet tekst.</p>') +
      (all > showN ? '<p style="margin:var(--sp3) 0 0"><button type="button" class="crowd-link" id="js-all-mentions">Vis alle ' + all + '</button></p>' : '') +
      '</div></div>';
    $('js-side').innerHTML = html;
    var btn = $('js-all-mentions');
    if (btn) btn.addEventListener('click', function () {
      $('js-mentions').innerHTML = pages.map(mention).join('');
    });

    // Search help — the links the person page already offers (docs/external-links.md)
    if (P && (P.bioLinks || []).length) {
      var q = encodeURIComponent(P.searchName || LABEL);
      $('js-side').insertAdjacentHTML('beforeend', '<div class="info-block info-block--enriched"><div class="info-block__header">Søgehjælp <span class="info-block__tag">tilføjet</span></div><div class="info-block__body" style="font-size:0.84rem">' +
        '<p class="crowd-dim" style="margin-top:0">Søgninger, ikke identifikationer.</p><div style="display:flex;flex-direction:column;gap:6px">' +
        P.bioLinks.map(function (l) { return U.externalLink(l.url, l.label); }).join('') +
        U.externalLink('https://museumodense.dk/alle-udgivelser/?artikel_navn=' + q.replace(/%20/g, '+'), 'Anderseniana') +
        '</div></div></div>');
    }

    if (APPROVED.length) {
      $('js-side').insertAdjacentHTML('beforeend', '<div class="info-block info-block--enriched"><div class="info-block__header">Allerede godkendt <span class="info-block__tag">tilføjet</span></div><div class="info-block__body">' +
        APPROVED.map(function (a) {
          return '<div class="crowd-claim"><strong>' + esc(U.label(T.fields, a.f, a.f)) + ':</strong> ' + esc(a.v) + ' ' + U.confPill(a.c) +
            '<br><span class="crowd-dim">' + esc(a.by) + ', ' + esc(U.fmtDate(a.d)) + '</span></div>';
        }).join('') + '<p class="crowd-dim" style="margin-bottom:0">Har du en anden oplysning eller en bedre kilde, så skriv den som nyt bidrag.</p></div></div>');
    }
    S.stats().then(function (st) {
      var ps = st && st.personStatus && st.personStatus[pid];
      if (ps && ps.pending) {
        $('js-side').insertAdjacentHTML('beforeend', '<div class="crowd-note crowd-note--inline">' + ps.pending + (ps.pending === 1 ? ' bidrag' : ' bidrag') + ' til denne person afventer redaktionen.</div>');
      }
    }).catch(function () {});
  }

  /* ── events ───────────────────────────────────────────────────────────── */
  var saveTimer = null;
  function scheduleSave() {
    clearTimeout(saveTimer);
    saveTimer = setTimeout(function () {
      if (editId) return;
      var copy = JSON.parse(JSON.stringify(state));
      copy.sources.forEach(function (s) { delete s.attachment; });
      copy._saved = new Date().toISOString().replace(/\.\d+Z$/, 'Z');
      S.draft.set(pid, copy);
      var el = $('js-saved'); if (el) el.textContent = 'Kladde gemt.';
    }, 400);
  }

  function setRowFilled(key) {
    var row = document.querySelector('[data-row="' + key + '"]');
    if (!row) return;
    var st = state.fields[key];
    row.classList.toggle('crowd-fld--filled', !!(st && st.value && st.value.trim()));
  }

  function onInput(ev) {
    var t = ev.target;
    var f = t.getAttribute('data-f'), k = t.getAttribute('data-k');
    if (f) {
      var st = state.fields[f] || (state.fields[f] = { value: '', confidence: '', comment: '', sources: [] });
      if (k === 'source') {
        var i = parseInt(t.value, 10), at = st.sources.indexOf(i);
        if (t.checked && at < 0) st.sources.push(i); else if (!t.checked && at >= 0) st.sources.splice(at, 1);
      } else st[k] = t.value;
      if (k === 'value') setRowFilled(f);
    } else if (t.hasAttribute('data-s')) {
      var si = parseInt(t.getAttribute('data-s'), 10), sk = t.getAttribute('data-k');
      if (sk === 'attachment') return attach(t, si);
      state.sources[si][sk] = t.value;
      if (sk === 'citation' || sk === 'type') refreshFieldSources();
    } else if (t.hasAttribute('data-id')) {
      var idk = t.getAttribute('data-id');
      if (idk === 'overall') state.overall = t.value;
      else {
        state.ident[idk] = t.value;
        if (idk === 'status' && ev.type === 'change') {
          $('js-ident-extra').innerHTML = identExtra();
          document.querySelectorAll('.crowd-radio').forEach(function (r) {
            var inp = r.querySelector('input[name="ident"]'); if (inp) r.classList.toggle('crowd-radio--on', inp.checked);
          });
        }
      }
    } else if (t.hasAttribute('data-c')) {
      var ck = t.getAttribute('data-c');
      state.contributor[ck] = t.type === 'checkbox' ? t.checked : t.value;
    } else if (t.hasAttribute('data-o')) {
      var ok = t.getAttribute('data-o');
      if (ok === 'consent') state.consent = t.checked; else state.comment = t.value;
    } else return;
    scheduleSave();
    if (live) showErrors(validateNow(), false);
  }

  function attach(input, i) {
    var file = input.files && input.files[0];
    if (!file) { delete state.sources[i].attachment; return; }
    if (file.size > T.limits.attachment_bytes) {
      state.sources[i].attachment = { name: file.name, type: file.type, bytes: file.size, data: '' };
      showErrors([{ path: 'sources[' + i + '].attachment', code: 'too_big', msg: 'Vedhæftningen er over 4 MB. Læg den et sted og angiv linket i stedet.' }], false);
      return;
    }
    var fr = new FileReader();
    fr.onload = function () {
      state.sources[i].attachment = { name: file.name, type: file.type, bytes: file.size, data: String(fr.result).split(',')[1] || '' };
    };
    fr.readAsDataURL(file);
  }

  /* ── validation / sending ─────────────────────────────────────────────── */
  function buildPayload() {
    var filled = fieldOrder.filter(function (k) { return state.fields[k] && String(state.fields[k].value || '').trim(); });
    return {
      person_id: pid, person_label: LABEL,
      identification: { status: state.ident.status, summary: state.ident.summary, same_as: state.ident.same_as },
      overall_confidence: state.overall,
      fields: filled.map(function (k) {
        var f = state.fields[k];
        return { field: k, value: f.value, confidence: f.confidence, comment: f.comment, sources: (f.sources || []).slice().sort(function (a, b) { return a - b; }) };
      }),
      sources: state.sources.map(function (s) {
        var o = { type: s.type, citation: s.citation, url: s.url, locator: s.locator, accessed: s.accessed, result: s.result, note: s.note };
        if (s.attachment && s.attachment.data) o.attachment = s.attachment;
        return o;
      }),
      comment: state.comment,
      contributor: state.contributor,
      consent: state.consent === true,
      context: { area: (REC && (REC.c || REC.lc)) || '', doubt: !!(REC && REC.g.indexOf('doubt') >= 0), level: REC ? REC.lv : '', gaps: REC ? REC.g : [] }
    };
  }
  function validateNow() { return V.validate(buildPayload(), T); }

  function errPathToSlot(path, payload) {
    var m = /^fields\[(\d+)\]\.(.+)$/.exec(path);
    if (m && payload.fields[+m[1]]) return 'fields.' + payload.fields[+m[1]].field + '.' + m[2];
    return path;
  }

  function showErrors(errs, scroll) {
    document.querySelectorAll('.crowd-err').forEach(function (n) { n.remove(); });
    document.querySelectorAll('.crowd-input-err').forEach(function (n) { n.classList.remove('crowd-input-err'); });
    var payload = buildPayload(), list = [];
    errs.forEach(function (e) {
      var slotPath = errPathToSlot(e.path, payload);
      var target = document.querySelector('[data-path="' + CSS.escape(slotPath) + '"]') ||
        document.querySelector('[data-path="' + CSS.escape(slotPath.replace(/\.[^.]*$/, '')) + '"]');
      var id = 'err-' + list.length;
      if (target) {
        if (target.classList.contains('crowd-err-slot')) target.insertAdjacentHTML('beforeend', '<p class="crowd-err" id="' + id + '">' + esc(e.msg) + '</p>');
        else {
          target.classList.add('crowd-input-err');
          var anchor = target.type === 'checkbox' && target.closest('label') ? target.closest('label') : target;
          anchor.insertAdjacentHTML('afterend', '<p class="crowd-err" id="' + id + '">' + esc(e.msg) + '</p>');
        }
      }
      list.push({ id: id, msg: e.msg, el: target });
    });
    var box = $('js-errors');
    if (!errs.length) { box.innerHTML = ''; return; }
    box.innerHTML = '<div class="crowd-summary-errors" role="alert" tabindex="-1"><strong>Bidraget kan ikke sendes endnu (' + errs.length + '):</strong><ul>' +
      list.map(function (l) { return '<li><a href="#' + l.id + '">' + esc(l.msg) + '</a></li>'; }).join('') + '</ul></div>';
    if (scroll) box.firstChild.focus();
  }

  function send() {
    live = true;
    var errs = validateNow();
    showErrors(errs, true);
    if (errs.length) return;
    var btn = $('js-send');
    btn.disabled = true; btn.textContent = 'Sender …';
    var payload = buildPayload();
    S.submit(payload, editId || null, { label: LABEL, description: DESC, area: payload.context.area, doubt: payload.context.doubt,
      level: payload.context.level, gaps: payload.context.gaps }).then(function (r) {
      S.draft.clear(pid);
      done(r.submission);
    }).catch(function (e) {
      btn.disabled = false; btn.textContent = 'Send bidrag';
      if (e && e.errors) showErrors(e.errors, true);
      else $('js-errors').innerHTML = '<div class="crowd-summary-errors" role="alert"><strong>Bidraget blev ikke sendt.</strong> ' + esc((e && e.message) || 'Ukendt fejl.') + '</div>';
    });
  }

  function done(sub) {
    var local = S.mode() === 'local';
    $('js-main').innerHTML = '<div class="crowd-done" role="status"><h2 style="margin-top:0">Tak for dit bidrag</h2>' +
      '<p>Det er registreret som <strong style="font-family:monospace">' + esc(sub.id) + '</strong> og afventer redaktionens gennemgang. ' +
      'Redaktionen godkender, retter eller afviser hvert felt for sig — og kan bede dig uddybe. Du kan følge status under »Mine bidrag«.</p>' +
      (local ? '<p><strong>Husk:</strong> bidraget ligger kun i denne browser. <button type="button" class="crowd-btn crowd-btn--primary" id="js-dl">Hent bidragsfil</button> og send den til redaktionen.</p>' : '') +
      '<p><a class="crowd-btn" href="crowd.html#mine">Mine bidrag</a> <a class="crowd-btn crowd-btn--quiet" href="crowd.html">Tilbage til arbejdskøen</a></p></div>';
    var dl = $('js-dl');
    if (dl) dl.addEventListener('click', function () {
      U.download('bidrag-' + sub.id + '.json', JSON.stringify(S.exportMine(), null, 2));
    });
    window.scrollTo(0, 0);
  }

  document.addEventListener('input', function (ev) { if (ev.target.closest && ev.target.closest('#js-form')) onInput(ev); });
  document.addEventListener('change', function (ev) { if (ev.target.closest && ev.target.closest('#js-form')) onInput(ev); });
  document.addEventListener('click', function (ev) {
    var t = ev.target;
    if (t.id === 'js-send') send();
    else if (t.id === 'js-add-src') {
      state.sources.push(newSource()); $('sec-srcs').innerHTML = sourcesSection(); refreshFieldSources(); scheduleSave();
    } else if (t.getAttribute && t.getAttribute('data-remove-src') !== null) {
      var i = parseInt(t.getAttribute('data-remove-src'), 10);
      state.sources.splice(i, 1);
      Object.keys(state.fields).forEach(function (k) {   // keep field → source links pointing at the right cards
        state.fields[k].sources = (state.fields[k].sources || []).filter(function (x) { return x !== i; })
          .map(function (x) { return x > i ? x - 1 : x; });
      });
      $('sec-srcs').innerHTML = sourcesSection(); refreshFieldSources(); scheduleSave();
    } else if (t.id === 'js-discard') {
      S.draft.clear(pid); state = blank(); renderAll();
    }
  });
  document.addEventListener('submit', function (ev) { ev.preventDefault(); });

  /* ── boot ─────────────────────────────────────────────────────────────── */
  function fromSubmission(sub) {
    var s = blank();
    s.ident = { status: sub.identification.status, summary: sub.identification.summary || '', same_as: sub.identification.same_as || '' };
    s.overall = sub.overall_confidence || '';
    s.sources = sub.sources.map(function (x) {
      var o = { type: x.type, citation: x.citation, url: x.url || '', locator: x.locator || '', accessed: x.accessed || '', result: x.result, note: x.note || '' };
      if (x.attachment) o.attachedFile = x.attachment.file;
      return o;
    });
    sub.fields.forEach(function (f) { s.fields[f.field] = { value: f.value, confidence: f.confidence, comment: f.comment || '', sources: f.sources.slice() }; });
    s.comment = sub.comment || '';
    s.consent = false;     // consent is given anew for each version
    return s;
  }

  S.init().then(function () {
    if (editId) {
      return S.mine().then(function (r) {
        var sub = (r.submissions || []).filter(function (x) { return x.id === editId; })[0];
        if (sub) state = fromSubmission(sub);
      });
    }
    var d = S.draft.get(pid);
    if (d && d.sources && d.fields) { state = d; state._restored = d._saved; state.consent = false; }
  }).then(function () {
    var openFilled = fieldOrder.some(function (k) { return state.fields[k] && state.fields[k].value; });
    void openFilled;
    renderAll();
    renderSide();
  });
})();
