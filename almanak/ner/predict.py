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
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from context import Context  # noqa: E402
import features as F  # noqa: E402
import titles as T  # noqa: E402
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
    if typ == "Person":
        rid = role_link(ctx, date, core)
        if rid:
            return rid, "alm-dato-rolle", [rid]
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


# Grænserne for gennemsynet (`model.py tiers`, blokvis krydsvalidering med navneordsfilter, 2026-11-24):
# modellens egen tærskel (tunet på bedste F1, 0,55-0,65) giver 17 % falske blandt de sikre; HIGH 0,75 halverer dem
# (22 -> 11 af 129/109) for 7 point recall, som flyttes ned i de usikre. LOW 0,6 tager de usikre fra 11 (5 falske) ved
# LOW 0,4 til 17 (8 falske) — men samlet falder de falske fra 27 til 19 ved samme samlede recall (0,79).
HIGH = 0.75   # p >= HIGH: sikkert forslag, markeres stiplet i teksten (runde 1)
LOW = 0.6     # LOW <= p < HIGH: usikkert forslag, ikke i teksten, tildeles i runde 3 (senere: LLM-trin, docs/plan-llm-trin.md)
LOW_LINKED = 0.3   # usikkert forslag allerede fra 0,3, hvis registret for datoen/dagbogssiden støtter det (gennemsyn 2:
                   # »Thorvaldsen« 0,53, »Kongen« 0,31–0,45; krydsvalidering: 3 af 4 sådanne var navne mod 4 af 14 uden støtte)

# Roller, der omtaler én bestemt person: »Kongen« på en dato er den konge, almanakregistret har på datoen.
# Beskrivelsen siger »1839 konge af«; før det år er personen ikke konge.
ROLES = {"kongen": "konge", "dronningen": "dronning", "kronprindsen": "kronprins", "kronprinsen": "kronprins",
         "kronprindsessen": "kronprinsesse", "kronprinsessen": "kronprinsesse"}


def role_link(ctx, date, core):
    """-> reg_id for en rolle (»Kongen«) ud fra almanakregistrets poster på datoen, eller ''."""
    role = ROLES.get(core.strip().lower())
    if not role:
        return ""
    hits = []
    for rid in ctx.alm_by_date.get(date, ()):
        info = ctx.alm_reg.get(rid, {})
        m = re.search(r"(?:(\d{4})\s+)?(?:fra\s+\d{4}\s+)?" + role + r"\b", info.get("d", ""))
        if m and not (m.group(1) and int(date[:4]) < int(m.group(1))):
            hits.append(rid)
    return hits[0] if len(hits) == 1 else ""


def annotate(ctx, m, date, text, low=None, nf=None, high=None, src="almanak"):
    """Forslag i posten. nf: NounFilter, der udelader fællesnavne uden støtte. high=None: modellens egen tærskel.
    low=None: kun sikre (p >= high). low=0.6: også usikre (tier='usikker'), som ikke skal markeres i teksten,
    men tildeles i en tredje runde."""
    import numpy as np
    from candidates import mention_kind
    spans, X = F.featurize(ctx, date, src, text)       # src: almanak | dagbog (samme model, trænet på begge)
    out = []
    if not len(spans):
        return out
    g_date, g_page = ctx.alm_date_gazetteer(date), ctx.page_gazetteer(date)
    p = m.m.predict_proba(X)[:, 1]
    thr = high if high is not None else m.threshold
    floor = min(low, LOW_LINKED) if low is not None else 2.0
    conf, unc = M.decode_tiers(spans, p, thr, floor, X, m.tm)
    conf, unc, _ = T.apply(text, conf, unc, thr)          # »Hertuginden af Augustenborg« = én person (omtale), ikke et sted
    rule_spans = set(T.ruler_spans(text))
    for tier, items in (("sikker", conf), ("usikker", unc)):
        for s, e, typ, pr in items:
            rid, src, cands = link(ctx, date, text[s:e], typ, g_date, g_page)
            if (s, e) in rule_spans:
                out.append(dict(start=s, end=e, text=text[s:e], type="Person", p=round(float(pr), 3), reg=rid, link_src=src,
                                link_candidates=cands, tier="sikker", mkind="omtale", rule="titel-af-sted"))
                continue
            if tier == "usikker" and pr < low and not (rid or cands):
                continue     # under LOW kun med støtte i registrene
            if nf is not None and not nf.keep(text[s:e], linked=bool(rid or cands)):
                continue     # åbenlyst fællesnavn uden støtte i registrene (noun_filter.py)
            out.append(dict(start=s, end=e, text=text[s:e], type=str(typ), p=round(float(pr), 3), reg=rid, link_src=src,
                            link_candidates=cands, tier=tier, mkind=mention_kind(text[s:e])))
    return sorted(out, key=lambda x: x["start"])


def cmd_all():
    import gold as G
    from noun_filter import NounFilter, allow_from_gold
    ctx = Context()
    m = load_model()
    ge = G.load_entries()
    nf = NounFilter(ctx, allow_from_gold((ge[a["post_id"]]["text"], {(a["start"], a["end"]): a["type"]})
                                         for a in G.load_gold() if a["post_id"] in ge))
    by_tier = collections.Counter()
    cov = collections.Counter()
    unlinked = collections.Counter()
    by_type = collections.Counter()
    M.OUT.mkdir(exist_ok=True)
    with open(M.OUT / "almanac_predictions.jsonl", "w", encoding="utf-8") as fh:
        for i, (date, v) in enumerate(sorted(ctx.alm.items())):
            pred = annotate(ctx, m, date, v["text"], low=LOW, nf=nf, high=HIGH)
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
                by_tier[p["tier"]] += 1
                by_type[p["type"]] += 1
                if not p["reg"] and not p["link_candidates"]:
                    unlinked[p["type"]] += 1
            if i % 500 == 0:
                print(i, date, dict(cov), flush=True)
    res = {"entries": cov["entries"], "almanac_index_person_refs": cov["index_refs"],
           "index_coverage_model": round(cov["model_linked"] / cov["index_refs"], 3),
           "index_coverage_rule": round(cov["rule_linked"] / cov["index_refs"], 3),
           "spans_model": cov["model_spans"], "spans_rule": cov["rule_spans"],
           "thresholds": {"high": HIGH, "low": LOW}, "model_spans_by_tier": dict(by_tier),
           "model_spans_by_type": dict(by_type), "model_spans_without_register_match": dict(unlinked)}
    (M.OUT / "coverage.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(res, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    if sys.argv[1:] == ["all"]:
        cmd_all()
    else:
        sys.exit(__doc__)
