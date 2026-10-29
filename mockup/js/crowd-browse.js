/* crowd-browse.js — crowd.html: the work queue.
 *
 * Browse and group the persons whose printed register entry is too thin to
 * identify them, by missing information, documentation level, presumed
 * country / locality, and year of mention. Uses the site's own FacetEngine
 * (js/facet-engine.js) over CROWD_QUEUE (scripts/build_mockup/
 * build_crowd_queue.py); nothing is copied from the diary pages — every
 * mention is a link into them.
 */
(function () {
  'use strict';

  var U = window.CrowdUI, T = U.T, S = window.CrowdStore, esc = U.esc;
  var PAGE = 30;

  var Q = window.CROWD_QUEUE || [];
  var APPROVED = window.CROWD_APPROVED || {};
  var STATS = window.CROWD_STATS || {};
  var el = function (id) { return document.getElementById(id); };

  if (!Q.length) {
    el('js-results').innerHTML = '<p class="crowd-empty">Arbejdskøen er ikke bygget endnu. Kør ' +
      '<code>python scripts/build_all.py --only 4g</code> (se docs/crowdsourcing.md).</p>';
    el('js-count').textContent = '0';
    return;
  }

  /* ── items ────────────────────────────────────────────────────────────── */
  var strip = function (s) { return String(s || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase(); };
  var ALL = Q.map(function (r) {
    return {
      r: r, id: r.id,
      hay: strip([r.l, r.ds, r.c, r.lc].join(' ')),   // the search box also finds a place or country
      decades: (r.ys || []).map(function (y) { return String(Math.floor(y / 10) * 10); })
        .filter(function (d, i, a) { return a.indexOf(d) === i; }),
      state: APPROVED[r.id] ? 'approved' : 'open'
    };
  });

  var letter = null, query = '', sortMode = 'name', shown = 0, facets = null, current = [];

  /* ── rendering ────────────────────────────────────────────────────────── */
  function mentionLinks(r) {
    var name = U.surnameOf(r.l);
    var first = r.m.slice(0, 3).map(function (m) {
      var when = m[2] ? ' · ' + U.fmtDate(m[2]) : '';
      return '<a href="' + esc(U.diaryHref(m[0], m[1], name)) + '">' + esc(U.pageLabel(m[0])) + esc(when) + '</a>';
    }).join('<br>');
    var more = r.n > 3 ? '<br><span class="crowd-dim">+ ' + (r.n - 3) + ' flere</span>' : '';
    return first + more;
  }

  function basisTag(key) {
    var b = U.find(T.bases, key);
    return b && b.key ? ' <span class="crowd-basis" title="' + esc(b.da) + '">' + esc(b.da) + '</span>' : '';
  }
  function placeText(r) {
    var out = [];
    if (r.c) out.push(esc(r.c) + basisTag(r.cb));
    if (r.lc && r.lc !== r.c) out.push(esc(r.lc) + (r.lb !== r.cb || !r.c ? basisTag(r.lb) : ''));
    return out.length ? out.join('<br>') : '<span class="crowd-dim">ukendt</span>';
  }

  function card(it) {
    var r = it.r;
    var state = it.state === 'approved' ? '<span class="crowd-status crowd-status--approved">Har godkendte bidrag</span>'
      : it.state === 'pending' ? '<span class="crowd-status crowd-status--submitted">Bidrag afventer redaktionen</span>' : '';
    var years = r.ys && r.ys.length ? (r.ys[0] === r.ys[r.ys.length - 1] ? r.ys[0] : r.ys[0] + '–' + r.ys[r.ys.length - 1]) : '';
    return '<article class="crowd-card">' +
      '<header class="crowd-card__head">' +
        '<h3 class="crowd-card__name"><a href="crowd-contribute.html?reg=' + esc(r.id) + '">' + esc(r.l) + '</a></h3>' +
        '<span class="crowd-id">' + esc(r.id) + '</span>' +
      '</header>' +
      '<p class="crowd-card__desc">' + (r.ds ? esc(r.ds) : '<span class="crowd-dim">Ingen beskrivelse i registret</span>') + '</p>' +
      '<div class="crowd-card__tags">' + U.levelBadge(r.lv) +
        (r.fl ? '<span class="crowd-badge crowd-badge--fleeting" title="Højst ' + T.fleetingMax + ' omtaler og højst ét anker i registret">Flygtig omtale</span>' : '') +
        state + '</div>' +
      '<div class="crowd-card__gaps" aria-label="Manglende oplysninger">' + U.gapChips(r.g.filter(function (g) { return g !== 'identity'; }), 5) + '</div>' +
      '<dl class="crowd-card__meta">' +
        '<div><dt>Formodet sted</dt><dd>' + placeText(r) + '</dd></div>' +
        '<div><dt>Omtalt</dt><dd>' + r.n + (r.n === 1 ? ' gang' : ' gange') + (years ? ' · ' + esc(years) : '') + '</dd></div>' +
        '<div class="crowd-card__mentions"><dt>I dagbogen</dt><dd>' + mentionLinks(r) + '</dd></div>' +
      '</dl>' +
      '<footer class="crowd-card__foot">' +
        '<a class="crowd-btn crowd-btn--primary" href="crowd-contribute.html?reg=' + esc(r.id) + '">Bidrag</a>' +
        '<a class="crowd-link" href="persons.html?reg=' + esc(r.id) + '">Personside</a>' +
      '</footer></article>';
  }

  function sorted(list) {
    var by = {
      name: function (a, b) { return U.collator.compare(a.r.l, b.r.l); },
      gaps: function (a, b) { return b.r.g.length - a.r.g.length || U.collator.compare(a.r.l, b.r.l); },
      first: function (a, b) { return (a.r.y0 || 9999) - (b.r.y0 || 9999) || U.collator.compare(a.r.l, b.r.l); },
      few: function (a, b) { return a.r.n - b.r.n || b.r.g.length - a.r.g.length || U.collator.compare(a.r.l, b.r.l); }
    };
    return list.slice().sort(by[sortMode] || by.name);
  }

  function renderMore(reset) {
    var box = el('js-results');
    if (reset) { box.innerHTML = ''; shown = 0; }
    var next = current.slice(shown, shown + PAGE);
    box.insertAdjacentHTML('beforeend', next.map(card).join(''));
    shown += next.length;
    el('js-more').hidden = shown >= current.length;
    if (!current.length) {
      box.innerHTML = '<p class="crowd-empty">Ingen personer matcher filtrene. <button type="button" class="crowd-link" id="js-reset-all">Nulstil filtre</button></p>';
    }
  }

  function onChange(filtered) {
    current = sorted(filtered);
    el('js-count').textContent = current.length.toLocaleString('da-DK');
    renderMore(true);
  }

  /* ── facets ───────────────────────────────────────────────────────────── */
  function makeFacets(personStatus) {
    ALL.forEach(function (it) {
      var ps = personStatus && personStatus[it.id];
      if (it.state === 'open' && ps && ps.pending) it.state = 'pending';
      if (ps && ps.approved) it.state = 'approved';
    });
    var levelOrder = T.levels.map(function (l) { return l.key; });
    facets = FacetEngine.create({
      panel: document.querySelector('.facet-panel'),
      items: ALL,
      accessors: {
        gap: function (it) { return it.r.g; },
        level: function (it) { return it.r.lv; },
        mentions: function (it) { return it.r.nb; },
        fleeting: function (it) { return it.r.fl ? 'ja' : null; },
        country: function (it) { return it.r.c; },
        locality: function (it) { return it.r.lc; },
        basis: function (it) { return it.r.cb; },
        years: function (it) { return it.r.ys; },
        decade: function (it) { return it.decades; },
        state: function (it) { return it.state; }
      },
      labels: {
        gap: function (k) { return U.label(T.gaps, k); },
        level: function (k) { return U.label(T.levels, k); },
        mentions: function (k) { return U.label(T.mentionBuckets, k); },
        fleeting: function () { return 'Højst ' + T.fleetingMax + ' omtaler og næsten uden oplysninger'; },
        basis: function (k) { return U.label(T.bases, k); },
        decade: function (k) { return k + '’erne'; },
        state: function (k) { return { open: 'Åben — ingen bidrag endnu', pending: 'Bidrag afventer redaktionen', approved: 'Har godkendte bidrag' }[k] || k; }
      },
      sortKeys: { country: function (k) { return k; }, locality: function (k) { return k; } },
      fixedOrder: {
        gap: T.gaps.map(function (g) { return g.key; }),
        level: levelOrder,
        mentions: T.mentionBuckets.map(function (b) { return b.key; }),
        basis: T.bases.map(function (b) { return b.key; }),
        decade: ['1820', '1830', '1840', '1850', '1860', '1870'],
        state: ['open', 'pending', 'approved']
      },
      onReset: function () { query = ''; el('js-q').value = ''; },
      onChange: onChange
    });

    // Preset filters from the URL (?gap=given_names&country=Italien …).
    var params = new URLSearchParams(location.search);
    ['gap', 'level', 'mentions', 'country', 'locality', 'basis', 'decade', 'state'].forEach(function (f) {
      var raw = params.get(f);
      if (!raw) return;
      raw.split(',').forEach(function (v) {
        var box = document.querySelector('.facet-panel input[data-facet="' + f + '"][data-match="' + CSS.escape(v.trim()) + '"]');
        if (box) box.checked = true;
      });
    });
    if (params.get('q')) { query = strip(params.get('q')); el('js-q').value = params.get('q'); applyPrefilter(); }
    facets.apply();
  }

  function applyPrefilter() {
    facets.setPrefilter(query ? function (it) { return it.hay.indexOf(query) >= 0; } : null);
  }

  /* ── "Dit bidrag" + mine ──────────────────────────────────────────────── */
  var NEXT_HINT = [
    ['first_accepted', 'Dit første godkendte bidrag giver mærket »Første godkendte bidrag«.'],
    ['five_sourced', 'Fem godkendte bidrag, hver med en stærk kilde, giver mærket »Fem godkendte med kilder«.']
  ];

  function renderMe(stats) {
    var me = stats && stats.me;
    var approvedPersons = {};
    Object.keys(APPROVED).forEach(function (id) { approvedPersons[id] = true; });
    Object.keys((stats && stats.personStatus) || {}).forEach(function (id) {
      if (stats.personStatus[id].approved) approvedPersons[id] = true;
    });
    var done = ALL.filter(function (it) { return approvedPersons[it.id]; }).length;
    var pct = Math.round(100 * done / ALL.length);
    var html = U.authBox(S) + '<h2 class="crowd-me__title">Fremdrift</h2>' +
      '<p class="crowd-me__progress"><strong>' + done.toLocaleString('da-DK') + '</strong> af ' + ALL.length.toLocaleString('da-DK') +
      ' poster i køen har fået godkendte bidrag.</p>' +
      '<div class="crowd-bar" role="img" aria-label="' + pct + ' procent"><span style="width:' + Math.max(pct, done ? 1 : 0) + '%"></span></div>';
    if (me && me.submitted) {
      html += '<p class="crowd-me__mine"><strong>Dine bidrag:</strong> ' + me.submitted + ' indsendt · ' + me.pending + ' afventer · ' +
        me.approved_submissions + ' godkendt (' + me.accepted_fields + ' felter, ' + me.persons + ' personer)</p>';
      if (me.badges && me.badges.length) html += '<p class="crowd-me__badges">' + U.badgesHtml(me.badges) + '</p>';
      else {
        var hint = NEXT_HINT.filter(function (h) { return !me.badges || me.badges.indexOf(h[0]) < 0; })[0];
        if (hint) html += '<p class="crowd-dim">' + esc(hint[1]) + '</p>';
      }
    } else {
      html += '<p class="crowd-dim">Du har ikke bidraget endnu. Vælg en person i listen og tryk »Bidrag«.</p>';
    }
    var areas = String(S.profile().expertise || '').split(/[,;]/).map(function (a) { return a.trim(); }).filter(Boolean);
    if (areas.length) {
      html += '<p class="crowd-me__areas"><span class="crowd-dim">Dine kendskabsområder:</span> ' + areas.map(function (a) {
        return '<button type="button" class="crowd-award" data-area="' + esc(a) + '">' + esc(a) + '</button>';
      }).join('') + '</p>';
    }
    html += '<p class="crowd-dim crowd-me__principle">Mærker gives for godkendte, kildebelagte bidrag — også for dokumenterede negative fund — ikke for hastighed eller antal.</p>';
    html += '<p><button type="button" class="crowd-btn" id="js-show-mine">Mine bidrag</button></p>';
    if (stats && stats.contributors && stats.contributors.length) {
      html += '<details class="crowd-contribs"><summary>Bidragydere med godkendte bidrag (' + stats.contributors.length + ')</summary><ul>' +
        stats.contributors.map(function (c) {
          return '<li>' + esc(c.name) + (c.affiliation ? ' <span class="crowd-dim">(' + esc(c.affiliation) + ')</span>' : '') +
            ' — ' + c.persons + (c.persons === 1 ? ' person' : ' personer') + '</li>';
        }).join('') + '</ul><p class="crowd-dim">Alfabetisk; ingen rangliste.</p></details>';
    }
    el('js-me').innerHTML = html;
  }

  function renderMine(open) {
    var sec = el('js-mine-section');
    sec.hidden = !open;
    if (!open) return;
    S.mine().then(function (r) {
      var subs = (r.submissions || []).slice().sort(function (a, b) { return a.created < b.created ? 1 : -1; });
      var html = '';
      if (S.mode() === 'local') {
        html += '<p class="crowd-note crowd-note--inline">Bidragene ligger kun i denne browser. ' +
          '<button type="button" class="crowd-btn" id="js-export-mine">Hent mine bidrag som fil</button> ' +
          'og send filen til redaktionen — eller åbn <a href="crowd-review.html">redaktionssiden</a> i samme browser for at prøve gennemgangen selv.</p>';
      }
      if (!subs.length) html += '<p class="crowd-dim">Ingen bidrag endnu.</p>';
      html += subs.map(function (s) {
        var rev = s.review;
        var fb = '';
        if (rev && (rev.note || Object.keys(rev.fields || {}).length)) {
          var dec = Object.keys(rev.fields || {}).map(function (i) {
            var d = rev.fields[i], f = s.fields[i] || {};
            return '<li>' + esc(U.label(T.fields.map(function (x) { return { key: x.key, da: x.da }; }), f.field)) + ': ' +
              (d.decision === 'reject' ? 'afvist' : d.decision === 'accept_edited' ? 'godkendt med rettelse (»' + esc(d.final_value) + '«)' : 'godkendt') +
              (d.note ? ' — ' + esc(d.note) : '') + '</li>';
          }).join('');
          fb = '<div class="crowd-feedback"><strong>Fra redaktionen' + (rev.reviewer ? ' (' + esc(rev.reviewer) + ')' : '') + ':</strong> ' +
            esc(rev.note || '') + (dec ? '<ul>' + dec + '</ul>' : '') + '</div>';
        }
        var open = s.status === 'submitted' || s.status === 'needs_changes';
        return '<div class="crowd-sub" data-sid="' + esc(s.id) + '">' +
          '<div class="crowd-sub__head"><a href="crowd-contribute.html?reg=' + esc(s.person_id) + '"><strong>' + esc(s.person_label || s.person_id) + '</strong></a> ' +
          '<span class="crowd-id">' + esc(s.person_id) + '</span> ' + U.statusPill(s.status) + '</div>' +
          '<div class="crowd-dim">' + esc(s.id) + ' · ' + esc(U.fmtStamp(s.created)) + ' · ' + s.fields.length + ' felter · ' + s.sources.length + ' kilder' +
          (s.revision > 1 ? ' · version ' + s.revision : '') + '</div>' + fb +
          (open ? '<div class="crowd-sub__actions"><a class="crowd-btn" href="crowd-contribute.html?reg=' + esc(s.person_id) + '&amp;edit=' + esc(s.id) + '">Ret og send igen</a> ' +
            '<button type="button" class="crowd-btn crowd-btn--quiet" data-withdraw="' + esc(s.id) + '">Træk tilbage</button></div>' : '') +
          '</div>';
      }).join('');
      el('js-mine').innerHTML = html;
    });
  }

  /* ── boot ─────────────────────────────────────────────────────────────── */
  function renderCategories() {
    var html = '<h3>Dokumentationsniveau</h3><p>Hvor mange af tre ankre registret selv giver: et fuldt <em>fornavn</em>, et <em>årstal</em> (fødsel eller død) og en <em>beskrivelse</em> på mindst to ord.</p><dl>' +
      T.levels.map(function (l) { return '<dt>' + esc(l.da) + '</dt><dd>' + l.anchors + ' af 3 ankre' + (l.anchors === 3 ? ' — står ikke i køen, med mindre registret selv er i tvivl' : '') + '</dd>'; }).join('') +
      '</dl><h3>Flygtig omtale</h3><p>Navnet står på højst ' + T.fleetingMax + ' dagbogssider og har højst ét anker. Det er de sværeste — og for forskningen de mest værdifulde — tilfælde.</p>' +
      '<h3>Manglende oplysninger</h3><dl>' + T.gaps.map(function (g) {
        return '<dt>' + esc(g.da) + '</dt><dd>' + esc(g.fields.map(function (f) { return U.label(T.fields, f); }).join(', ')) + '</dd>';
      }).join('') + '</dl>' +
      '<h3>Formodet land og lokalitet</h3><p>Hentes i denne rækkefølge: <em>nationalitet</em> i registrets beskrivelse, et <em>sted nævnt i beskrivelsen</em>, og til sidst <em>et sted på samme dagbogsside</em>. Det er en pejling, ikke en oplysning — filteret »Grundlag« viser, hvad den bygger på.</p>' +
      '<p class="crowd-dim">Se docs/crowdsourcing.md for de præcise regler.</p>';
    el('js-categories-body').innerHTML = html;
  }

  function boot(stats) {
    el('js-mode-note').innerHTML = U.modeNote(S.mode());
    el('js-hero-meta').innerHTML = '<span>' + (STATS.queued || ALL.length).toLocaleString('da-DK') + ' personer i køen</span>' +
      '<span>' + (STATS.fleeting || 0).toLocaleString('da-DK') + ' flygtige omtaler</span>' +
      '<span>' + (STATS.persons || 0).toLocaleString('da-DK') + ' enkeltpersoner i registret</span>';
    renderCategories();
    renderMe(stats);
    makeFacets(stats && stats.personStatus);
    renderMine(location.hash === '#mine');
  }

  // Events (delegated — no inline handlers, see docs/security.md)
  document.addEventListener('click', function (ev) {
    var t = ev.target;
    if (t.id === 'js-more') renderMore(false);
    else if (t.id === 'js-reset-all' && facets) { facets.reset(true); query = ''; el('js-q').value = ''; facets.setPrefilter(null, true); facets.apply(); }
    else if (t.getAttribute && t.getAttribute('data-area') && facets) {
      el('js-q').value = t.getAttribute('data-area'); query = strip(t.getAttribute('data-area')); applyPrefilter();
      el('js-results').scrollIntoView({ behavior: 'smooth', block: 'start' });
    } else if (t.id === 'js-show-mine') { renderMine(true); el('js-mine-section').scrollIntoView({ behavior: 'smooth', block: 'start' }); }
    else if (t.id === 'js-export-mine') {
      U.download('mine-bidrag-' + new Date().toISOString().slice(0, 10) + '.json', JSON.stringify(S.exportMine(), null, 2));
    } else if (t.getAttribute && t.getAttribute('data-withdraw')) {
      if (!window.confirm('Trække bidraget tilbage? Redaktionen vil ikke længere se det.')) return;
      S.withdraw(t.getAttribute('data-withdraw')).then(function () { renderMine(true); })
        .catch(function (e) { window.alert((e && e.message) || 'Kunne ikke trække bidraget tilbage.'); });
    }
  });
  el('js-sort').addEventListener('change', function (ev) { sortMode = ev.target.value; if (facets) facets.apply(); });
  var qTimer = null;
  el('js-q').addEventListener('input', function (ev) {
    clearTimeout(qTimer);
    qTimer = setTimeout(function () { query = strip(ev.target.value.trim()); applyPrefilter(); }, 150);
  });

  S.init().then(function () { return S.stats().catch(function () { return null; }); }).then(boot);
})();
