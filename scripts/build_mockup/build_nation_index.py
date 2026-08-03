#!/usr/bin/env python3
"""
build_nation_index.py
----------------------
Connects the ethnic/national adjectives extracted by
scripts/parsers/parse_person_ethnic_descriptors.py to the corresponding
nation's own entry in the place register (STED-REGISTER), and from there
to every OTHER place register entry geocoded inside that nation.

Three data sources come together here:

  1. data/curated/ethnic_adjectives_da.csv       — nationality keys
  2. data/curated/nation_place_labels_da.csv      — nationality key ->
     the exact place-register LABEL for that nation's own entry (hand-
     verified against data/normalized/entities.csv; not every key has
     one — several ethnic adjectives describe a people or region that
     was never itself entered as a place in this register, e.g. flamsk,
     kroatisk, armenisk. Those keys are reported, not silently dropped.
     The register also canonicalises some nations under a "see:"-alias
     target — Napoli, not Neapel; Venezia, not Venedig; Sverrig, not
     Sverige — the curated file already points at the canonical label.)
  3. mockup/data/places-extra.js                  — geo_source/country_da
     per place (see build_places_extra.py) — used to find every OTHER
     place register entry located inside a given nation.

Writes mockup/data/nation-index.js — a `NATION_INDEX` object consumed by
mockup/nation.html (the "mashup" page: a nation's persons + places in one
view). Degrades gracefully like every other *-extra.js: absent input
files are skipped with a warning, not a hard failure.

Person matches are split into persons_certain (the adjective was the
description's first word — see parse_person_ethnic_descriptors.py's
`position_type`) and persons_possible (embedded further in — may
describe a relative or institution instead of the register person). The
mashup page shows these as two separate groups rather than merging them,
so a person is never silently claimed as "French" on the strength of a
mention that might actually describe their French spouse.

Run after build_places_extra.py (needs its country_da output) and
parse_person_ethnic_descriptors.py (needs its match CSV).

Stdlib only.
"""

import csv
import json
import os
import re
import sys

ROOT           = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
ADJECTIVES     = os.path.join(ROOT, "data", "curated", "ethnic_adjectives_da.csv")
NATION_LABELS  = os.path.join(ROOT, "data", "curated", "nation_place_labels_da.csv")
ENTITIES       = os.path.join(ROOT, "data", "normalized", "entities.csv")
PERSON_MATCHES = os.path.join(ROOT, "data", "normalized", "person_ethnic_descriptors.csv")
WORK_LANGS     = os.path.join(ROOT, "data", "normalized", "work_languages.csv")
PLACES_EXTRA   = os.path.join(ROOT, "mockup", "data", "places-extra.js")
OUT            = os.path.join(ROOT, "mockup", "data", "nation-index.js")

# Which nationality key a work's LANGUAGE routes to. This is a language →
# nation mapping, and it is not the same claim as the person descriptors:
# a German-language book by a Danish author is German *in language only*.
# nation.html therefore renders these in their own section with their own
# heading, never merged into the "by artists from this nation" list.
# Latin is deliberately absent — it maps to no nation in this register.
LANG_TO_NATION = {
    "de": "tysk",     "fr": "fransk",  "en": "engelsk", "it": "italiensk",
    "sv": "svensk",   "da": "dansk",   "nl": "hollandsk", "es": "spansk",
    "pt": "portugisisk", "ru": "russisk", "hu": "ungarsk", "el": "græsk",
}


def load_adjectives(path):
    if not os.path.exists(path):
        sys.exit(f"Missing {path}")
    out = {}
    with open(path, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            out[row["key"]] = {"label_da": row["label_da"], "category": row["category"]}
    return out


def load_nation_labels(path):
    if not os.path.exists(path):
        return {}
    out = {}
    with open(path, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            label = row["place_label_da"].strip()
            if label:
                out[row["nationality_key"]] = label
    return out


def load_place_labels(path):
    if not os.path.exists(path):
        sys.exit(f"Missing {path}")
    labels = {}
    with open(path, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["entity_type"] == "place":
                labels[r["label"]] = r["entity_id"]
    return labels


def load_places_extra(path):
    """Returns {entity_id: country_da} — degrades to {} if the generated
    file is absent (fresh clone before Stage 4c has run)."""
    if not os.path.exists(path):
        print(f"  [!] {os.path.relpath(path, ROOT)} not found — run build_places_extra.py first. "
              f"Continuing with no places_in_country data.")
        return {}
    with open(path, encoding="utf-8") as f:
        content = f.read()
    m = re.search(r"const PLACES_EXTRA = (.*);\s*$", content, re.S)
    if not m:
        return {}
    data = json.loads(m.group(1))
    return {rid: rec.get("country_da") for rid, rec in data.items() if rec.get("country_da")}


def load_works_by_language(path):
    """{nationality_key: [entity_id, …]} from detect_work_language.py, via
    LANG_TO_NATION. Empty when that stage hasn't run."""
    out = {}
    if not os.path.exists(path):
        print(f"  [!] {os.path.relpath(path, ROOT)} not found — run "
              f"detect_work_language.py first. Continuing with no works-by-language data.")
        return out
    with open(path, encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            key = LANG_TO_NATION.get(r["lang"])
            if key:
                out.setdefault(key, []).append(r["entity_id"])
    return out


def load_person_matches(path):
    if not os.path.exists(path):
        print(f"  [!] {os.path.relpath(path, ROOT)} not found — run "
              f"parse_person_ethnic_descriptors.py first. Continuing with no person data.")
        return []
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def main():
    print(f"Loading {os.path.relpath(ADJECTIVES, ROOT)}…")
    adjectives = load_adjectives(ADJECTIVES)
    print(f"  {len(adjectives):,} nationality keys")

    print(f"Loading {os.path.relpath(NATION_LABELS, ROOT)}…")
    nation_labels = load_nation_labels(NATION_LABELS)
    print(f"  {len(nation_labels):,} keys with a curated place-register label")

    print(f"Loading {os.path.relpath(ENTITIES, ROOT)}…")
    place_label_to_id = load_place_labels(ENTITIES)
    print(f"  {len(place_label_to_id):,} place labels")

    print(f"Loading {os.path.relpath(PLACES_EXTRA, ROOT)}…")
    place_country = load_places_extra(PLACES_EXTRA)
    print(f"  {len(place_country):,} places with a resolved country_da")

    print(f"Loading {os.path.relpath(PERSON_MATCHES, ROOT)}…")
    person_matches = load_person_matches(PERSON_MATCHES)
    print(f"  {len(person_matches):,} person matches")

    print(f"Loading {os.path.relpath(WORK_LANGS, ROOT)}…")
    works_by_lang = load_works_by_language(WORK_LANGS)
    print(f"  works by language mapped to {len(works_by_lang):,} nationality keys "
          f"({sum(len(v) for v in works_by_lang.values()):,} works)")

    # nation label -> every OTHER place register entry geocoded inside it
    places_by_country = {}
    for rid, country in place_country.items():
        places_by_country.setdefault(country, []).append(rid)

    # nation label -> persons, split by confidence
    persons_certain = {}
    persons_possible = {}
    for m in person_matches:
        key = m["nationality_key"]
        bucket = persons_certain if m["position_type"] == "leading" else persons_possible
        bucket.setdefault(key, set()).add(m["entity_id"])

    index = {}
    resolved, unresolved = [], []
    for key, meta in adjectives.items():
        label = nation_labels.get(key)
        country_entity_id = place_label_to_id.get(label) if label else None
        if country_entity_id:
            resolved.append(key)
        elif label:
            unresolved.append((key, label))

        place_ids = places_by_country.get(label, []) if label else []
        place_ids = [rid for rid in place_ids if rid != country_entity_id]

        p_certain = sorted(persons_certain.get(key, set()))
        p_possible = sorted(persons_possible.get(key, set()) - persons_certain.get(key, set()))
        w_lang = sorted(works_by_lang.get(key, []))

        if not (country_entity_id or place_ids or p_certain or p_possible or w_lang):
            continue  # nothing to show for this key — skip it from the index

        index[key] = {
            "label_da":         meta["label_da"],
            "category":         meta["category"],
            "country_label":    label,
            "country_entity_id": country_entity_id,
            "places_in_country": place_ids,
            "persons_certain":  p_certain,
            "persons_possible": p_possible,
            # Works whose LANGUAGE is this nation's — a different claim from
            # authorship; kept in its own field and its own UI section.
            "works_in_language": w_lang,
        }

    print(f"\n  {len(resolved):,} keys resolved to a place-register entity")
    if unresolved:
        print(f"  {len(unresolved):,} keys have a curated label but NO matching place entity "
              f"(register doesn't carry that nation as its own entry):")
        for key, label in unresolved:
            print(f"    {key} -> {label!r}")
    no_country = sorted(set(adjectives) - set(nation_labels))
    print(f"  {len(no_country):,} keys have no curated nation label at all "
          f"(regional/historical/supranational categories mostly) — see the CSV notes column.")
    print(f"\n  {len(index):,} keys have at least one linked person/place and are in the index")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("// Auto-generated by scripts/build_mockup/build_nation_index.py — do not hand-edit.\n")
        f.write("// Links each ethnic/national adjective (data/curated/ethnic_adjectives_da.csv) to\n")
        f.write("// its nation's own place-register entry and to every other place geocoded inside\n")
        f.write("// it, plus the persons whose description carries that adjective. Consumed by\n")
        f.write("// mockup/nation.html. See docs/data-model/person-ethnic-descriptors.md.\n")
        f.write("const NATION_INDEX = ")
        f.write(json.dumps(index, ensure_ascii=False, separators=(",", ":")))
        f.write(";\n")
    print(f"  wrote {os.path.relpath(OUT, ROOT)}  ({os.path.getsize(OUT)/1024:.0f} KB)")


if __name__ == "__main__":
    main()
