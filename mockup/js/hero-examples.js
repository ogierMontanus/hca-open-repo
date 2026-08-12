/* hero-examples.js — the illustrated example pane at the top of a wing page.
 *
 * Renders one card per work that HAS a curated hero image, newest-curated
 * first within each H3, with the highest-referenced work of each H3 marked as
 * the example. Driven entirely by WORKS_EXTRA, so the pane cannot drift out of
 * sync with the data the way the previous hand-written cards did.
 *
 * Two rules this enforces that the hand-written markup could not:
 *
 *   1. Only works with a hero image appear. A card with no picture was
 *      rendering as an empty grey box with the Reg-id in it — visually the
 *      loudest thing on the page while carrying the least. Images come from
 *      data/curated/works_wikidata.csv, which is hand-verified, so "has an
 *      image" also means "has a confirmed Wikidata identification".
 *   2. If a hero image fails to load (a Commons file renamed or deleted), the
 *      card removes itself rather than leaving a broken frame behind.
 *
 * Markup note: the card is a <div> with a stretched <a class="result-card__link">
 * behind it, not an <a> wrapping everything. An <a> may not contain another
 * <a> — the previous markup nested the Wikidata badge inside the card link,
 * and the HTML parser resolved that by closing the card early, which is what
 * tore the grid apart (image in one cell, title in the next). Chip links sit
 * above the stretched link via .result-card__chip-link. Same technique as
 * .landing-card__link on the front page.
 */
window.HeroExamples = (function () {
  'use strict';

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c];
    });
  }

  function card(w, featured) {
    var chips = '';
    if (w.wd) {
      chips += '<a href="https://www.wikidata.org/wiki/' + esc(w.wd) + '" ' +
        'class="chip result-card__chip-link" ' +
        'style="font-size:0.65rem;background:#edf4fb;border-color:#93bcd9;color:#2a5e8a" ' +
        'target="_blank" rel="noopener noreferrer">wd:' + esc(w.wd) + '</a>';
    }
    if (w.refs) {
      chips += '<span style="font-size:0.7rem;color:var(--color-text-muted)">' +
        w.refs + ' ref' + (w.refs === 1 ? '.' : 's.') + '</span>';
    }
    var meta = [w.author, w.h3].filter(Boolean).map(esc).join(' · ');
    return '<div class="result-card' + (featured ? ' result-card--featured' : '') + '"' +
      (featured ? ' id="h3-' + esc((w.h3 || '').toLowerCase().split(' ')[0]) + '"' : '') + '>' +
      '<a href="work.html?reg=' + esc(w.rid) + '" class="result-card__link" ' +
      'title="' + esc(w.title) + '"></a>' +
      '<div class="result-card__thumb" style="padding:0;overflow:hidden">' +
      '<img src="' + esc(w.image) + '" alt="' + esc(w.title) + '" loading="lazy"></div>' +
      '<div class="result-card__body">' +
      '<div class="result-card__title">' + esc(w.title) + '</div>' +
      '<div class="result-card__meta">' + meta + '</div>' +
      '<div class="result-card__chips">' + chips + '</div></div></div>';
  }

  function render(container, opts) {
    opts = opts || {};
    if (!container || typeof WORKS_EXTRA === 'undefined') return null;
    var wing = opts.wing;
    var limit = opts.limit || 8;

    var all = [];
    for (var rid in WORKS_EXTRA) {
      if (!WORKS_EXTRA.hasOwnProperty(rid)) continue;
      var w = WORKS_EXTRA[rid];
      if (!w.image) continue;                       // rule 1
      if (wing && w.wing !== wing) continue;
      all.push({ rid: rid, title: w.title, author: w.author, h3: w.h3,
                 image: w.image, wd: w.wd, refs: w.refs || 0 });
    }
    if (!all.length) { container.innerHTML = ''; return { shown: 0, groups: 0 }; }

    // Highest-referenced work of each H3 becomes that H3's example card.
    var byH3 = {};
    all.forEach(function (w) { (byH3[w.h3 || '—'] = byH3[w.h3 || '—'] || []).push(w); });
    var groups = Object.keys(byH3).sort(function (a, b) {
      return byH3[b].length - byH3[a].length;
    });
    var out = [], featuredOf = {};
    groups.forEach(function (h3) {
      byH3[h3].sort(function (a, b) { return b.refs - a.refs; });
      featuredOf[h3] = byH3[h3][0].rid;
    });
    all.sort(function (a, b) { return b.refs - a.refs; });
    all.slice(0, limit).forEach(function (w) {
      out.push(card(w, featuredOf[w.h3 || '—'] === w.rid));
    });
    container.innerHTML = out.join('');

    // Rule 2 — a hero image that 404s takes its card with it.
    container.querySelectorAll('img').forEach(function (img) {
      img.addEventListener('error', function () {
        var c = img.closest('.result-card');
        if (c) c.remove();
        if (!container.querySelector('.result-card') && opts.onEmpty) opts.onEmpty();
      });
    });

    return { shown: Math.min(all.length, limit), total: all.length, groups: groups.length };
  }

  return { render: render };
})();
