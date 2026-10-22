'use strict';
// Browser tests for the AND/OR filter operators: the REAL facet-engine.js,
// category-catalogue.js and active-filters.js over small fixture pages
// (tests/js/fixtures/). Needs Playwright + Chromium; skipped when missing
// (the CI job does not install them). Run: node --test tests/js/filter-ui.test.js
const test = require('node:test');
const assert = require('node:assert/strict');
const path = require('node:path');
const fs = require('node:fs');
const { execSync } = require('node:child_process');

function loadChromium() {
  const tries = [() => require('playwright'), () => require(path.join(execSync('npm root -g').toString().trim(), 'playwright'))];
  for (const t of tries) { try { return t().chromium; } catch (e) { /* next */ } }
  return null;
}
function findChrome() {
  if (process.env.CHROMIUM_PATH) return process.env.CHROMIUM_PATH;
  const base = process.env.PLAYWRIGHT_BROWSERS_PATH || '/opt/pw-browsers';
  try {
    for (const d of fs.readdirSync(base)) {
      const p = path.join(base, d, 'chrome-linux', 'chrome');
      if (/^chromium-\d+$/.test(d) && fs.existsSync(p)) return p;
    }
  } catch (e) { /* none */ }
  return null;
}

const chromium = loadChromium();
const chrome = findChrome();
const FIX = (n) => 'file://' + path.join(__dirname, 'fixtures', n);
const skip = !chromium ? 'playwright not installed' : false;

let browser;
test.before(async () => {
  if (skip) return;
  try { browser = await chromium.launch(chrome ? { executablePath: chrome } : {}); }
  catch (e) { browser = null; }
});
test.after(async () => { if (browser) await browser.close(); });

async function open(url, viewport) {
  const page = await browser.newPage({ viewport: viewport || { width: 1200, height: 900 } });
  const errors = [];
  page.on('pageerror', (e) => errors.push(String(e)));
  await page.goto(url);
  page.errors = errors;
  return page;
}
const settle = (page) => page.waitForTimeout(80);

// ── Persons-like page (FacetEngine) ───────────────────────────────────────
const box = (field, val) => `input[data-facet="${field}"][data-match="${val}"]`;
const names = (page) => page.$$eval('#results li', (l) => l.map((x) => x.textContent).sort());
const sorted = (a) => a.slice().sort();
async function tick(page, field, val) { await page.locator(box(field, val)).check(); await settle(page); }
async function untick(page, field, val) { await page.locator(box(field, val)).uncheck(); await settle(page); }
async function ops(page) { return page.$$eval('.active-filter-op:not(.active-filter-op--fixed)', (s) => s.map((x) => x.value)); }
async function setOp(page, i, v) {
  await page.locator('.active-filter-op:not(.active-filter-op--fixed)').nth(i).selectOption(v);
  await settle(page);
}
// The operators shown must be the operators evaluated.
async function assertShownIsApplied(page) {
  // chips are drawn cluster by cluster: a group's term operators, then the next group's operator
  const expected = await page.evaluate(() => {
    const e = HcaFilter.shared.expr(), out = [];
    e.groups.forEach((g, gi) => { if (gi > 0) out.push(e.ops[gi - 1]); g.ops.forEach((o) => out.push(o)); });
    return out;
  });
  assert.deepEqual(await ops(page), expected);
}

test('FacetEngine page: 1 — a single filter', { skip }, async (t) => {
  if (!browser) return t.skip('no chromium');
  const page = await open(FIX('facet-engine.html'));
  assert.equal((await names(page)).length, 9);
  await tick(page, 'nationality', 'sv');
  assert.deepEqual(await names(page), ['Anna', 'Bo', 'Freja']);
  assert.deepEqual(await ops(page), []);                       // nothing to connect yet
  assert.deepEqual(page.errors, []);
  await page.close();
});

test('FacetEngine page: 2/3/4/5 — AND by default, Swedish AND musician, switch to OR in the bar', { skip }, async (t) => {
  if (!browser) return t.skip('no chromium');
  const page = await open(FIX('facet-engine.html'));
  await tick(page, 'nationality', 'sv');
  await tick(page, 'role', 'musiker');
  assert.deepEqual(await ops(page), ['AND']);
  assert.deepEqual(await names(page), ['Anna', 'Freja']);       // both criteria only
  assert.match(await page.textContent('.active-filters__formula'), /Nationalitet: sv AND Erhvervsgren: musiker/);
  await assertShownIsApplied(page);

  await setOp(page, 0, 'OR');                                   // directly in the interface
  assert.deepEqual(await ops(page), ['OR']);
  assert.deepEqual(await names(page), ['Anna', 'Bo', 'Carl', 'Erik', 'Freja', 'Hans']);   // at least one
  assert.match(await page.textContent('.active-filters__formula'), /sv OR .*musiker/);
  assert.equal(await page.textContent('#count'), '6');
  await assertShownIsApplied(page);

  await setOp(page, 0, 'AND');                                  // and back
  assert.deepEqual(await names(page), ['Anna', 'Freja']);
  await page.close();
});

test('FacetEngine page: 6 — three filters with different operators; AND binds tighter than OR', { skip }, async (t) => {
  if (!browser) return t.skip('no chromium');
  const page = await open(FIX('facet-engine.html'));
  await tick(page, 'nationality', 'sv');
  await tick(page, 'role', 'musiker');
  // no Swedish musician is male → under AND the value is unreachable and disabled …
  assert.equal(await page.locator(box('gender', 'mand')).isDisabled(), true);
  await setOp(page, 0, 'OR');                                   // … but reachable once the reader chooses OR
  assert.equal(await page.locator(box('gender', 'mand')).isDisabled(), false);
  await tick(page, 'gender', 'mand');
  assert.deepEqual(await ops(page), ['OR', 'AND']);             // sv OR (musiker AND mand)
  assert.deepEqual(await names(page), ['Anna', 'Bo', 'Carl', 'Erik', 'Freja', 'Hans']);
  assert.match(await page.textContent('.active-filters__formula'), /sv OR \(.*musiker AND .*mand\)/);
  await assertShownIsApplied(page);

  await setOp(page, 0, 'AND');                                  // sv AND musiker AND mand
  assert.deepEqual(await ops(page), ['AND', 'AND']);
  assert.deepEqual(await names(page), []);

  await setOp(page, 1, 'OR');                                   // (sv AND musiker) OR mand
  assert.deepEqual(await ops(page), ['AND', 'OR']);
  assert.deepEqual(await names(page), ['Anna', 'Bo', 'Carl', 'Erik', 'Freja', 'Gunnar', 'Hans']);
  assert.match(await page.textContent('.active-filters__formula'), /\(.*sv AND .*musiker\) OR .*mand/);
  await assertShownIsApplied(page);

  await setOp(page, 0, 'OR');                                   // sv OR musiker OR mand
  assert.deepEqual(await ops(page), ['OR', 'OR']);
  assert.deepEqual(await names(page), ['Anna', 'Bo', 'Carl', 'Erik', 'Freja', 'Gunnar', 'Hans']);
  await page.close();
});

test('FacetEngine page: same facet — OR by default (old behaviour), changeable', { skip }, async (t) => {
  if (!browser) return t.skip('no chromium');
  const page = await open(FIX('facet-engine.html'));
  await tick(page, 'nationality', 'sv');
  await tick(page, 'nationality', 'no');
  assert.deepEqual(await ops(page), ['OR']);
  assert.deepEqual(await names(page), ['Anna', 'Bo', 'Erik', 'Freja', 'Gunnar']);
  await tick(page, 'role', 'musiker');                          // (sv OR no) AND musiker
  assert.deepEqual(await ops(page), ['OR', 'AND']);
  assert.deepEqual(await names(page), ['Anna', 'Erik', 'Freja']);
  assert.match(await page.textContent('.active-filters__formula'), /\(.*sv OR no\) AND .*musiker/);
  await setOp(page, 0, 'AND');                                  // nobody has two nationalities
  assert.deepEqual(await names(page), []);
  await page.close();
});

test('FacetEngine page: 7 — add, change and remove filters', { skip }, async (t) => {
  if (!browser) return t.skip('no chromium');
  const page = await open(FIX('facet-engine.html'));
  await tick(page, 'nationality', 'sv');
  await tick(page, 'role', 'musiker');
  await setOp(page, 0, 'OR');
  await tick(page, 'gender', 'kvinde');                         // sv OR musiker AND kvinde
  assert.deepEqual(await ops(page), ['OR', 'AND']);
  assert.deepEqual(await names(page), ['Anna', 'Bo', 'Freja']);

  // remove the middle filter through its chip: the survivors keep their own operators
  await page.locator('.active-filter[data-key*="role"]').click();
  await settle(page);
  assert.deepEqual(await ops(page), ['AND']);                   // sv AND kvinde
  assert.deepEqual(await names(page), ['Anna', 'Freja']);

  // re-adding a removed filter starts from the default (AND) again
  await tick(page, 'role', 'maler');
  assert.deepEqual(await ops(page), ['AND', 'AND']);
  assert.deepEqual(await names(page), ['Freja']);

  // change a value of an existing filter
  await untick(page, 'role', 'maler');
  await tick(page, 'role', 'musiker');
  assert.deepEqual(await names(page), ['Anna', 'Freja']);

  // remove everything → full list, bar hidden
  await page.locator('.active-filters__clear').click();
  await settle(page);
  assert.equal((await names(page)).length, 9);
  assert.equal(await page.locator('.active-filters').isHidden(), true);
  // …and a fresh pair starts at the default again
  await tick(page, 'nationality', 'da');
  await tick(page, 'gender', 'mand');
  assert.deepEqual(await ops(page), ['AND']);
  await page.close();
});

test('FacetEngine page: year range takes part like any other filter', { skip }, async (t) => {
  if (!browser) return t.skip('no chromium');
  const page = await open(FIX('facet-engine.html'));
  await tick(page, 'nationality', 'da');
  await page.fill('[data-range-from]', '1860');
  await page.fill('[data-range-to]', '1870');
  await settle(page);
  assert.deepEqual(await ops(page), ['AND']);
  assert.deepEqual(await names(page), ['Carl', 'Dorte']);       // da AND mentioned 1860–1870
  await setOp(page, 0, 'OR');
  assert.deepEqual(await names(page), ['Carl', 'Dorte', 'Freja', 'Gunnar', 'Hans']);   // da OR years in range
  await assertShownIsApplied(page);
  await page.close();
});

test('FacetEngine page: facet counts follow "value as the facet\'s only selection" under the chosen operators', { skip }, async (t) => {
  if (!browser) return t.skip('no chromium');
  const page = await open(FIX('facet-engine.html'));
  const count = (field, val) => page.locator(box(field, val)).evaluate((b) => b.closest('.facet-item').querySelector('.facet-item__count').textContent);
  await tick(page, 'nationality', 'sv');
  assert.equal(await count('role', 'maler'), '2');              // Bo, Freja
  assert.equal(await count('role', 'musiker'), '2');            // Anna, Freja
  assert.equal(await page.locator(box('nationality', 'da')).isEnabled(), true);   // other value of the same facet: reachable
  await tick(page, 'role', 'musiker');
  await setOp(page, 0, 'OR');
  assert.equal(await count('role', 'maler'), '5');              // sv OR maler = Anna, Bo, Dorte, Freja, Gunnar
  await page.close();
});

test('FacetEngine page: reset button clears the selection and the operators', { skip }, async (t) => {
  if (!browser) return t.skip('no chromium');
  const page = await open(FIX('facet-engine.html'));
  await tick(page, 'nationality', 'sv');
  await tick(page, 'role', 'musiker');
  await setOp(page, 0, 'OR');
  await page.click('.facet-panel__clear');
  await settle(page);
  assert.equal((await names(page)).length, 9);
  await tick(page, 'nationality', 'sv');
  await tick(page, 'role', 'musiker');
  assert.deepEqual(await ops(page), ['AND']);
  await page.close();
});

test('FacetEngine page: dropdown is a native select that keeps keyboard focus when it redraws', { skip }, async (t) => {
  if (!browser) return t.skip('no chromium');
  const page = await open(FIX('facet-engine.html'), { width: 390, height: 800 });
  await tick(page, 'nationality', 'sv');
  await tick(page, 'role', 'musiker');
  const sel = page.locator('select.active-filter-op').first();
  await sel.focus();
  await sel.selectOption('OR');
  await settle(page);
  assert.equal(await page.evaluate(() => document.activeElement && document.activeElement.className), 'active-filter-op active-filter-op--group');
  assert.ok(await sel.getAttribute('aria-label'));
  await page.close();
});

// ── Category-catalogue page ───────────────────────────────────────────────
const titles = (page) => page.$$eval('#js-cat-results .result-card__title', (l) => l.map((x) => x.textContent).sort());
const cbox = (attr, val) => `input[data-${attr}="${val}"]`;
async function ctick(page, attr, val) { await page.locator(cbox(attr, val)).check(); await settle(page); }

test('Catalogue page: AND by default, OR on request, mixed operators, add/remove', { skip }, async (t) => {
  if (!browser) return t.skip('no chromium');
  const page = await open(FIX('category-catalogue.html'));
  assert.equal((await titles(page)).length, 6);
  await ctick(page, 'h2', 'H. C. ANDERSEN');
  assert.deepEqual(await titles(page), ['Værk 1', 'Værk 2', 'Værk 6']);
  await ctick(page, 'h3', 'Digte');
  assert.deepEqual(await ops(page), ['AND']);
  assert.deepEqual(await titles(page), ['Værk 1', 'Værk 6']);   // HCA AND Digte
  await assertShownIsApplied(page);
  await setOp(page, 0, 'OR');
  assert.deepEqual(await titles(page), ['Værk 1', 'Værk 2', 'Værk 3', 'Værk 6']);   // HCA OR Digte
  await setOp(page, 0, 'AND');

  await ctick(page, 'place', 'København');
  assert.deepEqual(await ops(page), ['AND', 'AND']);
  assert.deepEqual(await titles(page), ['Værk 6']);
  await setOp(page, 1, 'OR');                                   // (HCA AND Digte) OR København
  assert.deepEqual(await titles(page), ['Værk 1', 'Værk 3', 'Værk 5', 'Værk 6']);
  await assertShownIsApplied(page);
  await setOp(page, 0, 'OR');                                   // HCA OR Digte OR København
  assert.deepEqual(await titles(page), ['Værk 1', 'Værk 2', 'Værk 3', 'Værk 5', 'Værk 6']);

  await page.locator('.active-filter[data-key*="h2"]').click(); // remove HCA
  await settle(page);
  assert.deepEqual(await ops(page), ['OR']);                    // Digte OR København
  assert.deepEqual(await titles(page), ['Værk 1', 'Værk 3', 'Værk 5', 'Værk 6']);
  assert.deepEqual(page.errors, []);
  await page.close();
});

test('Catalogue page: same facet OR by default; availability follows the operators', { skip }, async (t) => {
  if (!browser) return t.skip('no chromium');
  const page = await open(FIX('category-catalogue.html'));
  await ctick(page, 'h3', 'Digte');
  await ctick(page, 'h3', 'Eventyr');
  assert.deepEqual(await ops(page), ['OR']);
  assert.deepEqual(await titles(page), ['Værk 1', 'Værk 2', 'Værk 3', 'Værk 5', 'Værk 6']);
  await ctick(page, 'h2', 'H. C. ANDERSEN');                    // (Digte OR Eventyr) AND HCA
  assert.deepEqual(await titles(page), ['Værk 1', 'Værk 2', 'Værk 6']);
  await page.close();

  const p2 = await open(FIX('category-catalogue.html'));
  await ctick(p2, 'h2', 'H. C. ANDERSEN');
  await ctick(p2, 'place', 'Odense');
  // HCA AND Odense = Værk 1, 2: no "Romaner" among them → unreachable, disabled
  assert.equal(await p2.locator(cbox('h3', 'Romaner')).isDisabled(), true);
  await setOp(p2, 0, 'OR');                                     // HCA OR Odense includes Værk 4 (Romaner)
  assert.equal(await p2.locator(cbox('h3', 'Romaner')).isDisabled(), false);
  await p2.close();
});
