"""
Regression guard for mockup/data/diary-print/vol-*.js (cart PDF data) and
mockup/data/diary-refs-overflow.js.

Both are generated, gitignored build artifacts (see .gitignore), so the
properties worth protecting are asserted on the built output:

  1. Every diary page in DIARY_META (the build's page scope) has a
     print record (text markup + full name list), and nothing is lost to
     DIARY_REFS' per-entity cap: DIARY_REFS[e] + DIARY_REFS_OVERFLOW[e]
     always adds up to the entity's total `n`.
  2. A page with many register entries carries all of them in `e` (the
     DIARY_INDEX chips are cut to 3 -- that is exactly why the PDF needs
     its own data).

Skips (does not fail) when the artifacts have not been built.
"""
import json
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "mockup" / "data"
PRINT_DIR = DATA / "diary-print"
REFS = DATA / "diary-refs.js"
OVERFLOW = DATA / "diary-refs-overflow.js"


def _json_after(path, marker, opener, closer):
    """The JSON value that starts at the first `opener` after `marker`
    (raw_decode stops at its end, so later consts in the file are ignored)."""
    s = path.read_text(encoding="utf-8")
    return json.JSONDecoder().raw_decode(s, s.index(opener, s.index(marker)))[0]


def _print_records():
    recs = {}
    for f in sorted(PRINT_DIR.glob("vol-*.js")):
        s = f.read_text(encoding="utf-8")
        recs.update(json.loads(s[s.index("Object.assign(window.DIARY_PRINT, ") + 34: s.rindex(");")]))
    return recs


@pytest.fixture(scope="module")
def records():
    if not PRINT_DIR.exists():
        pytest.skip("diary-print not built (scripts/build_mockup/build_diary_print.py)")
    return _print_records()


def test_every_page_has_a_print_record(records):
    # DIARY_META is the build's page scope (stale local diary-pages/*.html
    # from older scopes can outnumber it, so don't count files).
    if not REFS.exists():
        pytest.skip("diary-refs not built")
    expected = set(_json_after(REFS, "const DIARY_META", "{", "}"))
    assert expected, "no diary pages in DIARY_META"
    assert not (expected - set(records)), sorted(expected - set(records))[:5]


def test_records_have_text_and_entities(records):
    with_text = sum(1 for r in records.values() if r["h"])
    assert with_text > 0.95 * len(records)
    for r in records.values():
        for t, rid, label in r["e"]:
            assert t in ("person", "place", "work") and rid.startswith("Reg") and label


def test_refs_plus_overflow_equal_total():
    if not (REFS.exists() and OVERFLOW.exists()):
        pytest.skip("diary-refs / overflow not built (build_diary_index.py)")
    refs = _json_after(REFS, "const DIARY_REFS", "{", "}")
    over = _json_after(OVERFLOW, "const DIARY_REFS_OVERFLOW", "{", "}")
    assert over, "expected some entities above the cap"
    for eid, rec in refs.items():
        assert len(rec["e"]) + len(over.get(eid, [])) == rec["n"], eid
