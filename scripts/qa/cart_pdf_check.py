#!/usr/bin/env python3
"""
End-to-end check of the cart's in-browser PDF export (mockup/js/cart-pdf.js).

Not a pytest test (needs Playwright, pypdf, a built mockup incl.
mockup/data/diary-print/); run on demand:

    python scripts/qa/cart_pdf_check.py
    python scripts/qa/cart_pdf_check.py --pages 600     # also time a bigger cart

Fills the cart, clicks "Download som PDF" / "Download as PDF" and inspects the
downloaded file. Scenarios:

  worker       diary pages + register entries, generated in the Web Worker
  no-worker    same cart with window.Worker removed -> main-thread fallback
  english      cart_en.html (English labels, English detail-page links)
  register     register entries only (no diary pages)

Checks per scenario: the download happens, no page errors, the file has the
cover + at least one sheet per diary page + the appendix, expected text and
link annotations (to the right page), and -- for the worker scenarios -- that
the page stayed responsive while the PDF was being made (longest timer gap).
Exit code 1 on any failure.
"""
import argparse
import pathlib
import sys
import tempfile

from playwright.sync_api import sync_playwright

try:
    from pypdf import PdfReader
except ImportError:
    sys.exit("pypdf is required:  pip install pypdf")

ROOT = pathlib.Path(__file__).resolve().parents[2] / "mockup"

GAP_JS = """
() => { window.__gap = 0; let last = performance.now();
  window.__iv = setInterval(() => { const n = performance.now(); window.__gap = Math.max(window.__gap, n - last); last = n; }, 20); }
"""


def diary_items(n):
    out = []
    for vol in range(1, 11):
        for pg in range(1, 521):
            if len(out) >= n:
                return out
            out.append({"type": "diary", "rid": f"Pag{vol:02d}{pg:04d}", "label": "x", "by": ["*"]})
    return out


def register_items(n):
    return [{"type": ("person", "place", "work")[i % 3], "rid": f"Reg{39110 + i:07d}",
             "label": f"Black, Andreas (1819–1892) {i}", "by": ["*"]} for i in range(n)]


def run(browser, name, page_file, diaries, register, no_worker, workdir):
    ctx = browser.new_context(accept_downloads=True)
    page = ctx.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    if no_worker:
        page.add_init_script("window.Worker = undefined;")
    page.goto((ROOT / page_file).as_uri())
    items = diary_items(diaries) + register_items(register)
    page.evaluate("items => sessionStorage.setItem('hca-cart-v1', JSON.stringify({t: Date.now(), items}))", items)
    page.reload()
    page.evaluate(GAP_JS)
    with page.expect_download(timeout=600_000) as dl:
        page.click("#js-cart-download")
    path = workdir / f"{name}.pdf"
    dl.value.save_as(str(path))
    gap = page.evaluate("window.__gap")
    ctx.close()

    problems = []
    r = PdfReader(str(path))
    n_pages = len(r.pages)
    first = r.pages[0].extract_text()
    uris = [a.get_object()["/A"]["/URI"] for pg in r.pages for a in (pg.get("/Annots") or [])
            if "/A" in a.get_object() and "/URI" in a.get_object()["/A"]]
    en = page_file.endswith("_en.html")
    want_cover = "SELECTED DIARY PAGES" if en else "VALGTE DAGBOGSSIDER"
    if want_cover not in first:
        problems.append(f"cover lacks {want_cover!r}")
    if n_pages < 1 + diaries + (1 if register else 0):
        problems.append(f"{n_pages} pages for {diaries} diary pages + {register} register entries")
    if diaries and not any("diary-pages/Pag" in u for u in uris):
        problems.append("no link to a diary page")
    if register and not any("?reg=Reg" in u for u in uris):
        problems.append("no link to a register entry")
    if register:
        if not any(("persons_en.html" if en else "persons.html") in u for u in uris):
            problems.append("person links do not point at this language's page")
    head = "".join(pg.extract_text() for pg in r.pages[:3])
    if diaries and ("Volume I, page 1" if en else "Bind I, side 1") not in head:
        problems.append("first sheet title missing")
    if not no_worker and gap > 1000:
        problems.append(f"page froze for {gap:.0f} ms")
    if errors:
        problems.append("page errors: " + " | ".join(errors[:2]))
    size = path.stat().st_size / 1e6
    print(f"{'FAIL' if problems else 'ok  '} {name:10s} {n_pages:5d} pages  {size:6.1f} MB  {len(uris):6d} links  "
          f"longest freeze {gap:5.0f} ms  {dl.value.suggested_filename}")
    for p_ in problems:
        print("     -", p_)
    return not problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", type=int, default=0, help="also time a worker run with this many diary pages")
    args = ap.parse_args()
    if not (ROOT / "data" / "diary-print").exists():
        sys.exit("diary-print not built: python scripts/build_mockup/build_diary_print.py")

    ok = True
    with tempfile.TemporaryDirectory() as td, sync_playwright() as pw:
        wd = pathlib.Path(td)
        browser = pw.chromium.launch()
        ok &= run(browser, "worker", "cart.html", 30, 40, False, wd)
        ok &= run(browser, "no-worker", "cart.html", 30, 40, True, wd)
        ok &= run(browser, "english", "cart_en.html", 30, 40, False, wd)
        ok &= run(browser, "register", "cart.html", 0, 40, False, wd)
        if args.pages:
            ok &= run(browser, f"{args.pages}-pages", "cart.html", args.pages, 0, False, wd)
        browser.close()
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
