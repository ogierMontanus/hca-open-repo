"""almanak/ner: candidate spans, scoring and review evaluation (synthetic data, no source files)."""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "almanak" / "ner"))
import candidates as C  # noqa: E402
import eval_review as R  # noqa: E402

TEXT = "Middag hos Prof: Schlessinger. Brev fra Jette Wulff og Georges 0 Neill; Prindsessen af Preusen."


def spans(text):
    return {text[s:e] for s, e in C.generate(text)}


def test_candidates_cover_titles_full_names_particles_and_ocr_zero():
    got = spans(TEXT)
    for want in ("Prof: Schlessinger", "Jette Wulff", "Georges 0 Neill", "Prindsessen af Preusen", "Wulff"):
        assert want in got, want
    assert "Schlessinger. Brev" not in got          # sætningspunktum krydses ikke
    assert not any(s.endswith(" 0") for s in got)    # »0« afslutter aldrig et spænd


def test_score_counts_exact_typed_and_overlap():
    pytest.importorskip("numpy")          # CI-runneren har ikke numpy/scikit-learn; modellen køres lokalt
    pytest.importorskip("sklearn")
    import importlib
    M = importlib.import_module("model")
    items = {"x": {"gold": {(0, 5): "Person", (10, 15): "Sted"}}}
    preds = {"x": [(0, 5, "Person", 0.9), (10, 14, "Sted", 0.8), (20, 25, "Værk", 0.7)]}
    r = M.score(items, preds)
    assert r["exact"] == {"p": round(1 / 3, 3), "r": 0.5, "f1": 0.4}
    assert r["overlap"]["r"] == 1.0 and r["typed"]["p"] == round(1 / 3, 3)


def test_mention_kind_heuristic():
    for text, want in [("Jette Wulff", "navn"), ("Prof: Schlessinger", "navn"), ("Kongen", "omtale"), ("Maleren", "omtale"),
                       ("Lucien Bonapartes Datter", "omtale"), ("Fru O Neill og Sønnerne", "omtale"), ("han", "pronomen")]:
        assert C.mention_kind(text) == want, text


def test_eval_review_tiers_and_mention_kind(tmp_path):
    def a(s, e, typ, **kw):
        return {"post_id": "ALM-1838-09-26", "source": "almanak", "block": "E", "start": s, "end": e, "string": "Kongen" if kw.pop("k", 0) else "Jette Wulff",
                "type": typ, **kw}
    exp = {"meta": {"annotator": "T", "active_seconds_by_block": {"E": 600}}, "reviewed_days": ["1838-09-26"],
           "uncertain_open": 0,
           "annotations": [a(0, 5, "Person", origin="model", model_type="Person", tier="sikker"),
                           a(9, 14, "Sted", origin="model", model_type="Person", tier="sikker"),
                           a(20, 24, "Person", origin="human", k=1, mention_kind="omtale"),
                           a(30, 35, "Person", origin="model", model_type="Person", tier="usikker")],
           "rejected_suggestions": [{"post_id": "ALM-1838-09-26", "start": 40, "end": 45},
                                    {"post_id": "ALM-1838-09-26", "start": 50, "end": 55, "uncertain": True}]}
    p = tmp_path / "r.json"
    p.write_text(json.dumps(exp), encoding="utf-8")
    res, final, days = R.measure(p)
    assert res["sikre_forslag"] == {"n": 3, "praecision": round(2 / 3, 3), "typet_praecision": round(1 / 3, 3)}
    assert res["usikre_forslag"] == {"n": 2, "andel_der_var_navne": 0.5}
    assert res["recall_sikre"] == round(2 / 3, 3) and res["recall_med_usikre"] == 0.75
    assert res["pr_omtaleform"]["omtale"] == {"fundet af modellen": 0, "tilføjet": 1, "recall": 0.0}


class _Gaz:
    def __init__(self, known=()):
        self.known = set(known)

    def lookup(self, s, fuzzy=True):
        return (1.0, {("X", "person", "sur")}) if s.lower() in self.known else (0.0, set())


class _Ctx:
    ext_words = {"tænderne": "hca", "fluen": "hca", "theatret": "hca", "kongen": "hca", "lidenskabelig": "hca", "munk": "ods", "munks": "ods"}
    alm_gaz = _Gaz({"munks"})
    dia_gaz = _Gaz()


def test_noun_filter_drops_common_nouns_unless_supported():
    import noun_filter as N
    nf = N.NounFilter(_Ctx(), allow={"theatret"})
    assert not nf.keep("Tænderne") and not nf.keep("Fluen") and not nf.keep("Lidenskabelig")
    assert nf.keep("Theatret")                         # navnelignende fællesnavn (på listen)
    assert nf.keep("Kongen")                           # fra håndlisten data/entity_like_nouns.txt
    assert nf.keep("Fluen", linked=True)               # kobles til en registerpost
    assert nf.keep("Munks")                            # formen findes i registret
    assert nf.keep("Jette Wulff") and nf.keep("Frøken Tænderne")   # ikke kun fællesnavne / har titel


def test_role_link_uses_the_register_of_the_day_and_the_reign_year():
    pytest.importorskip("numpy")
    pytest.importorskip("sklearn")
    import predict as P

    class _C:
        alm_by_date = {"1840-05-01": ["K8", "Q", "W"], "1838-05-01": ["K8"], "1849-01-01": ["K8", "F7"]}
        alm_reg = {"K8": {"d": "(VIII), prins, 1839 konge af"}, "Q": {"d": "prinsesse, 1839 dronning af"},
                   "W": {"d": "kaptajn"}, "F7": {"d": "(VII), kronprins, 1848 konge af"}}
    assert P.role_link(_C, "1840-05-01", "Kongen") == "K8"
    assert P.role_link(_C, "1840-05-01", "Dronningen") == "Q"
    assert P.role_link(_C, "1838-05-01", "Kongen") == ""          # prins, endnu ikke konge
    assert P.role_link(_C, "1849-01-01", "Kongen") == ""          # to mulige: ingen afgørelse
    assert P.role_link(_C, "1840-05-01", "Maleren") == ""
