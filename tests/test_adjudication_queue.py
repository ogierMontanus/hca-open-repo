"""Adjudication queue for a returned overlap annotation (almanak/annotation/adjudication_queue.py,
docs/plan-streng-grounding.md §3.10). Synthetic data; no source files needed."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "almanak" / "annotation"))
import adjudication_queue as aq  # noqa: E402

TEXT = "Kjørt til Dresden med Fru Bull og Kongen. Saae Dresden og Kjöbenhavn; Bog fra Maleren Wien og"


def _a(pid, s, e, ty):
    return {"post_id": pid, "start": s, "end": e, "string": TEXT[s:e], "type": ty}


def _run(ann, cands=()):
    entries = {"DAG-1": {"text": TEXT, "c": list(cands)}}
    reg = {"LOCW": {"k": "S", "l": "Wien"}, "LOCK": {"k": "S", "l": "København"}}
    return aq.build(entries, reg, ann)


def i(s):
    return TEXT.index(s)


def test_unmarked_repeat_register_name_and_generic_suppressed():
    ann = [_a("DAG-1", i("Dresden"), i("Dresden") + 7, "Sted"),
           _a("DAG-1", i("Bog"), i("Bog") + 3, "Værk")]
    rows = _run(ann, [["LOCW", "ref+navn"], ["LOCK", "ref+navn"]])
    um = {(r["streng"], r["forslag"].split(" (")[0]) for r in rows if r["kategori"] == "UMARKERET"}
    assert ("Dresden", "mærk som Sted") in um          # anden forekomst, umarkeret
    assert ("Wien", "mærk som Sted") in um             # registernavn i teksten
    assert ("Kjöbenhavn", "mærk som Sted") in um       # stavevariant kj/k, ö/ø-foldning
    assert not any(s == "Bog" for s, _ in um)           # almindeligt navneord foreslås ikke
    assert any(r["kategori"] == "REGEL" and r["streng"] == "Bog" for r in rows)


def test_offsets_are_into_original_text():
    rows = _run([_a("DAG-1", i("Dresden"), i("Dresden") + 7, "Sted")])
    for r in rows:
        assert TEXT[r["start"]:r["end"]] == r["streng"]


def test_type_conflict_boundary_and_role():
    s2 = TEXT.index("Dresden", i("Dresden") + 1)
    ann = [_a("DAG-1", i("Dresden"), i("Dresden") + 7, "Sted"),
           _a("DAG-1", s2, s2 + 7, "Person"),
           _a("DAG-1", i("Fru Bull og"), i("Fru Bull og") + 11, "Person"),
           _a("DAG-1", i("Maleren"), i("Maleren") + 7, "Andet")]
    cats = {(r["kategori"], r["streng"]) for r in _run(ann)}
    assert ("TYPEKONFLIKT", "Dresden") in cats
    assert ("AFGRÆNSNING", "Fru Bull og") in cats
    assert ("REGEL", "Maleren") in cats
    assert ("UMARKERET", "Kongen") not in cats          # intet grundlag: ikke markeret andetsteds
