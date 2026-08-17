/* icons.js — shared SVG icon sprite for the Hvem/Hvad/Hvor/Hvornår facet
 * icons, reused in the side-acc accordion and carried into H1/H2/H3
 * headings (persons/places/billedkunst/bibliotek/teater-musik/works.html).
 *
 * A page mounts the sprite with:
 *   <div id="icon-sprite"></div>
 *   <script src="js/icons.js"></script>
 * placed as the FIRST thing inside <body>, before any <svg><use> that
 * references it — same "one shared script, many pages" pattern as
 * cart.js/entity-refs.js, chosen over duplicating raw SVG path data in
 * every HTML file. A blocking script tag (no defer/async) executes the
 * moment the parser reaches it, so the mount div is already present by
 * then; <use> also re-resolves reactively if a page ever loads this out
 * of order, so there's no hard requirement either way — this is just the
 * simplest correct placement.
 *
 * Icons: person (Hvem), pin (Hvor), book (Bibliotek), painting (Billedkunst
 * — brush across a framed canvas, not a photo), sculpture (Billedkunst —
 * bust on a plinth), note (Teater & Musik), mask (Teater & Musik — a
 * classic theater mask, smiling), calendar (Hvornår).
 */
(function () {
  'use strict';
  var el = document.getElementById('icon-sprite');
  if (!el) return;
  el.outerHTML =
    '<svg width="0" height="0" style="position:absolute" aria-hidden="true"><defs>' +
      '<g id="icon-person">' +
        '<circle cx="12" cy="8.2" r="3.6"/>' +
        '<path d="M4.8 20c.6-4 3.4-6.4 7.2-6.4s6.6 2.4 7.2 6.4"/>' +
      '</g>' +
      '<g id="icon-pin">' +
        '<path d="M12 21.5C8.5 17.9 5.5 14 5.5 9.8a6.5 6.5 0 1 1 13 0c0 4.2-3 8.1-6.5 11.7Z"/>' +
        '<circle cx="12" cy="9.6" r="2.3"/>' +
      '</g>' +
      '<g id="icon-book">' +
        '<path d="M12 5.4c-1.9-1.1-4.2-1.5-6.9-1.1V17c2.7-.4 5 0 6.9 1.1"/>' +
        '<path d="M12 5.4c1.9-1.1 4.2-1.5 6.9-1.1V17c-2.7-.4-5 0-6.9 1.1"/>' +
        '<path d="M12 5.4v12.7"/>' +
      '</g>' +
      '<g id="icon-painting">' +
        '<rect x="3.6" y="3.8" width="16.8" height="16.4" rx="1.3"/>' +
        '<path d="M8.6 15.4 16 8c.8-.8 2-.8 2.8 0 .8.8.8 2 0 2.8l-7.4 7.4"/>' +
        '<path d="M8.6 15.4c-.9.3-1.6 1.1-1.9 2l-.4 1.6 1.6-.4c.9-.3 1.7-1 2-1.9"/>' +
      '</g>' +
      '<g id="icon-sculpture">' +
        '<circle cx="12" cy="6.8" r="2.9"/>' +
        '<path d="M9 15.4v-3c0-1.4 1.3-2.4 3-2.4s3 1 3 2.4v3"/>' +
        '<rect x="8.6" y="15.4" width="6.8" height="3.6"/>' +
        '<path d="M5.8 20.6h12.4"/>' +
      '</g>' +
      '<g id="icon-note">' +
        '<circle cx="7.7" cy="17.5" r="2.9" fill="currentColor" stroke="none"/>' +
        '<path d="M10.6 17.5V4.6l6-1.4v3.3"/>' +
        '<path d="M16.6 6.5c1.7.4 2.7 1.4 2.7 2.8"/>' +
      '</g>' +
      '<g id="icon-mask">' +
        // Small tied-hair/laurel flourishes at the crown, like the classic
        // gold theater masks — this is what reads as "mask" rather than
        // "smiley" at a glance.
        '<path d="M7.6 4.6 5.6 6.2M16.4 4.6l2 1.6"/>' +
        '<ellipse cx="12" cy="11.6" rx="6.6" ry="7.6"/>' +
        // Angled, raised brows — Thalia's animated comedic brow.
        '<path d="M8.4 9.2l1.8.9M15.6 9.2l-1.8.9" stroke-width="2"/>' +
        '<ellipse cx="9.6" cy="11.6" rx=".9" ry="1.3" fill="currentColor" stroke="none"/>' +
        '<ellipse cx="14.4" cy="11.6" rx=".9" ry="1.3" fill="currentColor" stroke="none"/>' +
        // Wide open laughing mouth — filled, not a thin curved line.
        '<path d="M8.6 15.2c1 1.9 5.8 1.9 6.8 0-.3 2.1-1.8 3.4-3.4 3.4s-3.1-1.3-3.4-3.4z" fill="currentColor" stroke="none"/>' +
      '</g>' +
      '<g id="icon-calendar">' +
        '<rect x="3.6" y="5.2" width="16.8" height="15" rx="1.6"/>' +
        '<path d="M3.6 9.6h16.8"/>' +
        '<path d="M8 3.4v3.6M16 3.4v3.6"/>' +
      '</g>' +
    '</defs></svg>';
})();
