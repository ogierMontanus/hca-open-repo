'use strict';
// Unit tests for mockup/js/filter-logic.js — run with: node --test tests/js/
const test = require('node:test');
const assert = require('node:assert/strict');
const path = require('node:path');
const F = require(path.join(__dirname, '..', '..', 'mockup', 'js', 'filter-logic.js'));

// Build an expression by hand: groups = [[ 'a', 'b' ], [ 'c' ]] with ops.
function expr(groups, groupOps, termOps) {
  return {
    groups: groups.map(function (terms, gi) {
      return {
        key: 'g' + gi,
        terms: terms.map(function (k) { return { key: k }; }),
        ops: (termOps && termOps[gi]) || terms.slice(1).map(function () { return 'OR'; })
      };
    }),
    ops: groupOps || groups.slice(1).map(function () { return 'AND'; })
  };
}
const truth = function (set) { return function (k) { return set.indexOf(k) !== -1; }; };

test('empty expression matches everything', () => {
  assert.equal(F.evalExpr({ groups: [], ops: [] }, truth([])), true);
});

test('single term', () => {
  const e = expr([['a']]);
  assert.equal(F.evalExpr(e, truth(['a'])), true);
  assert.equal(F.evalExpr(e, truth([])), false);
});

test('AND truth table across groups', () => {
  const e = expr([['a'], ['b']], ['AND']);
  assert.equal(F.evalExpr(e, truth(['a', 'b'])), true);
  assert.equal(F.evalExpr(e, truth(['a'])), false);
  assert.equal(F.evalExpr(e, truth(['b'])), false);
  assert.equal(F.evalExpr(e, truth([])), false);
});

test('OR truth table across groups', () => {
  const e = expr([['a'], ['b']], ['OR']);
  assert.equal(F.evalExpr(e, truth(['a', 'b'])), true);
  assert.equal(F.evalExpr(e, truth(['a'])), true);
  assert.equal(F.evalExpr(e, truth(['b'])), true);
  assert.equal(F.evalExpr(e, truth([])), false);
});

test('default state reproduces the old rule: OR inside a facet, AND between facets', () => {
  const s = F.createState();
  s.sync([
    { key: 'nat=sv', group: 'g0' }, { key: 'nat=no', group: 'g0' }, { key: 'role=m', group: 'g1' }
  ]);
  const e = s.expr();
  assert.deepEqual(e.ops, ['AND']);
  assert.deepEqual(e.groups[0].ops, ['OR']);
  const t = (set) => (k) => set.includes(k);
  assert.equal(F.evalExpr(e, t(['nat=sv', 'role=m'])), true);
  assert.equal(F.evalExpr(e, t(['nat=no', 'role=m'])), true);
  assert.equal(F.evalExpr(e, t(['nat=sv'])), false);     // not a musician
  assert.equal(F.evalExpr(e, t(['role=m'])), false);     // neither nationality
});

test('Swedish AND musician: only people satisfying both', () => {
  const people = [
    { n: 'sv', r: 'musiker' }, { n: 'sv', r: 'maler' }, { n: 'da', r: 'musiker' }, { n: 'da', r: 'maler' }
  ];
  const s = F.createState();
  s.sync([{ key: 'nat=sv', group: 'g0' }, { key: 'role=musiker', group: 'g1' }]);
  const e = s.expr();
  const hit = (p) => F.evalExpr(e, (k) => (k === 'nat=sv' ? p.n === 'sv' : p.r === 'musiker'));
  assert.deepEqual(people.filter(hit), [{ n: 'sv', r: 'musiker' }]);
  // switch to OR → at least one criterion
  assert.equal(s.setOp('group', 'g1', 'OR'), true);
  const e2 = s.expr();
  const hit2 = (p) => F.evalExpr(e2, (k) => (k === 'nat=sv' ? p.n === 'sv' : p.r === 'musiker'));
  assert.deepEqual(people.filter(hit2), [
    { n: 'sv', r: 'musiker' }, { n: 'sv', r: 'maler' }, { n: 'da', r: 'musiker' }
  ]);
});

test('AND binds tighter than OR (A OR B AND C)', () => {
  const e = expr([['a'], ['b'], ['c']], ['OR', 'AND']);
  // A OR (B AND C)
  assert.equal(F.evalExpr(e, truth(['a'])), true);
  assert.equal(F.evalExpr(e, truth(['b'])), false);
  assert.equal(F.evalExpr(e, truth(['b', 'c'])), true);
  assert.equal(F.evalExpr(e, truth(['c'])), false);
  // a strict left-to-right reading would give (A OR B) AND C → false for ['a']
});

test('A AND B OR C', () => {
  const e = expr([['a'], ['b'], ['c']], ['AND', 'OR']);
  assert.equal(F.evalExpr(e, truth(['a', 'b'])), true);
  assert.equal(F.evalExpr(e, truth(['c'])), true);
  assert.equal(F.evalExpr(e, truth(['a'])), false);
});

test('exhaustive: three and four terms with every operator combination match a reference evaluator', () => {
  function ref(vals, ops) {          // textbook: split on OR, AND inside each run
    let any = false, run = vals[0];
    for (let i = 1; i < vals.length; i++) {
      if (ops[i - 1] === 'AND') run = run && vals[i];
      else { any = any || run; run = vals[i]; }
    }
    return any || run;
  }
  for (const n of [3, 4]) {
    for (let om = 0; om < (1 << (n - 1)); om++) {
      const ops = []; for (let i = 0; i < n - 1; i++) ops.push(om & (1 << i) ? 'OR' : 'AND');
      for (let vm = 0; vm < (1 << n); vm++) {
        const vals = []; for (let i = 0; i < n; i++) vals.push(!!(vm & (1 << i)));
        const keys = vals.map((_, i) => 't' + i);
        const e = expr(keys.map((k) => [k]), ops);
        const on = keys.filter((_, i) => vals[i]);
        assert.equal(F.evalExpr(e, truth(on)), ref(vals, ops), n + ' ' + ops.join(',') + ' ' + vals.join(','));
      }
    }
  }
});

test('groups act as parentheses: (N1 OR N2) AND R, and (N1 AND N2) when switched', () => {
  const s = F.createState();
  s.sync([{ key: 'n1', group: 'g0' }, { key: 'n2', group: 'g0' }, { key: 'r', group: 'g1' }]);
  const t = (set) => (k) => set.includes(k);
  assert.equal(F.evalExpr(s.expr(), t(['n2', 'r'])), true);
  assert.equal(F.evalExpr(s.expr(), t(['n2'])), false);
  s.setOp('term', 'n2', 'AND');
  assert.equal(F.evalExpr(s.expr(), t(['n1', 'r'])), false);
  assert.equal(F.evalExpr(s.expr(), t(['n1', 'n2', 'r'])), true);
});

test('mixed operators at both levels (spec example)', () => {
  // Nationalitet: Svensk [AND] Erhvervsgren: Musiker [OR] Fødeland: Danmark
  const s = F.createState();
  s.sync([{ key: 'sv', group: 'nat' }, { key: 'mus', group: 'role' }, { key: 'dk', group: 'born' }]);
  s.setOp('group', 'born', 'OR');
  const e = s.expr();
  assert.deepEqual(e.ops, ['AND', 'OR']);
  const t = (set) => (k) => set.includes(k);
  assert.equal(F.evalExpr(e, t(['sv', 'mus'])), true);
  assert.equal(F.evalExpr(e, t(['dk'])), true);
  assert.equal(F.evalExpr(e, t(['sv'])), false);
  assert.equal(F.evalExpr(e, t(['mus'])), false);
});

test('state: order = selection order, groups keep their terms together', () => {
  const s = F.createState();
  s.sync([{ key: 'a1', group: 'A' }]);
  s.sync([{ key: 'a1', group: 'A' }, { key: 'b1', group: 'B' }]);
  s.sync([{ key: 'a1', group: 'A' }, { key: 'a2', group: 'A' }, { key: 'b1', group: 'B' }]);
  assert.deepEqual(s.snapshot().map((x) => x.key), ['a1', 'a2', 'b1']);
  assert.deepEqual(s.snapshot().map((x) => x.level), [null, 'term', 'group']);
  assert.deepEqual(s.snapshot().map((x) => x.op), [null, 'OR', 'AND']);
});

test('state: sync is idempotent', () => {
  const s = F.createState();
  const act = [{ key: 'a', group: 'A' }, { key: 'b', group: 'B' }];
  s.sync(act); s.setOp('group', 'B', 'OR'); s.sync(act); s.sync(act);
  assert.deepEqual(s.expr().ops, ['OR']);
});

test('state: removing a filter drops its operator; successor keeps its own', () => {
  const s = F.createState();
  s.sync([{ key: 'a', group: 'A' }, { key: 'b', group: 'B' }, { key: 'c', group: 'C' }]);
  s.setOp('group', 'B', 'OR');   // a OR b
  s.setOp('group', 'C', 'OR');   // b OR c
  s.setOp('group', 'C', 'AND');  // b AND c  (back to default)
  s.setOp('group', 'B', 'AND');  // a AND b
  s.setOp('group', 'C', 'OR');   // b OR c
  s.sync([{ key: 'a', group: 'A' }, { key: 'c', group: 'C' }]);   // remove b
  assert.deepEqual(s.expr().ops, ['OR']);         // c keeps ITS operator
  s.sync([{ key: 'a', group: 'A' }, { key: 'b', group: 'B' }, { key: 'c', group: 'C' }]);
  assert.deepEqual(s.snapshot().map((x) => x.key), ['a', 'c', 'b']);   // b is new → last
  assert.deepEqual(s.expr().ops, ['OR', 'AND']);  // b starts from the default
});

test('state: re-added filter starts from the default operator', () => {
  const s = F.createState();
  s.sync([{ key: 'a', group: 'A' }, { key: 'b', group: 'B' }]);
  s.setOp('group', 'B', 'OR');
  s.sync([{ key: 'a', group: 'A' }]);
  s.sync([{ key: 'a', group: 'A' }, { key: 'b', group: 'B' }]);
  assert.equal(s.getOp('group', 'B'), 'AND');
});

test('state: a new first element hides the old operator; clearing everything resets', () => {
  const s = F.createState();
  s.sync([{ key: 'a', group: 'A' }, { key: 'b', group: 'B' }]);
  s.setOp('group', 'B', 'OR');
  s.sync([{ key: 'b', group: 'B' }]);
  assert.equal(s.snapshot()[0].op, null);
  assert.deepEqual(s.expr().ops, []);
  s.sync([]);
  assert.deepEqual(s.expr(), { groups: [], ops: [] });
});

test('state: setOp rejects unknown operators and reports changes', () => {
  const s = F.createState();
  s.sync([{ key: 'a', group: 'A' }, { key: 'b', group: 'B' }]);
  assert.throws(() => s.setOp('group', 'B', 'XOR'));
  assert.equal(s.setOp('group', 'B', 'AND'), false);
  assert.equal(s.setOp('group', 'B', 'OR'), true);
});

test('has() only knows synced terms', () => {
  const s = F.createState();
  s.sync([{ key: 'a', group: 'A' }]);
  assert.equal(s.has('a'), true);
  assert.equal(s.has('z'), false);
});

test('force: replaces one group (facet counts)', () => {
  const e = expr([['n1', 'n2'], ['r']], ['AND']);
  const none = truth([]);
  assert.equal(F.evalExpr(e, truth(['r']), { force: { key: 'g0', value: true } }), true);
  assert.equal(F.evalExpr(e, none, { force: { key: 'g0', value: true } }), false);
  assert.equal(F.evalExpr(e, truth(['r']), { force: { key: 'g0', value: false } }), false);
  // under OR the unforced rest can still carry the record
  const eOr = expr([['n'], ['r']], ['OR']);
  assert.equal(F.evalExpr(eOr, truth(['r']), { force: { key: 'g0', value: false } }), true);
});

test('force: a group not in the expression is appended with AND', () => {
  const e = expr([['a']]);
  assert.equal(F.evalExpr(e, truth(['a']), { force: { key: 'new', value: true } }), true);
  assert.equal(F.evalExpr(e, truth([]), { force: { key: 'new', value: true } }), false);
  assert.equal(F.evalExpr(e, truth(['a']), { force: { key: 'new', value: false } }), false);
  const empty = { groups: [], ops: [] };
  assert.equal(F.evalExpr(empty, truth([]), { force: { key: 'new', value: true } }), true);
  assert.equal(F.evalExpr(empty, truth([]), { force: { key: 'new', value: false } }), false);
});

test('force with default operators equals the old "all other groups" rule', () => {
  const people = [];
  for (const n of ['sv', 'no', 'da']) for (const g of ['m', 'k']) for (const r of ['mus', 'mal'])
    people.push({ n, g, r });
  const s = F.createState();
  s.sync([{ key: 'n:sv', group: 'N' }, { key: 'g:m', group: 'G' }]);
  const e = s.expr();
  const val = (p) => (k) => ({ 'n:sv': p.n === 'sv', 'g:m': p.g === 'm' })[k];
  // old rule for group N = records passing every OTHER group (G)
  const old = people.filter((p) => p.g === 'm');
  const forced = people.filter((p) => F.evalExpr(e, val(p), { force: { key: 'N', value: true } }));
  assert.deepEqual(forced, old);
});

test('describe: explicit parentheses', () => {
  const s = F.createState();
  s.sync([{ key: 'sv', group: 'N' }, { key: 'no', group: 'N' }, { key: 'mus', group: 'R' }]);
  assert.equal(F.describe(s.expr()), '(sv OR no) AND mus');
  s.setOp('group', 'R', 'OR');
  assert.equal(F.describe(s.expr()), '(sv OR no) OR mus');
  const s2 = F.createState();
  s2.sync([{ key: 'a', group: 'A' }, { key: 'b', group: 'B' }, { key: 'c', group: 'C' }]);
  s2.setOp('group', 'B', 'OR');   // a OR b AND c
  assert.equal(F.describe(s2.expr()), 'a OR (b AND c)');
  s2.setOp('group', 'B', 'AND'); s2.setOp('group', 'C', 'OR');
  assert.equal(F.describe(s2.expr()), '(a AND b) OR c');
  assert.equal(F.describe({ groups: [], ops: [] }), '');
  assert.equal(F.describe(s2.expr(), (k) => k.toUpperCase()), '(A AND B) OR C');
});

test('registry: a new operator can be added without touching the evaluator', () => {
  F.registerOp('XOR', { prec: 1, fn: (a, b) => a !== b });
  assert.ok(F.opNames().includes('XOR'));
  const e = expr([['a'], ['b']], ['XOR']);
  assert.equal(F.evalExpr(e, truth(['a'])), true);
  assert.equal(F.evalExpr(e, truth(['a', 'b'])), false);
  delete F.OPS.XOR;
  assert.throws(() => F.evalExpr(e, truth(['a'])), /Unknown operator/);
});
