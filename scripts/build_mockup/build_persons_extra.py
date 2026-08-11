#!/usr/bin/env python3
"""
build_persons_extra.py
----------------------
Generates mockup/data/persons-extra.js — a `PERSONS_EXTRA` JS object
with one entry per row in data/normalized/entities.csv where
entity_type == 'person'. The hand-curated `PERSONS` object inside
mockup/person.html (if any) keeps precedence; PERSONS_EXTRA fills every
other gap so any ?reg=… link to person.html resolves to real metadata
instead of a blank page.

Also emits `NATIONALITY_LABELS` — a companion const (same pattern as
build_cooccurrence.py's multiple exports) mapping each nationality key
that occurs among persons to its Danish display label. Feeds the
"Nationalitet" facet on persons.html.

Each person's `nationalities` array is populated only from LEADING
matches in data/normalized/person_ethnic_descriptors.csv (the adjective
was the description's first word) — i.e. the same persons_certain
selection used by build_nation_index.py. Embedded matches are left out
here on purpose: they may describe a relative or institution rather than
the person themself (see docs/data-model/person-ethnic-descriptors.md),
which is too uncertain to drive a filter a reader trusts at face value.

Stdlib only. Run after scripts/normalization/hca_xlsx_to_csv.py. Degrades
gracefully — nationalities stay empty and NATIONALITY_LABELS stays empty
if parse_person_ethnic_descriptors.py hasn't been run.
"""

import csv
import json
import os
import re
import sys
from collections import Counter

ROOT       = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
ENTITIES   = os.path.join(ROOT, "data", "normalized", "entities.csv")
REFS       = os.path.join(ROOT, "data", "normalized", "references.csv")
ETHNIC     = os.path.join(ROOT, "data", "normalized", "person_ethnic_descriptors.csv")
ADJECTIVES = os.path.join(ROOT, "data", "curated", "ethnic_adjectives_da.csv")
GENDER     = os.path.join(ROOT, "data", "normalized", "person_gender.csv")
OUT        = os.path.join(ROOT, "mockup", "data", "persons-extra.js")

# Life-dates parsed from labels like
#   "Aabye, Johan Peter (1818–1880)"
#   "Lyell, Mary, Lady, f. Horner (død 1873)"
#   "Aagaard, Peder (1761–1834)"
# Tolerate both en-dash and hyphen, and a "ca." prefix.
LIFE_RE   = re.compile(r"\((?:ca\.?\s*)?(\d{4})\s*[–\-]\s*(\d{4})\)")
DIED_RE   = re.compile(r"\(død\s+(\d{4})\)")


def parse_life(label: str):
    m = LIFE_RE.search(label)
    if m:
        return m.group(1), m.group(2)
    m = DIED_RE.search(label)
    if m:
        return None, m.group(1)
    return None, None


def era_for(born: str | None, died: str | None) -> str | None:
    y = born or died
    if not y:
        return None
    try:
        n = int(y)
    except ValueError:
        return None
    if n < 1700:    return "Før 1700"
    if n < 1800:    return "1700-tallet"
    if n < 1900:    return "1800-tallet"
    return "Efter 1900"


def load_nationalities():
    """Returns {entity_id: [nationality_key, ...]} from LEADING matches
    only (see module docstring), plus {key: label_da} for every key that
    actually occurs. Degrades to ({}, {}) if either input is absent."""
    if not os.path.exists(ETHNIC) or not os.path.exists(ADJECTIVES):
        return {}, {}

    labels = {}
    with open(ADJECTIVES, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            labels[row["key"]] = row["label_da"]

    by_person: dict[str, list] = {}
    used_keys = set()
    with open(ETHNIC, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            if row["position_type"] != "leading":
                continue
            key = row["nationality_key"]
            keys = by_person.setdefault(row["entity_id"], [])
            if key not in keys:
                keys.append(key)
            used_keys.add(key)

    return by_person, {k: labels[k] for k in used_keys if k in labels}


def load_gender() -> dict:
    """{entity_id: (koen, confidence)} fra parse_person_gender.py.

    Tom, hvis parseren ikke er kørt — så bliver `gender` None overalt, og
    Køn-facetten viser blot ingen rækker (FacetEngine springer tomme
    værdier over). Kategoriseringen er en FACET, ikke en påstand om den
    enkelte person: den skriver ikke til registrets øvrige felter, og
    "Endnu ubestemt" er en gyldig værdi, ikke en manglende værdi."""
    out = {}
    if not os.path.exists(GENDER):
        return out
    with open(GENDER, encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            out[r["entity_id"]] = (r["koen"], float(r["confidence"]))
    return out


def main() -> None:
    if not os.path.exists(ENTITIES):
        sys.exit(f"Missing {ENTITIES} — run scripts/normalization/hca_xlsx_to_csv.py first.")

    print(f"Loading {os.path.relpath(ENTITIES, ROOT)}…")
    persons = []
    with open(ENTITIES, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["entity_type"] == "person":
                persons.append(r)
    print(f"  {len(persons):,} persons")

    ref_count: Counter[str] = Counter()
    if os.path.exists(REFS):
        with open(REFS, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                ref_count[r["entity_id"]] += 1
        print(f"  reference counts loaded for {len(ref_count):,} entities")

    print(f"Loading {os.path.relpath(ETHNIC, ROOT)} + {os.path.relpath(ADJECTIVES, ROOT)}…")
    nationalities_by_person, nationality_labels = load_nationalities()
    print(f"  {len(nationalities_by_person):,} persons with a leading nationality match, "
          f"{len(nationality_labels):,} distinct nationality keys")

    gender_by_person = load_gender()
    if gender_by_person:
        print(f"  {len(gender_by_person):,} persons with a gender classification "
              f"(scripts/parsers/parse_person_gender.py)")
    else:
        print("  no person_gender.csv — gender facet stays empty "
              "(run scripts/parsers/parse_person_gender.py)")

    # Emit one entry per person, INCLUDING IDs that mockup/person.html
    # also curates. person.html's `ALL_PERSONS = Object.assign({},
    # PERSONS_EXTRA, PERSONS)` still gives the hand-curated entries
    # precedence; emitting the extras for them too lets EntityRefs
    # (mockup/js/entity-refs.js) see the full register from any page.
    generated: dict[str, dict] = {}
    for r in persons:
        rid = r["entity_id"]
        label = (r.get("label") or "").strip()
        born, died = parse_life(label)
        generated[rid] = {
            "label":         label,
            "description":   (r.get("description") or "").strip() or None,
            "born":          born,
            "died":          died,
            "era":           era_for(born, died),
            "refs":          ref_count.get(rid, 0),
            "nationalities": nationalities_by_person.get(rid, []),
            # Afledt facet-værdi, ikke en registreret oplysning — se
            # docs/data-model/person-gender-facet.md. genderConf bæres med,
            # så en senere UI kan skelne "høj sikkerhed" fra "sandsynlig"
            # uden at genberegne noget.
            "gender":       gender_by_person.get(rid, (None, None))[0],
            "genderConf":   gender_by_person.get(rid, (None, None))[1],
        }

    print(f"  generated {len(generated):,} entries")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("// Auto-generated by scripts/build_mockup/build_persons_extra.py — do not hand-edit.\n")
        f.write("// One entry per person in PERSON-REGISTER. The hand-curated\n")
        f.write("// PERSONS object in person.html takes precedence (see ALL_PERSONS merge).\n")
        f.write("// `nationalities` — see data/curated/ethnic_adjectives_da.csv and\n")
        f.write("// docs/data-model/person-ethnic-descriptors.md — is leading-match-only;\n")
        f.write("// NATIONALITY_LABELS below gives each key's Danish display label.\n")
        f.write("const PERSONS_EXTRA = ")
        f.write(json.dumps(generated, ensure_ascii=False, separators=(",", ":")))
        f.write(";\n")
        f.write("const NATIONALITY_LABELS = ")
        f.write(json.dumps(nationality_labels, ensure_ascii=False, separators=(",", ":")))
        f.write(";\n")
    print(f"  wrote {os.path.relpath(OUT, ROOT)}  "
          f"({os.path.getsize(OUT)/1024:.0f} KB)")


if __name__ == "__main__":
    main()
