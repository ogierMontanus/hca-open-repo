/* crowd-review.js — crowd-review.html: the editor's side.
 *
 * Every field of a submission is decided on its own (approve / approve with
 * correction / reject), the sources are right next to the claim, and
 * conflicting claims from other contributors are shown before anything is
 * approved. Approving does not touch the register: it makes the submission
 * exportable (scripts/crowdsource/export_approved.py), and only that export
 * reaches data/curated/ — docs/crowdsourcing.md §6.
 */
(function () {
  'use strict';

  var U = window.CrowdUI, T = U.T, S = window.CrowdStore, esc = U.esc;
  var $ = function (id) { return document.getElementById(id); };
  var selected = null;

  function fieldDa(key) { return U.label(T.fields, key, key); }

  function registerSays(pid, key) {
    var P = (typeof PERSONS_EXTRA !== 'undefined' && PERSONS_EXTRA[pid]) || null;
    if (!P) return '';
    var nat = (typeof NATIONALITY_LABELS !== 'undefined' && NATIONALITY_LABELS) || {};
    return ({ surname: U.surnameOf(P.label), birth_date: P.born || '', death_date: P.died || '', description: P.description || '',
      nationality: (P.nationalities || []).map(function (k) { return nat[k] || k; }).join(', '),
      gender: P.gender || '', role_bucket: (P.roles || []).join('; ') })[key] || '';
  }

  /* ── gate ─────────────────────────────────────────────────────────────── */
  function showGate(msg) {
    $('js-gate').hidden = false; $('js-app').hidden = true;
    var err = $('js-gate-err'); err.hidden = !msg; err.textContent = msg || '';
  }

  function start() {
    $('js-mode-note').innerHTML = S.mode() === 'api'
      ? '<strong>Forbundet til redaktionens server.</strong> Alle indsendte bidrag fra alle bidragydere.'
      : '<strong>Lokal prøvetilstand.</strong> Du ser de bidrag, denne browser selv har oprettet, plus dem du importerer fra en bidragsfil. Afgørelserne gemmes i denne browser og kan hentes som fil til indlæsning (<code>export_approved.py --import-json</code>).';
    $('js-reviewer').value = (S.profile().reviewer || '');
    $('js-status').value = new URLSearchParams(location.search).get('status') === null ? 'submitted' : (new URLSearchParams(location.search).get('status') || '');
    S.admin.list({ status: $('js-status').value }).then(function () {
      $('js-gate').hidden = true; $('js-app').hidden = false;
      tools(); refreshList();
    }).catch(function (e) {
      if (e && e.status === 401) showGate(S.admin.token() ? 'Nøglen blev ikke godkendt.' : '');
      else showGate('Kunne ikke hente bidrag: ' + ((e && e.message) || 'ukendt fejl'));
    });
  }

  function tools() {
    var box = $('js-export-tools');
    if (S.mode() === 'api') {
      box.innerHTML = '<button type="button" class="crowd-btn" data-dl="tsv">Hent godkendte (TSV)</button> ' +
        '<button type="button" class="crowd-btn" data-dl="xlsx">Hent godkendte (Excel)</button> ' +
        '<span class="crowd-dim">Indlæsning i den autoritative data: <code>python scripts/crowdsource/export_approved.py --write</code></span>';
    } else {
      box.innerHTML = '<label class="crowd-btn" for="js-import">Importér bidragsfil</label><input type="file" id="js-import" accept="application/json,.json" class="sr-only"> ' +
        '<button type="button" class="crowd-btn" id="js-export-all">Hent alle afgørelser (JSON)</button> <span id="js-import-msg" class="crowd-dim"></span>';
    }
  }

  /* ── list ─────────────────────────────────────────────────────────────── */
  function refreshList() {
    S.admin.list({ status: $('js-status').value }).then(function (r) {
      var subs = r.submissions;
      $('js-list').innerHTML = subs.length ? subs.map(function (s) {
        return '<button type="button" class="crowd-qitem' + (s.id === selected ? ' crowd-qitem--on' : '') + '" data-open="' + esc(s.id) + '">' +
          '<div class="crowd-qitem__top"><strong>' + esc(s.person_label || s.person_id) + '</strong>' + U.statusPill(s.status) + '</div>' +
          '<div class="crowd-dim">' + esc(s.contributor.name) + ' · ' + esc(U.fmtDate((s.created || '').slice(0, 10))) + ' · ' + s.n_fields + ' felter' +
          (s.revision > 1 ? ' · v' + s.revision : '') + (s.incorporated ? ' · indlæst' : '') + '</div></button>';
      }).join('') : '<p class="crowd-dim">Ingen bidrag med denne status.</p>';
    });
    S.admin.contributors().then(function (r) {
      $('js-contribs').innerHTML = '<table class="crowd-table"><thead><tr><th>Navn</th><th>Indsendt</th><th>Godkendt</th><th>Felter</th><th>Mærker</th></tr></thead><tbody>' +
        r.contributors.map(function (c) {
          return '<tr><td>' + esc(c.name) + (c.public_credit ? '' : ' <span class="crowd-dim">(anonym)</span>') + '</td><td>' + c.submitted + '</td><td>' + c.approved_submissions + '</td><td>' + c.accepted_fields + '</td><td>' + U.badgesHtml(c.badges) + '</td></tr>';
        }).join('') + '</tbody></table>' + (r.contributors.length ? '' : '<p class="crowd-dim">Ingen endnu.</p>');
    }).catch(function () {});
  }

  /* ── detail ───────────────────────────────────────────────────────────── */
  function open(id) {
    selected = id;
    S.admin.get(id).then(function (r) { renderDetail(r); refreshList(); }).catch(function (e) {
      $('js-detail').innerHTML = '<div class="crowd-note crowd-note--danger">' + esc((e && e.message) || 'Kunne ikke åbne bidraget.') + '</div>';
    });
  }

  function decisionControls(i, f, prev) {
    var d = prev || {};
    var cur = d.decision || '';
    var conf = d.final_confidence || f.confidence;
    return '<div class="crowd-decision" data-dec="' + i + '">' +
      ['accept:Godkend', 'accept_edited:Godkend med rettelse', 'reject:Afvis'].map(function (o) {
        var p = o.split(':');
        return '<label><input type="radio" name="dec-' + i + '" value="' + p[0] + '"' + (cur === p[0] ? ' checked' : '') + '> ' + p[1] + '</label>';
      }).join('') +
      '<input type="text" data-final="' + i + '" placeholder="Rettet værdi" value="' + esc(d.final_value || '') + '"' + (cur === 'accept_edited' ? '' : ' hidden') + ' aria-label="Rettet værdi">' +
      '<select data-finalconf="' + i + '" aria-label="Sikkerhedsgrad efter gennemgang">' + T.confidence.map(function (c) {
        return '<option value="' + c.key + '"' + (c.key === conf ? ' selected' : '') + '>' + esc(c.da) + '</option>'; }).join('') + '</select>' +
      '<input type="text" data-note="' + i + '" placeholder="Note (valgfri)" value="' + esc(d.note || '') + '" aria-label="Note"></div>';
  }

  function renderDetail(r) {
    var s = r.submission, rev = s.review || {}, reg = r.register || {};
    var meta = (typeof DIARY_META !== 'undefined') ? DIARY_META : {};
    var locked = !!s.incorporated;
    var h = '<section class="crowd-sec"><h2>' + esc(s.person_label || s.person_id) + ' <span class="crowd-id">' + esc(s.person_id) + '</span> ' + U.statusPill(s.status) + '</h2>' +
      '<table class="info-table"><tr><td>Bidragyder</td><td>' + esc(s.contributor.name) + (r.contributor && r.contributor.affiliation ? ' (' + esc(r.contributor.affiliation) + ')' : '') +
      (r.contributor && r.contributor.contact ? ' · ' + esc(r.contributor.contact) : '') + (r.contributor && r.contributor.expertise ? '<br><span class="crowd-dim">Kendskab: ' + esc(r.contributor.expertise) + '</span>' : '') + '</td></tr>' +
      '<tr><td>Indsendt</td><td>' + esc(U.fmtStamp(s.created)) + (s.revision > 1 ? ' · version ' + s.revision : '') + '</td></tr>' +
      '<tr><td>Registret</td><td>' + esc(reg.description || (s.register_snapshot || {}).description || '—') + '</td></tr>' +
      (reg.label && (s.register_snapshot || {}).label && reg.label !== s.register_snapshot.label ?
        '<tr><td>Obs</td><td class="crowd-err">Registerets label er ændret siden bidraget: »' + esc(s.register_snapshot.label) + '« → »' + esc(reg.label) + '«. Vurdér på ny.</td></tr>' : '') +
      '<tr><td>Links</td><td><a href="persons.html?reg=' + esc(s.person_id) + '">Personsiden</a></td></tr></table>' +
      mentionList(s.person_id, meta) + '</section>';

    // identification
    var id = s.identification;
    var idLabel = U.label(T.identification, id.status);
    var needsDec = ['duplicate', 'not_individual', 'unidentifiable'].indexOf(id.status) >= 0;
    h += '<section class="crowd-sec"><h2>Identifikation</h2><p><strong>' + esc(idLabel) + '</strong>' +
      (id.same_as ? ' — <a href="persons.html?reg=' + esc(id.same_as) + '">' + esc(id.same_as) + '</a>' : '') +
      (s.overall_confidence ? ' ' + U.confPill(s.overall_confidence) : '') + '</p>' +
      (id.summary ? '<p style="white-space:pre-wrap">' + esc(id.summary) + '</p>' : '') +
      (needsDec ? '<div class="crowd-decision" data-idec><label><input type="radio" name="dec-id" value="accept"' + (rev.identification && rev.identification.decision === 'accept' ? ' checked' : '') + '> Godkend udsagnet</label>' +
        '<label><input type="radio" name="dec-id" value="reject"' + (rev.identification && rev.identification.decision === 'reject' ? ' checked' : '') + '> Afvis udsagnet</label>' +
        '<input type="text" data-idnote placeholder="Note (valgfri)" value="' + esc((rev.identification && rev.identification.note) || '') + '"></div>' : '') + '</section>';

    // conflicts
    if (r.conflicts && r.conflicts.length) {
      h += '<section class="crowd-sec"><h2>Modstridende bidrag til samme person</h2>' + r.conflicts.map(function (c) {
        return '<div class="crowd-conflict"><strong>' + esc(fieldDa(c.field)) + ':</strong> »' + esc(c.value) + '« ' + U.confPill(c.confidence) +
          ' — ' + esc(c.contributor) + ' · ' + esc(c.submission) + ' · ' + esc(U.label(T.statuses, c.status)) + '</div>';
      }).join('') + '</section>';
    }

    // fields
    if (s.fields.length) {
      h += '<section class="crowd-sec"><h2>Felter</h2><table class="crowd-table"><thead><tr><th>Felt</th><th>Forslag og begrundelse</th><th>Afgørelse</th></tr></thead><tbody>' +
        s.fields.map(function (f, i) {
          var says = registerSays(s.person_id, f.field);
          return '<tr><td><strong>' + esc(fieldDa(f.field)) + '</strong>' + (says ? '<br><span class="crowd-dim">Registret: ' + esc(says) + '</span>' : '') + '</td>' +
            '<td><div style="white-space:pre-wrap"><strong>' + esc(f.value) + '</strong></div>' + U.confPill(f.confidence) +
            (f.comment ? '<p style="margin:6px 0 0;white-space:pre-wrap">' + esc(f.comment) + '</p>' : '') +
            '<div class="crowd-dim" style="margin-top:6px">Kilder: ' + f.sources.map(function (n) { return 'K' + (n + 1); }).join(', ') + '</div></td>' +
            '<td>' + (locked ? '<span class="crowd-dim">Indlæst — låst</span>' : decisionControls(i, f, (rev.fields || {})[String(i)])) + '</td></tr>';
        }).join('') + '</tbody></table></section>';
    }

    // sources
    h += '<section class="crowd-sec"><h2>Kilder</h2>' + s.sources.map(function (x, i) {
      var st = U.find(T.sourceTypes, x.type);
      return '<div class="crowd-src-line"><strong>K' + (i + 1) + '</strong> · ' + esc(st ? st.da : x.type) + ' · <em>' + esc(U.label(T.sourceResults.map(function (q) { return q; }), x.result)) + '</em><br>' +
        esc(x.citation) + (x.locator ? ' <span class="crowd-dim">[' + esc(x.locator) + ']</span>' : '') +
        (U.safeUrl(x.url) ? '<br>' + U.externalLink(x.url, x.url) : '') +
        (x.accessed ? '<br><span class="crowd-dim">Opslået ' + esc(U.fmtDate(x.accessed)) + '</span>' : '') +
        (x.attachment ? '<br><button type="button" class="crowd-link" data-att="' + esc(x.attachment.file) + '" data-sid="' + esc(s.id) + '">Vis bilag (' + esc(x.attachment.file) + ')</button>' : '') +
        (x.note ? '<br><span style="white-space:pre-wrap">' + esc(x.note) + '</span>' : '') + '</div>';
    }).join('') + '</section>';

    if (s.comment) h += '<section class="crowd-sec"><h2>Bidragyderens kommentar</h2><p style="white-space:pre-wrap">' + esc(s.comment) + '</p></section>';

    // decision
    if (locked) {
      h += '<section class="crowd-sec"><div class="crowd-note">Indlæst i den autoritative data (' + esc(s.incorporated.batch) + ') og låst.</div></section>';
    } else if (['withdrawn'].indexOf(s.status) < 0) {
      h += '<section class="crowd-sec"><h2>Afgørelse</h2>' +
        (rev.reviewer ? '<p class="crowd-dim">Tidligere gennemgået af ' + esc(rev.reviewer) + ' ' + esc(U.fmtStamp(rev.decided)) + '.</p>' : '') +
        '<label class="crowd-lbl" for="js-rnote">Besked til bidragyderen (påkrævet ved »Bed om uddybning«)</label>' +
        '<textarea id="js-rnote" rows="3">' + esc(rev.note || '') + '</textarea>' +
        '<div class="crowd-actions" style="margin-top:var(--sp4)">' +
        (s.fields.length ? '<button type="button" class="crowd-btn" id="js-all-ok">Godkend alle felter</button>' : '') +
        '<button type="button" class="crowd-btn crowd-btn--primary" id="js-decide">Gem afgørelse</button>' +
        '<button type="button" class="crowd-btn crowd-btn--quiet" id="js-ask">Bed om uddybning</button></div><div id="js-rv-err"></div></section>';
    }
    $('js-detail').innerHTML = h;
    $('js-detail').setAttribute('data-sid', s.id);
    $('js-detail').__sub = s;
  }

  function mentionList(pid, meta) {
    var pages = (window.DiaryWire && DiaryWire.pagesFor(pid)) || [];
    var rec = U.queueRecord(pid), anchors = {}, kb = window.CROWD_KB_LINKS || {};
    if (rec) rec.m.forEach(function (m) { anchors[m[0]] = m[1]; });
    var name = U.surnameOf((rec && rec.l) || ((typeof PERSONS_EXTRA !== 'undefined' && PERSONS_EXTRA[pid]) || {}).label || '');
    if (!pages.length) return '';
    return '<details><summary>Omtaler i dagbøgerne (' + pages.length + ')</summary><ul style="margin:var(--sp2) 0 0;padding-left:var(--sp5);font-size:0.84rem">' +
      pages.slice(0, 25).map(function (p) {
        var m = meta[p] || {};
        return '<li><a href="' + esc(U.diaryHref(p, anchors[p] || '', name)) + '">' + esc(U.pageLabel(p)) + '</a>' + (m.y ? ' · ' + esc(m.y) : '') + (m.pl ? ' · ' + esc(m.pl) : '') +
          (kb[p] ? ' · ' + U.externalLink(kb[p], 'Det Kgl. Bibliotek') : '') + '</li>';
      }).join('') + '</ul></details>';
  }

  function collect(sub) {
    var fields = {}, missing = [];
    sub.fields.forEach(function (f, i) {
      var chosen = document.querySelector('input[name="dec-' + i + '"]:checked');
      if (!chosen) { missing.push(fieldDa(f.field)); return; }
      var d = { decision: chosen.value, note: (document.querySelector('[data-note="' + i + '"]') || {}).value || '' };
      d.final_confidence = (document.querySelector('[data-finalconf="' + i + '"]') || {}).value || f.confidence;
      if (chosen.value === 'accept_edited') d.final_value = (document.querySelector('[data-final="' + i + '"]') || {}).value || '';
      fields[String(i)] = d;
    });
    var out = { fields: fields };
    if (['duplicate', 'not_individual', 'unidentifiable'].indexOf(sub.identification.status) >= 0) {
      var c = document.querySelector('input[name="dec-id"]:checked');
      if (!c) missing.push('identifikationen');
      else out.identification = { decision: c.value, note: (document.querySelector('[data-idnote]') || {}).value || '' };
    }
    return { decisions: out, missing: missing };
  }

  function review(action) {
    var sub = $('js-detail').__sub, err = $('js-rv-err');
    var reviewer = $('js-reviewer').value.trim();
    var body = { reviewer: reviewer, action: action, note: $('js-rnote').value, decisions: {} };
    if (action === 'decide') {
      var c = collect(sub);
      if (c.missing.length) { err.innerHTML = '<p class="crowd-err">Mangler afgørelse for: ' + esc(c.missing.join(', ')) + '.</p>'; return; }
      body.decisions = c.decisions;
    }
    if (!reviewer) { err.innerHTML = '<p class="crowd-err">Skriv dit navn som redaktør øverst, så afgørelsen kan tilskrives dig.</p>'; return; }
    S.saveProfile({ reviewer: reviewer });
    S.admin.review(sub.id, body).then(function () { open(sub.id); }).catch(function (e) {
      err.innerHTML = '<p class="crowd-err">' + esc((e && e.message) || 'Afgørelsen kunne ikke gemmes.') + '</p>';
    });
  }

  /* ── events ───────────────────────────────────────────────────────────── */
  document.addEventListener('click', function (ev) {
    var t = ev.target;
    var openBtn = t.closest && t.closest('[data-open]');
    if (openBtn) return open(openBtn.getAttribute('data-open'));
    if (t.id === 'js-login') {
      S.admin.setToken($('js-token').value.trim()); start();
    } else if (t.id === 'js-all-ok') {
      var sub = $('js-detail').__sub;
      sub.fields.forEach(function (f, i) { var r = document.querySelector('input[name="dec-' + i + '"][value="accept"]'); if (r) r.checked = true; });
      var idr = document.querySelector('input[name="dec-id"][value="accept"]'); if (idr) idr.checked = true;
    } else if (t.id === 'js-decide') review('decide');
    else if (t.id === 'js-ask') review('request_changes');
    else if (t.getAttribute && t.getAttribute('data-att')) {
      S.admin.attachment(t.getAttribute('data-sid'), t.getAttribute('data-att')).then(function (url) { window.open(url, '_blank', 'noopener'); })
        .catch(function () { window.alert('Bilaget kunne ikke hentes.'); });
    } else if (t.getAttribute && t.getAttribute('data-dl')) {
      var fmt = t.getAttribute('data-dl');
      S.admin.download(fmt).then(function (blob) { U.download('person_crowd_approved.' + fmt, blob); })
        .catch(function (e) { window.alert('Eksport mislykkedes: ' + (e && e.message)); });
    } else if (t.id === 'js-export-all') {
      U.download('hca-crowd-afgoerelser-' + new Date().toISOString().slice(0, 10) + '.json', JSON.stringify(S.admin.exportJSON(false), null, 2));
    }
  });
  document.addEventListener('change', function (ev) {
    var t = ev.target;
    if (t.id === 'js-status') refreshList();
    else if (t.name && /^dec-\d+$/.test(t.name)) {
      var i = t.name.slice(4), fin = document.querySelector('[data-final="' + i + '"]');
      if (fin) fin.hidden = t.value !== 'accept_edited';
    } else if (t.id === 'js-import' && t.files && t.files[0]) {
      var fr = new FileReader();
      fr.onload = function () {
        S.admin.importFile(String(fr.result)).then(function (r) {
          $('js-import-msg').textContent = r.added + ' nye, ' + r.updated + ' opdaterede' + (r.skipped.length ? ', ' + r.skipped.length + ' sprunget over (ugyldige)' : '') + '.';
          refreshList();
        }).catch(function (e) { $('js-import-msg').textContent = (e && e.message) || 'Import mislykkedes.'; });
      };
      fr.readAsText(t.files[0]);
    }
  });

  S.init().then(function () {
    if (S.mode() === 'api' && !S.admin.token()) { $('js-mode-note').innerHTML = '<strong>Forbundet til redaktionens server.</strong>'; showGate(''); }
    else start();
  });
})();
