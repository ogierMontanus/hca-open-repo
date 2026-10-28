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


# ── stable ids (plan-tidstavle-data.md step 1.1) ──────────────────────────

def _sql_timeline_ids():
    import csv
    path = REPO / "data" / "normalized_v092" / "timeline.csv"
    with path.open(encoding="utf-8-sig", newline="") as f:
        return {r["event_id"] for r in csv.DictReader(f)}


def test_ids_have_the_stable_tv_form():
    for r in _rows():
        assert re.fullmatch(r"TV\d{2}\d{4}", r["id"]), r["id"]
        assert r["id"] == bt.entry_id(r["v"], int(r["id"][4:])), r["id"]


def test_ids_are_unique():
    ids = [r["id"] for r in _rows()]
    assert len(ids) == len(set(ids))


def test_ids_do_not_collide_with_the_sql_timeline():
    sql_ids = _sql_timeline_ids()
    assert len(sql_ids) == 1446 and all(i.startswith("T") and i[1:].isdigit() for i in sql_ids)
    clash = {r["id"] for r in _rows()} & sql_ids
    assert not clash, sorted(clash)[:5]


def test_id_does_not_depend_on_other_volumes():
    # Inserting a row in bind 1 must not renumber bind 2: the id is built from
    # the volume and the row *within* the sheet, never a running counter.
    assert bt.entry_id(2, 5) == "TV020005"
    assert bt.entry_id(10, 1234) == "TV101234"


def test_content_key_ignores_position_but_not_wording():
    k = bt.content_key("1845-11-01", "1845-11-10", "Glorup.")
    assert k == bt.content_key("1845-11-01", "1845-11-10", "  Glorup.  ")
    assert k == bt.content_key("1845-11-01", "1845-11-10", "Glorup.")
    assert k != bt.content_key("1845-11-01", "1845-11-10", "Glorup. Besøg.")
    assert k != bt.content_key("1845-11-01", "1845-11-11", "Glorup.")
    assert re.fullmatch(r"[0-9a-f]{12}", k)
    # an absent end date is part of the key, not an error
    assert bt.content_key("1845-11-01", None, "x") == bt.content_key("1845-11-01", "", "x")


def test_every_row_has_a_content_key_and_edits_change_it():
    rows = _rows()
    assert all(re.fullmatch(r"[0-9a-f]{12}", r["key"]) for r in rows)
    # distinct rows are (almost) always distinct content; the known identical
    # source duplicates (audit §2C) are the only allowed repeats.
    from collections import Counter
    repeats = sum(n - 1 for n in Counter(r["key"] for r in rows).values() if n > 1)
    assert repeats <= 5, repeats
