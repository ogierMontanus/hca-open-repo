// Runs the shared cases in tests/fixtures/crowd_cases.json against the
// browser validator; tests/test_crowd_validate.py runs the same file against
// scripts/crowdsource/validate.py, so the two cannot drift apart.
// The taxonomy comes from scripts/crowdsource/taxonomy.py via CROWD_TAXONOMY_JSON
// (set by tests/test_crowd_js.py).
const test = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const path = require('node:path');

const V = require('../../mockup/js/crowd-validate.js');
const tax = JSON.parse(fs.readFileSync(process.env.CROWD_TAXONOMY_JSON, 'utf8'));
const fx = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'fixtures', 'crowd_cases.json'), 'utf8'));

for (const c of fx.cases) {
  test('validate: ' + c.name, () => {
    const got = V.validate(c.payload, tax, fx.today).map(e => [e.path, e.code]).sort();
    assert.deepStrictEqual(got, c.errors);
  });
}

test('normalise collapses whitespace and strips control characters', () => {
  assert.strictEqual(V.normalise('  a \t b\u0000 '), 'a b');
  assert.strictEqual(V.normalise('a\n\n\n\nb', true), 'a\n\nb');
});
