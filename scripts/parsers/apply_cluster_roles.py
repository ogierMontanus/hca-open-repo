#!/usr/bin/env python3
"""
apply_cluster_roles.py
-----------------------
Fører den manuelle klynge→erhvervsgren-tildeling (K01–K20, annotationsarket
data/normalized/person_role_unassigned_annotation_,manual.xlsx, kolonne C)
ud på de personer, som parse_person_role.py ikke gav nogen rolle.

Reads : data/normalized/person_role.csv            (kun personer med tom `roller`)
        data/normalized/person_role_unassigned_persons.csv  (klynge + andre_klynger
                                                              + restgruppe)
        data/curated/person_role_cluster_buckets.csv        (klynge -> bucket)
Writes: data/normalized/person_role_manual.csv  (entity_id, roller, kilde)

  kilde = "klynge:K01;K07" for personer i en klynge (primær + sekundære),
          "adel:titel"     restgruppe R2–R4 med arvelig titel i etiketten,
          "adel:relation"  restgruppe R2–R4 med adelig slægtning (titel i
                           slægtskabs-/ægteskabsled) — arver Adel/Kongelig/Hof,
          "klynge:K11;adel:titel"  klyngepersoner, der desuden arver Adel,
          "adel+:titel|relation"   personer med automatisk rolle (person_role.csv),
                           der desuden arver Adel/Kongelig/Hof — TILLÆG, ikke
                           erstatning: build_persons_extra.py lægger Adel oven på,
          "rest:R3"        for restgruppe R3 (kun slægtskab angivet),
          "rest"           for resten (R1, R2, R4: ingen erhvervsord).

Regler:
  * Primær OG sekundære klynger tæller (som `antal_inkl_sekundaere` i arket).
  * Restkategorien (REST_BUCKET) gives kun til en person, der ellers ville stå
    uden nogen erhvervsgren — også klyngernes "Endnu ukategoriseret"-bucket
    (K19/K20) falder væk, hvis personen har en anden klynge med reel bucket.
  * Adelsarv: en person med titel i etiketten (Grevinde, Baronesse, f.
    Komtesse …) eller med en adelig slægtning ("g. m. Grev X", "Datter af
    Baron Y") får Adel/Kongelig/Hof — i stedet for restkategorien (R2–R4),
    og som TILLÆG til en eksisterende gren (klynge- eller automatisk rolle).
    Uden for R2–R4 bruges kun den stramme, ledbaserede relationsregel (titel
    og slægtskabsord i samme komma-led); den løse "titel + relationsord et
    sted i teksten" er forbeholdt de korte R2–R4-beskrivelser.
    Hofembeder (Kammerherre) er ikke slægtsbærende og tæller ikke. Fagord,
    ledere og efternavne indgår bevidst IKKE (et grådigere forsøg blev
    kasseret 2026-10-20 som for grumset).
  * Skriver ikke til person_role.csv: den er input til
    cluster_unassigned_roles.py, så kørslen forbliver idempotent.
    build_persons_extra.py lægger person_role_manual.csv ovenpå.
"""
import csv
import os
import re

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
ROLES = os.path.join(ROOT, "data", "normalized", "person_role.csv")
PERSONS = os.path.join(ROOT, "data", "normalized", "person_role_unassigned_persons.csv")
ENTITIES = os.path.join(ROOT, "data", "normalized", "entities.csv")
MAPPING = os.path.join(ROOT, "data", "curated", "person_role_cluster_buckets.csv")
OUT = os.path.join(ROOT, "data", "normalized", "person_role_manual.csv")

UNCATEGORISED = "Endnu ukategoriseret/Uden for kategori/Intet kendt lønnet erhverv"
REST_BUCKET = UNCATEGORISED
# Restgrupper (cluster_unassigned_roles.py) med egen erhvervsgren frem for
# REST_BUCKET. Nøglen er restgruppe-kolonnens præfiks ("R3 Kun slægtskab/…").
REST_GROUP_BUCKET = {
    "R3": "Kun slægtskab angivet",
}


ADEL = "Adel/Kongelig/Hof"
NOBLE_TITLES = (
    "Grev|Greve|Grevinde|Rigsgrevinde|Lensgreve|Landgreve|Baron|Baronesse|Friherre|Friherreinde|"
    "Komtesse|Fyrste|Fyrstinde|Prins|Prinsesse|Hertug|Hertuginde|Storhertug|Storhertuginde|"
    "Markis|Marquis|Marquess|Lord|Lady|Kurfyrste|Kejser|Kejserinde|Dronning|Konge|Kong|Jarl|"
    "Kongesøn|Kongedatter|Fyrstesøn|Fyrstedatter|Storfyrste|Storfyrstinde|Kronprins|Kronprinsesse|"
    "Infantinde|Infant|Visconde|Viscondessa|Viscount|Earl|Duke"
)
TITLE_RE = re.compile(r"\b(?:%s)\b" % NOBLE_TITLES)
RELATION_WORD_RE = re.compile(
    r"\b(?:Datter|Søn|Søster|Broder|Enke|Enkemand|Hustru|Svigerdatter|Svigersøn|Plejedatter|"
    r"Plejesøn|Niece|Nevø|Fætter|Kusine|Moder|Fader|Slægtning|Stedatter|Stedsøn|Dattersøn|"
    r"Sønnesøn|Barnebarn)\b|\bg\.\s*(?:\d{4}\s*)?(?:\d\s*°\s*)?m\.|\bg\.\s*m\.|\bgift\b|\bm\.\s")
# "Grev Holcks Svigersøn": titlen tilhører en anden end slægtningen.
GENITIVE_TITLE_RE = re.compile(r"\w+(?:s|’s|'s)\s+(?:%s)\b" % NOBLE_TITLES)


def noble_signal(label, desc, loose=False):
    """'titel' (arvelig titel i etiketten efter efternavnet), 'relation'
    (titel i et slægtskabs-/ægteskabsled) eller None. loose=True tillader
    desuden titel og slægtskabsord i forskellige led (kun R2–R4)."""
    rest = re.sub(r"\(.*?\)", "", label.split(",", 1)[1]) if "," in label else ""
    if TITLE_RE.search(rest):
        return "titel"
    for clause in re.split(r"[;,]", desc or ""):
        if TITLE_RE.search(clause) and RELATION_WORD_RE.search(clause) \
                and not GENITIVE_TITLE_RE.search(clause):
            return "relation"
    # Titlen i et eget komma-led ("Datter af X, Grev, g. m. Y")
    if loose and TITLE_RE.search(desc or "") and RELATION_WORD_RE.search(desc or "") \
            and not GENITIVE_TITLE_RE.search(desc or ""):
        return "relation"
    return None


def main():
    with open(MAPPING, encoding="utf-8", newline="") as f:
        cluster_bucket = {r["klynge"]: r["bucket"] for r in csv.DictReader(f)}
    with open(PERSONS, encoding="utf-8", newline="") as f:
        clusters_by_person, restgroup_by_person, text_by_person = {}, {}, {}
        for r in csv.DictReader(f):
            ks = [r["klynge"]] + (r["andre_klynger"] or "").split(";")
            clusters_by_person[r["entity_id"]] = [k for k in ks if k]
            restgroup_by_person[r["entity_id"]] = (r["restgruppe"] or "").split(" ", 1)[0]
            text_by_person[r["entity_id"]] = (r["label"] or "", r["description"] or "")

    rows, n_cluster, n_group, n_rest, n_adel, n_plus = [], 0, 0, 0, 0, 0
    auto_ids = set()
    with open(ROLES, encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            if r["roller"]:
                if ADEL not in r["roller"].split(";"):
                    auto_ids.add(r["entity_id"])
                continue
            rid = r["entity_id"]
            ks = clusters_by_person.get(rid, [])
            buckets = []
            for k in ks:
                b = cluster_bucket[k]
                if b not in buckets:
                    buckets.append(b)
            real = [b for b in buckets if b != UNCATEGORISED]
            group = restgroup_by_person.get(rid, "")
            label, desc = text_by_person.get(rid, ("", ""))
            if real:
                kind = noble_signal(label, desc) if ADEL not in real else None
                rows.append((rid, ";".join(real + ([ADEL] if kind else [])),
                             "klynge:" + ";".join(ks) + (";adel:" + kind if kind else "")))
                n_cluster += 1
                n_adel += bool(kind)
            elif buckets and noble_signal(label, desc):
                rows.append((rid, ADEL,
                             "klynge:" + ";".join(ks) + ";adel:" + noble_signal(label, desc)))
                n_cluster += 1
                n_adel += 1
            elif buckets:
                rows.append((rid, UNCATEGORISED, "klynge:" + ";".join(ks)))
                n_cluster += 1
            elif group in ("R2", "R3", "R4") and noble_signal(label, desc, loose=True):
                rows.append((rid, ADEL, "adel:" + noble_signal(label, desc, loose=True)))
                n_adel += 1
            elif group in REST_GROUP_BUCKET:
                rows.append((rid, REST_GROUP_BUCKET[group], "rest:" + group))
                n_group += 1
            else:
                rows.append((rid, REST_BUCKET, "rest"))
                n_rest += 1

    # Personer med automatisk rolle: Adel som tillæg.
    with open(ENTITIES, encoding="utf-8", newline="") as f:
        for e in csv.DictReader(f):
            if e["entity_type"] != "person" or e["entity_id"] not in auto_ids:
                continue
            kind = noble_signal(e["label"] or "", e["description"] or "")
            if kind:
                rows.append((e["entity_id"], ADEL, "adel+:" + kind))
                n_plus += 1

    with open(OUT, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["entity_id", "roller", "kilde"])
        w.writerows(rows)
    print(f"{len(rows):,} rækker: {n_cluster:,} via klynge, {n_adel:,} adelsarv i klynge/rest, "
          f"{n_plus:,} adelstillæg til automatisk rolle, {n_group:,} via egen "
          f"restgruppe-gren, {n_rest:,} restkategori -> {OUT}")


if __name__ == "__main__":
    main()
