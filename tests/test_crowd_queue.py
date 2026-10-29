"""The classification behind the crowdsourcing work queue
(scripts/build_mockup/build_crowd_queue.py, docs/crowdsourcing.md §2)."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "build_mockup"))
sys.path.insert(0, str(ROOT / "scripts" / "crowdsource"))
import build_crowd_queue as q  # noqa: E402
import taxonomy as tx  # noqa: E402

UNCAT = "Endnu ukategoriseret/Uden for kategori/Intet kendt lønnet erhverv"


@pytest.mark.parametrize("label,expect", [
    ("Aabye, Johan Peter (1818–1880)", (True, True)),
    ("Absalon (ca. 1128–1201)", (True, True)),
    ("Mohrenheim, Louise von, f. von Korff (1835–?)", (True, False)),
    ("Este, Eleonora, Prinsesse af – (1535–?)", (True, False)),
    ("Alexander III (død 1181)", (False, True)),
    ("Lyell, Mary, Lady, f. Horner (død 1873)", (False, True)),
    ("Bernhard, X (f. 1812)", (True, False)),
    ("Augustus, Julius Cæsar Octavianus (63 f.Chr.-14 e.Chr.)", (True, True)),
    ("Aaberg", (False, False)),
    ("Warberg (Vahrberg), Casten Adolf (1785–1868)", (True, True)),
])
def test_life_flags(label, expect):
    assert q.life_flags(label) == expect


@pytest.mark.parametrize("label,expect", [
    ("Aabye, Johan Peter (1818–1880)", "full"),
    ("Aagaard, C.F. (1833–1895)", "initials"),
    ("Agerskov, A. J. H. (1811–1872)", "initials"),
    ("Bushby, Mrs. Anne S. (død 1875)", "full"),
    ("Bushby, Mr.", "initials"),
    ("Absalon (ca. 1128–1201)", "mono"),
    ("Aaberg", "none"),
    ("Collin, Jonas d.Æ. (1776–1861)", "full"),
    ("Warberg (Vahrberg), Casten Adolf (1785–1868)", "full"),
])
def test_given_name_state(label, expect):
    assert q.given_name_state(label) == expect


def _c(label, desc, **kw):
    base = dict(n_mentions=1, roles=[], nationalities=[], gender=None, uncategorised=UNCAT)
    base.update(kw)
    return q.classify(label, desc, **base)


def test_levels_count_the_three_anchors():
    full = _c("Aabye, Johan Peter (1818–1880)", "Distriktslæge i Flensborg 1858–1864.")
    assert (full["level"], full["anchors"]) == ("dokumenteret", 3)
    partly = _c("Abbott, John", "Engelsk Ingeniør i Indien.")
    assert (partly["level"], partly["anchors"]) == ("delvist", 2)
    fragment = _c("Åberg", "Svensk rejsende, Italien 1834.")
    assert (fragment["level"], fragment["anchors"]) == ("fragmentarisk", 1)
    bare = _c("Aaberg", "Tigger.")
    assert (bare["level"], bare["anchors"]) == ("navn_alene", 0)


def test_gaps():
    g = _c("Aaberg", "Tigger.")["gaps"]
    assert {"identity", "given_names", "birth", "death", "description", "occupation", "nationality", "gender"} <= set(g)
    ok = _c("Aabye, Johan Peter (1818–1880)", "Distriktslæge i Flensborg 1858–1864.",
            roles=["Lærd"], nationalities=["dansk"], gender="Mandlig")
    assert ok["gaps"] == []
    # the uncategorised bucket is a placeholder, not a role
    assert "occupation" in _c("Aabye, Johan Peter (1818–1880)", "Læge.", roles=[UNCAT], nationalities=["dansk"], gender="Mandlig")["gaps"]


def test_register_doubt_is_a_gap_even_when_documented():
    r = _c("Haffner", "General (enten Generalmajor Wenzel H. (1774–1844) eller Generalløjtnant X).")
    assert "doubt" in r["gaps"]
    doc = _c("Aabye, Johan Peter (1818–1880)", "Distriktslæge (?) i Flensborg.", roles=["Lærd"], nationalities=["dansk"], gender="Mandlig")
    assert doc["level"] == "dokumenteret" and doc["gaps"] == ["doubt"]


def test_fleeting_needs_few_mentions_and_few_anchors():
    assert _c("Aaberg", "Tigger.", n_mentions=2)["fleeting"]
    assert not _c("Aaberg", "Tigger.", n_mentions=3)["fleeting"]
    assert not _c("Aabye, Johan Peter (1818–1880)", "Distriktslæge i Flensborg.", n_mentions=1)["fleeting"]


@pytest.mark.parametrize("n,key", [(1, "1"), (2, "2-3"), (3, "2-3"), (4, "4+"), (400, "4+")])
def test_mention_buckets(n, key):
    assert q.mention_bucket(n) == key


def test_place_in_description():
    lex = {"Toledo": "LOC1", "København": "LOC2", "Viborg": "LOC3"}
    assert q.place_in_description("Hotelvært i Toledo.", lex, "Abad") == "LOC1"
    assert q.place_in_description("Professor ved Københavns Universitet.", lex, "X") == "LOC2"
    assert q.place_in_description("Toledo 1862", lex, "Toledo") is None       # own surname
    assert q.place_in_description("Ingen steder her.", lex, "X") is None
    assert q.place_in_description("", lex, "X") is None


def test_place_lexicon_drops_ambiguous_and_wrong_category():
    places = {
        "L1": {"label": "Toledo", "country": "Spanien", "category": "City"},
        "L2": {"label": "Frederiksborg", "country": "Danmark", "category": "City"},
        "L3": {"label": "Frederiksborg", "country": "Danmark", "category": "Property"},
        "L4": {"label": "Frederiksborg", "country": "Danmark", "category": "City"},
        "L5": {"label": "Donau", "country": "Østrig", "category": "River"},
    }
    lex = q.build_place_lexicon(places)
    assert lex == {"Toledo": "L1"}


def test_taxonomy_is_consistent():
    assert set(tx.QUEUED_LEVELS) <= {k for k, *_ in tx.LEVELS}
    for _k, _da, _en, fields in tx.GAPS:
        assert set(fields) <= set(tx.FIELD_KEYS)
    assert len(set(tx.FIELD_KEYS)) == len(tx.FIELD_KEYS)
    js = tx.taxonomy_for_js()
    assert js["schema"] == tx.SCHEMA and js["limits"]["max_sources"] == tx.LIMITS["max_sources"]


@pytest.mark.skipif(not (ROOT / "data" / "normalized" / "entities.csv").exists(), reason="normalised CSVs not present")
def test_build_gates_non_individuals_and_links_every_mention():
    queue, meta, _kb = q.build()
    assert meta["queued"] == len(queue) > 1000
    assert all(r["id"].startswith("Reg") for r in queue)
    assert all(r["m"] and r["n"] >= 1 for r in queue)
    assert all(r["lv"] in tx.QUEUED_LEVELS or "doubt" in r["g"] for r in queue)
    # the relational placeholders ("– Hans Søster") never reach the queue
    assert not [r for r in queue if q._RELATIONAL_RE.match(r["l"])]
    assert len({r["id"] for r in queue}) == len(queue)
