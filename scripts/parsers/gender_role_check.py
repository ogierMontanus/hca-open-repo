#!/usr/bin/env python3
"""
gender_role_check.py
---------------------
Advarselsflag mod uønsket "arv" af mandsdominerede erhvervsgrene hos
kvindelige poster.

Problemet: en kvindes beskrivelse nævner ofte faderens eller ægtefællens
titel ("Enke efter Sognepræst X", "g. 1867 m. Løjtnant i Søetaten, senere
Kaptajn Y", "Datter af Konsul Z"). Høsten i parse_person_role.py fjerner kun
indledende slægtskabsled og kort ægtefælleapposition, så titler lækker ind
som kvindens egen erhvervsgren.

Regel: for en post med køn "Kvindelig" i en af CHECKED_BUCKETS kræves, at
mindst ét af de termer, der gav grenen, står i personens EGEN tekst — dvs.
beskrivelsen før første ægteskabs-/enkemarkør (g. m., Enke efter, gift,
Hustru …) og uden slægtskabsled ("Datter af X", "Søster til X" …).
  * står en term i egen tekst  → status "beholdt" (advarsel bevares til gennemsyn;
                                 fx Konventualinde, Lærerinde, Diakonisse)
  * står ingen term i egen tekst → status "fjernet": grenen tages af personen.
Står personen uden gren tilbage, får hun "Kun slægtskab angivet" (hvis
beskrivelsen har slægtskabsmarkører) ellers "Endnu ukategoriseret/…"
(kolonnen `ersatz`).

Grenene: Militær, Embedsmand/Jura/Politik, Gejstlig, Handel, Håndværk,
Landbrug/Søfart og Lærd/Akademisk … (mandsdominerede, eller hvor lækage er
hyppig). Kunst, Musik, Forfatter, Adel, Gæstgiveri og Tjenestefolk
kontrolleres ikke — kvinder er almindelige dér.

Reads : build_persons_extra.load_roles() (de samlede roller), person_role.csv,
        person_role_unassigned_persons.csv, person_gender.csv, entities.csv,
        data/curated/person_role_terms_da.csv
Writes: data/normalized/person_role_gender_flags.csv  (UTF-8 med BOM — åbner
        direkte i Excel). build_persons_extra.py fjerner `fjernet`-grenene.
"""
import csv
import os
import re
import sys
from collections import Counter

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "scripts", "build_mockup"))
import build_persons_extra as bpe  # noqa: E402

N = os.path.join(ROOT, "data", "normalized")
ROLES = os.path.join(N, "person_role.csv")
CLUSTER_PERSONS = os.path.join(N, "person_role_unassigned_persons.csv")
GENDER = os.path.join(N, "person_gender.csv")
ENTITIES = os.path.join(N, "entities.csv")
TERMS = os.path.join(ROOT, "data", "curated", "person_role_terms_da.csv")
OUT = os.path.join(N, "person_role_gender_flags.csv")

CHECKED_BUCKETS = {
    "Militær", "Embedsmand/Jura/Politik", "Gejstlig", "Handel", "Håndværk", "Landbrug/Søfart",
    "Lærd/Akademisk uddannelse uden for jura og teologi",
}
FEMALE = "Kvindelig"
REL_BUCKET = "Kun slægtskab angivet"
UNCATEGORISED = "Endnu ukategoriseret/Uden for kategori/Intet kendt lønnet erhverv"

MARRIAGE_CUT_RE = re.compile(
    r"\bg\.\s*(?=\d|m\.|m\b|°)|\bg\.m\.|\bgift\b|\bEnke\b|\bEnkemand\b|\bHustru\b|\bforlovet\b|"
    r"\bFrue,\s*g\.")
KIN_CLAUSE_RE = re.compile(
    r"\b(?:Datter|Søn|Søster|Broder|Moder|Fader|Svigerdatter|Svigersøn|Plejedatter|Plejesøn|"
    r"Niece|Nevø|Kusine|Fætter|Slægtning|Stedatter|Barnebarn|Dattersøn|Sønnesøn|Søsterdatter|"
    r"Brodersøn|Søstersøn|Broderdatter|Svigerinde|Svoger)\b[^,;.]*")
WORD_RE = re.compile(r"[a-zæøåéüöä][a-zæøåéüöä'\-]*")


def own_text(desc):
    d = MARRIAGE_CUT_RE.split(desc or "", maxsplit=1)[0]
    return KIN_CLAUSE_RE.sub(" ", d)


def has_relation_markers(desc):
    return bool(MARRIAGE_CUT_RE.search(desc or "") or KIN_CLAUSE_RE.search(desc or ""))


def in_text(term, words):
    t = term.lstrip("~").lower()
    return any(w == t or w.startswith(t + "-") or w.endswith("-" + t) for w in words)


def main():
    roles, _ = bpe.load_roles()
    gender = {}
    with open(GENDER, encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            gender[r["entity_id"]] = (r["koen"], r["confidence"])
    ent = {}
    with open(ENTITIES, encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            if r["entity_type"] == "person":
                ent[r["entity_id"]] = r
    term_bucket = {}
    with open(TERMS, encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            term_bucket[r["term"].strip().lower()] = r["bucket"].strip()
    auto_terms = {}
    with open(ROLES, encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            if r["roller"]:
                auto_terms[r["entity_id"]] = [t for t in r["kilde_beskrivelse_termer"].split(";") if t]
    cluster_terms = {}
    with open(CLUSTER_PERSONS, encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            cluster_terms[r["entity_id"]] = [t for t in r["matchede_termer"].split(";") if t]

    rows, removed_by = [], {}
    stats = Counter()
    for rid, rr in roles.items():
        if gender.get(rid, ("",))[0] != FEMALE or rid not in ent:
            continue
        e = ent[rid]
        desc = e["description"] or ""
        words = WORD_RE.findall(own_text(desc).lower())
        for bucket in rr:
            if bucket not in CHECKED_BUCKETS:
                continue
            if rid in auto_terms:
                terms = [t for t in auto_terms[rid] if term_bucket.get(t.lower()) == bucket]
            else:
                terms = cluster_terms.get(rid, [])
            if not terms:
                continue  # grenen stammer ikke fra beskrivelsens fagord
            found = [t for t in terms if in_text(t, words)]
            status = "beholdt" if found else "fjernet"
            stats[(bucket, status)] += 1
            if status == "fjernet":
                removed_by.setdefault(rid, set()).add(bucket)
            rows.append({
                "entity_id": rid, "label": e["label"], "koen": FEMALE, "confidence": gender[rid][1],
                "bucket": bucket, "termer": ";".join(terms),
                "egen_tekst": " ".join(own_text(desc).split())[:120], "status": status,
                "ersatz": "", "description": desc,
            })
    for row in rows:
        rid = row["entity_id"]
        if rid in removed_by and not (set(roles[rid]) - removed_by[rid]):
            row["ersatz"] = REL_BUCKET if has_relation_markers(row["description"]) else UNCATEGORISED

    rows.sort(key=lambda r: (r["status"], r["bucket"], r["label"]))
    with open(OUT, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else ["entity_id"])
        w.writeheader()
        w.writerows(rows)
    print(f"Kvindelige poster i kontrollerede grene: {len(rows):,} (række pr. person × gren)")
    for b in sorted(CHECKED_BUCKETS):
        print(f"  {b[:38]:38} fjernet {stats[(b, 'fjernet')]:4}   beholdt {stats[(b, 'beholdt')]:4}")
    print(f"-> {OUT}")


if __name__ == "__main__":
    main()
