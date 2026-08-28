/* facet-overlay.js — shared "expand a capped facet list into an overlay"
 * mechanics for js/facet-engine.js (places.html/persons.html) and
 * js/category-catalogue.js (bibliotek.html/teater-musik.html/billedkunst.html).
 *
 * Both engines cap long facet lists (Land, Forfatter, ...) at a top-N by
 * count, but a reader chasing a mid-frequency value (Holland at rank 15 of
 * 79 countries; any of 331 authors past the top 20) still needs to find and
 * select it. This module owns the "Vis alle" -> full-viewport overlay that
 * solves that: expand/collapse state, the shared backdrop, the stacking fix
 * that keeps the overlay clickable above it, and focus/ARIA — the two
 * engines only supply the row/toggle markup itself, since what a "value" is
 * differs between FacetEngine's generic field/value model and
 * category-catalogue.js's h2/h3/author/place predicates.
 *
 * ── Usage ─────────────────────────────────────────────────────────────────
 *
 *   FacetOverlay.attach(host, function (expanded, sortMode) {
 *     // Return the full innerHTML for that state: rows sorted by count
 *     // (sortMode === 'count', the default) or alphabetically (sortMode
 *     // === 'alpha'), plus a <button data-facet-more>Vis alle (N)</button>
 *     // toggle when there are more values than the caller's own limit,
 *     // and — only while expanded — two small
 *     // <button data-facet-sort="count"|"alpha"> pills so the reader can
 *     // switch between them (sortMode only ever matters expanded; the
 *     // collapsed top-N view stays count-sorted always, since "top 20
 *     // alphabetically" isn't a top-N in any useful sense). Call attach()
 *     // again (e.g. after the underlying data or checked state changes)
 *     // to repaint host at its current expand/sort state.
 *     return html;
 *   }, function () {
 *     // Optional: called after every repaint (from attach() itself, or
 *     // from the module's own toggle/backdrop/Escape handling) — use it to
 *     // refresh availability counts/dimming for whatever rows just
 *     // appeared, since expanding can reveal hundreds of rows at once.
 *   });
 *
 * host must sit inside a <div class="facet-group"> (for the expanded class
 * + aria-label source) inside a <div class="facet-panel"> (for the
 * stacking-context fix) — the same markup contract both engines already use.
 *
 * The sort mode picked for a facet persists across close/reopen (it's
 * per-host state, not reset on collapse) since a reader who switched to
 * alphabetical probably wants it again next time they open that facet —
 * it's a browsing preference, independent of which values are ticked, so
 * "Nulstil" (which clears ticked values) leaves it alone too.
 *
 * Ticking a checkbox inside the overlay does NOT close it — a reader
 * narrowing down a 79-value list often wants to tick more than one before
 * moving on, and re-opening "Vis alle" from scratch after every click would
 * be worse than the original unbounded list. Only a backdrop click, the
 * toggle itself ("Vis alle" / "✕ Vis færre"), or Escape close it (see the
 * document-level listeners at the bottom of this file); a value ticked
 * while it's open still stays visible in the folded list afterwards even
 * below the top-N cutoff, same as before.
 *
 * Before clearing every checkbox on a "Nulstil" reset, callers should fold
 * back any open overlay first, so nothing reopens re-checked:
 *
 *   FacetOverlay.collapseAll();
 */
window.FacetOverlay = (function () {
  'use strict';

  // Only one facet body can be expanded into the overlay at a time, and a
  // shared backdrop element is created lazily on first use.
  var expandedHost = null;
  var backdropEl   = null;

  function ensureBackdrop() {
    if (backdropEl) return backdropEl;
    backdropEl = document.createElement('div');
    backdropEl.className = 'facet-backdrop';
    backdropEl.setAttribute('hidden', '');
    document.body.appendChild(backdropEl);
    backdropEl.addEventListener('click', collapse);
    return backdropEl;
  }

  // Whichever direction the overlay just moved, focus lands on the toggle
  // button that reappears in the freshly-rendered host — keyboard users
  // never lose their place, regardless of whether a click, Escape, a
  // backdrop click, or a selection triggered the fold-back.
  function focusToggle(host) {
    var btn = host.querySelector('[data-facet-more]');
    if (btn) btn.focus();
  }

  // The overlay covers most of the viewport, so mark it as a dialog for
  // assistive tech while open — cleared again once folded back down.
  function applyChrome(host, expanded) {
    var group = host.closest ? host.closest('.facet-group') : null;
    if (group) group.classList.toggle('facet-group--expanded', expanded);
    if (expanded) {
      host.setAttribute('role', 'dialog');
      host.setAttribute('aria-modal', 'true');
      var headerEl = group ? group.querySelector('.facet-group__header') : null;
      if (headerEl) host.setAttribute('aria-label', headerEl.textContent.replace(/[▲▾]/g, '').trim());
    } else {
      host.removeAttribute('role');
      host.removeAttribute('aria-modal');
      host.removeAttribute('aria-label');
    }
  }

  function repaint(host) {
    var expanded = host === expandedHost;
    var sortMode = host._facetSortMode || 'count';
    host.innerHTML = host._facetOverlayRender(expanded, sortMode);
    applyChrome(host, expanded);
    if (host._facetOverlayAfterRender) host._facetOverlayAfterRender();
  }

  function panelOf(host) {
    return host.closest ? host.closest('.facet-panel') : null;
  }

  function collapse() {
    if (!expandedHost) return;
    var host = expandedHost;
    expandedHost = null;
    repaint(host);
    var panel = panelOf(host);
    if (panel) panel.classList.remove('facet-panel--overlay-open');
    if (backdropEl) backdropEl.setAttribute('hidden', '');
    focusToggle(host);
  }

  function expand(host) {
    if (expandedHost && expandedHost !== host) collapse();
    expandedHost = host;
    repaint(host);
    // .facet-panel is position:sticky, which (per spec) always opens its
    // own stacking context; the backdrop's positive z-index otherwise
    // beats it regardless of any z-index set *inside* that context.
    // Lifting the panel's own z-index above the backdrop's is the one
    // level that actually reaches far enough up the stacking chain — see
    // .facet-panel--overlay-open in style.css.
    var panel = panelOf(host);
    if (panel) panel.classList.add('facet-panel--overlay-open');
    ensureBackdrop().removeAttribute('hidden');
    focusToggle(host);
  }

  // Render (or re-render) host at its current expand/sort state.
  // renderFn(expanded, sortMode) must return the full innerHTML, toggle
  // button included. afterRenderFn, if given, runs after every repaint
  // regardless of what triggered it.
  function attach(host, renderFn, afterRenderFn) {
    host._facetOverlayRender = renderFn;
    host._facetOverlayAfterRender = afterRenderFn || null;
    repaint(host);
  }

  function isExpanded(host) {
    return host === expandedHost;
  }

  // Delegated on the document, not a panel, since exactly one facet-panel
  // exists per page across every caller of this module.
  document.addEventListener('click', function (ev) {
    var moreBtn = ev.target && ev.target.closest ? ev.target.closest('[data-facet-more]') : null;
    if (moreBtn) {
      var host = moreBtn.closest('[data-facet-source]');
      if (!host) return;
      ev.preventDefault();
      if (host === expandedHost) collapse();
      else expand(host);
      return;
    }
    var sortBtn = ev.target && ev.target.closest ? ev.target.closest('[data-facet-sort]') : null;
    if (sortBtn) {
      var sortHost = sortBtn.closest('[data-facet-source]');
      if (!sortHost) return;
      ev.preventDefault();
      sortHost._facetSortMode = sortBtn.getAttribute('data-facet-sort');
      repaint(sortHost);
    }
  });

  document.addEventListener('keydown', function (ev) {
    if (ev.key === 'Escape' && expandedHost) collapse();
  });

  return {
    attach: attach,
    collapseAll: collapse,
    isExpanded: isExpanded
  };
})();
