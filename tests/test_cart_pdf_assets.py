"""
Guards for the cart's in-browser PDF export (mockup/js/cart-pdf.js).

  1. mockup/vendor/pdfmake/pdf-assets.js (the library source + fonts as
     strings for the PDF worker) is in sync with the pdfmake build it is
     generated from -- i.e. build_pdf_assets.py was re-run after a bump.
  2. The embedded fonts cover every character the diaries and register use
     (the one known gap, the pound sign U+2114, is substituted in
     cart-pdf.js). A character outside the subset would print as an empty box.
  3. The edition markup only uses tags cart-pdf.js's parser understands. An
     unknown block tag would silently flatten into running text.

(2) and (3) need the generated diary-print data and skip when it has not been
built (scripts/build_mockup/build_diary_print.py); (2) also needs fontTools.
"""
import base64
import io
import json
import pathlib
import re

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
ASSETS = ROOT / "mockup" / "vendor" / "pdfmake" / "pdf-assets.js"
PDFMAKE = ROOT / "scripts" / "build_mockup" / "vendor" / "pdfmake.min.js"
PRINT_DIR = ROOT / "mockup" / "data" / "diary-print"

FACES = {
    "LiberationSerif-Regular.ttf", "LiberationSerif-Italic.ttf",
    "LiberationSerif-Bold.ttf", "LiberationSerif-BoldItalic.ttf",
    "LiberationSans-Regular.ttf", "LiberationSans-Bold.ttf",
}
# cart-pdf.js: clean() replaces these before they reach the fonts.
SUBSTITUTED = {"℔"}
# cart-pdf.js: parseMarkup() handles exactly these.
KNOWN_TAGS = {"div", "i", "br", "aside", "figure", "figcaption", "span", "ul", "li", "table", "tr", "td"}


def _assets():
    s = ASSETS.read_text(encoding="utf-8")
    dec = json.JSONDecoder()
    out = {}
    for name in ("HCA_PDFMAKE_SRC", "HCA_PDF_FONTS"):
        marker = f"window.{name} = "
        out[name] = dec.raw_decode(s, s.index(marker) + len(marker))[0]
    return out


def _print_records():
    recs = {}
    for f in sorted(PRINT_DIR.glob("vol-*.js")):
        s = f.read_text(encoding="utf-8")
        recs.update(json.loads(s[s.index("Object.assign(window.DIARY_PRINT, ") + 34: s.rindex(");")]))
    return recs


def test_assets_in_sync_with_pdfmake_build():
    a = _assets()
    assert a["HCA_PDFMAKE_SRC"] == PDFMAKE.read_text(encoding="utf-8"), (
        "pdf-assets.js is stale: run python scripts/build_mockup/build_pdf_assets.py")
    assert set(a["HCA_PDF_FONTS"]) == FACES


def test_fonts_cover_the_corpus():
    ttlib = pytest.importorskip("fontTools.ttLib")
    if not PRINT_DIR.exists():
        pytest.skip("diary-print not built (scripts/build_mockup/build_diary_print.py)")
    fonts = _assets()["HCA_PDF_FONTS"]
    cmaps = {n: ttlib.TTFont(io.BytesIO(base64.b64decode(b))).getBestCmap() for n, b in fonts.items()}

    chars = set()
    for rec in _print_records().values():
        chars |= set(re.sub(r"<[^>]*>", "", rec["h"] or ""))
        for _type, _rid, label in rec["e"]:
            chars |= set(label)
    chars -= {"\n", "\r", "\t"} | SUBSTITUTED

    for name, cmap in cmaps.items():
        missing = sorted(c for c in chars if ord(c) not in cmap)
        assert not missing, f"{name} lacks {[(c, hex(ord(c))) for c in missing]}: widen UNICODES in build_pdf_assets.py or substitute in cart-pdf.js clean()"


def test_markup_uses_only_known_tags():
    if not PRINT_DIR.exists():
        pytest.skip("diary-print not built (scripts/build_mockup/build_diary_print.py)")
    seen = set()
    for rec in _print_records().values():
        seen |= {t.lower() for t in re.findall(r"<([a-zA-Z][a-zA-Z0-9]*)", rec["h"] or "")}
    assert seen <= KNOWN_TAGS, f"unhandled tags {sorted(seen - KNOWN_TAGS)}: teach parseMarkup() in cart-pdf.js"
