"""Guards for the Tidstavle companion track (scripts/build_mockup/build_timeline.py).

Reads only committed inputs (data/HCA_Tidstavler_*.xlsx, data/normalized/*.csv),
so it runs everywhere without the generated mockup/data/*.js files.
"""
import re
import sys
from pathlib import Path

REPO = Path(__file__).parent.parent
sys.path.insert(0, str(REPO / "scripts" / "build_mockup"))

import build_timeline as bt  # noqa: E402

ISO = re.compile(r"^\d{4}-\d\d-\d\d$")


def _rows():
    return bt.read_workbook(bt.find_workbook())


def test_every_row_parses_to_a_valid_iso_range():
    rows = _rows()
    assert len(rows) == 1745
    for r in rows:
        assert ISO.match(r["a"]) and ISO.match(r["b"]), r
        assert r["a"] <= r["b"], r
        assert r["pa"] in "dmy" and r["pb"] in "dmy", r


def test_invalid_printed_date_is_clamped_and_flagged():
    # The printed timeline has "29. februar 1841" (1841 was not a leap year).
    hit = [r for r in _rows() if "ugyldig" in r["q"]]
    assert len(hit) == 1
    assert hit[0]["a"] == "1841-02-28"


def test_note_parsing_keeps_page_url_and_original_date():
    pages, url, orig, note = bt.parse_note(
        "Bind 3, s. XIII: https://epub3.kb.dk/x.xhtml\n\nOriginal datoangivelse: 7.4.")
    assert pages == ["XIII"] and url.endswith("x.xhtml")
    assert orig == "7.4." and note is None
    # intro-prose rows carry no original date
    _, _, orig, note = bt.parse_note(
        "Bind 1, s. XXXI: https://epub3.kb.dk/y.xhtml\n\n"
        "Original datoangivelse: Indledende prosatekst\n\nKort gengivelse.")
    assert orig is None and note == "Kort gengivelse."


def test_linking_is_conservative_and_resolves_against_the_register():
    m = bt.Matcher()
    segs = m.link("Berlin. Jenny Lind. Besøg hos Hertz.", 3, 1845)
    linked = {s[0]: s[1] for s in segs if isinstance(s, list)}
    assert linked.get("Berlin") == "p"
    assert linked.get("Jenny Lind") == "s"
    # every linked id exists in the register
    ids = set(m.persons) | set(m.places) | set(m.works)
    assert all(s[2] in ids for s in segs if isinstance(s, list))


def test_author_himself_is_never_linked():
    # "Andersen, Hans Christian" in the register is a photographer from
    # Nykøbing Mors, not the author the whole timeline is about.
    m = bt.Matcher()
    for text in ("H. C. Andersen besøger Weimar.", "Hans Christian Andersens fødselsdag."):
        segs = m.link(text, 3, 1845)
        assert not any(isinstance(s, list) and s[1] == "s" and "Andersen" in s[0] for s in segs)


def test_bare_first_names_and_genitives_stay_unlinked():
    m = bt.Matcher()
    segs = m.link("Carl kom og Italiens nationaldag.", 5, 1861)
    assert not any(isinstance(s, list) for s in segs)
