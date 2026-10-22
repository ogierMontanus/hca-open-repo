/* no-submit.js — keep the header/landing search forms from navigating.
   Replaces the inline `onsubmit="return false"` attribute (inline handlers
   are blocked by the site's Content-Security-Policy, see docs/security.md).
   Mark a form with `data-no-submit`; the typeahead in site-search.js handles
   the query itself. Delegated, so it works whenever this file is loaded. */
document.addEventListener('submit', function (e) {
  if (e.target && e.target.hasAttribute && e.target.hasAttribute('data-no-submit')) {
    e.preventDefault();
  }
}, true);
