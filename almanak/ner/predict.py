#!/usr/bin/env python3
"""
predict.py — maskinannotér almanakposter med den trænede model (model.py train) og foreslå en
registerpost for hvert spænd.

  python almanak/ner/predict.py all        # alle almanakposter -> out/almanac_predictions.jsonl + out/coverage.json

Kobling (forslag, ikke afgørelse): kernen af spændet (uden titel og genitiv) slås op i
  1. almanakkens register for datoen (Topsøe-Jensens henvisninger)       kilde »alm-dato«
  2. dagbogsregistret for dagens dagbogsside(r)                           kilde »dagbog-side«
og kun et entydigt fund (én post) foreslås; flere fund gives som kandidater.

Dækningsmålet (»silver«) bruger almanakregistret som facit: hvor stor en andel af registrets
personhenvisninger til en dato får et spænd i posten, der kobles til den person? Det måles for
modellen og for regelgrundlinjen. Bemærk: grundlinjen er bygget af netop de navne, så målet
favoriserer den; modellens fordel er de spænd, registret ikke kender.
"""
from __future__ import annotations

import collections
import json
import pickle
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from context import Context  # noqa: E402
import features as F  # noqa: E402
import model as M  # noqa: E402

TYPE_KEY = {"Person": "P", "Sted": "S", "Værk": "V", "Lokalitet": "L", "Andet": "A"}
KIND_OK = {"Person": {"person"}, "Sted": {"place"}, "Værk": {"work"}, "Lokalitet": {"place"}, "Andet": set()}


def load_model(path=M.OUT / "model.pkl"):
    with open(path, "rb") as fh:
        obj = pickle.load(fh)
    if obj["features"] != F.FEATURE_NAMES:
        sys.exit("Modellen er trænet med andre træk; kør model.py train igen.")
    return obj["model"]


def link(ctx, date, span_text, typ, g_date=None, g_page=None):
    """-> (reg_id | '', kilde, [kandidater])"""
    core, _ = F._core(span_text)
    toks = core.split()
    g_date = g_date or ctx.alm_date_gazetteer(date)
    g_page = g_page or ctx.page_gazetteer(date)
    for g, src in ((g_date, "alm-dato"), (g_page, "dagbog-side")):
        for key in (core, toks[-1] if toks else core):
            sc, ents = g.lookup(key, fuzzy=True)
            ents = {(eid, kind) for eid, kind, _ in ents if not KIND_OK[typ] or kind in KIND_OK[typ]}
            ids = sorted({eid for eid, _ in ents})
            if len(ids) == 1:
                return ids[0], src, ids
            if len(ids) > 1:
                return "", src, ids[:3]
    return "", "", []


def annotate(ctx, m, date, text, low=None, nf=None):
    """Forslag i posten. nf: NounFilter, der udelader fællesnavne uden støtte. low=None: kun sikre (p >= modellens tærskel). low=0.2: også usikre (tier='usikker'),
    som ikke skal markeres i teksten, men tildeles i en tredje runde."""
    import numpy as np
    from candidates import mention_kind
    spans, X = F.featurize(ctx, date, "almanak", text)
    out = []
    if not len(spans):
        return out
    g_date, g_page = ctx.alm_date_gazetteer(date), ctx.page_gazetteer(date)
    p = m.m.predict_proba(X)[:, 1]
    conf, unc = M.decode_tiers(spans, p, m.threshold, low if low is not None else 2.0, X, m.tm)
    for tier, items in (("sikker", conf), ("usikker", unc)):
        for s, e, typ, pr in items:
            rid, src, cands = link(ctx, date, text[s:e], typ, g_date, g_page)
            if nf is not None and not nf.keep(text[s:e], linked=bool(rid or cands)):
                continue     # åbenlyst fællesnavn uden støtte i registrene (noun_filter.py)
            out.append(dict(start=s, end=e, text=text[s:e], type=str(typ), p=round(float(pr), 3), reg=rid, link_src=src,
                            link_candidates=cands, tier=tier, mkind=mention_kind(text[s:e])))
    return sorted(out, key=lambda x: x["start"])


def cmd_all():
    ctx = Context()
    m = load_model()
    cov = collections.Counter()
    unlinked = collections.Counter()
    by_type = collections.Counter()
    M.OUT.mkdir(exist_ok=True)
    with open(M.OUT / "almanac_predictions.jsonl", "w", encoding="utf-8") as fh:
        for i, (date, v) in enumerate(sorted(ctx.alm.items())):
            pred = annotate(ctx, m, date, v["text"])
            rule = M.baseline_rule(ctx, {"date": date, "text": v["text"]})
            fh.write(json.dumps({"date": date, "text": v["text"], "spans": pred}, ensure_ascii=False) + "\n")
            persons = {rid for rid in ctx.alm_by_date.get(date, ()) if ctx.alm_reg[rid]["k"] == "P"}
            linked = {p["reg"] for p in pred} | {c for p in pred for c in p["link_candidates"]}
            rule_linked = set()
            for s, e, typ, _ in rule:
                rid, _, cands = link(ctx, date, v["text"][s:e], typ)
                rule_linked |= {rid} | set(cands)
            cov["index_refs"] += len(persons)
            cov["model_linked"] += len(persons & linked)
            cov["rule_linked"] += len(persons & rule_linked)
            cov["entries"] += 1
            cov["model_spans"] += len(pred)
            cov["rule_spans"] += len(rule)
            for p in pred:
                by_type[p["type"]] += 1
                if not p["reg"] and not p["link_candidates"]:
                    unlinked[p["type"]] += 1
            if i % 500 == 0:
                print(i, date, dict(cov), flush=True)
    res = {"entries": cov["entries"], "almanac_index_person_refs": cov["index_refs"],
           "index_coverage_model": round(cov["model_linked"] / cov["index_refs"], 3),
           "index_coverage_rule": round(cov["rule_linked"] / cov["index_refs"], 3),
           "spans_model": cov["model_spans"], "spans_rule": cov["rule_spans"],
           "model_spans_by_type": dict(by_type), "model_spans_without_register_match": dict(unlinked)}
    (M.OUT / "coverage.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(res, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    if sys.argv[1:] == ["all"]:
        cmd_all()
    else:
        sys.exit(__doc__)
