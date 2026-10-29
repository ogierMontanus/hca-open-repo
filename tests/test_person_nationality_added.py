"""
Guards the ADDED nationality value «Dansk*» (docs/plan-lex-dk-links.md §3d).

User decision 2026-10-29: "unmarked" is not "Danish". A person gets «Dansk*» (born in Denmark or
resident there for many years) beyond the register's own explicit «dansk» ONLY with a confirmed
Dansk Biografisk Leksikon article, and the value is stored as added data (data/curated/
person_nationality_added.csv), never mixed into the register's own descriptors.

Skips when the curated file has not been built.
"""
import csv
import importlib.util
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
ADDED = ROOT / "data" / "curated" / "person_nationality_added.csv"
ENTITIES = ROOT / "data" / "normalized" / "entities.csv"

pytestmark = pytest.mark.skipif(not ADDED.exists(), reason="person_nationality_added.csv not built")


@pytest.fixture(scope="module")
def rows():
    with open(ADDED, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def test_rows_are_dbl_confirmed_danish(rows):
    assert rows, "empty file"
    for r in rows:
        assert r["nationality_key"] == "dansk", r
        assert r["nat_basis"] == "dbl_optagelse", r
        assert r["source_url"].startswith("https://biografiskleksikon.lex.dk/"), r


def test_no_duplicate_person_or_shared_article(rows):
    rids = [r["rid"] for r in rows]
    assert len(rids) == len(set(rids))
    # one DBL article belongs to ONE register person — except a reviewed alias (the same person under a
    # second register entry, e.g. maiden name), which must name the entry that holds the article
    by_url = {}
    for r in rows:
        by_url.setdefault(r["source_url"], []).append(r)
    for url, rs in by_url.items():
        if len(rs) > 1:
            owners = {r["rid"] for r in rs if not r["alias_of"]}
            assert len(owners) == 1, f"{url} claimed by several register persons: {[r['rid'] for r in rs]}"
            assert all(r["alias_of"] in owners and r["confirmed_by"] == "manual_review" for r in rs if r["alias_of"])


def test_manual_review_rows_are_traceable(rows):
    decisions = ROOT / "data" / "curated" / "lex" / "dbl_review_decisions.csv"
    if not decisions.exists():
        pytest.skip("no review decisions")
    with open(decisions, encoding="utf-8", newline="") as f:
        acc = {d["rid"] for d in csv.DictReader(f) if d["decision"] in ("accept", "accept_alias")}
    assert {r["rid"] for r in rows if r["confirmed_by"] == "manual_review"} == acc


def test_rids_exist_as_persons(rows):
    with open(ENTITIES, encoding="utf-8", newline="") as f:
        persons = {r["entity_id"] for r in csv.DictReader(f) if r["entity_type"] == "person"}
    assert {r["rid"] for r in rows} <= persons


def test_builder_applies_star_and_note(rows):
    sys.path.insert(0, str(ROOT / "scripts" / "build_mockup"))   # sibling import _diary_scope
    spec = importlib.util.spec_from_file_location(
        "build_persons_extra", ROOT / "scripts" / "build_mockup" / "build_persons_extra.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules.setdefault("build_persons_extra", mod)
    spec.loader.exec_module(mod)
    by_person, labels = mod.load_nationalities()
    assert labels["dansk"] == "Dansk*"
    assert "Danmark" in mod.DANSK_NOTE_DA and "længere årrække" in mod.DANSK_NOTE_DA
    missing = [r["rid"] for r in rows if "dansk" not in by_person.get(r["rid"], [])]
    assert not missing, f"added persons missing from the facet: {missing[:5]}"
