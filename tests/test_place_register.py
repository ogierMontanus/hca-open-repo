"""
Guards for the place-register base (data/HCA_Steder_GÆLDENDE_*_LocationID_*.xlsx).

The workbook is the base of the STED-REGISTER since 2026-10-21; its
LocationIDs (LOC…) replaced the V0.82 Reg… ids for places in
data/normalized/{entities,references,places}.csv. See
scripts/normalization/place_register.py and
docs/data-model/place-register-gaeldende.md.

What is protected:
  1. the workbook parses (unique LOC ids, every Category mapped to the UI's
     English vocabulary, plausible row count);
  2. the committed normalized CSVs really are built from it — same ids, no
     leftover Reg… place rows, no orphan place references;
  3. the first-page rule (Book/PageRef is always among a place's pages).
"""
import csv
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "normalization"))
import place_register  # noqa: E402

NORMALIZED = ROOT / "data" / "normalized"


@pytest.fixture(scope="module")
def places():
    if place_register.find_place_xlsx(required=False) is None:
        pytest.skip("place-register workbook not present")
    return place_register.load_places()


def _rows(name):
    with (NORMALIZED / name).open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def test_workbook_parses(places):
    assert 2_000 < len(places) < 4_000
    ids = [p["entity_id"] for p in places]
    assert len(ids) == len(set(ids))
    assert ids == sorted(ids, key=lambda i: int(i[3:])), "register order = ascending LocationID"
    assert all(p["label"] for p in places)


def test_every_category_is_mapped(places):
    assert not place_register.unmapped_categories(places), (
        "new Category value in the place workbook — add it to CATEGORY_DA_TO_EN "
        "and to CATEGORY_LABELS_DA in mockup/places.html + kort.html")


def test_normalized_places_are_the_workbook(places):
    ents = [e for e in _rows("entities.csv") if e["entity_type"] == "place"]
    assert [e["entity_id"] for e in ents] == [p["entity_id"] for p in places]
    assert not any(e["entity_id"].startswith("Reg") for e in ents)
    # place.html prints `description` as prose — it must stay empty for places
    assert not any(e["description"] for e in ents)
    assert [r["entity_id"] for r in _rows("places.csv")] == [p["entity_id"] for p in places]


def test_place_references_only_point_at_register_places(places):
    ids = {p["entity_id"] for p in places}
    ents = {e["entity_id"] for e in _rows("entities.csv")}
    refs = _rows("references.csv")
    place_refs = [r for r in refs if r["entity_id"].startswith("LOC")]
    assert place_refs
    assert {r["entity_id"] for r in place_refs} <= ids
    assert all(r["entity_id"] in ents for r in refs), "orphan reference"
    assert len({r["page_id"] for r in refs}) == len(refs), "page_id must stay a unique row key"


def test_first_page_is_always_a_page_of_the_place(places):
    by_place = {}
    for r in _rows("references.csv"):
        if r["entity_id"].startswith("LOC"):
            by_place.setdefault(r["entity_id"], set()).add((r["vol"], r["page"]))
    for p in places:
        if p["book"] and p["page"]:
            first = (place_register.ROMAN[p["book"]], str(p["page"]))
            assert first in by_place.get(p["entity_id"], set()), (p["entity_id"], p["label"], first)


def test_merge_pages_replaces_corrected_first_page():
    place = {"book": 3, "page": 177}
    pages, corrected = place_register.merge_pages(place, [("II", "177")])
    assert corrected and pages == [("III", "177")]
    pages, corrected = place_register.merge_pages(place, [("III", "177"), ("IV", "5")])
    assert not corrected and pages == [("III", "177"), ("IV", "5")]
