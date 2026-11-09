"""Navn/omtale-opdeling af personmarkeringer (almanak/annotation/split_mentions.py,
docs/plan-streng-grounding.md §3.10)."""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
ANN = ROOT / "almanak" / "annotation"
sys.path.insert(0, str(ANN))

pytestmark = pytest.mark.skipif(not (ROOT / "data" / "normalized" / "entities.csv").exists(),
                                reason="personregister mangler")


@pytest.fixture(scope="module")
def lex():
    import split_mentions as m
    names = m.load_gazetteer()
    return m, names, m.load_homonyms(names)


@pytest.mark.parametrize("string,kind,name,title", [
    ("Hansen", "navn", "Hansen", ""),
    ("Collins", "navn", "Collins", ""),                 # familieflertal
    ("Heibergs", "navn", "Heibergs", ""),               # genitiv
    ("Humbold[t]", "navn", "Humbold[t]", ""),           # udgiverens klamme
    ("H. C. Ørsted", "navn", "H. C. Ørsted", ""),       # initialer
    ("Pastor Boye", "titel+navn", "Boye", "Pastor"),
    ("Prof: Guldberg", "titel+navn", "Guldberg", "Prof:"),
    ("Skues: Holst", "titel+navn", "Holst", "Skues:"),  # ukendt forkortelse foran navn
    ("Skuespiller Nielsen", "titel+navn", "Nielsen", "Skuespiller"),
    ("Kongen", "omtale", "", ""),
    ("Kronprindsessen", "omtale", "", ""),
    ("min Moder", "omtale", "", ""),
    ("Carl og Otto Moltke", "flere", "", ""),
])
def test_classify(lex, string, kind, name, title):
    m, names, hom = lex
    k, ns, ne, t, _reason = m.classify(string, names, hom)
    assert k == kind
    assert (string[ns:ne] if ns is not None else "") == name
    assert t == title


def test_title_before_unregistered_name(lex):
    m, names, hom = lex
    k, ns, ne, t, reason = m.classify("Prof: Xyzzelmann", names, hom)
    assert (k, "Prof: Xyzzelmann"[ns:ne], t) == ("titel+navn", "Xyzzelmann", "Prof:")
    assert "ikke i registret" in reason


def test_unknown_bare_word_goes_to_review(lex):
    m, names, hom = lex
    assert m.classify("Xyzzelmann", names, hom)[0] == "tvivl"


def test_cli_offsets_point_at_name_core(lex, tmp_path):
    m, _n, _h = lex
    text = "Middag hos Pastor Boye med Kongen."
    s = text.index("Pastor Boye")
    k = text.index("Kongen")
    res = tmp_path / "r.json"
    res.write_text(json.dumps({"annotations": [
        {"post_id": "X", "start": s, "end": s + 11, "string": "Pastor Boye", "type": "Person"},
        {"post_id": "X", "start": k, "end": k + 6, "string": "Kongen", "type": "Person"},
        {"post_id": "X", "start": 0, "end": 6, "string": "Middag", "type": "Værk"},
    ]}, ensure_ascii=False), encoding="utf-8")
    out = tmp_path / "o.tsv"
    assert m.main([str(res), "--out", str(out)]) == 0
    rows = [ln.split("\t") for ln in out.read_text(encoding="utf-8").splitlines()]
    head, body = rows[0], rows[1:]
    assert len(body) == 2                                  # kun Person
    r = dict(zip(head, body[0]))
    assert text[int(r["name_start"]):int(r["name_end"])] == "Boye"
    assert dict(zip(head, body[1]))["mention_kind"] == "omtale"
