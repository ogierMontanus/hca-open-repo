/* report-issue.js — "Indberet fejl" button + dialog.
 *
 * Loaded on every page by nav.js. Posts the report to the Cloudflare Worker in
 * workers/report-issue/, which files it as a GitHub issue (the GitHub token
 * must never reach the browser). Setup: docs/report-issue.md.
 *
 * Until REPORT_ENDPOINT is filled in, the dialog falls back to opening GitHub's
 * own "new issue" page pre-filled in a new tab, so the button is never dead.
 */
(function () {
  'use strict';
  if (window.__hcaReportIssue) return;   // loaded by nav.js and/or a page tag
  window.__hcaReportIssue = true;

  var REPORT_ENDPOINT = window.HCA_REPORT_ENDPOINT || '';   // https://hca-report-issue.<account>.workers.dev
  var REPO = 'ogierMontanus/hca-open-repo';
  var ISSUE_LABEL = 'brugerrapport';

  var MAX_INPUT_BYTES = 15 * 1024 * 1024;   // refuse absurd originals up front
  var MAX_UPLOAD_BYTES = 2.5 * 1024 * 1024; // must match the Worker's limit
  var MAX_IMAGE_EDGE = 1600;

  var T = {
    da: {
      open: 'Indberet fejl', title: 'Indberet en fejl',
      intro: 'Har du fundet en fejl eller noget, der ser forkert ud? Fortæl os det, så opretter vi en sag, vi kan følge op på.',
      name: 'Dit navn', email: 'Din e-mail', summary: 'Kort overskrift', details: 'Hvad gik galt?',
      detailsHint: 'Beskriv hvad du gjorde, hvad du forventede, og hvad der skete i stedet.',
      shot: 'Skærmbillede', optional: '(valgfrit)', shotHint: 'Vælg en billedfil eller indsæt et billede fra udklipsholderen (Ctrl+V).',
      shotFallback: 'Du kan trække et skærmbillede ind i GitHub-vinduet, der åbner.',
      remove: 'Fjern billede', page: 'Side', consent: 'Jeg forstår, at mit navn, min e-mail og evt. skærmbillede bliver offentligt synlige i fejlrapporten på GitHub.',
      send: 'Send indberetning', sending: 'Sender…', cancel: 'Annuller', close: 'Luk',
      thanks: 'Tak! Fejlen er registreret', thanksNum: 'som sag #', viewIssue: 'Se sagen på GitHub',
      screenshotLost: 'Dit skærmbillede kunne dog ikke gemmes.',
      fallbackDone: 'GitHub er åbnet i et nyt faneblad — tryk “Submit new issue” dér for at gennemføre indberetningen.',
      newTab: ' (åbner i nyt faneblad)',
      errors: {
        invalid_name: 'Skriv dit navn.', invalid_email: 'Skriv en gyldig e-mailadresse.',
        invalid_title: 'Overskriften skal være mellem 3 og 120 tegn.', invalid_description: 'Beskrivelsen skal være mellem 10 og 5000 tegn.',
        invalid_screenshot: 'Skærmbilledet kunne ikke læses. Prøv et andet billede.', screenshot_too_large: 'Skærmbilledet er for stort.',
        network: 'Kunne ikke nå serveren. Tjek din forbindelse og prøv igen.', generic: 'Noget gik galt, og indberetningen blev ikke sendt. Prøv igen om lidt.',
        notImage: 'Filen er ikke et billede.', tooBig: 'Billedet er for stort (højst 15 MB).', imgFail: 'Billedet kunne ikke behandles.'
      }
    },
    en: {
      open: 'Report a problem', title: 'Report a problem',
      intro: 'Found something wrong? Tell us and we will open an issue we can follow up on.',
      name: 'Your name', email: 'Your email', summary: 'Short summary', details: 'What went wrong?',
      detailsHint: 'Describe what you did, what you expected, and what happened instead.',
      shot: 'Screenshot', optional: '(optional)', shotHint: 'Choose an image file or paste one from the clipboard (Ctrl+V).',
      shotFallback: 'You can drag a screenshot into the GitHub window that opens.',
      remove: 'Remove image', page: 'Page', consent: 'I understand that my name, email and any screenshot will be publicly visible in the report on GitHub.',
      send: 'Send report', sending: 'Sending…', cancel: 'Cancel', close: 'Close',
      thanks: 'Thank you! The problem has been logged', thanksNum: 'as issue #', viewIssue: 'View the issue on GitHub',
      screenshotLost: 'Your screenshot could not be saved, though.',
      fallbackDone: 'GitHub opened in a new tab — press “Submit new issue” there to finish reporting.',
      newTab: ' (opens in new tab)',
      errors: {
        invalid_name: 'Please enter your name.', invalid_email: 'Please enter a valid email address.',
        invalid_title: 'The summary must be 3–120 characters.', invalid_description: 'The description must be 10–5000 characters.',
        invalid_screenshot: 'The screenshot could not be read. Try another image.', screenshot_too_large: 'The screenshot is too large.',
        network: 'Could not reach the server. Check your connection and try again.', generic: 'Something went wrong and the report was not sent. Please try again shortly.',
        notImage: 'That file is not an image.', tooBig: 'The image is too large (15 MB max).', imgFail: 'The image could not be processed.'
      }
    }
  };
  var lang = (document.documentElement.lang || 'da').slice(0, 2) === 'en' ? 'en' : 'da';
  var t = T[lang];

  var dialog, form, statusEl, sendBtn, fileInput, preview, previewImg, shot = null, lastFocus = null;

  function el(tag, attrs, children) {
    var n = document.createElement(tag);
    Object.keys(attrs || {}).forEach(function (k) {
      if (k === 'text') n.textContent = attrs[k];
      else if (k === 'class') n.className = attrs[k];
      else n.setAttribute(k, attrs[k]);
    });
    (children || []).forEach(function (c) { n.appendChild(c); });
    return n;
  }

  function field(id, label, control, hint) {
    var kids = [el('label', { for: id, text: label })];
    kids.push(control);
    if (hint) kids.splice(1, 0, el('p', { class: 'report-hint', id: id + '-hint', text: hint }));
    if (hint) control.setAttribute('aria-describedby', id + '-hint');
    return el('div', { class: 'report-field' }, kids);
  }

  function build() {
    var name = el('input', { id: 'report-name', name: 'name', type: 'text', required: '', maxlength: '100', autocomplete: 'name' });
    var email = el('input', { id: 'report-email', name: 'email', type: 'email', required: '', maxlength: '254', autocomplete: 'email' });
    var summary = el('input', { id: 'report-title', name: 'title', type: 'text', required: '', minlength: '3', maxlength: '120' });
    var details = el('textarea', { id: 'report-details', name: 'description', required: '', minlength: '10', maxlength: '5000', rows: '5' });

    fileInput = el('input', { id: 'report-file', type: 'file', accept: 'image/*' });
    previewImg = el('img', { class: 'report-preview__img', alt: '' });
    var removeBtn = el('button', { type: 'button', class: 'report-link', text: t.remove });
    preview = el('div', { class: 'report-preview', hidden: '' }, [previewImg, removeBtn]);
    removeBtn.addEventListener('click', clearShot);
    fileInput.addEventListener('change', function () { if (fileInput.files[0]) setShot(fileInput.files[0]); });

    var shotLabel = t.shot + ' ' + t.optional;
    var shotField = field('report-file', shotLabel, fileInput, REPORT_ENDPOINT ? t.shotHint : t.shotFallback);
    if (!REPORT_ENDPOINT) { fileInput.hidden = true; shotField.querySelector('label').hidden = true; }
    shotField.appendChild(preview);

    // Honeypot: invisible to people, tempting to bots. The Worker drops any
    // submission where it is filled in.
    var trap = el('div', { class: 'report-trap', 'aria-hidden': 'true' }, [
      el('label', { for: 'report-website', text: 'Website' }),
      el('input', { id: 'report-website', name: 'website', type: 'text', tabindex: '-1', autocomplete: 'off' })
    ]);

    var consent = el('input', { id: 'report-consent', type: 'checkbox', required: '' });
    var consentRow = el('div', { class: 'report-consent' }, [consent, el('label', { for: 'report-consent', text: t.consent })]);

    statusEl = el('p', { class: 'report-status', role: 'status', 'aria-live': 'polite' });
    sendBtn = el('button', { type: 'submit', class: 'report-btn report-btn--primary', text: t.send });
    var cancel = el('button', { type: 'button', class: 'report-btn', text: t.cancel });
    cancel.addEventListener('click', function () { dialog.close(); });

    var pageLine = el('p', { class: 'report-page' });
    pageLine.textContent = t.page + ': ' + location.pathname.split('/').slice(-2).join('/') + location.search;

    form = el('form', { class: 'report-form', novalidate: '' }, [
      field('report-name', t.name, name), field('report-email', t.email, email),
      field('report-title', t.summary, summary), field('report-details', t.details, details, t.detailsHint),
      shotField, trap, consentRow, pageLine, statusEl,
      el('div', { class: 'report-actions' }, [cancel, sendBtn])
    ]);
    form.addEventListener('submit', onSubmit);

    var closeX = el('button', { type: 'button', class: 'report-x', 'aria-label': t.close, text: '×' });
    closeX.addEventListener('click', function () { dialog.close(); });

    dialog = el('dialog', { class: 'report-dialog', 'aria-labelledby': 'report-heading' }, [
      closeX, el('h2', { id: 'report-heading', text: t.title }), el('p', { class: 'report-intro', text: t.intro }), form
    ]);
    // Click on the backdrop (the dialog element itself) closes it.
    dialog.addEventListener('mousedown', function (e) { if (e.target === dialog) dialog.close(); });
    dialog.addEventListener('paste', function (e) {
      var items = (e.clipboardData && e.clipboardData.files) || [];
      if (items.length && /^image\//.test(items[0].type) && REPORT_ENDPOINT) { e.preventDefault(); setShot(items[0]); }
    });
    dialog.addEventListener('close', function () { if (lastFocus) lastFocus.focus(); });
    document.body.appendChild(dialog);
  }

  function setStatus(msg, isError) {
    statusEl.textContent = msg || '';
    statusEl.classList.toggle('is-error', !!isError);
  }

  function clearShot() {
    shot = null; fileInput.value = ''; preview.hidden = true; previewImg.removeAttribute('src');
  }

  /** Downscale + re-encode as JPEG so uploads stay small and uniform. */
  function setShot(file) {
    setStatus('');
    if (!/^image\//.test(file.type)) return setStatus(t.errors.notImage, true);
    if (file.size > MAX_INPUT_BYTES) return setStatus(t.errors.tooBig, true);
    var url = URL.createObjectURL(file);
    var img = new Image();
    img.onload = function () {
      var scale = Math.min(1, MAX_IMAGE_EDGE / Math.max(img.naturalWidth, img.naturalHeight));
      var canvas = document.createElement('canvas');
      canvas.width = Math.max(1, Math.round(img.naturalWidth * scale));
      canvas.height = Math.max(1, Math.round(img.naturalHeight * scale));
      var ctx = canvas.getContext('2d');
      ctx.fillStyle = '#fff';                      // JPEG has no alpha
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
      URL.revokeObjectURL(url);
      var dataUrl = canvas.toDataURL('image/jpeg', 0.85);
      var b64 = dataUrl.split(',')[1];
      if (b64.length * 3 / 4 > MAX_UPLOAD_BYTES) { clearShot(); return setStatus(t.errors.tooBig, true); }
      shot = { type: 'image/jpeg', data: b64 };
      previewImg.src = dataUrl;
      preview.hidden = false;
    };
    img.onerror = function () { URL.revokeObjectURL(url); clearShot(); setStatus(t.errors.imgFail, true); };
    img.src = url;
  }

  function fieldValue(name) { return form.elements[name].value; }

  function onSubmit(e) {
    e.preventDefault();
    if (!form.reportValidity()) return;
    var payload = {
      name: fieldValue('name'), email: fieldValue('email'), title: fieldValue('title'),
      description: fieldValue('description'), website: fieldValue('website'),
      pageUrl: location.href.split('#')[0], userAgent: navigator.userAgent,
      viewport: window.innerWidth + 'x' + window.innerHeight, lang: document.documentElement.lang || '',
      screenshot: shot
    };
    if (!REPORT_ENDPOINT) return openGithubFallback(payload);

    sendBtn.disabled = true; sendBtn.textContent = t.sending; setStatus('');
    fetch(REPORT_ENDPOINT, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload)
    }).then(function (res) {
      return res.json().catch(function () { return {}; }).then(function (j) { return { ok: res.ok, json: j }; });
    }).then(function (r) {
      if (!r.ok || !r.json.ok) throw new Error(r.json.error || 'generic');
      showThanks(r.json);
    }).catch(function (err) {
      var known = t.errors[err.message];
      setStatus(known || (err instanceof TypeError ? t.errors.network : t.errors.generic), true);
      sendBtn.disabled = false; sendBtn.textContent = t.send;
    });
  }

  /** No Worker configured yet: hand the report to GitHub's own issue form. */
  function openGithubFallback(p) {
    var body = p.description + '\n\n---\n- Navn: ' + p.name + '\n- E-mail: ' + p.email +
      '\n- Side: ' + p.pageUrl + '\n- Browser: ' + p.userAgent + '\n- Vindue: ' + p.viewport;
    var url = 'https://github.com/' + REPO + '/issues/new?labels=' + encodeURIComponent(ISSUE_LABEL) +
      '&title=' + encodeURIComponent('[Fejlrapport] ' + p.title) +
      '&body=' + encodeURIComponent(body.slice(0, 5000));
    window.open(url, '_blank', 'noopener,noreferrer');
    setStatus(t.fallbackDone);
  }

  function showThanks(res) {
    var kids = [];
    var msg = t.thanks + (res.number ? ' ' + t.thanksNum + res.number : '') + '.';
    kids.push(el('p', { class: 'report-thanks', text: msg }));
    if (res.screenshot === false) kids.push(el('p', { class: 'report-hint', text: t.screenshotLost }));
    if (res.url) {
      // External link: discreet, new tab, announced to screen readers
      // (docs/external-links.md).
      var a = el('a', { class: 'external-link', href: res.url, target: '_blank', rel: 'noopener noreferrer' }, [
        document.createTextNode(t.viewIssue),
        el('span', { class: 'external-link__icon', 'aria-hidden': 'true', text: '↗' }),
        el('span', { class: 'sr-only', text: t.newTab })
      ]);
      kids.push(el('p', {}, [a]));
    }
    var done = el('button', { type: 'button', class: 'report-btn report-btn--primary', text: t.close });
    done.addEventListener('click', function () { dialog.close(); });
    kids.push(el('div', { class: 'report-actions' }, [done]));
    form.replaceChildren.apply(form, kids);
    done.focus();
  }

  function reset() {
    if (dialog) dialog.remove();
    shot = null;
    build();
  }

  function open() {
    lastFocus = document.activeElement;
    reset();                      // fresh form every time (also after a success)
    dialog.showModal();
    form.elements.name.focus();
  }

  function init() {
    if (typeof HTMLDialogElement === 'undefined') return;   // very old browser: no button rather than a broken one
    var btn = el('button', { type: 'button', class: 'report-fab', text: t.open, 'aria-haspopup': 'dialog' });
    btn.addEventListener('click', open);
    document.body.appendChild(btn);
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
