#!/usr/bin/env python3
"""
build_review_page.py — gennemsynsside: en NY stikprøve af almanakposter, maskinannoteret af modellen
(model.py train), som Søren og Ole retter i stedet for at markere fra bunden (§3.11).

Stikprøver: fire blokke à otte dage, ingen af dem i træningsdata (A–D) eller i en tidligere stikprøve.
  Stikprøve 1 (2026-11-23):  E 1838-09-26 – 10-03 (uden dagbog), F 1843-04-19 – 04-26 (bind II),
                             G 1853-07-20 – 07-27 (uden dagbog), H 1861-06-28 – 07-05 (bind V)
  Stikprøve 2 (2026-11-24):  I 1840-04-29 – 05-06 (uden dagbog), J 1844-01-22 – 01-29 (uden dagbog),
                             K 1857-06-25 – 07-02 (bind IV), L 1860-06-17 – 06-24 (bind IV)
  Stikprøve 2 bruger den nye metode: strammere grænser (sikre ≥ 0,75, usikre ≥ 0,6), fællesnavnsfilteret,
  registret med rettede årstal (§3.15) og registertegnet ÷ (ikke i Dagbøger XI / ikke identificeret).
Blokke uden dagbog viser, hvordan modellen klarer sig uden »diary2almanac«-trækkene.

Siden genbruger annoteringssiden (template-overlap.html) i gennemsynstilstand: forslagene står stiplet;
slettede forslag og rettelser kommer med i eksporten, så præcision og overset kan måles (eval_review.py).

  python almanak/ner/build_review_page.py                       -> almanak/annotation/out/almanak-gennemsyn.html
  python almanak/ner/build_review_page.py --out mockup/almanak-gennemsyn.html
  python almanak/ner/build_review_page.py --sample 2 --out mockup/almanak-gennemsyn2.html
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "almanak" / "annotation"))
import build_annotation_page as bap  # noqa: E402
import build_overlap_page as bop  # noqa: E402
from context import Context  # noqa: E402
import predict as P  # noqa: E402
import gold as G  # noqa: E402
from noun_filter import NounFilter, allow_from_gold  # noqa: E402

REVIEW_BLOCKS = [
    ("E", "1838-09-26", "1838-10-03", ""),
    ("F", "1843-04-19", "1843-04-26", "II"),
    ("G", "1853-07-20", "1853-07-27", ""),
    ("H", "1861-06-28", "1861-07-05", "V"),
]
SAMPLE_ID = "review-2026-11-E-H"
REVIEW_BLOCKS_2 = [
    ("I", "1840-04-29", "1840-05-06", ""),
    ("J", "1844-01-22", "1844-01-29", ""),
    ("K", "1857-06-25", "1857-07-02", "IV"),
    ("L", "1860-06-17", "1860-06-24", "IV"),
]

GUIDE = """<div class="modelnote"><b>Gennemsyn af maskinforslag i tre runder.</b> Teksten er <i>allerede markeret</i> af en lille
model, trænet på Sørens markeringer fra 1841–66. <b>Kun almanakposten markeres.</b> Dagbogen samme dag kan foldes ud som hjælp (blok __DIARY__).
<ol class="steps" style="margin-top:6px">
<li><b>Runde 1, egennavne.</b> Forslag med høj sikkerhed står stiplet i teksten. Ret typen (klik og vælg), slet det, der ikke er et navn,
og markér selv det oversete. Er et forslag afgrænset forkert, så slet det og markér strengen selv.</li>
<li><b>Runde 2, omtaler.</b> Under hver post står de registerposter for dagen, som endnu ingen markering peger på. Er de omtalt uden navn
(«Kongen», «Faderen», «Lucien Bonapartes Datter»)? Markér omtalen, og vælg <i>Omtaleform</i> i markeringens redigering (egennavn / omtale uden navn / pronomen).
Angivelsen er valgfri, men meget nyttig.</li>
<li><b>Runde 3, usikre forslag.</b> Modellen er i tvivl om nogle strenge. De er <i>ikke</i> markeret i teksten, men står som en liste under posten.
Vælg en type eller «Ikke et navn» for hver. Dagen kan først afsluttes, når listen er tom.</li>__REGNOTE__
<li>Sæt flueben ved <b>Almanakposten gennemgået</b>. Forslag, der står tilbage, regnes som godkendt. Registerposten er kun et forslag; at rette den er valgfrit.</li>
</ol>
Søren og Ole gennemgår de samme poster hver for sig, så vi også kan se, hvor I er uenige. Siden måler aktiv tid pr. blok.</div>"""


REGNOTE2 = """
<li><b>Nyt i stikprøve 2.</b> Færre, men sikrere forslag; åbenlyse fællesnavne («Tænderne», «Kongen» uden støtte) foreslås ikke.
Registerkortet siger nu, om personen er mærket ÷ i almanakkens register: <i>står ikke i Dagbøgernes personregister</i> eller
<i>ikke identificeret</i>. Registrets årstal er rettet for OCR-fejl, så flere navne kobles til den rigtige dag.</li>"""

SAMPLES = {
    1: dict(blocks=REVIEW_BLOCKS, sample_id=SAMPLE_ID, prefill="review_prefill.json", diary="F og H", regnote="",
            page=dict(store="almanak-gennemsyn-maskinforslag-v1", title="Gennemsyn: maskinforslag i almanakken",
                      sub="Fire nye blokke på otte dage (1838, 1843, 1853, 1861). Modellens forslag står stiplet; ret, slet og tilføj.")),
    2: dict(blocks=REVIEW_BLOCKS_2, sample_id="review-2026-11-I-L", prefill="review_prefill2.json", diary="K og L", regnote=REGNOTE2,
            page=dict(store="almanak-gennemsyn-maskinforslag-2-v1", title="Gennemsyn 2: maskinforslag i almanakken",
                      sub="Stikprøve 2: fire nye blokke på otte dage (1840, 1844, 1857, 1860), med den nye metode. "
                          "Modellens forslag står stiplet; ret, slet og tilføj.")),
}


def review_page(sample):
    sp = SAMPLES[sample]
    return dict(sp["page"], reviewed_label="Almanakposten gennemgået", mode="review",
                guide_extra=GUIDE.replace("__DIARY__", sp["diary"]).replace("__REGNOTE__", sp["regnote"]))


REVIEW_PAGE = review_page(1)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--sample", type=int, default=1, choices=sorted(SAMPLES))
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args(argv)
    sp = SAMPLES[args.sample]
    args.out = args.out or REPO / "almanak" / "annotation" / "out" / ("almanak-gennemsyn.html" if args.sample == 1
                                                                       else f"almanak-gennemsyn{args.sample}.html")

    reg_alm, by_date, year_n = bap.load_register()
    al = {r["date"]: r for r in csv.DictReader(open(REPO / "almanak" / "data" / "extracted" / "aligned.csv", encoding="utf-8"))}
    entries, blocks, REG, ents, place_info = bop.build_entries(sp["blocks"], al, reg_alm, by_date, year_n,
                                                               require_diary=False, diary_ctx=True)
    ctx = Context()
    m = P.load_model()
    G_entries, G_gold = G.load_entries(), G.load_gold()
    nf = NounFilter(ctx, allow_from_gold((G_entries[a["post_id"]]["text"], {(a["start"], a["end"]): a["type"]})
                                         for a in G_gold if a["post_id"] in G_entries))
    prefill, stats = [], {"forslag": 0, "med registerpost": 0}
    for e in entries:
        if e["src"] != "almanak":
            continue
        assert ctx.alm[e["date"]]["text"] == e["text"], e["id"]
        linked = set()
        for s in P.annotate(ctx, m, e["date"], e["text"], low=P.LOW, nf=nf, high=P.HIGH):
            rid = s["reg"]
            if rid and rid not in REG and rid in ents:
                REG[rid] = bop.reg_entry(ents[rid], "", place_info)
            if rid and rid not in REG:
                rid = ""
            k = P.TYPE_KEY[s["type"]]
            prefill.append(dict(entry=e["id"], start=s["start"], end=s["end"], text=s["text"], type=k, mtype=k,
                                p=s["p"], reg=rid, tier=s["tier"], mkind=s["mkind"]))
            linked |= {rid} | set(s["link_candidates"])
            stats[s["tier"]] = stats.get(s["tier"], 0) + 1
            stats["forslag"] += 1
            stats["med registerpost"] += bool(rid)
        # runde 2: almanakregistrets poster for datoen, som ingen forslag peger på
        e["um"] = [r for r in sorted(ctx.alm_by_date.get(e["date"], ())) if r not in linked and r in REG]
    html = bop.render(entries, REG, blocks, args.out, prefill=prefill, page=review_page(args.sample))
    P.M.OUT.mkdir(exist_ok=True)
    (P.M.OUT / sp["prefill"]).write_text(
        json.dumps({"sample": sp["sample_id"], "blocks": blocks, "prefill": prefill}, ensure_ascii=False, indent=1), encoding="utf-8")
    n = sum(1 for e in entries if e["src"] == "almanak")
    print(f"{n} almanakposter, {stats['forslag']} forslag ({stats.get('sikker', 0)} sikre, {stats.get('usikker', 0)} usikre; "
          f"{stats['med registerpost']} med registerpost); "
          f"{len(html) // 1024} KB -> {args.out}")


if __name__ == "__main__":
    main()
