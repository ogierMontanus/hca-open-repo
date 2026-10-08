#!/usr/bin/env python3
"""
Scenario checks + seeded random "monkey" walk for the selection cart
(mockup/js/cart.js) across every page that touches it.

Not a pytest test (needs Playwright + a built mockup); run on demand:

    python scripts/qa/cart_monkey.py                      # scenarios + 300 steps, seed 1
    python scripts/qa/cart_monkey.py --steps 500 --seed 7
    python scripts/qa/cart_monkey.py --partition          # emulate per-directory storage

--partition emulates browsers (Firefox under file://) that give mockup/ and
mockup/diary-pages/ separate storage: an init script prefixes every Web
Storage key with the page's directory, so the cart only survives the jump
into/out of diary-pages/ through cart.js's window.name bridge.

Invariants checked after every step:
  I1  badge count == Cart.count() == items in the newest stored copy
  I2  no item with an empty `by`; every owner key named in a `by` is in the cart
  I3  every rendered cart checkbox (.result-card__select input) == Cart.has()
  I4  the cart count survives navigation (same tab, incl. diary-pages/)
  I5  no uncaught page errors
Exit code 1 on any violation.
"""
import argparse
import pathlib
import random
import sys

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[2] / "mockup"

PARTITION_JS = r"""
(() => {
  const dir = location.pathname.replace(/[^/]*$/, '');
  const P = Storage.prototype, g = P.getItem, s = P.setItem, r = P.removeItem;
  P.getItem = function (k) { return g.call(this, dir + '::' + k); };
  P.setItem = function (k, v) { return s.call(this, dir + '::' + k, v); };
  P.removeItem = function (k) { return r.call(this, dir + '::' + k); };
})();
"""

STATE_JS = r"""
() => {
  if (typeof Cart === 'undefined') return null;
  const items = Cart.all();
  const keys = new Set(items.map(i => i.type + '|' + i.rid));
  const problems = [];
  for (const it of items) {
    if (!it.by || !it.by.length) problems.push('empty by: ' + it.type + '|' + it.rid);
    else for (const o of it.by) if (o !== '*' && !keys.has(o)) problems.push('orphan owner ' + o + ' on ' + it.rid);
  }
  let stored = null;
  try { const v = JSON.parse(sessionStorage.getItem('hca-cart-v1') || 'null'); stored = v ? (Array.isArray(v) ? v.length : v.items.length) : 0; } catch (e) { stored = -1; }
  let named = null;
  try { named = (window.name || '').startsWith('hca-cart:') ? JSON.parse(window.name.slice(9)).items.length : null; } catch (e) { named = -1; }
  const badge = document.querySelector('#js-cart-badge .cart-badge__count');
  const badgeN = badge ? parseInt(badge.textContent, 10) : (document.querySelector('#js-cart-badge a') ? 0 : null);
  const boxes = [...document.querySelectorAll('.result-card__select input[data-cart-rid]')]
    .filter(cb => cb.offsetParent !== null)
    .filter(cb => cb.checked !== Cart.has(cb.dataset.cartType, cb.dataset.cartRid))
    .map(cb => cb.dataset.cartType + '|' + cb.dataset.cartRid);
  return { count: Cart.count(), stored, named, badge: badgeN, problems, badBoxes: boxes.slice(0, 5) };
}
"""

PAGES = [
    "persons.html", "persons_en.html", "places.html", "places_en.html",
    "bibliotek.html", "billedkunst.html", "teater-musik.html", "teater-musik_en.html",
    "diaries.html", "cart.html", "cart_en.html",
    "persons.html?reg=Reg0042200", "persons.html?reg=Reg0048690", "persons_en.html?reg=Reg0042200",
    "place.html?reg=Reg0017430", "place.html?reg=Reg0010590", "work.html?reg=Reg000476",
    "diary-pages/Pag020283.html", "diary-pages/Pag040246.html", "diary-pages/Pag100400.html",
]


def url(rel):
    path, _, q = rel.partition("?")
    return (ROOT / path).as_uri() + ("?" + q if q else "")


class Monkey:
    def __init__(self, page, rng, log):
        self.page, self.rng, self.log = page, rng, log
        self.errors = []
        self.violations = []
        page.on("pageerror", lambda e: self.errors.append(str(e)))
        page.on("dialog", self.on_dialog)
        self.accept_dialogs = True

    def on_dialog(self, d):
        try:
            (d.accept() if (d.type != "confirm" or self.accept_dialogs) else d.dismiss())
        except Exception:
            pass

    def state(self):
        try:
            return self.page.evaluate(STATE_JS)
        except Exception as e:  # navigation in flight
            return None

    def check(self, step, what, expect_count=None):
        st = self.state()
        if st is None:
            return
        v = []
        if st["stored"] not in (None, -1) and st["stored"] != st["count"]:
            v.append(f"I1 stored {st['stored']} != Cart.count {st['count']}")
        if st["badge"] is not None and st["badge"] != st["count"]:
            v.append(f"I1 badge {st['badge']} != Cart.count {st['count']}")
        if st["problems"]:
            v.append("I2 " + "; ".join(st["problems"][:3]))
        if st["badBoxes"]:
            v.append("I3 checkbox out of sync: " + ", ".join(st["badBoxes"]))
        if expect_count is not None and st["count"] != expect_count:
            v.append(f"I4 count {st['count']} after navigation, expected {expect_count}")
        if self.errors:
            v.append("I5 " + " | ".join(self.errors[:2]))
            self.errors.clear()
        for x in v:
            self.violations.append(f"step {step} [{what}] @ {self.page.url.split('/mockup/')[-1]}: {x}")
        return st

    def goto(self, rel):
        self.page.goto(url(rel))
        self.page.wait_for_load_state("load")
        self.page.wait_for_timeout(250)

    def visible(self, sel):
        return [h for h in self.page.query_selector_all(sel) if h.is_visible()]

    def step(self, i):
        rng, page = self.rng, self.page
        self.accept_dialogs = rng.random() < 0.75
        before = self.state()
        n_before = before["count"] if before else None
        roll = rng.random()
        what = ""
        nav = False
        try:
            if roll < 0.30:
                boxes = self.visible(".result-card__select input[data-cart-rid]")
                if boxes:
                    rng.choice(boxes[:80]).click()
                    what = "tick"
            elif roll < 0.40:
                b = self.visible(".cart-toggle-btn")
                if b:
                    b[0].click(); what = "toggle-btn"
            elif roll < 0.48:
                sa = self.visible("#js-select-all") + self.visible(".results-header__select-all input")
                if sa:
                    rng.choice(sa).click(); what = "select-all"
            elif roll < 0.56 and "cart" in page.url:
                rm = self.visible(".cart-item__remove")
                if rm:
                    rng.choice(rm).click(); what = "cart-remove"
                elif self.visible("#js-cart-download"):
                    page.evaluate("window.print = function(){}")
                    page.click("#js-cart-download"); page.wait_for_timeout(1200); what = "pdf"
            elif roll < 0.58 and "cart" in page.url and self.visible("#js-cart-clear"):
                page.click("#js-cart-clear"); what = "cart-clear"
            elif roll < 0.78:
                links = [a for a in self.visible("a[href]")
                         if (a.get_attribute("target") or "") != "_blank"
                         and not (a.get_attribute("href") or "").startswith(("http", "#", "mailto"))]
                if links:
                    rng.choice(links[:150]).click(); nav = True; what = "link"
            elif roll < 0.85:
                page.go_back(); nav = True; what = "back"
            else:
                self.goto(rng.choice(PAGES)); nav = True; what = "goto"
        except Exception as e:
            what = (what or "action") + " (skipped: " + str(e).splitlines()[0][:60] + ")"
        page.wait_for_timeout(200)
        if nav:
            try:
                page.wait_for_load_state("load")
                page.wait_for_timeout(250)
            except Exception:
                pass
        self.log(f"{i:4d} {what or 'noop'}")
        self.check(i, what, expect_count=n_before if (nav and n_before is not None) else None)


def scenarios(page, M):
    """Deterministic checks of the ownership rules (README for the bugs they guard)."""
    fails = []

    def ev(js, arg=None):
        return page.evaluate(js, arg) if arg is not None else page.evaluate(js)

    M.goto("persons.html")
    ev("sessionStorage.clear(); window.name=''")
    M.goto("persons.html")
    bremer, dickens = "Reg0042200", ev("Object.keys(PERSONS_EXTRA).find(k => /^Dickens, Charles/.test(PERSONS_EXTRA[k].label))")
    rel = lambda rid: ev("r => Cart.relatedFor('person', r).map(x => x.type + '|' + x.rid)", rid)
    rb, rd = set(rel(bremer)), set(rel(dickens))
    shared = rb & rd
    ev("([a,b]) => { Cart.selectBundles([{type:'person',rid:a,label:'B'}], true); Cart.selectBundles([{type:'person',rid:b,label:'D'}], true); }", [bremer, dickens])
    n_both = ev("Cart.count()")
    if n_both != len(rb | rd) + 2:
        fails.append(f"S1 bundle union: {n_both} != {len(rb | rd) + 2}")
    manual = sorted(rb - rd)[0].split("|")[1]
    ev("p => Cart.add('diary', p, 'manual')", manual)
    ev("r => Cart.remove('person', r)", bremer)
    keys = set(ev("Cart.all().map(i => i.type + '|' + i.rid)"))
    if not shared <= keys:
        fails.append("S2 shared pages lost when un-ticking Bremer")
    if ("diary|" + manual) not in keys:
        fails.append("S3 explicitly ticked page removed with Bremer")
    if (rb - rd - {"diary|" + manual}) & keys:
        fails.append("S4 Bremer-only pages left behind")
    ev("r => Cart.remove('person', r)", dickens)
    if ev("Cart.count()") != 1:
        fails.append(f"S5 expected only the manual page left, got {ev('Cart.count()')}")
    # List checkbox brings the bundle; badge follows into diary-pages/ and back.
    ev("Cart.clear()")
    M.goto("teater-musik.html")
    cb = M.visible(".result-card__select input[data-cart-type='work']")
    if cb:
        rid = cb[0].get_attribute("data-cart-rid")
        cb[0].click(); page.wait_for_timeout(200)
        n = ev("Cart.count()"); exp = 1 + ev("r => Cart.bundleSize('work', r)", rid)
        if n != exp:
            fails.append(f"S6 work list tick added {n}, expected bundle {exp}")
    n = ev("Cart.count()")
    M.goto("diary-pages/Pag040246.html")
    if ev("Cart.count()") != n:
        fails.append(f"S7 diary page sees {ev('Cart.count()')} != {n}")
    ev("Cart.add('diary','Pag040246','x')")
    n2 = ev("Cart.count()")
    M.goto("cart.html")
    if ev("Cart.count()") != n2:
        fails.append(f"S8 cart.html after diary page sees {ev('Cart.count()')} != {n2}")
    return fails


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--steps", type=int, default=300)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--partition", action="store_true")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()
    out = [] if a.quiet else None
    log = (lambda s: None) if a.quiet else print
    with sync_playwright() as p:
        b = p.chromium.launch()
        ctx = b.new_context()
        if a.partition:
            ctx.add_init_script(PARTITION_JS)
        page = ctx.new_page()
        M = Monkey(page, random.Random(a.seed), log)
        fails = scenarios(page, M)
        for f in fails:
            print("SCENARIO FAIL:", f)
        M.goto(M.rng.choice(PAGES))
        for i in range(a.steps):
            M.step(i)
        b.close()
    print(f"\nscenarios: {len(fails)} failed; monkey: {len(M.violations)} violations in {a.steps} steps "
          f"(seed {a.seed}{', partitioned storage' if a.partition else ''})")
    for v in M.violations[:40]:
        print("  ", v)
    sys.exit(1 if (fails or M.violations) else 0)


if __name__ == "__main__":
    main()
