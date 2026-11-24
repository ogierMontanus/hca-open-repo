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
  python almanak/ner/build_review_page.py --sample 3 --out mockup/gennemsyn_dagbog3.html     # to dagbogssider
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


# Stikprøve 3: DAGBOGEN, to sider (bind III s. 178–179, september 1846), samme model og grænser som stikprøve 2.
DIARY_SAMPLE = dict(vol="III", pages=("178", "179"), block="M")

GUIDE3 = """<div class="modelnote"><b>Gennemsyn af maskinforslag i dagbogen: to sider.</b> Samme model og samme grænser som
i almanakgennemsynet (stikprøve 2), men her på <i>dagbogsteksten</i> (bind III, s. 178–179). Modellen er trænet på Sørens markeringer
i både almanak og dagbog; i krydsvalideringen er dagbogen svagere (sikre forslag: præcision ca. 0,76, recall ca. 0,55).
<ol class="steps" style="margin-top:6px">
<li><b>Runde 1, egennavne.</b> Forslag med høj sikkerhed står stiplet i teksten. Ret typen (klik og vælg), slet det, der ikke er et navn,
og markér selv det oversete. Er et forslag afgrænset forkert, så slet det og markér strengen selv.</li>
<li><b>Runde 3, usikre forslag.</b> Modellen er i tvivl om nogle strenge, eller et registerstøttet forslag ligger lavt. De er <i>ikke</i> markeret i teksten,
men står som en liste under dagen. Vælg en type eller «Ikke et navn» for hver. Dagen kan først afsluttes, når listen er tom.</li>
<li>Under hver dag står de registerposter, som dagbogsregistret knytter til siderne (som i overlap-stikprøven). Registerposten på en markering er kun et forslag.</li>
<li>Sæt flueben ved <b>Dagen gennemgået</b>. Forslag, der står tilbage, regnes som godkendt.</li>
</ol></div>"""

REGNOTE2 = """
<li><b>Nyt i stikprøve 2.</b> Færre, men sikrere forslag; åbenlyse fællesnavne («Tænderne», «Kongen» uden støtte) foreslås ikke.
Registerkortet siger nu, om personen er mærket ÷ i almanakkens register: <i>står ikke i Dagbøgernes personregister</i> eller
<i>ikke identificeret</i>. Registrets årstal er rettet for OCR-fejl, så flere navne kobles til den rigtige dag.</li>"""

SAMPLES = {
    1: dict(blocks=REVIEW_BLOCKS, sample_id=SAMPLE_ID, prefill="review_prefill.json", diary="F og H", regnote="",
            page=dict(store="almanak-gennemsyn-maskinforslag-v1", title="Gennemsyn: maskinforslag i almanakken",
                      sub="Fire nye blokke på otte dage (1838, 1843, 1853, 1861). Modellens forslag står stiplet; ret, slet og tilføj.")),
    3: dict(kind="diary", blocks=None, sample_id="review-2026-11-dagbog-III-178-179", prefill="review_prefill3.json", diary="",
            regnote="",
            page=dict(store="dagbog-gennemsyn-maskinforslag-3-v1", title="Gennemsyn 3: maskinforslag i dagbogen",
                      sub="To dagbogssider (bind III, s. 178–179, september 1846). Modellens forslag står stiplet; ret, slet og tilføj.")),
    2: dict(blocks=REVIEW_BLOCKS_2, sample_id="review-2026-11-I-L", prefill="review_prefill2.json", diary="K og L", regnote=REGNOTE2,
            page=dict(store="almanak-gennemsyn-maskinforslag-2-v1", title="Gennemsyn 2: maskinforslag i almanakken",
                      sub="Stikprøve 2: fire nye blokke på otte dage (1840, 1844, 1857, 1860), med den nye metode. "
                          "Modellens forslag står stiplet; ret, slet og tilføj.")),
}


def review_page(sample):
    sp = SAMPLES[sample]
    if sp.get("kind") == "diary":
        return dict(sp["page"], reviewed_label="Dagen gennemgået", mode="review", guide_extra=GUIDE3)
    return dict(sp["page"], reviewed_label="Almanakposten gennemgået", mode="review",
                guide_extra=GUIDE.replace("__DIARY__", sp["diary"]).replace("__REGNOTE__", sp["regnote"]))


REVIEW_PAGE = review_page(1)


def build_diary_entries(reg_alm):
    """Dagbogsdage, hvis tekst kun ligger på de to sider -> ENTRIES (kun dagbog), BLOCKS, REG, ents, place_info."""
    vol, pages, key = DIARY_SAMPLE["vol"], set(DIARY_SAMPLE["pages"]), DIARY_SAMPLE["block"]
    pgset = {(vol, p) for p in pages}
    rows = [r for r in G.diary_rows() if (r["vol"], r["page"]) in pgset and not r["date"].endswith("XX")]
    first, last = min(r["date"] for r in rows), max(r["date"] for r in rows)
    diary = bop.load_diary(first, last)
    days = sorted(d for d, (t, pg) in diary.items() if set(pg) <= pgset)
    refs, ents = bop.load_page_refs(list(pgset))
    kb, place_info = bop.load_kb(), bop.load_place_info()
    entries = []
    for d in days:
        text, dpages = diary[d]
        pgs = []
        for p in dpages:
            if p not in [(x["v"], x["p"]) for x in pgs]:
                pgs.append(dict(v=p[0], p=p[1], kb=kb.get(p, "")))
        ed = dict(id="DAG-" + d, date=d, wd=bop.bap._weekday(d), src="dagbog", block=key, tv=bop.TV_DAG,
                  page=f"{pgs[0]['v']}:{pgs[0]['p']}" + (f"-{pgs[-1]['p']}" if len(pgs) > 1 else ""), pages=pgs, text=text, dbdiff=[])
        ed["c"] = bop.diary_candidates(text, [(p["v"], p["p"]) for p in pgs], refs, ents)
        entries.append(ed)
    blocks = [dict(id=key, first=days[0], last=days[-1], vol=vol, n=len(days))]
    REG = {rid: {k: v for k, v in info.items() if k != "see"} for rid, info in reg_alm.items() if not info["see"]}
    for e in entries:
        for eid, _ in e["c"]:
            if eid not in REG:
                REG[eid] = bop.reg_entry(ents[eid], e["page"], place_info)
    return entries, blocks, REG, ents, place_info


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
    if sp.get("kind") == "diary":
        entries, blocks, REG, ents, place_info = build_diary_entries(reg_alm)
    else:
        entries, blocks, REG, ents, place_info = bop.build_entries(sp["blocks"], al, reg_alm, by_date, year_n,
                                                                   require_diary=False, diary_ctx=True)
    ctx = Context()
    m = P.load_model()
    G_entries, G_gold = G.load_entries(), G.load_gold()
    nf = NounFilter(ctx, allow_from_gold((G_entries[a["post_id"]]["text"], {(a["start"], a["end"]): a["type"]})
                                         for a in G_gold if a["post_id"] in G_entries))
    prefill, stats = [], {"forslag": 0, "med registerpost": 0}
    for e in entries:
        if e["src"] == "almanak":
            assert ctx.alm[e["date"]]["text"] == e["text"], e["id"]
        elif sp.get("kind") != "diary":
            continue
        linked = set()
        for s in P.annotate(ctx, m, e["date"], e["text"], low=P.LOW, nf=nf, high=P.HIGH, src=e["src"]):
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
        if e["src"] == "almanak":
            e["um"] = [r for r in sorted(ctx.alm_by_date.get(e["date"], ())) if r not in linked and r in REG]
    html = bop.render(entries, REG, blocks, args.out, prefill=prefill, page=review_page(args.sample))
    P.M.OUT.mkdir(exist_ok=True)
    (P.M.OUT / sp["prefill"]).write_text(
        json.dumps({"sample": sp["sample_id"], "blocks": blocks, "prefill": prefill}, ensure_ascii=False, indent=1), encoding="utf-8")
    n = sum(1 for e in entries if e["src"] == ("dagbog" if sp.get("kind") == "diary" else "almanak"))
    print(f"{n} {'dagbogsdage' if sp.get('kind') == 'diary' else 'almanakposter'}, {stats['forslag']} forslag ({stats.get('sikker', 0)} sikre, {stats.get('usikker', 0)} usikre; "
          f"{stats['med registerpost']} med registerpost); "
          f"{len(html) // 1024} KB -> {args.out}")


if __name__ == "__main__":
    main()
