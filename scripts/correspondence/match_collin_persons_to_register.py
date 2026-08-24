#!/usr/bin/env python3
"""
match_collin_persons_to_register.py
-------------------------------------
Maps data/curated/collin_letters_person_index.csv (digitized from the
printed IV. PERSON-REGISTER of H. C. Andersens Brevveksling med Edvard
og Henriette Collin -- see extract_collin_person_index.py) against this
project's own PERSON-REGISTER (mockup/data/persons-extra.js), matching
on (surname, birth year) as requested -- the most reliable simple key
available: given-name spelling/abbreviation varies far more between the
two sources than a surname + a specific birth year does.

Match tiers:
  exact       surname (case/diacritic-normalized) + birth year both match
              exactly one register entry
  ambiguous   surname + birth year match MORE THAN ONE register entry
              (rare -- same surname, same birth year, different people)
  surname_only  surname matches but the register entry has no recorded
              birth year (`born` is null) -- plausible, not confirmed
  none        no register entry shares the surname at all

Nothing here is written back into entities.csv or persons-extra.js --
this only proposes matches for human verification, same shape as every
other cross-reference in this project (works_wikidata.csv,
breve_person_crosswalk.csv, collin_letters_place_index.csv, ...).

Output: data/curated/collin_letters_person_match.csv (all Collin entries
with a birth year, one row each, plus their match tier and candidate(s)).

Run from the repo root:
  python scripts/correspondence/match_collin_persons_to_register.py
"""

import csv
import json
import os
import re
import unicodedata

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
COLLIN_CSV = os.path.join(ROOT, "data", "curated", "collin_letters_person_index.csv")
PERSONS_JS = os.path.join(ROOT, "mockup", "data", "persons-extra.js")
OUT_CSV = os.path.join(ROOT, "data", "curated", "collin_letters_person_match.csv")


def load_persons_extra():
    """Isolate the PERSONS_EXTRA object literal (the file has a second
    object -- a nationality-label lookup -- appended after it) via
    bracket counting, then parse it as JSON."""
    text = open(PERSONS_JS, encoding="utf-8").read()
    start = text.index("{")
    depth = 0
    in_str = False
    esc = False
    end = None
    for i in range(start, len(text)):
        c = text[i]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
            continue
        if c == '"':
            in_str = True
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    if end is None:
        raise SystemExit("Could not find end of PERSONS_EXTRA object")
    return json.loads(text[start:end])


def normalize_surname(s):
    """Fold to a comparable key: strip accents/diacritics down to ASCII,
    uppercase, drop non-letters. æ/ø/å get their own explicit mapping
    first (NFD-stripping alone would mangle them, same reasoning as
    mockup/js/*'s own initialOf() helpers elsewhere in this project)."""
    s = (s or "").strip()
    s = s.replace("æ", "ae").replace("Æ", "AE")
    s = s.replace("ø", "o").replace("Ø", "O")
    s = s.replace("å", "aa").replace("Å", "AA")
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = re.sub(r"[^A-Za-z]", "", s)
    return s.upper()


def surname_from_label(label):
    return (label or "").split(",")[0].strip()


def main():
    print("Loading persons-extra.js …")
    persons = load_persons_extra()
    print(f"  {len(persons)} register persons loaded")

    # Index: normalized surname -> list of (reg_id, label, born, died)
    by_surname = {}
    for reg_id, p in persons.items():
        key = normalize_surname(surname_from_label(p.get("label")))
        if not key:
            continue
        by_surname.setdefault(key, []).append(
            (reg_id, p.get("label"), p.get("born"), p.get("died")))

    print("Loading Collin person index …")
    with open(COLLIN_CSV, encoding="utf-8") as f:
        collin_rows = list(csv.DictReader(f))
    print(f"  {len(collin_rows)} Collin entries")

    out_rows = []
    tiers = {"exact": 0, "ambiguous": 0, "surname_only": 0, "none": 0}
    for row in collin_rows:
        if not row["birth_year"]:
            continue  # out of scope: no birth year to match on
        key = normalize_surname(row["surname"])
        candidates = by_surname.get(key, [])
        birth_year = row["birth_year"]

        exact = [c for c in candidates if c[2] == birth_year]
        no_year_same_surname = [c for c in candidates if not c[2]]

        if len(exact) == 1:
            tier = "exact"
            matches = exact
        elif len(exact) > 1:
            tier = "ambiguous"
            matches = exact
        elif no_year_same_surname:
            tier = "surname_only"
            matches = no_year_same_surname
        elif candidates:
            # Surname matches exist but all have a DIFFERENT recorded
            # birth year -- worth surfacing as a near-miss, not silence.
            tier = "surname_year_mismatch"
            matches = candidates
        else:
            tier = "none"
            matches = []
        tiers[tier] = tiers.get(tier, 0) + 1

        out_rows.append({
            "collin_surname": row["surname"],
            "collin_given_names": row["given_names"],
            "collin_birth_year": row["birth_year"],
            "collin_death_year": row["death_year"],
            "match_tier": tier,
            "match_count": len(matches),
            "match_reg_ids": ";".join(m[0] for m in matches),
            "match_labels": " | ".join(m[1] for m in matches),
        })

    os.makedirs(os.path.dirname(OUT_CSV), exist_ok=True)
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(out_rows[0].keys()))
        w.writeheader()
        w.writerows(out_rows)
    print(f"wrote {os.path.relpath(OUT_CSV, ROOT)}  ({len(out_rows)} rows)")
    print("Tiers:", tiers)


if __name__ == "__main__":
    main()
