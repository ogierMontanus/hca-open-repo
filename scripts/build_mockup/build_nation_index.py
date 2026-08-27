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
UMBRELLAS      = os.path.join(ROOT, "data", "curated", "nation_umbrellas_da.csv")
ENTITIES       = os.path.join(ROOT, "data", "normalized", "entities.csv")
PERSON_MATCHES = os.path.join(ROOT, "data", "normalized", "person_ethnic_descriptors.csv")
WORK_LANGS     = os.path.join(ROOT, "data", "normalized", "work_languages.csv")
PLACES_EXTRA   = os.path.join(ROOT, "mockup", "data", "places-extra.js")
COUNTRY_TO_NATION = os.path.join(ROOT, "data", "curated", "steder_country_to_nation_da.csv")
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


def load_country_to_nation(path):
    """Returns {xlsx_country: nation_place_label} from data/curated/
    steder_verified_categories.csv's country column having become far
    more granular than this file's own nationality vocabulary (England
    and Skotland are now distinct country_da values, not one folded
    "Storbritannien" — see docs/data-model/steder-verificeret-category-
    mapping.md and build_places_extra.py). Rows with a blank
    nation_place_label (Tjekkiet, Kroatien, the continents, ...) are
    genuinely unmapped -- no corresponding nationality key exists yet --
    and are skipped rather than guessed at; load_places_extra() below
    falls back to the raw country_da unchanged for those and for any
    country_da this crosswalk doesn't mention at all, so a value it
    doesn't know about degrades to "use it as-is" rather than vanishing."""
    out = {}
    if not os.path.exists(path):
        return out
    with open(path, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            if row.get("xlsx_country") and row.get("nation_place_label"):
                out[row["xlsx_country"]] = row["nation_place_label"]
    return out


def load_places_extra(path, country_to_nation):
    """Returns {entity_id: country_da} — degrades to {} if the generated
    file is absent (fresh clone before Stage 4c has run). Each country_da
    is passed through country_to_nation (see load_country_to_nation) so
    e.g. both "England" and "Skotland" places land in the "England"
    bucket britisk's umbrella expects, without places.html/kort.html's
    own (more granular) Country facet needing to change at all — that
    facet reads country_da directly from places-extra.js, unmapped."""
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
    return {rid: country_to_nation.get(rec["country_da"], rec["country_da"])
            for rid, rec in data.items() if rec.get("country_da")}


def load_umbrellas(path):
    """[(umbrella_key, label, place_label, [member_key, …]), …].

    An umbrella groups several nationality keys the register distinguishes
    but a reader usually does not — the pre-1871 German polities under
    Tyskland, England/Skotland/Irland under Britisk, ancient and modern
    Greece under Græsk. Membership is deliberately many-to-many: Kurland
    is German-speaking *and* Russian-annexed, the Schleswig-Holstein keys
    are Danish *and* German, finlandssvensk is Swedish *and* Finnish.
    Forcing any of those into a single parent would take a side the
    register itself does not take."""
    if not os.path.exists(path):
        return []
    out = []
    with open(path, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            members = [m.strip() for m in row["members"].split(";") if m.strip()]
            out.append((row["umbrella_key"], row["umbrella_label"],
                        row["place_label_da"].strip() or None, members))
    return out


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

    print(f"Loading {os.path.relpath(COUNTRY_TO_NATION, ROOT)}…")
    country_to_nation = load_country_to_nation(COUNTRY_TO_NATION)
    print(f"  {len(country_to_nation):,} country -> nation-bucket mappings")

    print(f"Loading {os.path.relpath(PLACES_EXTRA, ROOT)}…")
    place_country = load_places_extra(PLACES_EXTRA, country_to_nation)
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

        # Every declared key is indexed, even an empty one (badisk, hessisk —
        # attested nowhere in this register but still legitimate members of
        # the Tysk umbrella). Dropping empty keys HERE would run "does this
        # key have data" before umbrella enrollment even gets a chance to
        # pool them together; that check belongs after clustering instead
        # (see the standalone-key loop below), so it only judges a key on
        # its own once nothing has claimed it.
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
    empty_keys = sorted(
        k for k, v in index.items()
        if not (v["country_entity_id"] or v["places_in_country"] or v["persons_certain"]
                or v["persons_possible"] or v["works_in_language"])
    )
    print(f"\n  {len(index):,} keys indexed ({len(empty_keys):,} empty — no entity of their own): "
          f"{', '.join(empty_keys)}")

    # ── Umbrella roll-up ────────────────────────────────────────────────────
    # Each umbrella keeps its members' contributions SEPARATE (so the page can
    # show which sub-identity every entry came from) as well as a deduplicated
    # union (for the picker's counts and the summary line). A member may sit
    # under several umbrellas — Kurland under both Tyskland and Rusland — so
    # the two are built independently rather than by partitioning.
    umbrellas = load_umbrellas(UMBRELLAS)
    print(f"\nLoading {os.path.relpath(UMBRELLAS, ROOT)}…")
    print(f"  {len(umbrellas):,} umbrellas defined")

    grouped, member_of = {}, {}
    clustered = set()
    for ukey, ulabel, uplace, members in umbrellas:
        present = [m for m in members if m in index]
        if not present:
            continue
        clustered.update(present)
        for m in present:
            member_of.setdefault(m, []).append(ukey)

        country_label = uplace or next(
            (index[m]["country_label"] for m in present if index[m]["country_label"]), None)
        country_entity_id = place_label_to_id.get(country_label) if country_label else None

        union = {"persons_certain": [], "persons_possible": [], "places_in_country": [],
                 "works_in_language": []}
        seen = {k: set() for k in union}
        member_blocks = []
        for m in present:
            src = index[m]
            member_blocks.append({
                "key": m, "label": src["label_da"], "category": src["category"],
                "persons_certain": src["persons_certain"],
                "persons_possible": src["persons_possible"],
                "places_in_country": src["places_in_country"],
                "works_in_language": src["works_in_language"],
                "country_entity_id": src["country_entity_id"],
            })
            for field in union:
                for rid in src[field]:
                    if rid not in seen[field]:
                        seen[field].add(rid)
                        union[field].append(rid)
        # A person listed as certain under one member and only possible under
        # another is certain for the umbrella — don't report them twice.
        union["persons_possible"] = [r for r in union["persons_possible"]
                                     if r not in seen["persons_certain"]]
        # The umbrella's own country entry is a place in its own right; don't
        # also list it among "other places inside this nation".
        union["places_in_country"] = [r for r in union["places_in_country"]
                                      if r != country_entity_id]

        grouped[ukey] = {
            "label_da": ulabel, "category": "umbrella",
            "country_label": country_label, "country_entity_id": country_entity_id,
            "members": member_blocks, **union,
        }

    # Keys no umbrella claims stay top-level, as their own single-member
    # group, so nothing is lost by clustering. This is where "does this key
    # have any data at all" is judged — deliberately AFTER enrollment, and
    # only for keys enrollment left behind. A key that's empty but claimed by
    # an umbrella (badisk, hessisk under tysk) already got its chance above;
    # an empty, unclaimed key (kroatisk) would only ever produce a lonely,
    # permanently-disabled picker entry, so it's dropped here instead.
    for key, entry in index.items():
        if key in clustered:
            continue
        if not (entry["country_entity_id"] or entry["places_in_country"] or entry["persons_certain"]
                or entry["persons_possible"] or entry["works_in_language"]):
            continue
        grouped[key] = {**entry, "members": [{
            "key": key, "label": entry["label_da"], "category": entry["category"],
            "persons_certain": entry["persons_certain"],
            "persons_possible": entry["persons_possible"],
            "places_in_country": entry["places_in_country"],
            "works_in_language": entry["works_in_language"],
            "country_entity_id": entry["country_entity_id"],
        }]}
        member_of.setdefault(key, []).append(key)

    multi = {k: v for k, v in member_of.items() if len(v) > 1}
    print(f"  {len(clustered):,} keys clustered into {sum(1 for g in grouped.values() if g['category'] == 'umbrella'):,} umbrellas")
    print(f"  {len(grouped) - sum(1 for g in grouped.values() if g['category'] == 'umbrella'):,} keys left standalone")
    print(f"  {len(multi):,} keys with multiple memberships: " +
          ", ".join(f"{k}→{'+'.join(v)}" for k, v in sorted(multi.items())))
    dropped_empty = sum(1 for k in empty_keys if k not in clustered)
    print(f"\n  picker goes from {len(adjectives):,} adjective keys to {len(grouped):,} entries "
          f"({dropped_empty:,} dropped as empty and unclaimed by any umbrella)")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("// Auto-generated by scripts/build_mockup/build_nation_index.py — do not hand-edit.\n")
        f.write("// NATION_INDEX is keyed by UMBRELLA (data/curated/nation_umbrellas_da.csv):\n")
        f.write("// the pre-1871 German polities roll up under 'tysk', England/Skotland/Irland\n")
        f.write("// under 'britisk', ancient + modern Greece under 'græsk'. Each entry carries a\n")
        f.write("// deduplicated union for counts AND a `members` array keeping every contributing\n")
        f.write("// nationality key separate, so nation.html can show the sub-identity each entry\n")
        f.write("// came from. Membership is many-to-many — NATION_MEMBER_OF maps a nationality\n")
        f.write("// key to every umbrella that claims it.\n")
        f.write("// See docs/data-model/person-ethnic-descriptors.md.\n")
        f.write("const NATION_INDEX = ")
        f.write(json.dumps(grouped, ensure_ascii=False, separators=(",", ":")))
        f.write(";\n")
        f.write("const NATION_MEMBER_OF = ")
        f.write(json.dumps(member_of, ensure_ascii=False, separators=(",", ":")))
        f.write(";\n")
    print(f"  wrote {os.path.relpath(OUT, ROOT)}  ({os.path.getsize(OUT)/1024:.0f} KB)")


if __name__ == "__main__":
    main()
