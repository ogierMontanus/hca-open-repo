#!/usr/bin/env python3
"""
model.py — lille rangeringsmodel for navnespænd i almanakken (»diary2almanac«), evalueret mod
Sørens overlap-annotering med blokvis krydsvalidering, sammen med to grundlinjer.

  python almanak/ner/model.py eval            # krydsvalidering -> almanak/ner/out/eval.json + .md
  python almanak/ner/model.py train           # træn på alle 32 dage -> almanak/ner/out/model.pkl

Model: span-klassifikator (er kandidaten et navnespænd?) + typeklassifikator (Person/Sted/Lokalitet/
Værk/Andet), begge scikit-learn. Afkodning: grådigt, ikke-overlappende, efter score over en tærskel,
der vælges i en indre krydsvalidering (aldrig på testblokken).
"""
from __future__ import annotations

import argparse
import collections
import json
import pickle
import sys
from pathlib import Path

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gold as G  # noqa: E402
from context import Context, canon, nm  # noqa: E402
import features as F  # noqa: E402

OUT = HERE / "out"
TYPES = ["Person", "Sted", "Lokalitet", "Værk", "Andet"]
BLOCKS = ["A", "B", "C", "D"]
SEED = 20261123


# ---------------------------------------------------------------- data
def build_dataset(ctx, entries, ann):
    gold = collections.defaultdict(dict)
    for a in ann:
        gold[a["post_id"]][(a["start"], a["end"])] = a["type"]
    data = []
    for pid, e in entries.items():
        spans, X = F.featurize(ctx, e["date"], e["src"], e["text"])
        y = np.array([1 if sp in gold[pid] else 0 for sp in spans])
        t = [gold[pid].get(sp) for sp in spans]
        data.append(dict(pid=pid, block=e["block"], src=e["src"], date=e["date"], text=e["text"],
                         spans=spans, X=X, y=y, types=t, gold=gold[pid]))
    return data


def stack(items):
    X = np.vstack([d["X"] for d in items if len(d["spans"])])
    y = np.concatenate([d["y"] for d in items if len(d["spans"])])
    t = [x for d in items for x in d["types"]]
    return X, y, t


# ---------------------------------------------------------------- modeller
def make_span_model(kind):
    if kind == "logreg":
        return make_pipeline(StandardScaler(), LogisticRegression(C=0.3, max_iter=3000, class_weight="balanced"))
    return HistGradientBoostingClassifier(max_depth=3, learning_rate=0.08, max_iter=250, min_samples_leaf=10,
                                          l2_regularization=1.0, class_weight="balanced", random_state=SEED)


def make_type_model():
    return make_pipeline(StandardScaler(), LogisticRegression(C=0.5, max_iter=3000))


class SpanModel:
    def __init__(self, kind="gbm"):
        self.kind = kind
        self.threshold = 0.5

    def fit(self, items, tune=True):
        X, y, t = stack(items)
        self.m = make_span_model(self.kind).fit(X, y)
        pos = y == 1
        self.tm = make_type_model().fit(X[pos], [x for x, p in zip(t, pos) if p])
        if tune:
            self.threshold = tune_threshold(items, self.kind)
        return self

    def predict(self, d):
        if not len(d["spans"]):
            return []
        p = self.m.predict_proba(d["X"])[:, 1]
        return decode(d["spans"], p, self.threshold, d["X"], self.tm)


def decode_tiers(spans, p, thr, low, X, tm):
    """Sikre forslag (p >= thr) og usikre (low <= p < thr, uden overlap med de sikre)."""
    conf = decode(spans, p, thr, X, tm)
    taken = [(a, b) for a, b, *_ in conf]
    p2 = np.where([any(s < b and a < e for a, b in taken) for s, e in spans], -1.0, p)
    unc = [u for u in decode(spans, p2, low, X, tm) if u[3] < thr]
    return conf, unc


def decode(spans, p, thr, X=None, tm=None):
    order = np.argsort(-p)
    taken, out = [], []
    for i in order:
        if p[i] < thr:
            break
        s, e = spans[i]
        if any(s < b and a < e for a, b in taken):
            continue
        taken.append((s, e))
        typ = tm.predict(X[i:i + 1])[0] if tm is not None else "Person"
        out.append((s, e, typ, float(p[i])))
    return sorted(out)


def tune_threshold(items, kind):
    """Indre blokvis krydsvalidering på træningsblokkene; tærskel med bedste almanak-F1."""
    blocks = sorted({d["block"] for d in items})
    if len(blocks) < 2:
        return 0.5
    scored = []
    for b in blocks:
        tr = [d for d in items if d["block"] != b]
        te = [d for d in items if d["block"] == b and d["src"] == "almanak"]
        X, y, _ = stack(tr)
        m = make_span_model(kind).fit(X, y)
        for d in te:
            if len(d["spans"]):
                scored.append((d, m.predict_proba(d["X"])[:, 1]))
    best = (0.5, -1)
    for thr in np.arange(0.2, 0.91, 0.05):
        preds = {d["pid"]: decode(d["spans"], p, thr) for d, p in scored}
        f1 = score({d["pid"]: d for d, _ in scored}, preds)["exact"]["f1"]
        if f1 > best[1]:
            best = (float(thr), f1)
    return best[0]


# ---------------------------------------------------------------- grundlinjer
def baseline_rule(ctx, d):
    """Reglerne fra trin 2 anvendt på almanakken: almanakregistrets navne for datoen og dagbogsregistrets
    navne for dagens sider, fundet i posten (varianter, genitiv, titel med, fuldt navn ved nabostilling)."""
    view = nm.TextView(d["text"], line_tags=False)
    hits = []
    for g, src in ((ctx.alm_date_gazetteer(d["date"]), "alm"), (ctx.page_gazetteer(d["date"]), "dia")):
        for form, ents in g.full.items():
            kind = sorted(ents)[0][1]
            for m in nm.variant_regex(form).finditer(view.fold):
                if not view.text[m.start()].isupper():
                    continue
                s = nm.extend_title(view, m.start()) if kind == "person" else m.start()
                typ = {"person": "Person", "place": "Sted", "work": "Værk"}[kind]
                hits.append((s, m.end(), typ, 1.0 if " " in form else 0.8))
    hits.sort(key=lambda h: (-(h[1] - h[0]), -h[3]))
    out = []
    for h in hits:
        if not any(h[0] < b and a < h[1] for a, b, *_ in out):
            out.append(h)
    return sorted(out)


def baseline_caps(ctx, d):
    """Naiv: hvert ord med stort, der ikke indleder en sætning og ikke er i navneordslisten -> Person."""
    out = []
    for s, e, w in F.C.tokens(d["text"]):
        if not w[:1].isupper():
            continue
        if s == 0 or d["text"][max(0, s - 2):s].strip() in {".", "!", "?"}:
            continue
        if canon(w) in ctx.nouns:
            continue
        out.append((s, e, "Person", 1.0))
    return out


# ---------------------------------------------------------------- måling
def score(items, preds):
    """items: {pid: d}; preds: {pid: [(s,e,typ,p)]}"""
    c = collections.Counter()
    by_type = collections.defaultdict(collections.Counter)
    for pid, d in items.items():
        g = d["gold"]
        pr = preds.get(pid, [])
        c["gold"] += len(g); c["pred"] += len(pr)
        for (s, e), t in g.items():
            by_type[t]["gold"] += 1
            if any(ps == s and pe == e for ps, pe, *_ in pr):
                by_type[t]["exact"] += 1
            if any(ps < e and s < pe for ps, pe, *_ in pr):
                by_type[t]["overlap"] += 1
        for ps, pe, pt, _ in pr:
            if (ps, pe) in g:
                c["exact"] += 1
                if g[(ps, pe)] == pt:
                    c["typed"] += 1
            if any(ps < e and s < pe for s, e in g):
                c["overlap_p"] += 1
        c["overlap_r"] += sum(1 for s, e in g if any(ps < e and s < pe for ps, pe, *_ in pr))

    def prf(tp_p, tp_r=None):
        tp_r = tp_p if tp_r is None else tp_r
        p = tp_p / c["pred"] if c["pred"] else 0.0
        r = tp_r / c["gold"] if c["gold"] else 0.0
        return {"p": round(p, 3), "r": round(r, 3), "f1": round(2 * p * r / (p + r), 3) if p + r else 0.0}
    return {"n_gold": c["gold"], "n_pred": c["pred"], "exact": prf(c["exact"]), "typed": prf(c["typed"]),
            "overlap": prf(c["overlap_p"], c["overlap_r"]),
            "recall_by_type": {t: {"n": v["gold"], "exact": round(v["exact"] / v["gold"], 3),
                                   "overlap": round(v["overlap"] / v["gold"], 3)} for t, v in sorted(by_type.items())}}


def bootstrap_f1(items, preds, n=2000, seed=SEED):
    """95 %-interval for exact-F1 ved at gensample poster (ikke spænd)."""
    rng = np.random.default_rng(seed)
    pids = list(items)
    vals = []
    for _ in range(n):
        smp = rng.choice(pids, len(pids))
        it = {f"{p}#{i}": items[p] for i, p in enumerate(smp)}
        pr = {f"{p}#{i}": preds.get(p, []) for i, p in enumerate(smp)}
        vals.append(score(it, pr)["exact"]["f1"])
    return [round(float(np.percentile(vals, 2.5)), 3), round(float(np.percentile(vals, 97.5)), 3)]


# ---------------------------------------------------------------- kommandoer
def cmd_eval(args):
    ctx = Context()
    entries, ann = G.load_entries(), G.load_gold()
    data = build_dataset(ctx, entries, ann)
    by_pid = {d["pid"]: d for d in data}
    results = {}
    systems = {
        "regel (registernavne)": lambda tr, d: baseline_rule(ctx, d),
        "store bogstaver": lambda tr, d: baseline_caps(ctx, d),
    }
    variants = {"model logreg (begge kilder)": ("logreg", True), "model gbm (begge kilder)": ("gbm", True),
                "model gbm (kun almanak)": ("gbm", False)}
    preds = collections.defaultdict(dict)
    thresholds = collections.defaultdict(dict)
    for b in BLOCKS:
        test = [d for d in data if d["block"] == b]
        for name, (kind, both) in variants.items():
            train = [d for d in data if d["block"] != b and (both or d["src"] == "almanak")]
            m = SpanModel(kind).fit(train)
            thresholds[name][b] = m.threshold
            for d in test:
                preds[name][d["pid"]] = m.predict(d)
        for name, fn in systems.items():
            for d in test:
                preds[name][d["pid"]] = fn(None, d)
    for src in ("almanak", "dagbog"):
        items = {p: d for p, d in by_pid.items() if d["src"] == src}
        for name in list(systems) + list(variants):
            r = score(items, preds[name])
            r["exact_f1_ci95"] = bootstrap_f1(items, preds[name], n=500)
            results.setdefault(src, {})[name] = r
    # kandidatloft: hvor mange guldspænd kan overhovedet foreslås?
    ceil = {src: round(sum(1 for d in data if d["src"] == src for sp in d["gold"] if sp in set(d["spans"]))
                       / sum(len(d["gold"]) for d in data if d["src"] == src), 3) for src in ("almanak", "dagbog")}
    # trækkenes vægt (gbm, alle data): permutationsvigtighed ville være bedre; her logreg-koefficienter
    lr = SpanModel("logreg").fit(data, tune=False)
    coefs = lr.m[-1].coef_[0]
    top = sorted(zip(F.FEATURE_NAMES, coefs), key=lambda x: -abs(x[1]))[:20]
    out = {"candidate_ceiling_exact": ceil, "thresholds": thresholds, "results": results,
           "logreg_top_features": [[n, round(float(c), 2)] for n, c in top],
           "n_candidates": {s: int(sum(len(d["spans"]) for d in data if d["src"] == s)) for s in ("almanak", "dagbog")}}
    # fejl i almanakken for den bedste model (til rapporten)
    best = max(variants, key=lambda n: results["almanak"][n]["exact"]["f1"])
    errs = []
    for pid, d in by_pid.items():
        if d["src"] != "almanak":
            continue
        pr = {(s, e): t for s, e, t, _ in preds[best][pid]}
        for sp, t in d["gold"].items():
            if sp not in pr:
                errs.append(["mangler", pid, d["text"][sp[0]:sp[1]], t])
            elif pr[sp] != t:
                errs.append(["forkert type", pid, d["text"][sp[0]:sp[1]], f"{pr[sp]} (guld {t})"])
        for sp, t in pr.items():
            if sp not in d["gold"]:
                errs.append(["overskud", pid, d["text"][sp[0]:sp[1]], t])
    out["best"] = best
    out["almanak_errors_best"] = errs
    OUT.mkdir(exist_ok=True)
    (OUT / "eval.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in out.items() if k != "almanak_errors_best"}, ensure_ascii=False, indent=1))
    print(f"\nbedste: {best}; fejl i almanakken: {len(errs)}")
    for e in errs:
        print("  ", e)


ABLATIONS = {
    "alt": [],
    "uden dagbogen (other_*)": ["other_"],
    "uden almanakkens register (own_idx)": ["own_idx"],
    "uden registre og dagbog (kun form og kontekst)": ["other_", "own_idx", "alm_glob", "dia_glob", "given_plus",
                                                       "only_given", "only_sur"],
}


def cmd_tiers(args):
    """To lag: sikre forslag markeres i teksten, usikre holdes ude og tildeles i en tredje runde.
    Måler præcision og recall pr. lag i blokvis krydsvalidering (almanakken)."""
    ctx = Context()
    data = build_dataset(ctx, G.load_entries(), G.load_gold())
    res = {}
    for low in (0.2, 0.3, 0.4, 0.5):
        c = collections.Counter()
        for b in BLOCKS:
            m = SpanModel(args.kind).fit([d for d in data if d["block"] != b])
            for d in data:
                if d["block"] != b or d["src"] != "almanak" or not len(d["spans"]):
                    continue
                p = m.m.predict_proba(d["X"])[:, 1]
                conf, unc = decode_tiers(d["spans"], p, m.threshold, low, d["X"], m.tm)
                g = d["gold"]
                c["gold"] += len(g)
                for name, tier in (("sikre", conf), ("usikre", unc)):
                    c[name + "_n"] += len(tier)
                    c[name + "_ok"] += sum(1 for s, e, *_ in tier if (s, e) in g)
                    c[name + "_typed"] += sum(1 for s, e, t, _ in tier if g.get((s, e)) == t)
        res[str(low)] = {"gold": c["gold"], "sikre": [c["sikre_n"], c["sikre_ok"], c["sikre_typed"]],
                         "usikre": [c["usikre_n"], c["usikre_ok"], c["usikre_typed"]],
                         "praecision_sikre": round(c["sikre_ok"] / c["sikre_n"], 3),
                         "praecision_usikre": round(c["usikre_ok"] / c["usikre_n"], 3) if c["usikre_n"] else None,
                         "recall_sikre": round(c["sikre_ok"] / c["gold"], 3),
                         "recall_alle": round((c["sikre_ok"] + c["usikre_ok"]) / c["gold"], 3)}
        print(low, res[str(low)])
    OUT.mkdir(exist_ok=True)
    (OUT / "tiers.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")


def cmd_ablate(args):
    """Hvor meget bidrager dagbogen (diary2almanac) og almanakkens eget register? Træk sættes til 0."""
    ctx = Context()
    data = build_dataset(ctx, G.load_entries(), G.load_gold())
    res = {}
    for name, prefixes in ABLATIONS.items():
        cols = [i for i, n in enumerate(F.FEATURE_NAMES) if any(n.startswith(p) for p in prefixes)]
        dd = []
        for d in data:
            X = d["X"].copy()
            if len(X):
                X[:, cols] = 0.0
            dd.append({**d, "X": X})
        preds = {}
        for b in BLOCKS:
            m = SpanModel(args.kind).fit([d for d in dd if d["block"] != b])
            for d in dd:
                if d["block"] == b:
                    preds[d["pid"]] = m.predict(d)
        items = {d["pid"]: d for d in dd if d["src"] == "almanak"}
        r = score(items, preds)
        res[name] = {"exact": r["exact"], "typed_f1": r["typed"]["f1"], "ci95": bootstrap_f1(items, preds, n=500),
                     "n_features_zeroed": len(cols)}
        print(name, res[name])
    OUT.mkdir(exist_ok=True)
    (OUT / "ablation.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")


def cmd_train(args):
    ctx = Context()
    data = build_dataset(ctx, G.load_entries(), G.load_gold())
    m = SpanModel(args.kind).fit(data)
    OUT.mkdir(exist_ok=True)
    with open(OUT / "model.pkl", "wb") as fh:
        pickle.dump({"model": m, "features": F.FEATURE_NAMES, "kind": args.kind}, fh)
    print(f"tærskel {m.threshold:.2f}; gemt {OUT / 'model.pkl'}")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("eval")
    tt = sub.add_parser("tiers")
    tt.add_argument("--kind", default="logreg", choices=["gbm", "logreg"])
    a = sub.add_parser("ablate")
    a.add_argument("--kind", default="logreg", choices=["gbm", "logreg"])
    t = sub.add_parser("train")
    t.add_argument("--kind", default="logreg", choices=["gbm", "logreg"])
    args = ap.parse_args(argv)
    {"eval": cmd_eval, "tiers": cmd_tiers, "ablate": cmd_ablate, "train": cmd_train}[args.cmd](args)


if __name__ == "__main__":
    import model as _self  # klasserne skal pickles som model.SpanModel, ikke __main__.SpanModel
    _self.main()
