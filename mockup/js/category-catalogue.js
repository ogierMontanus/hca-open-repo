/* category-catalogue.js — appends a complete, browsable work catalogue to a
 * works-category landing page (billedkunst.html / teater-musik.html /
 * bibliotek.html), below its hand-curated showcase.
 *
 * The page selects its slice by setting two globals before loading this file:
 *   window.CATEGORY_WING   — 'billedkunst.html' | 'teater-musik.html' | 'bibliotek.html'
 *   window.CATEGORY_LABEL  — human label for the result count ('Billedkunst', …)
 *
 * It expects these containers somewhere on the page:
 *   #js-cat-alpha-bar  — alphabet bar (chips generated here)
 *   #js-cat-results    — list container
 *   #js-cat-more       — "Vis flere" button
 *   #js-cat-count      — result-count element
 *
 * Data comes from WORKS_EXTRA (data/works-extra.js). If that global is absent
 * (fresh clone, no build) the script is a no-op and the showcase stands alone.
 */
(function () {
  'use strict';
  // Mount the cart badge before the early-return guards below — it should
  // reflect the cart even on a page whose own catalogue can't render, since
  // the cart may already hold items added from a different page.
  if (typeof Cart !== 'undefined') Cart.mountBadge(document.getElementById('js-cart-badge'));

  var grid = document.getElementById('js-cat-results');
  var wing = window.CATEGORY_WING;
  if (!grid || !wing || typeof WORKS_EXTRA === 'undefined') return;

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c];
    });
  }

  // First letter of the title, skipping leading punctuation/quotes/asterisks
  // common in the register ("*»Bring Hilsen …" → B). "Aa" folds to Å.
  // Diacritics fold so accented forms file under the right bucket instead
  // of falling into "#":
  //   ä→æ, ö→ø, ü→y (Danish convention; ü is articulated as y in Danish)
  //   ß→s; generic accents (é, à, ñ, ç, î …) collapse to their base letter
  //   via NFD strip of combining marks. æ/ø/å have no decomposition and
  //   pass through.
  function initialOf(label) {
    var s = (label || '')
      .replace(/ä/g, 'æ').replace(/Ä/g, 'Æ')
      .replace(/ö/g, 'ø').replace(/Ö/g, 'Ø')
      .replace(/ü/g, 'y').replace(/Ü/g, 'Y')
      .replace(/ß/g, 's');
    // Keep Latin-1 accented letters (À–ÿ) in the keep-set so the
    // punctuation strip doesn't also eat a leading accented char like
    // "*»École" → that would lose the É before the NFD fold below.
    s = s.replace(/^[^0-9A-Za-zÆØÅæøåÀ-ÿ]+/, '').trim();
    if (!s) return '#';
    if (/^aa/i.test(s)) return 'Å';
    var c = s.charAt(0).toUpperCase();
    if (/[A-ZÆØÅ]/.test(c)) return c;
    // Generic accents fall through to NFD strip: é→E, ç→C, ñ→N, î→I, …
    // Å/å are handled above — they NFD-decompose to A/a + combining ring.
    if (c.normalize) {
      var folded = c.normalize('NFD').replace(/[\u0300-\u036f]/g, '');
      if (/[A-Z]/.test(folded.charAt(0))) return folded.charAt(0);
    }
    return '#';
  }

  var ALL = Object.keys(WORKS_EXTRA).reduce(function (acc, rid) {
    var w = WORKS_EXTRA[rid];
    if (w.wing !== wing) return acc;
    acc.push({
      rid: rid, title: w.title || rid,
      meta: [w.author, w.h3, w.year].filter(Boolean).join(' · '),
      refs: w.refs || 0, init: initialOf(w.title),
      h2: w.h2 || '', h3: w.h3 || '', author: w.author || '',
      place: w.place || ''
    });
    return acc;
  }, []);

  // Faceted filtering — read state from the sibling .facet-panel on every
  // render. Each H2/H3/author/rid/place checkbox carries the matching
  // data-* attribute naming the exact WORKS_EXTRA value it filters on.
  // Within a .facet-group the predicates combine with OR; across groups
  // with AND; an empty group (no boxes ticked) imposes no constraint.
  var FACET_SEL =
    'input[type=checkbox][data-h2], input[type=checkbox][data-h3], ' +
    'input[type=checkbox][data-author], input[type=checkbox][data-rid], ' +
    'input[type=checkbox][data-place]';

  function predOf(b) {
    return {
      h2: b.getAttribute('data-h2') || null,
      h3: b.getAttribute('data-h3') || null,
      author: b.getAttribute('data-author') || null,
      rid: b.getAttribute('data-rid') || null,
      place: b.getAttribute('data-place') || null
    };
  }

  function matchesPred(w, p) {
    return (p.h2 == null || w.h2 === p.h2) &&
           (p.h3 == null || w.h3 === p.h3) &&
           (p.author == null || w.author === p.author) &&
           (p.rid == null || w.rid === p.rid) &&
           (p.place == null || w.place === p.place);
  }

  function readFacetGroups() {
    var groups = [];
    document.querySelectorAll('.facet-panel .facet-group').forEach(function (g) {
      var boxes = g.querySelectorAll(FACET_SEL);
      if (!boxes.length) return;
      var preds = [];
      for (var i = 0; i < boxes.length; i++) {
        if (boxes[i].checked) preds.push(predOf(boxes[i]));
      }
      if (preds.length) groups.push(preds);
    });
    return groups;
  }

  // Per-group active predicates indexed by group element — needed by
  // updateFacetAvailability() which counts under "all OTHER groups" for
  // each option (the standard adaptive-facet pattern).
  function readGroupsByEl() {
    var els = Array.prototype.slice.call(
      document.querySelectorAll('.facet-panel .facet-group'));
    return els.map(function (g) {
      var boxes = g.querySelectorAll(FACET_SEL);
      var preds = [];
      for (var i = 0; i < boxes.length; i++) {
        if (boxes[i].checked) preds.push(predOf(boxes[i]));
      }
      return { el: g, preds: preds };
    });
  }

  function passesFacets(w, groups) {
    for (var i = 0; i < groups.length; i++) {
      var preds = groups[i];
      var ok = false;
      for (var j = 0; j < preds.length; j++) {
        if (matchesPred(w, preds[j])) { ok = true; break; }
      }
      if (!ok) return false;
    }
    return true;
  }

  var collator = (typeof Intl !== 'undefined' && Intl.Collator)
    ? new Intl.Collator('da') : null;
  function byTitle(a, b) {
    return collator ? collator.compare(a.title, b.title)
                    : (a.title < b.title ? -1 : a.title > b.title ? 1 : 0);
  }
  function byRefs(a, b) { return b.refs - a.refs || byTitle(a, b); }

  var PAGE = 60;
  var letter = null;
  var shown = 0;
  var filtered = ALL.slice().sort(byRefs);
  var label = window.CATEGORY_LABEL || 'registret';
  var countEl = document.getElementById('js-cat-count');
  var moreBtn = document.getElementById('js-cat-more');

  // "Liste" (cards, paginated via Vis flere) vs "Tabel" (flat, sortable,
  // every filtered row at once) — same switcher pattern as cart.html's own
  // Liste/Tabel toggle. Shared localStorage key across all three wings
  // (billedkunst/teater-musik/bibliotek): they're separate page loads of
  // the same catalogue concept, so one Tabel preference should carry over
  // once the reader has actually chosen one.
  //
  // The *default* before any choice is saved differs by wing: Tabel for
  // bibliotek/teater-musik, but billedkunst keeps Liste — its cards are the
  // one place on the register where a reader browses by cover thumbnail
  // rather than by row, so collapsing straight to a flat table by default
  // would hide that. See docs/data-model/detail-page-redundancy.md's
  // "Gitter"-removal note for why every OTHER Liste/Grid toggle on the site
  // lost its Grid option in favor of Tabel — billedkunst.html was never one
  // of those (it had no Grid to begin with) and is deliberately exempted
  // from the Tabel-default sweep too.
  var layout = (function () {
    try {
      var saved = localStorage.getItem('works-layout');
      if (saved) return saved;
    } catch (e) { /* ignore */ }
    return wing === 'billedkunst.html' ? 'list' : 'table';
  })();
  var tableView = (typeof TableView !== 'undefined') ? TableView.create(grid, [
    { key: 'select', label: '', sortable: false,
      html: function (w) { return '<label class="result-card__select"><input type="checkbox" data-cart-type="work" data-cart-rid="' +
        esc(w.rid) + '" data-cart-label="' + esc(w.title) + '"></label>'; } },
    { key: 'rid', label: 'ID',
      html: function (w) { return '<a class="data-table__id-link" href="work.html?reg=' +
        esc(w.rid) + '">' + esc(w.rid) + '</a>'; } },
    { key: 'title', label: 'Titel', value: function (w) { return w.title; } },
    { key: 'author', label: 'Forfatter', value: function (w) { return w.author || ''; },
      sortValue: function (w) { return surnameKey(w.author || ''); } },
    { key: 'category', label: 'Kategori', value: function (w) { return w.h3 || w.h2 || ''; } },
    { key: 'place', label: 'Sted', value: function (w) { return w.place || ''; } },
    { key: 'refs', label: 'Refs.', numeric: true, value: function (w) { return w.refs; } }
  ], { initialSort: 'refs', initialDir: 'desc',
       afterRender: function (c) { if (typeof Cart !== 'undefined') Cart.syncCheckboxes(c); } }) : null;

  function card(w) {
    return '<div class="result-row">' +
      '<label class="result-card__select"><input type="checkbox" ' +
      'data-cart-type="work" data-cart-rid="' + esc(w.rid) + '" data-cart-label="' + esc(w.title) + '"></label>' +
      '<a href="work.html?reg=' + esc(w.rid) + '" class="result-card result-card--list" ' +
      'style="display:flex;align-items:baseline;gap:var(--sp4);padding:var(--sp4)">' +
      '<div style="min-width:90px;font-size:0.72rem;font-weight:600;color:var(--color-text-muted);font-family:monospace">' + esc(w.rid) + '</div>' +
      '<div style="flex:1"><div class="result-card__title" style="font-size:0.95rem">' + esc(w.title) + '</div>' +
      (w.meta ? '<div class="result-card__meta">' + esc(w.meta) + '</div>' : '') + '</div>' +
      '<div style="min-width:70px;text-align:right;font-size:0.78rem;color:var(--color-text-muted)">' + w.refs + ' refs.</div></a>' +
      '</div>';
  }

  function renderMore() {
    var next = filtered.slice(shown, shown + PAGE);
    grid.insertAdjacentHTML('beforeend', next.map(card).join(''));
    shown += next.length;
    moreBtn.style.display = shown < filtered.length ? '' : 'none';
    if (typeof Cart !== 'undefined') Cart.syncCheckboxes(grid);
  }

  // The "Vælg alle" checkbox means every currently FILTERED work, not just
  // the ones paginated onto the screen — same convention as persons.html /
  // places.html's cart wiring (see docs/data-model/cart-and-export.md).
  var selectAllCb = document.getElementById('js-cat-select-all');
  function updateSelectAll() {
    if (!selectAllCb || typeof Cart === 'undefined') return;
    if (!filtered.length) { selectAllCb.checked = false; selectAllCb.indeterminate = false; return; }
    var inCount = 0;
    for (var i = 0; i < filtered.length; i++) if (Cart.has('work', filtered[i].rid)) inCount++;
    selectAllCb.checked = inCount === filtered.length;
    selectAllCb.indeterminate = inCount > 0 && inCount < filtered.length;
  }
  if (selectAllCb) {
    selectAllCb.addEventListener('change', function () {
      if (selectAllCb.checked) {
        if (filtered.length > 100 &&
            !confirm('Tilføj alle ' + filtered.length.toLocaleString('da-DK') + ' værker til kurven?')) {
          selectAllCb.checked = false;
          return;
        }
        Cart.addMany(filtered.map(function (w) { return { type: 'work', rid: w.rid, label: w.title }; }));
      } else {
        Cart.removeMany(filtered.map(function (w) { return { type: 'work', rid: w.rid }; }));
      }
      Cart.syncCheckboxes(grid);
    });
  }
  if (typeof Cart !== 'undefined') { Cart.wireCheckboxes(); Cart.subscribe(updateSelectAll); }

  // Empty-state markup shown inside #js-cat-results when filtered.length === 0.
  // The "Nulstil filter" button delegates to the panel's own Nulstil control
  // so we don't duplicate reset logic. See clearBtn wiring below.
  function emptyStateHtml() {
    return '<div class="empty-state" style="padding:var(--sp7) var(--sp5);text-align:center;' +
      'background:var(--color-surface-2);border:1px dashed var(--color-border);border-radius:var(--radius)">' +
      '<div style="font-size:1.05rem;font-weight:500;margin-bottom:var(--sp3)">Ingen resultater matcher de valgte filtre.</div>' +
      '<div style="font-size:0.85rem;color:var(--color-text-muted);margin-bottom:var(--sp4)">' +
      'Prøv at fjerne et af filtrene — eller nulstil for at se hele ' + esc(label) + '-registret.</div>' +
      '<button type="button" class="chip" id="js-empty-reset" ' +
      'style="cursor:pointer;background:var(--color-accent);color:#fff;border-color:var(--color-accent);padding:6px 14px">' +
      'Nulstil alle filtre</button></div>';
  }

  // For each facet checkbox: count items that pass the letter filter AND all
  // OTHER groups' active preds AND this option's pred. Options with 0 reach
  // get disabled + dimmed; their .facet-item__count is also updated so the
  // sidebar mirrors the live state. Checked boxes are never disabled — they
  // are contributing to the current set and unticking them is the way out.
  function updateFacetAvailability() {
    var byEl = readGroupsByEl();
    byEl.forEach(function (entry, gi) {
      var otherGroups = [];
      for (var k = 0; k < byEl.length; k++) {
        if (k === gi || !byEl[k].preds.length) continue;
        otherGroups.push(byEl[k].preds);
      }
      var boxes = entry.el.querySelectorAll(FACET_SEL);
      boxes.forEach(function (b) {
        var optPred = predOf(b);
        var count = 0;
        for (var i = 0; i < ALL.length; i++) {
          var w = ALL[i];
          if (letter && w.init !== letter) continue;
          if (!passesFacets(w, otherGroups)) continue;
          if (!matchesPred(w, optPred)) continue;
          count++;
        }
        var item = b.closest ? b.closest('.facet-item') : null;
        var countEl2 = item ? item.querySelector('.facet-item__count') : null;
        if (countEl2) countEl2.textContent = count;
        var dim = count === 0 && !b.checked;
        b.disabled = dim;
        if (item) {
          item.style.opacity = dim ? '0.4' : '';
          item.style.cursor = dim ? 'not-allowed' : '';
          item.title = dim ? 'Ingen resultater under de øvrige filtre' : '';
        }
      });
    });
  }

  // Dim alphabet chips whose letter has 0 hits under the current facet
  // selection. The "Alle" chip (no data-letter) is left alone.
  function updateLetterAvailability() {
    if (!bar) return;
    var groups = readFacetGroups();
    var counts = {};
    for (var i = 0; i < ALL.length; i++) {
      var w = ALL[i];
      if (!passesFacets(w, groups)) continue;
      counts[w.init] = (counts[w.init] || 0) + 1;
    }
    bar.querySelectorAll('a.chip').forEach(function (chip) {
      var l = chip.getAttribute('data-letter');
      if (!l) return;
      var has = !!counts[l];
      chip.style.opacity = has ? '' : '0.35';
      chip.style.pointerEvents = has ? '' : 'none';
      chip.title = has ? '' : 'Ingen resultater under de valgte facetter';
    });
  }

  function apply() {
    var groups = readFacetGroups();
    filtered = ALL.filter(function (w) {
      if (letter && w.init !== letter) return false;
      return passesFacets(w, groups);
    });
    filtered.sort(letter ? byTitle : byRefs);
    var activeFacets = groups.reduce(function (n, g) { return n + g.length; }, 0);
    var anyActive = activeFacets > 0 || letter !== null;
    showcaseEls.forEach(function (el) { el.style.display = anyActive ? 'none' : ''; });
    if (countEl) {
      var note = '';
      if (letter) note += ' &nbsp;<span style="font-weight:400;font-size:0.8rem;color:var(--color-text-muted)">— bogstav ' + letter + '</span>';
      if (activeFacets) note += ' &nbsp;<span style="font-weight:400;font-size:0.8rem;color:var(--color-text-muted)">— ' + activeFacets + ' facet' + (activeFacets === 1 ? '' : 'ter') + '</span>';
      countEl.innerHTML = '<strong>' + filtered.length.toLocaleString('da-DK') + '</strong> poster i ' + esc(label) + note;
    }
    grid.innerHTML = '';
    shown = 0;
    if (filtered.length === 0) {
      grid.innerHTML = emptyStateHtml();
      moreBtn.style.display = 'none';
      var resetBtn = document.getElementById('js-empty-reset');
      if (resetBtn) {
        resetBtn.addEventListener('click', function () {
          var cb = document.querySelector('.facet-panel__clear');
          if (cb) cb.click();
        });
      }
    } else if (layout === 'table' && tableView) {
      moreBtn.style.display = 'none';
      tableView.render(filtered);
    } else {
      renderMore();
    }
    updateFacetAvailability();
    updateLetterAvailability();
    updateSelectAll();
  }

  var bar = document.getElementById('js-cat-alpha-bar');
  if (bar) {
    var present = {};
    ALL.forEach(function (w) { present[w.init] = true; });
    var order = 'ABCDEFGHIJKLMNOPQRSTUVWXYZÆØÅ#'.split('').filter(function (l) { return present[l]; });
    var chips = [{ l: null, t: 'Alle' }].concat(order.map(function (l) { return { l: l, t: l }; }));
    chips.forEach(function (ch) {
      var a = document.createElement('a');
      a.href = '#';
      a.className = 'chip';
      a.textContent = ch.t;
      if (ch.l) a.setAttribute('data-letter', ch.l);
      a.addEventListener('click', function (ev) {
        ev.preventDefault();
        letter = ch.l;
        bar.querySelectorAll('a.chip').forEach(function (x) { x.style.background = ''; x.style.color = ''; });
        a.style.background = 'var(--color-accent)';
        a.style.color = '#fff';
        apply();
      });
      if (ch.l === null) { a.style.background = 'var(--color-accent)'; a.style.color = '#fff'; }
      bar.appendChild(a);
    });
  }

  moreBtn.addEventListener('click', renderMore);

  var layoutSwitcher = document.getElementById('js-cat-layout-switcher');
  function syncLayoutButtons() {
    if (!layoutSwitcher) return;
    layoutSwitcher.querySelectorAll('[data-layout]').forEach(function (b) {
      b.classList.toggle('layout-switcher__btn--active', b.getAttribute('data-layout') === layout);
    });
  }
  syncLayoutButtons();
  if (layoutSwitcher) {
    layoutSwitcher.addEventListener('click', function (ev) {
      var btn = ev.target.closest('[data-layout]');
      if (!btn) return;
      layout = btn.getAttribute('data-layout');
      try { localStorage.setItem('works-layout', layout); } catch (e) {}
      syncLayoutButtons();
      apply();
    });
  }

  // Extract a person's surname for alphabetic sorting. The register's
  // person labels are already "Surname, Given names" (Collin, Edvard),
  // so the part before the first comma IS the surname. WORKS_EXTRA.author
  // is the looser "Given Surname" / "X. Surname" form (Lorenz Frølich,
  // V. Pedersen) — fall back to the last whitespace-separated token in
  // that case. Project preference: sort persons by surname wherever the
  // label format permits (see CLAUDE.md).
  function surnameKey(label) {
    var s = (label || '').trim();
    if (!s) return '';
    var c = s.indexOf(',');
    if (c >= 0) return s.slice(0, c).trim();
    var parts = s.split(/\s+/);
    return parts[parts.length - 1];
  }

  // Shared by the author/place blocks below: caps a sorted row list at
  // FACET_LIMIT and hands off to FacetOverlay (js/facet-overlay.js) for the
  // "Vis alle" -> full-viewport-overlay treatment once a wing has more
  // distinct values than that — bibliotek.html alone has 331 authors, all
  // shown unbounded before this, same problem places.html's Land facet had
  // with 79 countries. rows: [{value, label, count}], already sorted; a
  // value ticked while the overlay was open stays visible in the folded
  // list afterwards even below the cutoff, same guarantee facet-engine.js
  // makes.
  var FACET_LIMIT = 20;
  function buildCappedFacetHtml(host, dataAttr, rows, expanded) {
    var checkedVals = {};
    var existing = host.querySelectorAll('input[' + dataAttr + ']');
    for (var e = 0; e < existing.length; e++) {
      if (existing[e].checked) checkedVals[existing[e].getAttribute(dataAttr)] = true;
    }

    var total = rows.length;
    var visibleRows = rows;
    if (!expanded && total > FACET_LIMIT) {
      visibleRows = rows.slice(0, FACET_LIMIT);
      var shown = {};
      for (var r = 0; r < visibleRows.length; r++) shown[visibleRows[r].value] = true;
      for (var r2 = 0; r2 < rows.length; r2++) {
        if (checkedVals[rows[r2].value] && !shown[rows[r2].value]) visibleRows.push(rows[r2]);
      }
    }

    var html = visibleRows.map(function (row) {
      var v = esc(row.value);
      var checked = checkedVals[row.value] ? ' checked' : '';
      return '<label class="facet-item"><input type="checkbox" ' + dataAttr + '="' + v + '"' + checked + '>' +
        '<span class="facet-item__label">' + esc(row.label) +
        '</span><span class="facet-item__count">' + row.count + '</span></label>';
    }).join('');

    if (total > FACET_LIMIT) {
      var toggle = expanded
        ? '<button type="button" class="facet-more-toggle" data-facet-more>✕ Vis færre</button>'
        : '<button type="button" class="facet-more-toggle" data-facet-more>Vis alle (' + total + ') ▾</button>';
      html = expanded ? toggle + html : html + toggle;
    }
    return html;
  }

  var placeCollator = (typeof Intl !== 'undefined' && Intl.Collator)
    ? new Intl.Collator('da') : null;

  // Renders both dynamic facet lists from the current DOM checked state.
  // Called once at setup, and again by the Nulstil handler below *after* it
  // clears every checkbox — re-rendering is what actually drops a value
  // that was only shown past the top-20 cutoff because it was ticked (see
  // buildCappedFacetHtml); calling FacetOverlay.collapseAll() alone is not
  // enough, since that repaints from whatever is *still* checked at the
  // moment it runs.
  function renderFacetLists() {
    // Forfatter/Kunstner/Komponist — data-facet-source="author", one row
    // per distinct author in the wing (data-author=…), sorted by works
    // descending. Same pattern can later carry data-facet-source="h3" /
    // "rid" if a page wants every value enumerated automatically.
    document.querySelectorAll('.facet-panel [data-facet-source="author"]').forEach(function (host) {
      var counts = {};
      ALL.forEach(function (w) {
        if (!w.author) return;
        // Skip wing fallthroughs — the literal H2 strings the parser
        // leaves behind when no individual author can be extracted.
        if (w.author === w.h2) return;
        counts[w.author] = (counts[w.author] || 0) + 1;
      });
      var rows = Object.keys(counts)
        .map(function (a) { return { value: a, label: a, count: counts[a], sk: surnameKey(a) }; })
        .sort(function (a, b) {
          // Primary: works descending. Secondary: surname collation (da).
          return b.count - a.count || a.sk.localeCompare(b.sk, 'da');
        });
      FacetOverlay.attach(
        host,
        function (expanded) { return buildCappedFacetHtml(host, 'data-author', rows, expanded); },
        updateFacetAvailability
      );
    });

    // Sted — data-facet-source="place", populated from WORKS_EXTRA.place
    // (build_works_extra.py's place_from_billedkunst_title() /
    // place_from_teater_title() — "City" or "City — Venue"). Sorted purely
    // alphabetically (da collator) on the label itself, per CLAUDE.md-adjacent
    // convention set for this facet: because every value starts with its
    // city, a plain alphabetical sort already clusters every venue directly
    // under its city ("Firenze" next to "Firenze — Uffizi" next to
    // "Firenze — Pitti", then "München", …) with no separate city/venue sort
    // key needed — unlike Kunstner/Komponist above, this is NOT ranked by
    // count, so the top-20-before-"Vis alle" cutoff is the first 20
    // alphabetically rather than the 20 most-used places.
    document.querySelectorAll('.facet-panel [data-facet-source="place"]').forEach(function (host) {
      var counts = {};
      ALL.forEach(function (w) {
        if (!w.place) return;
        counts[w.place] = (counts[w.place] || 0) + 1;
      });
      var rows = Object.keys(counts)
        .map(function (p) { return { value: p, label: p, count: counts[p] }; })
        .sort(function (a, b) {
          return placeCollator ? placeCollator.compare(a.value, b.value)
                                : (a.value < b.value ? -1 : a.value > b.value ? 1 : 0);
        });
      FacetOverlay.attach(
        host,
        function (expanded) { return buildCappedFacetHtml(host, 'data-place', rows, expanded); },
        updateFacetAvailability
      );
    });
  }

  renderFacetLists();

  // Cross-page/URL-hash facet activation — e.g. billedkunst.html's own
  // subsection cards link to "#h3-skulptur", and a bare visit to that URL
  // should land with the Skulptur H3 facet already ticked, not just an
  // inert scroll target. window.CATEGORY_H3_SLUGS (declared per-page,
  // alongside CATEGORY_WING/CATEGORY_LABEL) maps each slug to the exact H3
  // facet value it should check — the slugs aren't a mechanical transform
  // of the H3 label (teater-musik.html's are hand-picked short names), so
  // this is a lookup table, not a slugify function.
  var h3Slugs = window.CATEGORY_H3_SLUGS;
  if (h3Slugs && location.hash) {
    var h3Label = h3Slugs[location.hash.replace(/^#/, '')];
    if (h3Label) {
      var h3Box = document.querySelector(
        '.facet-panel input[data-h3="' + h3Label.replace(/"/g, '') + '"]');
      if (h3Box) h3Box.checked = true;
    }
  }

  // The curated showcase sits directly inside the browse-layout main column,
  // above the catalogue block. When the reader narrows by H2/H3 or by letter,
  // the showcase becomes noise (it doesn't react to facets) and pushes the
  // filtered list below the fold. Hide the showcase header + grid (direct
  // children of the main column) whenever any filter is active; the
  // catalogue's own .cat-block wrapper stays visible alongside the sticky
  // facet-panel.
  var showcaseEls = document.querySelectorAll(
    '.browse-layout > div > .results-header, .browse-layout > div > .result-grid'
  );

  // Wire facet checkboxes for live filtering. Delegated on .facet-panel
  // (rather than bound once per checkbox) because the author/place bodies
  // below are re-rendered by FacetOverlay whenever their "Vis alle" toggle
  // fires — a one-time NodeList.forEach binding would only ever cover the
  // checkboxes that existed at page load, silently going dead on every row
  // FacetOverlay redraws afterwards.
  var facetPanel = document.querySelector('.facet-panel');
  if (facetPanel) {
    facetPanel.addEventListener('change', function (ev) {
      if (ev.target && ev.target.matches && ev.target.matches(FACET_SEL)) apply();
      var host = ev.target.closest ? ev.target.closest('[data-facet-source]') : null;
      if (host) FacetOverlay.collapseIfExpanded(host);
    });
  }

  // Wire the Nulstil button to clear all facet checkboxes + reset to "Alle".
  // Queried fresh (not the stale NodeList a one-time querySelectorAll would
  // give) for the same reason the change listener above is delegated.
  var clearBtn = document.querySelector('.facet-panel__clear');
  if (clearBtn) {
    clearBtn.addEventListener('click', function () {
      FacetOverlay.collapseAll();
      (facetPanel ? facetPanel.querySelectorAll(FACET_SEL) : []).forEach(function (cb) { cb.checked = false; });
      // Re-render the capped lists now that nothing is checked, so a value
      // only shown past the top-20 cutoff because it was ticked (see
      // buildCappedFacetHtml) actually drops out again — collapseAll()
      // above already repainted once, but from whatever was *still*
      // checked at that point, before this uncheck loop ran.
      renderFacetLists();
      letter = null;
      if (bar) {
        bar.querySelectorAll('a.chip').forEach(function (x, i) {
          x.style.background = i === 0 ? 'var(--color-accent)' : '';
          x.style.color = i === 0 ? '#fff' : '';
        });
      }
      apply();
    });
  }

  apply();
})();
