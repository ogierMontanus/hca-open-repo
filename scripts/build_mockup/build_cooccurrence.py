#!/usr/bin/env python3
"""
build_cooccurrence.py
---------------------
Builds the co-occurrence index that powers the reciprocal-link sections
on mockup/person.html, mockup/place.html, and the data-driven coPlaces /
coWorks fallback on mockup/work.html:

  • PERSON_TOP_PLACES  : { person_rid: [[place_rid,  count], …] }   (cap 12)
  • PERSON_TOP_PERSONS : { person_rid: [[person_rid, count], …] }   (cap 12)
  • PLACE_TOP_PERSONS  : { place_rid:  [[person_rid, count], …] }   (cap 12)
  • PLACE_TOP_PLACES   : { place_rid:  [[place_rid,  count], …] }   (cap 12)
  • WORK_TOP_PLACES    : { work_rid:   [[place_rid,  count], …] }   (cap 12)
  • WORK_TOP_WORKS     : { work_rid:   [[work_rid,   count], …] }   (cap 12)
  • PLACE_PERSON_INBOUND : { place_rid: [[person_rid, count], …] }  (uncapped)

Two entities co-occur once per diary page they both appear on (per
references.csv). Counts are page-level, not occurrence-level: the same
page mentioning Edvard Collin twice still counts once.

Why PLACE_PERSON_INBOUND exists — the one-way-link problem
-----------------------------------------------------------
The underlying relation is symmetric: person↔place is counted once per
shared page, identically in both directions. The CAP is what breaks
symmetry. A hub place like København shares a page with thousands of
people, so its own top-12 keeps only the twelve strongest; but for a
minor person, København easily ranks among *their* top twelve. The
result was that 84 % of the person→place links rendered under
"Hyppigste steder" had no return path: you could click from the person
to the place, and the place's card gave no way back.

PLACE_PERSON_INBOUND closes that loop. For each place it lists exactly
the persons who carry this place in their own top-12 but who are absent
from the place's top-12 — i.e. precisely the previously orphaned edges,
and nothing else (the two lists are disjoint by construction). It is
deliberately uncapped: capping it would recreate the very problem it
exists to solve. place.html paginates it instead, so a hub like
København (1,737 inbound persons) stays navigable without truncating.

Stdlib only. Reads data/normalized/{entities,references}.csv. Writes
mockup/data/cooccurrence.js. Wire as Stage 4e in scripts/build_all.py
and the CI workflow.
"""

import csv
import json
import os
import sys
from collections import Counter, defaultdict

ROOT     = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
ENTITIES = os.path.join(ROOT, "data", "normalized", "entities.csv")
REFS     = os.path.join(ROOT, "data", "normalized", "references.csv")
OUT      = os.path.join(ROOT, "mockup", "data", "cooccurrence.js")

CAP = 12        # show top-N peers per entity
MIN_COUNT = 2   # drop singleton co-occurrences (noise); keeps the file lean


def main() -> None:
    if not os.path.exists(ENTITIES) or not os.path.exists(REFS):
        sys.exit("Missing entities.csv / references.csv — run normalisation first.")

    # entity_id → entity_type ('person'|'place'|'work'|…)
    etype: dict[str, str] = {}
    with open(ENTITIES, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            t = (r.get("entity_type") or "").strip()
            if t:
                etype[r["entity_id"]] = t
    print(f"  loaded {len(etype):,} entity types")

    # (vol, page) → set of {person|place|work}_rids on that physical
    # diary page. Note: references.csv's `page_id` column is a per-row
    # primary key (one Pag* id per entity-on-page reference); the physical
    # page is identified by (vol, page) — that's the join key for
    # co-occurrence.
    persons_on_page: dict[tuple, set[str]] = defaultdict(set)
    places_on_page:  dict[tuple, set[str]] = defaultdict(set)
    works_on_page:   dict[tuple, set[str]] = defaultdict(set)
    with open(REFS, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            rid = row.get("entity_id")
            key = (row.get("vol") or "", row.get("page") or "")
            if not rid or key == ("", ""):
                continue
            t = etype.get(rid)
            if t == "person":
                persons_on_page[key].add(rid)
            elif t == "place":
                places_on_page[key].add(rid)
            elif t == "work":
                works_on_page[key].add(rid)
    print(f"  pages with persons: {len(persons_on_page):,}  "
          f"pages with places: {len(places_on_page):,}  "
          f"pages with works: {len(works_on_page):,}")

    person_place: dict[str, Counter] = defaultdict(Counter)
    person_person: dict[str, Counter] = defaultdict(Counter)
    place_person: dict[str, Counter] = defaultdict(Counter)
    place_place:  dict[str, Counter] = defaultdict(Counter)
    work_place:   dict[str, Counter] = defaultdict(Counter)
    work_work:    dict[str, Counter] = defaultdict(Counter)

    pages = set(persons_on_page) | set(places_on_page) | set(works_on_page)
    for pid in pages:
        ppl = persons_on_page.get(pid) or set()
        pls = places_on_page.get(pid) or set()
        wks = works_on_page.get(pid) or set()

        # person ↔ place
        for pr in ppl:
            for pl in pls:
                person_place[pr][pl] += 1
                place_person[pl][pr] += 1

        # person ↔ person (skip self-pair)
        ppl_list = list(ppl)
        for i, a in enumerate(ppl_list):
            for b in ppl_list[i + 1:]:
                person_person[a][b] += 1
                person_person[b][a] += 1

        # place ↔ place (skip self-pair)
        pls_list = list(pls)
        for i, a in enumerate(pls_list):
            for b in pls_list[i + 1:]:
                place_place[a][b] += 1
                place_place[b][a] += 1

        # work → place (one-way; works.html consumes WORK_TOP_PLACES)
        for wk in wks:
            for pl in pls:
                work_place[wk][pl] += 1

        # work ↔ work (skip self-pair)
        wks_list = list(wks)
        for i, a in enumerate(wks_list):
            for b in wks_list[i + 1:]:
                work_work[a][b] += 1
                work_work[b][a] += 1

    def top(c: Counter) -> list[list]:
        return [[rid, n] for rid, n in c.most_common(CAP) if n >= MIN_COUNT]

    # Drop empty lists (entities whose only peers had count<MIN_COUNT) so
    # the JS-side `length > 0` checks render cleanly.
    def trim(d):
        return {k: lst for k, lst in ((k, top(v)) for k, v in d.items()) if lst}

    person_top_places = trim(person_place)
    place_top_persons = trim(place_person)

    # Reciprocal closure for person→place (see module docstring). Every edge
    # a person shows under "Hyppigste steder" must be walkable back from the
    # place. Anything already in the place's own top-12 is skipped, so the
    # two lists never repeat each other.
    place_own: dict[str, set[str]] = {
        pl: {rid for rid, _ in lst} for pl, lst in place_top_persons.items()
    }
    inbound: dict[str, list] = defaultdict(list)
    for per, lst in person_top_places.items():
        for pl, n in lst:
            if per not in place_own.get(pl, ()):
                inbound[pl].append([per, n])
    # Strongest shared-page count first, so the first page of the paginated
    # UI is the most substantial companions rather than an arbitrary slice.
    for pl in inbound:
        inbound[pl].sort(key=lambda x: (-x[1], x[0]))
    print(f"  reciprocal closure: {sum(len(v) for v in inbound.values()):,} inbound "
          f"person→place edges across {len(inbound):,} places "
          f"(previously one-way)")

    payload = {
        "PERSON_TOP_PLACES":  person_top_places,
        "PERSON_TOP_PERSONS": trim(person_person),
        "PLACE_TOP_PERSONS":  place_top_persons,
        "PLACE_TOP_PLACES":   trim(place_place),
        "WORK_TOP_PLACES":    trim(work_place),
        "WORK_TOP_WORKS":     trim(work_work),
        "PLACE_PERSON_INBOUND": dict(inbound),
    }
    counts = {k: len(v) for k, v in payload.items()}

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("// Auto-generated by scripts/build_mockup/build_cooccurrence.py — do not hand-edit.\n")
        f.write("// Page-level co-occurrence index over references.csv. Each map is\n")
        f.write(f"// {{rid: [[other_rid, count], ...]}} capped at top {CAP} per entity.\n")
        f.write("// Consumed by mockup/person.html and mockup/place.html.\n")
        for name, data in payload.items():
            f.write(f"const {name} = ")
            f.write(json.dumps(data, ensure_ascii=False, separators=(",", ":")))
            f.write(";\n")

    print(f"  wrote {os.path.relpath(OUT, ROOT)}  "
          f"({os.path.getsize(OUT)/1024:.0f} KB)  counts={counts}")


if __name__ == "__main__":
    main()
