/* filter-logic.js — boolean combination of active filters (AND / OR).
 *
 * One small, DOM-free module shared by every filtering page, so that the
 * operators the reader sees between the active-filter chips
 * (js/active-filters.js) and the rule that actually decides which records
 * match (js/facet-engine.js, js/category-catalogue.js) come from the SAME
 * object and cannot drift apart. Documented in docs/filter-logic.md.
 *
 * ── Model ─────────────────────────────────────────────────────────────────
 *
 * Every ticked facet value (and every non-empty year range) is a TERM.
 * Terms of the same facet form a GROUP, and a group behaves as if
 * parenthesised: it is evaluated first, then the groups are combined.
 *
 *   expr = { groups: [ { key, terms: [{key}, …], ops: [op, …] }, … ],
 *            ops:    [op, …] }
 *
 * ops[i] is the operator between element i and element i+1 at that level.
 * Defaults: OR between two values of the same facet (what the register did
 * before operators existed), AND between two different facets. With nothing
 * but defaults the result is therefore identical to the old rule
 * "OR inside a group, AND between groups".
 *
 * ── Evaluation (unambiguous) ──────────────────────────────────────────────
 *
 * On each level (inside a group, then between groups) a flat list
 * `a op1 b op2 c …` is read with the usual boolean precedence: AND binds
 * tighter than OR, equal operators associate left to right.
 *
 *   A OR  B AND C   =  A OR (B AND C)
 *   A AND B OR  C   =  (A AND B) OR C
 *
 * describe() prints the expression with explicit parentheses, so the
 * reader can see exactly what is being evaluated.
 *
 * ── Extending ─────────────────────────────────────────────────────────────
 *
 * Operators live in a registry (registerOp). A new binary operator is one
 * registry entry; deeper nesting would be a further level of `groups`.
 *
 * Works as a plain <script> (window.HcaFilter) and under Node (require).
 */
(function (root, factory) {
  var api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.HcaFilter = api;
})(typeof window !== 'undefined' ? window : this, function () {
  'use strict';

  /* ── Operator registry ──────────────────────────────────────────────── */

  var OPS = {
    AND: { prec: 2, fn: function (a, b) { return a && b; } },
    OR:  { prec: 1, fn: function (a, b) { return a || b; } }
  };

  // Which operator a new connection starts with, per level.
  var DEFAULT_OP = { term: 'OR', group: 'AND' };

  function registerOp(name, def) {
    if (!name || !def || typeof def.fn !== 'function' || typeof def.prec !== 'number') {
      throw new Error('registerOp: need a name and { prec: number, fn: function }');
    }
    OPS[name] = { prec: def.prec, fn: def.fn };
  }

  function opNames() { return Object.keys(OPS); }

  function opDef(name) {
    var d = OPS[name];
    if (!d) throw new Error('Unknown operator: ' + name);
    return d;
  }

  /* ── Reduction (precedence, left-associative) ───────────────────────── */

  // values[i] and values[i+1] are joined by ops[i]. `combine(op, a, b)`
  // builds the result — a boolean when evaluating, a tree when printing.
  function reduceWith(values, ops, combine) {
    if (!values.length) return undefined;
    var out = [values[0]], stack = [];
    function applyTop() {
      var op = stack.pop();
      var b = out.pop(), a = out.pop();
      out.push(combine(op, a, b));
    }
    for (var i = 1; i < values.length; i++) {
      var op = ops[i - 1];
      var prec = opDef(op).prec;
      while (stack.length && opDef(stack[stack.length - 1]).prec >= prec) applyTop();
      stack.push(op);
      out.push(values[i]);
    }
    while (stack.length) applyTop();
    return out[0];
  }

  function evalCombine(op, a, b) { return opDef(op).fn(a, b); }

  /* ── Evaluating an expression ───────────────────────────────────────── */

  function hasGroup(expr, key) {
    for (var g = 0; g < expr.groups.length; g++) {
      if (expr.groups[g].key === key) return true;
    }
    return false;
  }

  // Does the record match? `test(termKey)` answers for ONE term.
  //
  // opts.force = { key, value } overrides the truth of the group `key` — used
  // for facet counts ("how many records if this facet's value were X").
  // Forcing a group that is not in the expression treats it as a new group
  // joined with AND: result = base AND value.
  function evalExpr(expr, test, opts) {
    var force = opts && opts.force;
    var gv = [], g, t;
    for (g = 0; g < expr.groups.length; g++) {
      var grp = expr.groups[g];
      if (force && grp.key === force.key) { gv.push(!!force.value); continue; }
      var tv = new Array(grp.terms.length);
      for (t = 0; t < grp.terms.length; t++) tv[t] = !!test(grp.terms[t].key);
      gv.push(reduceWith(tv, grp.ops, evalCombine));
    }
    var base = gv.length ? reduceWith(gv, expr.ops, evalCombine) : true;
    if (force && !hasGroup(expr, force.key)) return !!force.value && base;
    return base;
  }

  /* ── Printing ───────────────────────────────────────────────────────── */

  function node(op, l, r) { return { op: op, prec: opDef(op).prec, l: l, r: r }; }

  function print(n) {
    if (n.s !== undefined) return n.s;
    return wrap(n.l, n) + ' ' + n.op + ' ' + wrap(n.r, n);
  }

  function wrap(child, parent) {
    if (child.s !== undefined) return child.s;
    // Parenthesise whenever the operator changes, even where precedence alone
    // would make it unambiguous: the point is that nobody has to know the rule.
    return child.op !== parent.op ? '(' + print(child) + ')' : print(child);
  }

  // Text form of the expression with explicit parentheses, e.g.
  //   (Svensk OR Norsk) AND Musiker
  function describe(expr, labelOf) {
    labelOf = labelOf || function (k) { return k; };
    var several = expr.groups.length > 1;
    var leaves = expr.groups.map(function (g) {
      var leafs = g.terms.map(function (t) { return { s: String(labelOf(t.key)) }; });
      var s = print(reduceWith(leafs, g.ops, node));
      return { s: several && g.terms.length > 1 ? '(' + s + ')' : s };
    });
    return leaves.length ? print(reduceWith(leaves, expr.ops, node)) : '';
  }

  /* ── Selection state (order + operators) ────────────────────────────── */

  // Remembers in which order the reader picked the filters and which
  // operator joins each pair. Operators are stored on the LATER element of
  // a pair ("the operator before me"):
  //   – removing an element deletes its own operator; its successor keeps
  //     the operator it had;
  //   – an element that becomes first simply stops showing its operator;
  //   – re-adding a removed filter starts from the default again.
  function createState() {
    var groups = [];     // [{ key, terms: [termKey, …] }]
    var opBefore = {};   // 'term:<termKey>' | 'group:<groupKey>' → operator

    function getOp(level, key) { return opBefore[level + ':' + key] || DEFAULT_OP[level]; }

    // `active` = every term that is currently selected, in document order:
    // [{ key, group }]. Safe to call repeatedly with the same set.
    function sync(active) {
      var present = {}, i, g;
      for (i = 0; i < active.length; i++) present[active[i].key] = active[i].group;

      for (g = groups.length - 1; g >= 0; g--) {
        var kept = [];
        for (i = 0; i < groups[g].terms.length; i++) {
          var k = groups[g].terms[i];
          if (present[k] === groups[g].key) kept.push(k);
          else delete opBefore['term:' + k];
        }
        groups[g].terms = kept;
        if (!kept.length) {
          delete opBefore['group:' + groups[g].key];
          groups.splice(g, 1);
        }
      }

      var known = {};
      groups.forEach(function (grp) { grp.terms.forEach(function (k) { known[k] = true; }); });
      active.forEach(function (a) {
        if (known[a.key]) return;
        known[a.key] = true;
        var grp = null;
        for (var j = 0; j < groups.length; j++) if (groups[j].key === a.group) { grp = groups[j]; break; }
        if (!grp) { grp = { key: a.group, terms: [] }; groups.push(grp); }
        grp.terms.push(a.key);
      });
    }

    function has(termKey) {
      for (var g = 0; g < groups.length; g++) {
        if (groups[g].terms.indexOf(termKey) !== -1) return true;
      }
      return false;
    }

    function expr() {
      var out = { groups: [], ops: [] };
      groups.forEach(function (grp, gi) {
        if (gi > 0) out.ops.push(getOp('group', grp.key));
        out.groups.push({
          key: grp.key,
          terms: grp.terms.map(function (k) { return { key: k }; }),
          ops: grp.terms.slice(1).map(function (k) { return getOp('term', k); })
        });
      });
      return out;
    }

    // Flat, ordered list for the chip bar. `op` is the operator BEFORE the
    // chip (null for the very first); `level` + `opKey` say how to change it.
    function snapshot() {
      var out = [];
      groups.forEach(function (grp, gi) {
        grp.terms.forEach(function (k, ti) {
          var level = null, opKey = null, op = null;
          if (ti > 0) { level = 'term'; opKey = k; op = getOp('term', k); }
          else if (gi > 0) { level = 'group'; opKey = grp.key; op = getOp('group', grp.key); }
          out.push({ key: k, group: grp.key, level: level, opKey: opKey, op: op });
        });
      });
      return out;
    }

    function setOp(level, key, op) {
      opDef(op);
      if (level !== 'term' && level !== 'group') throw new Error('Unknown level: ' + level);
      var before = getOp(level, key);
      if (op === DEFAULT_OP[level]) delete opBefore[level + ':' + key];
      else opBefore[level + ':' + key] = op;
      return before !== op;
    }

    function reset() { groups = []; opBefore = {}; }

    return { sync: sync, has: has, expr: expr, snapshot: snapshot, setOp: setOp, getOp: getOp, reset: reset };
  }

  /* ── DOM helpers (only touched from the browser) ────────────────────── */

  var KEY_ATTRS = ['data-facet', 'data-match', 'data-facet-empty',
                   'data-h2', 'data-h3', 'data-author', 'data-rid', 'data-place'];

  function groupKeyOf(el) {
    var grp = el.closest('.facet-group');
    if (!grp) return null;
    var panel = grp.closest('.facet-panel');
    var all = panel ? panel.querySelectorAll('.facet-group') : [];
    for (var i = 0; i < all.length; i++) if (all[i] === grp) return 'g' + i;
    return 'g?';
  }

  // Stable identity of one ticked checkbox: its group + its predicate.
  function termKeyOfBox(box) {
    var parts = [groupKeyOf(box)];
    for (var i = 0; i < KEY_ATTRS.length; i++) {
      if (box.hasAttribute(KEY_ATTRS[i])) parts.push(KEY_ATTRS[i].slice(5) + '=' + box.getAttribute(KEY_ATTRS[i]));
    }
    return parts.join('|');
  }

  // Identity of a year-range term (the host carries data-facet-range).
  function termKeyOfRange(host) {
    return groupKeyOf(host) + '|range=' + host.getAttribute('data-facet-range');
  }

  return {
    OPS: OPS,
    DEFAULT_OP: DEFAULT_OP,
    registerOp: registerOp,
    opNames: opNames,
    reduceWith: reduceWith,
    evalExpr: evalExpr,
    hasGroup: hasGroup,
    describe: describe,
    createState: createState,
    groupKeyOf: groupKeyOf,
    termKeyOfBox: termKeyOfBox,
    termKeyOfRange: termKeyOfRange,
    // One selection state per page: the engine writes it, the chip bar
    // reads and edits it.
    shared: createState()
  };
});
