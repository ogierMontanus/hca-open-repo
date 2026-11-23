#!/usr/bin/env python3
"""
ner_page_grounding.py
----------------------
Lokaliserer forekomst-strenge i dagbogsteksten for de entiteter, som
`data/normalized/references.csv` allerede siger er knyttet til en given
side. Dette er IKKE åben NER-udtræk: `entity_id` er kendt på forhånd
(facit er `references.csv`), og opgaven er alene at finde og skelne de
konkrete strenge i sidens rå tekst — se
docs/data-model/ner-page-task.md for den fulde opgavedefinition.

Kilder:
    data/normalized/references.csv  — facit: side↔entitet-links (kun
                                       entity_type person/place bruges;
                                       'work' er uden for scope)
    data/normalized/entities.csv    — kun brugt til entity_type-filter
    data/normalized/diary.csv       — rå sidetekst. Én side kan bestå af
                                       flere rækker (afsnit/sektioner);
                                       de sammenkædes i filens rækkefølge.

diary.csv dækkede først kun 751 sider (bind VI–VII); 2026-11 har den
tekst for 4.412 af de 4.541 sider i references.csv (alle bind). Kun referencerækker, hvor sidens tekst rent faktisk
findes i diary.csv, kan groundes — resten springes stiltiende over
(rapporteret i opsummeringen, ikke skrevet som "no_match", da fravær
af kildetekst er noget andet end et forgæves match-forsøg).

Metode (regelbaseret grundlinje, ikke NLP-model):
    1. For hver entitet i sidens facit-liste udledes søgeformer af
       `entity_label`: efternavn (delen før første komma) og første
       fornavn (delen mellem komma og evt. årstalsparentes).
    2. Efternavn og fornavn søges hver for sig i sidens tekst
       (helordsmatch, store/små bogstaver ignoreres). Findes begge
       inden for kort afstand af hinanden, slås de sammen til ét
       højsikkert fund ("fuldt navn"). Ellers er et efternavns-match
       middel sikkert, et enligt fornavns-match lavt sikkert.
    3. Stedentiteter matches som hele mærkatet (evt. faldende til
       første ord for flerords-stednavne).
    4. Alle kandidat-fund på en side sorteres efter confidence og
       tildeles grådigt til ikke-overlappende tekst-spans —
       hvert tegn-span går til højst én entitet (1:1-princippet i
       opgavedefinitionen). Der beholdes højst
       `--max-mentions-per-entity` fund pr. entitet (heuristikken om
       1-5 forekomster pr. side).
    5. Entiteter i facit-listen uden noget fund får én "no_match"-række
       med confidence 0.0, så mangelen er synlig og ikke stiltiende.
    6. Krydsreference-mærkater ("X, se: Y") kan ikke matches meningsfuldt
       ud fra selve mærkatet og markeres "cross_reference_unresolved"
       uden forsøg på tekstsøgning.

Output:
    data/normalized/ner_page_grounding.csv   — alle forslagsrækker
    data/normalized/ner_page_grounding_review.csv
        — delmængde under --min-conf, til menneskelig gennemgang

Dette script skriver IKKE til references.csv. Det er et rent
forslags-lag, samme adskillelses-princip som wikidata_lookup.py.

Kør:
    python scripts/parsers/ner_page_grounding.py
    python scripts/parsers/ner_page_grounding.py --min-conf 0.7

Kun standardbiblioteket (+ name_matching.py i samme mappe).

Revision 2026-11 (docs/plan-streng-grounding.md §3.11): søgningen sker i en
løbende version af teksten (linjetags fjernet, orddeling samlet) via
name_matching.py, med stavevarianter, krav om stort begyndelsesbogstav,
fuldt navn kun ved nabostilling, én-tegns-varianter og titel medtaget.
Offsets skrives stadig i sidens rå tekst. Metoderne hedder nu
full_name, surname_only, surname_variant, given_name_only, place_label,
place_variant, place_first_word, no_match, cross_reference_unresolved.
"""

from __future__ import annotations

import argparse
import csv
import os
import re
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import name_matching as nm  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
REFERENCES = os.path.join(ROOT, "data", "normalized", "references.csv")
ENTITIES = os.path.join(ROOT, "data", "normalized", "entities.csv")
DIARY = os.path.join(ROOT, "data", "normalized", "diary.csv")

OUT = os.path.join(ROOT, "data", "normalized", "ner_page_grounding.csv")
OUT_REVIEW = os.path.join(ROOT, "data", "normalized", "ner_page_grounding_review.csv")

IN_SCOPE_TYPES = {"person", "place"}

MAX_MENTIONS_PER_ENTITY_DEFAULT = 5
FULL_NAME_GAP = re.compile(r"^(?:\s+|\s*[A-ZÆØÅ][a-zæøå]*\.?\s*){0,2}$")  # fornavn [mellemnavn/initial] efternavn
CROSS_REF = re.compile(r",?\s*se:\s*", re.IGNORECASE)


REJECT: set[str] = set()   # sættes i main(): korpusnavneord (»en Billet«)


def candidate_mentions(entity_id: str, entity_label: str, entity_type: str, view: nm.TextView):
    """Yield (start, end, confidence, method) i view-koordinater (løbende tekst).

    Regler (rev. 2026-11, docs/plan-streng-grounding.md §3.10–3.11):
      * stavevarianter aa/å, kj/k/c, w/v, ph/f, th/t, ö/ø, accenter, O’Neill/O Neill, genitiv-s
      * navnet skal stå med stort begyndelsesbogstav (»hans« er ikke fornavnet Hans)
      * fuldt navn kun når fornavn og efternavn står ved siden af hinanden (højst en initial imellem)
      * én tegnforskel (Brun/Bruun) for navne ≥ 5 bogstaver, lavere sikkerhed
      * titel/rolle lige foran medtages i spændet
    """
    if CROSS_REF.search(entity_label) and entity_type == "person" and "," not in entity_label.split("se:")[0]:
        yield None, None, 0.0, "cross_reference_unresolved"
        return
    if entity_type == "person":
        surnames, given = nm.person_forms(entity_label)
        s_hits = sorted({h for f in surnames for h in nm.find(view, f)})
        g_hits = sorted({h for f in given for h in nm.find(view, f)})
        used = set()
        for s, e in s_hits:
            full = None
            for gi, (gs, ge) in enumerate(g_hits):
                if gi not in used and ge <= s and FULL_NAME_GAP.match(view.text[ge:s]):
                    full = gi
            if full is not None:
                used.add(full)
                yield g_hits[full][0], e, 0.90, "full_name"
            else:
                yield s, e, (0.55 if len(surnames[0]) > 5 else 0.45), "surname_only"
        for gi, (gs, ge) in enumerate(g_hits):
            if gi not in used:
                yield gs, ge, 0.30, "given_name_only"
        if not s_hits:
            for f in surnames:
                for s, e in nm.fuzzy_find(view, f, exclude=g_hits, reject=REJECT):
                    yield s, e, 0.35, "surname_variant"
    elif entity_type == "place":
        forms, fallback = nm.place_forms(entity_label)
        hits = sorted({h for f in forms for h in nm.find(view, f)})
        for s, e in hits:
            yield s, e, 0.85, "place_label"
        if not hits:
            fz = sorted({h for f in forms for h in nm.fuzzy_find(view, f, reject=REJECT)})
            for s, e in fz:
                yield s, e, 0.45, "place_variant"
            if not fz and fallback:
                for s, e in nm.find(view, fallback):
                    yield s, e, 0.50, "place_first_word"


def ground_page(entities_on_page: list[dict], text: str, max_mentions: int) -> list[dict]:
    """entities_on_page: list of {entity_id, entity_label, entity_type, ref_page_id}.
    start/end i resultatet er offsets i sidens rå `text` (linjetags medregnet)."""
    view = nm.TextView(text)
    raw = []
    for ent in entities_on_page:
        for start, end, conf, method in candidate_mentions(
            ent["entity_id"], ent["entity_label"], ent["entity_type"], view
        ):
            if start is not None and ent["entity_type"] == "person":
                start = nm.extend_title(view, start)
            raw.append({**ent, "start": start, "end": end, "confidence": conf, "method": method})

    matched = [r for r in raw if r["start"] is not None]
    unmatched_special = [r for r in raw if r["start"] is None]

    matched.sort(key=lambda r: (-r["confidence"], -(r["end"] - r["start"])))
    consumed: list[tuple[int, int]] = []
    accepted_by_entity: dict[str, list[dict]] = defaultdict(list)
    for r in matched:
        s, e = r["start"], r["end"]
        if any(s < ce and cs < e for cs, ce in consumed):
            continue
        if len(accepted_by_entity[r["entity_id"]]) >= max_mentions:
            continue
        consumed.append((s, e))
        accepted_by_entity[r["entity_id"]].append(r)

    out = []
    for ent in entities_on_page:
        rows = accepted_by_entity.get(ent["entity_id"], [])
        if rows:
            for r in sorted(rows, key=lambda r: r["start"]):
                rs, re_ = view.raw_span(r["start"], r["end"])
                out.append({**r, "start": rs, "end": re_, "mention": text[rs:re_]})
            continue
        special = [r for r in unmatched_special if r["entity_id"] == ent["entity_id"]]
        if special:
            out.append({**special[0], "mention": ""})
        else:
            out.append({**ent, "start": None, "end": None, "mention": "",
                        "confidence": 0.0, "method": "no_match"})
    return out


def load_entity_types() -> dict[str, str]:
    with open(ENTITIES, encoding="utf-8") as f:
        return {r["entity_id"]: r["entity_type"] for r in csv.DictReader(f)}


def load_references_by_page(entity_types: dict[str, str]) -> dict[tuple[str, str], list[dict]]:
    by_page: dict[tuple[str, str], list[dict]] = defaultdict(list)
    with open(REFERENCES, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            etype = entity_types.get(r["entity_id"])
            if etype not in IN_SCOPE_TYPES:
                continue
            key = (r["vol"], r["page"])
            by_page[key].append({
                "ref_page_id": r["page_id"],
                "entity_id": r["entity_id"],
                "entity_label": r["entity_label"],
                "entity_type": etype,
                "vol": r["vol"],
                "page": r["page"],
            })
    return by_page


def load_diary_text_by_page() -> dict[tuple[str, str], str]:
    parts: dict[tuple[str, str], list[str]] = defaultdict(list)
    with open(DIARY, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            parts[(r["vol"], r["page"])].append(r["text"])
    return {k: "\n".join(v) for k, v in parts.items()}


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--min-conf", type=float, default=0.6,
                    help="Tærskel under hvilken rækker havner i review-CSV'en (default 0.6)")
    ap.add_argument("--max-mentions-per-entity", type=int,
                    default=MAX_MENTIONS_PER_ENTITY_DEFAULT,
                    help="Loft over accepterede fund pr. entitet pr. side (default 5)")
    args = ap.parse_args()

    for path in (REFERENCES, ENTITIES, DIARY):
        if not os.path.exists(path):
            sys.exit(f"Mangler {path} — kør scripts/normalization/hca_xlsx_to_csv.py først.")

    entity_types = load_entity_types()
    refs_by_page = load_references_by_page(entity_types)
    diary_text_by_page = load_diary_text_by_page()

    # Kun korpusnavneord afvises som varianter. Andre registrerede navne afvises IKKE: registret knytter
    # netop denne entitet til siden, så »Block« på en side med Bloch, Carl er sandsynligvis Bloch
    # (afprøvet 2026-11: at afvise kendte navne kostede flere rigtige end forkerte fund).
    REJECT.update(nm.corpus_nouns(diary_text_by_page.values()))

    groundable_pages = [k for k in refs_by_page if k in diary_text_by_page]
    ungroundable_ref_rows = sum(
        len(v) for k, v in refs_by_page.items() if k not in diary_text_by_page
    )

    results = []
    for key in groundable_pages:
        text = diary_text_by_page[key]
        page_rows = ground_page(refs_by_page[key], text, args.max_mentions_per_entity)
        results.extend(page_rows)

    fieldnames = ["ref_page_id", "vol", "page", "entity_id", "entity_label",
                  "mention_text", "mention_start", "mention_end", "confidence", "method"]
    with open(OUT, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in results:
            w.writerow({
                "ref_page_id": r["ref_page_id"],
                "vol": r["vol"],
                "page": r["page"],
                "entity_id": r["entity_id"],
                "entity_label": r["entity_label"],
                "mention_text": r["mention"],
                "mention_start": r["start"] if r["start"] is not None else "",
                "mention_end": r["end"] if r["end"] is not None else "",
                "confidence": round(r["confidence"], 3),
                "method": r["method"],
            })

    review = [r for r in results if r["confidence"] < args.min_conf]
    with open(OUT_REVIEW, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in review:
            w.writerow({
                "ref_page_id": r["ref_page_id"],
                "vol": r["vol"],
                "page": r["page"],
                "entity_id": r["entity_id"],
                "entity_label": r["entity_label"],
                "mention_text": r["mention"],
                "mention_start": r["start"] if r["start"] is not None else "",
                "mention_end": r["end"] if r["end"] is not None else "",
                "confidence": round(r["confidence"], 3),
                "method": r["method"],
            })

    by_method = defaultdict(int)
    for r in results:
        by_method[r["method"]] += 1

    print(f"Sider med facit-entiteter: {len(refs_by_page):,}")
    print(f"  heraf med kildetekst i diary.csv: {len(groundable_pages):,}")
    print(f"  facit-rækker uden kildetekst (sprunget over): {ungroundable_ref_rows:,}")
    print(f"Groundede facit-rækker (person/place): {len(results):,}")
    for method, n in sorted(by_method.items(), key=lambda kv: -kv[1]):
        print(f"  {method}: {n:,}")
    print(f"Skrev {os.path.relpath(OUT, ROOT)}")
    print(f"Skrev {os.path.relpath(OUT_REVIEW, ROOT)} ({len(review):,} rækker under {args.min_conf})")


if __name__ == "__main__":
    main()
