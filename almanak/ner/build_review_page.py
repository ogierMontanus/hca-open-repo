#!/usr/bin/env python3
"""
build_review_page.py — gennemsynsside: en NY stikprøve af almanakposter, maskinannoteret af modellen
(model.py train), som Søren og Ole retter i stedet for at markere fra bunden (§3.11).

Stikprøve: fire blokke à otte dage, ingen af dem i træningsdata:
  E 1838-09-26 – 10-03   kun almanak (ingen dagbog disse dage)
  F 1843-04-19 – 04-26   almanak + dagbog (bind II)
  G 1853-07-20 – 07-27   kun almanak
  H 1861-06-28 – 07-05   almanak + dagbog (bind V)
To blokke uden dagbog viser, hvordan modellen klarer sig uden »diary2almanac«-trækkene.

Siden genbruger annoteringssiden (template-overlap.html) i gennemsynstilstand: forslagene står stiplet;
slettede forslag og rettelser kommer med i eksporten, så præcision og overset kan måles (eval_review.py).

  python almanak/ner/build_review_page.py                       -> almanak/annotation/out/almanak-gennemsyn.html
  python almanak/ner/build_review_page.py --out mockup/almanak-gennemsyn.html
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

REVIEW_BLOCKS = [
    ("E", "1838-09-26", "1838-10-03", ""),
    ("F", "1843-04-19", "1843-04-26", "II"),
    ("G", "1853-07-20", "1853-07-27", ""),
    ("H", "1861-06-28", "1861-07-05", "V"),
]
SAMPLE_ID = "review-2026-11-E-H"

GUIDE = """<div class="modelnote"><b>Gennemsyn af maskinforslag i tre runder.</b> Teksten er <i>allerede markeret</i> af en lille
model, trænet på Sørens markeringer fra 1841–66. <b>Kun almanakposten markeres.</b> Dagbogen samme dag kan foldes ud som hjælp (blok F og H).
<ol class="steps" style="margin-top:6px">
<li><b>Runde 1, egennavne.</b> Forslag med høj sikkerhed står stiplet i teksten. Ret typen (klik og vælg), slet det, der ikke er et navn,
og markér selv det oversete. Er et forslag afgrænset forkert, så slet det og markér strengen selv.</li>
<li><b>Runde 2, omtaler.</b> Under hver post står de registerposter for dagen, som endnu ingen markering peger på. Er de omtalt uden navn
(«Kongen», «Faderen», «Lucien Bonapartes Datter»)? Markér omtalen, og vælg <i>Omtaleform</i> i markeringens redigering (egennavn / omtale uden navn / pronomen).
Angivelsen er valgfri, men meget nyttig.</li>
<li><b>Runde 3, usikre forslag.</b> Modellen er i tvivl om nogle strenge. De er <i>ikke</i> markeret i teksten, men står som en liste under posten.
Vælg en type eller «Ikke et navn» for hver. Dagen kan først afsluttes, når listen er tom.</li>
<li>Sæt flueben ved <b>Almanakposten gennemgået</b>. Forslag, der står tilbage, regnes som godkendt. Registerposten er kun et forslag; at rette den er valgfrit.</li>
</ol>
Søren og Ole gennemgår de samme poster hver for sig, så vi også kan se, hvor I er uenige. Siden måler aktiv tid pr. blok.</div>"""

LOW = 0.4   # under dette: intet forslag; mellem LOW og modellens tærskel: »usikker« (runde 3); `model.py tiers`

REVIEW_PAGE = dict(
    store="almanak-gennemsyn-maskinforslag-v1",
    title="Gennemsyn: maskinforslag i almanakken",
    sub="Fire nye blokke på otte dage (1838, 1843, 1853, 1861). Modellens forslag står stiplet; ret, slet og tilføj.",
    reviewed_label="Almanakposten gennemgået",
    guide_extra=GUIDE,
    mode="review",
)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--out", type=Path, default=REPO / "almanak" / "annotation" / "out" / "almanak-gennemsyn.html")
    args = ap.parse_args(argv)

    reg_alm, by_date, year_n = bap.load_register()
    al = {r["date"]: r for r in csv.DictReader(open(REPO / "almanak" / "data" / "extracted" / "aligned.csv", encoding="utf-8"))}
    entries, blocks, REG, ents, place_info = bop.build_entries(REVIEW_BLOCKS, al, reg_alm, by_date, year_n,
                                                               require_diary=False, diary_ctx=True)
    ctx = Context()
    m = P.load_model()
    prefill, stats = [], {"forslag": 0, "med registerpost": 0}
    for e in entries:
        if e["src"] != "almanak":
            continue
        assert ctx.alm[e["date"]]["text"] == e["text"], e["id"]
        linked = set()
        for s in P.annotate(ctx, m, e["date"], e["text"], low=LOW):
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
    html = bop.render(entries, REG, blocks, args.out, prefill=prefill, page=REVIEW_PAGE)
    P.M.OUT.mkdir(exist_ok=True)
    (P.M.OUT / "review_prefill.json").write_text(
        json.dumps({"sample": SAMPLE_ID, "blocks": blocks, "prefill": prefill}, ensure_ascii=False, indent=1), encoding="utf-8")
    n = sum(1 for e in entries if e["src"] == "almanak")
    print(f"{n} almanakposter, {stats['forslag']} forslag ({stats.get('sikker', 0)} sikre, {stats.get('usikker', 0)} usikre; "
          f"{stats['med registerpost']} med registerpost); "
          f"{len(html) // 1024} KB -> {args.out}")


if __name__ == "__main__":
    main()
