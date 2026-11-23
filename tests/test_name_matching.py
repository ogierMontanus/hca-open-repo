"""Shared name matching for diary/almanac grounding (scripts/parsers/name_matching.py,
docs/plan-streng-grounding.md §3.11). Synthetic data only."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "parsers"))
import name_matching as nm  # noqa: E402
import ner_page_grounding as g  # noqa: E402

RAW = "038-03     Middag hos Fru Bjer-\n038-04     ring og Kjöbenhavns Setubal; hans Søn\n038-05     O’Neill og Carl Bøgh."


def test_textview_removes_line_tags_joins_hyphenation_and_maps_back():
    v = nm.TextView(RAW)
    assert v.text == "Middag hos Fru Bjerring og Kjöbenhavns Setubal; hans Søn O’Neill og Carl Bøgh."
    s = v.text.index("Bjerring")
    rs, re_ = v.raw_span(s, s + len("Bjerring"))
    assert RAW[rs:re_] == "Bjer-\n038-04     ring"


def test_variants_genitive_and_case():
    v = nm.TextView(RAW)
    hit = lambda form: [v.text[s:e] for s, e in nm.find(v, form)]
    assert hit("København") == ["Kjöbenhavns"]          # kj/k, ö/ø, genitiv
    assert hit("Setúbal") == ["Setubal"]                 # accent
    assert hit("O'Neill") == ["O’Neill"]                 # apostrof
    assert hit("Hans") == []                             # pronomenet »hans« er ikke fornavnet


def test_edit1_and_fuzzy_rejects_nouns():
    assert nm.edit1("bruun", "brun") and nm.edit1("giessing", "giesing") and not nm.edit1("brandes", "bransis")
    v = nm.TextView("Fik en Billet af Bille og Brun.")
    assert [v.text[s:e] for s, e in nm.fuzzy_find(v, "Bruun")] == []     # under 5 bogstaver i teksten
    assert [v.text[s:e] for s, e in nm.fuzzy_find(v, "Bilet")] == ["Billet"]
    assert [v.text[s:e] for s, e in nm.fuzzy_find(v, "Bilet", reject={"billet"})] == []   # korpusnavneord


def test_label_forms():
    assert nm.person_forms("Ahrens (Arenz)") == (["Ahrens", "Arenz"], [])
    sur, given = nm.person_forms("Wulff, Henriette (Jette) (1804–1858)")
    assert sur == ["Wulff"] and given[:2] == ["Henriette", "Jette"]
    assert nm.place_forms("Galatz (Galati)")[0] == ["Galatz", "Galati"]
    assert nm.place_forms("Baja (Ungarn)")[0] == ["Baja"]                # beskrivende parentes er ikke en variant


def test_ground_page_full_name_title_and_raw_offsets():
    ents = [dict(entity_id="P1", entity_label="Bøgh, Carl (1830–1900)", entity_type="person", ref_page_id="x"),
            dict(entity_id="P2", entity_label="Bjerring, Anna", entity_type="person", ref_page_id="x"),
            dict(entity_id="P3", entity_label="Koch, Hans Henrik", entity_type="person", ref_page_id="x"),
            dict(entity_id="L1", entity_label="Setúbal", entity_type="place", ref_page_id="x")]
    rows = {r["entity_id"]: r for r in g.ground_page(ents, RAW, 5)}
    assert rows["P1"]["mention"] == "Carl Bøgh" and rows["P1"]["method"] == "full_name"
    assert rows["P2"]["mention"] == "Fru Bjer-\n038-04     ring"           # titel med, rå offsets
    assert RAW[rows["P2"]["start"]:rows["P2"]["end"]] == rows["P2"]["mention"]
    assert rows["P3"]["method"] == "no_match"                            # ikke »hans«
    assert rows["L1"]["mention"] == "Setubal"
