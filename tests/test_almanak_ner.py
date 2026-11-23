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


def test_eval_review_counts_accept_retype_reject_add(tmp_path):
    exp = {"meta": {"annotator": "T", "active_seconds_by_block": {"E": 600}},
           "reviewed_days": ["1838-09-26"],
           "annotations": [
               {"post_id": "ALM-1838-09-26", "source": "almanak", "block": "E", "start": 0, "end": 5, "type": "Person", "origin": "model", "model_type": "Person"},
               {"post_id": "ALM-1838-09-26", "source": "almanak", "block": "E", "start": 9, "end": 14, "type": "Sted", "origin": "model", "model_type": "Person"},
               {"post_id": "ALM-1838-09-26", "source": "almanak", "block": "E", "start": 20, "end": 24, "type": "Person", "origin": "human"},
               {"post_id": "ALM-1838-09-27", "source": "almanak", "block": "E", "start": 0, "end": 3, "type": "Person", "origin": "model", "model_type": "Person"}],
           "rejected_suggestions": [{"post_id": "ALM-1838-09-26", "start": 30, "end": 35}]}
    p = tmp_path / "r.json"
    p.write_text(json.dumps(exp), encoding="utf-8")
    res, final, days = R.measure(p)
    assert (res["godkendt"], res["type rettet"], res["slettet"], res["tilføjet"]) == (1, 1, 1, 1)
    assert res["praecision"] == round(2 / 3, 3) and res["recall"] == round(2 / 3, 3)
    assert len(final) == 3                                         # ugennemgået dag tælles ikke
