// The review rules of the browser-local back-end (mockup/js/crowd-store.js),
// ported from scripts/crowdsource/store.py: decision → status, final values,
// conflicts, badges.
const test = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');

global.CROWD_TAXONOMY = JSON.parse(fs.readFileSync(process.env.CROWD_TAXONOMY_JSON, 'utf8'));
global.CrowdValidate = require('../../mockup/js/crowd-validate.js');
const Store = require('../../mockup/js/crowd-store.js');

function sub(over) {
  return Object.assign({
    id: 'CS-20261029-aaaaaa', person_id: 'Reg0030030', person_label: 'Aagaard', status: 'submitted', revision: 1,
    identification: { status: 'identified', summary: '', same_as: '' }, overall_confidence: 'probable',
    fields: [
      { field: 'given_names', value: 'Peder', confidence: 'probable', comment: '', sources: [0] },
      { field: 'birth_date', value: '1820', confidence: 'proposed', comment: '', sources: [0] }],
    sources: [{ type: 'web', citation: 'DDD', url: 'https://x.dk/a', result: 'stoetter' }],
    contributor: { id: 'C-1', name: 'Anne', public_credit: true }, history: [], review: null, incorporated: null,
    register_snapshot: { doubt: true, area: 'Danmark' }
  }, over || {});
}

test('all fields accepted → approved; final value is kept', () => {
  const s = sub();
  Store._reviewSub(s, 'Holger', { fields: { 0: { decision: 'accept' }, 1: { decision: 'accept_edited', final_value: '1821' } } }, '', 'decide');
  assert.strictEqual(s.status, 'approved');
  assert.strictEqual(s.review.fields['1'].final_value, '1821');
  assert.strictEqual(s.review.fields['0'].final_confidence, 'probable');
});

test('mixed → partially_approved, none → rejected', () => {
  const a = sub();
  Store._reviewSub(a, 'H', { fields: { 0: { decision: 'accept' }, 1: { decision: 'reject' } } }, '', 'decide');
  assert.strictEqual(a.status, 'partially_approved');
  const b = sub();
  Store._reviewSub(b, 'H', { fields: { 0: { decision: 'reject' }, 1: { decision: 'reject' } } }, '', 'decide');
  assert.strictEqual(b.status, 'rejected');
});

test('every field needs a decision; edits need a value; changes need a note', () => {
  assert.throws(() => Store._reviewSub(sub(), 'H', { fields: { 0: { decision: 'accept' } } }, '', 'decide'), /no decision/);
  assert.throws(() => Store._reviewSub(sub(), 'H', { fields: { 0: { decision: 'accept_edited' }, 1: { decision: 'accept' } } }, '', 'decide'), /final_value/);
  assert.throws(() => Store._reviewSub(sub(), 'H', {}, 'x', 'request_changes'), /note is required/);
  const s = sub();
  Store._reviewSub(s, 'H', {}, 'Mangler kilde til fødselsåret', 'request_changes');
  assert.strictEqual(s.status, 'needs_changes');
});

test('identification statements without fields are decided separately', () => {
  const s = sub({ identification: { status: 'unidentifiable', summary: 'søgt', same_as: '' }, fields: [] });
  assert.throws(() => Store._reviewSub(s, 'H', { fields: {} }, '', 'decide'), /identification/);
  Store._reviewSub(s, 'H', { fields: {}, identification: { decision: 'accept' } }, '', 'decide');
  assert.strictEqual(s.status, 'approved');
});

test('an incorporated submission is locked', () => {
  assert.throws(() => Store._reviewSub(sub({ incorporated: { batch: 'B' } }), 'H', {}, 'x', 'request_changes'), /incorporated/);
});

test('conflicts name other live claims with a different value', () => {
  const a = sub(), b = sub({ id: 'CS-20261029-bbbbbb', contributor: { id: 'C-2', name: 'Bo' } });
  b.fields[0].value = 'Peter';
  const c = Store._conflictsFor(a, [a, b]);
  assert.strictEqual(c.length, 1);
  assert.strictEqual(c[0].field, 'given_names');
  b.status = 'rejected';
  assert.strictEqual(Store._conflictsFor(a, [a, b]).length, 0);
});

test('badges are earned from reviewed work only', () => {
  const s = sub();
  assert.deepStrictEqual(Store._computeStats([s])[0].badges, []);
  Store._reviewSub(s, 'H', { fields: { 0: { decision: 'accept' }, 1: { decision: 'accept' } } }, '', 'decide');
  const st = Store._computeStats([s])[0];
  assert.deepStrictEqual(st.badges.sort(), ['first_accepted', 'resolved_doubt']);
  assert.strictEqual(st.accepted_fields, 2);
});

test('an imported file cannot claim a status its decisions do not support', () => {
  const forged = sub({ status: 'approved', review: { reviewer: 'x', fields: { 0: { decision: 'accept' } } }, evil: '<img>' });
  const out = Store._normaliseImported(forged);
  assert.strictEqual(out.status, 'submitted');
  assert.strictEqual(out.review, null);
  assert.ok(!('evil' in out));
  const real = sub({ status: 'approved', review: { reviewer: 'H', decided: 'x', note: '', fields: { 0: { decision: 'accept' }, 1: { decision: 'reject' } } } });
  assert.strictEqual(Store._normaliseImported(real).status, 'partially_approved');
  const weird = sub({ created: 42, contributor: { id: {}, name: ' Anne ' } });
  const w = Store._normaliseImported(weird);
  assert.strictEqual(typeof w.created, 'string');
  assert.strictEqual(w.contributor.name, 'Anne');
});
