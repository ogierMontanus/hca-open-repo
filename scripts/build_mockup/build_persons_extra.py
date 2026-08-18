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

Also emits `wd` (Wikidata QID, currently always null — see
load_person_wikidata()) and `bioLinks` (a broad, non-asserting biographical
search link for Lex.dk/Deutsche Biographie/VIAF, added only when `wd` is
absent — see docs/data-model/person-bio-search-links.md for the full rule).

Stdlib only. Run after scripts/normalization/hca_xlsx_to_csv.py. Degrades
gracefully — nationalities stay empty and NATIONALITY_LABELS stays empty
if parse_person_ethnic_descriptors.py hasn't been run.
"""

import csv
import json
import os
import re
import sys
import urllib.parse
from collections import Counter

ROOT       = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
ENTITIES   = os.path.join(ROOT, "data", "normalized", "entities.csv")
REFS       = os.path.join(ROOT, "data", "normalized", "references.csv")
ETHNIC     = os.path.join(ROOT, "data", "normalized", "person_ethnic_descriptors.csv")
ADJECTIVES = os.path.join(ROOT, "data", "curated", "ethnic_adjectives_da.csv")
UMBRELLAS  = os.path.join(ROOT, "data", "curated", "nation_umbrellas_da.csv")
GENDER     = os.path.join(ROOT, "data", "normalized", "person_gender.csv")
ROLE       = os.path.join(ROOT, "data", "normalized", "person_role.csv")
WIKIDATA   = os.path.join(ROOT, "data", "curated", "persons_wikidata.csv")
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


def load_roles() -> dict:
    """{entity_id: [bucket, ...]} fra parse_person_role.py — VÆRK-REGISTER-
    optræden kombineret med en høstet klassificering af beskrivelsesfeltet
    (se docs/data-model/person-role-facet.md). Ligesom Køn er dette en
    AFLEDT facet-værdi: en person uden match får en tom liste, hvilket
    FacetEngine viser som "ingen rolle fundet" snarere end en fejl.

    Tom, hvis parseren ikke er kørt."""
    out = {}
    if not os.path.exists(ROLE):
        return out
    with open(ROLE, encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            roller = [x for x in (r.get("roller") or "").split(";") if x]
            if roller:
                out[r["entity_id"]] = roller
    return out


def load_person_wikidata() -> dict:
    """{entity_id: wd_qid} from an optional data/curated/persons_wikidata.csv
    (rid,wd — same shape as works_wikidata.csv). No such file exists yet as
    of this writing (only mockup/person.html's own small hand-curated demo
    entry, Dickens/Q5686, carries a wd value, and that page isn't the one
    linked from the live register — persons.html is). This loader exists so
    the "already has an authority link" check below is forward-compatible:
    if a curated overlay is added later, bio_search_links() picks it up
    automatically and stops suggesting a search link for those persons,
    with no code change needed."""
    out = {}
    if not os.path.exists(WIKIDATA):
        return out
    with open(WIKIDATA, encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            wd = (r.get("wd") or "").strip()
            if wd:
                out[r["entity_id"]] = wd
    return out


def load_nation_umbrellas() -> dict:
    """{umbrella_key: {member_key, ...}} from data/curated/nation_umbrellas_da.csv
    — the same clustering nation.html itself uses (e.g. "Tyskland" groups
    tysk with every pre-1871 German state: preussisk, sachsisk, bayersk...).
    Reused here rather than re-deriving a narrower "German states" list by
    hand, so a person bio_search_links() calls German is exactly the same
    set of persons nation.html's own Tyskland page would show — including
    the deliberately dual-membership Schleswig-Holstein keys (holstensk,
    slesvigholstensk, holstenlauenborgsk), which count as BOTH Danish and
    German per that CSV's own documented rationale (the duchies were the
    contested ground of the 1848-51 and 1864 wars; picking one nation for
    them would take a side the register does not take)."""
    out = {}
    if not os.path.exists(UMBRELLAS):
        return out
    with open(UMBRELLAS, encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            out[r["umbrella_key"]] = set((r.get("members") or "").split(";"))
    return out


# Strips a label's trailing "(1805–1875)" / "(død 1918)" / "(ca. 1866–…)"
# date parenthetical, but NOT a mid-string one — "Reventlow, Frederik
# (Fritz), Greve (1791–1851)" must keep the "(Fritz)" nickname and only
# lose the trailing date, since only the trailing one is ever a date here.
_TRAILING_DATE_PAREN_RE = re.compile(r"\s*\([^)]*\)\s*$")
_MID_NICKNAME_PAREN_RE = re.compile(r"\s*\([^)]*\)")
# Redirect-stub labels — the same "se også:"/"se:" convention
# build_works_extra.py's SEE_TAIL_RE/head_label() already strip for works,
# reused here for persons. Two shapes, stripped in opposite directions:
# "– Se også: Hansen, Magdalene." has the real name AFTER the marker (the
# whole label IS the pointer); "Christensen, dansk Officer, se:
# Christiansen, Eduard." has it BEFORE (a self-contained entry that
# happens to also cross-reference another spelling). ~630 of 10,228
# persons carry one of these two shapes. The colon after "også" is
# optional — 6 leading labels read "– Se også X" with no colon.
_LEADING_SEE_ALSO_RE = re.compile(r"^\s*[–-]\s*[Ss]e\s+ogs[åa]a?\s*:?\s*")
_TRAILING_SEE_RE = re.compile(r",?\s*\bse\s*:.*$", re.I)


def full_name_from_label(label: str) -> str:
    """"Efternavn, Fornavn(e) [, Titel...]" -> "Fornavn(e) Efternavn" for a
    search-engine query — deliberately looser than the name parsing
    parse_person_gender.py/parse_person_role.py do, since a search query
    only needs to be close enough for the target site's own (fuzzy,
    relevance-ranked) search to find the right person, not a structurally
    correct name field. A label with no comma (surname only, e.g. "Fog",
    "Schytte" — no given name known in this register) is returned as-is;
    that is still a legitimate, if wide, search. A third+ comma-separated
    segment (a title like ", Greve" / ", Baron") is dropped rather than
    appended, since it would only add search noise, not help."""
    s = _LEADING_SEE_ALSO_RE.sub("", label)
    s = _TRAILING_SEE_RE.sub("", s)
    s = _TRAILING_DATE_PAREN_RE.sub("", s).strip()
    parts = [p.strip() for p in s.split(",")]
    if len(parts) == 1:
        return parts[0]
    surname, given = parts[0], parts[1]
    given = _MID_NICKNAME_PAREN_RE.sub("", given).strip()
    return (given + " " + surname).strip() if given else surname


# A person with NO recorded nationality at all defaults to Lex.dk too —
# see the dedicated comment inside bio_search_links() for why that's a
# resource default, not a nationality inference. Two umbrella keys
# ('dansk','tysk') from nation_umbrellas_da.csv decide Lex.dk / Deutsche
# Biographie eligibility for everyone who DOES have one; 'norsk' has no
# umbrella row (no Norwegian sub-regional keys exist in
# ethnic_adjectives_da.csv, unlike the Danish/German regional/historical-
# state variants), so it's checked as a bare nationality key. Everyone
# left after those three — nationality recorded, but neither Danish,
# German nor Norwegian — gets GND Explorer, a general person/corporate-
# body/subject authority search.
#
# URL templates — verified against a real, independently crawled/indexed
# URL for each site (not guessed), per CLAUDE.md's live-verification rule,
# EXCEPT Lex.dk and Store norske leksikon, whose oddball leading-dot path
# (".search", not "search") this sandbox's blocked network access to
# lex.dk/snl.no couldn't confirm — both instead manually confirmed by the
# user in a real browser (lex.dk: https://lex.dk/.search?query=Ingemann;
# snl.no supplied directly with the same convention, the two sites being
# sibling national encyclopedias on shared infrastructure, which is also
# retroactive corroboration for the Lex.dk fix). See docs/data-model/
# person-bio-search-links.md for the full per-resource confidence notes.
#   Lex.dk:                https://lex.dk/.search?query=...
#   Store norske leksikon:  https://snl.no/.search?query=...
#   Deutsche Biographie:    https://www.deutsche-biographie.de/search?name=...
#                           &geburtsjahr=...&todesjahr=...&st=erw — an actual
#                           URL the site itself emitted, found crawled/indexed
#                           (not a documentation guess); st=erw selects its
#                           "erweiterte Suche" (advanced search) mode so the
#                           separate name/year fields are honoured.
#   GND Explorer:           https://explore.gnd.network/en/search?term=...
#                           &rows=25 — URL and both param names (term, rows)
#                           supplied directly by the user, not independently
#                           verified by this session.
#
# ARCHIVED URLS (no longer in use):
#   VIAF (replaced by GND Explorer for all non-Danish/German/Norwegian persons):
#                           https://viaf.org/en/viaf/search?field=cql.any+all&index=VIAF&searchTerms=...
def bio_search_links(label, born, died, nationalities, roles, umbrellas):
    name = full_name_from_label(label)
    if not name:
        return []
    date_bits = [d for d in (born, died) if d]
    query = " ".join([name] + date_bits)

    # Unverified nationality (nothing recorded at all) also defaults to
    # Lex.dk, per an explicit follow-up instruction — NOT the same thing
    # as inferring a nationality from the name, which the brief's own
    # principle 4 forbids. This register is itself Danish-centric (H.C.
    # Andersen's own diaries): its editorial convention marks nationality
    # explicitly only when a person is NOT Danish, so an unmarked person
    # defaulting to a Danish search is a reasonable resource choice, not
    # an assertion that the person IS Danish. 8,259 of 10,228 persons
    # carry no nationality tag at all and fall into this branch.
    if not nationalities:
        return [{
            "label": "Søg på Lex.dk",
            "url": "https://lex.dk/.search?query=" + urllib.parse.quote(query),
        }]

    nat_set = set(nationalities)
    danish_keys = umbrellas.get("dansk", set())
    german_keys = umbrellas.get("tysk", set())
    is_danish = bool(nat_set & danish_keys)
    is_german = bool(nat_set & german_keys)
    is_norwegian = "norsk" in nat_set

    links = []
    if is_danish:
        links.append({
            "label": "Søg på Lex.dk",
            "url": "https://lex.dk/.search?query=" + urllib.parse.quote(query),
        })
    if is_german:
        links.append({
            "label": "Søg hos Deutsche Biographie",
            "url": "https://www.deutsche-biographie.de/search?name=" +
                   urllib.parse.quote(name) +
                   "&geburtsjahr=" + urllib.parse.quote(born or "") +
                   "&todesjahr=" + urllib.parse.quote(died or "") +
                   "&st=erw",
        })
    if is_norwegian:
        links.append({
            "label": "Søg på Store norske leksikon",
            "url": "https://snl.no/.search?query=" + urllib.parse.quote(name),
        })
    if not (is_danish or is_german or is_norwegian):
        links.append({
            "label": "Søg i GND Explorer",
            "url": "https://explore.gnd.network/en/search?term=" +
                   urllib.parse.quote(query) + "&rows=25",
        })
    return links


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

    roles_by_person = load_roles()
    if roles_by_person:
        print(f"  {len(roles_by_person):,} persons with a Rolle/Erhverv classification "
              f"(scripts/parsers/parse_person_role.py)")
    else:
        print("  no person_role.csv — role facet stays empty "
              "(run scripts/parsers/parse_person_role.py)")

    wd_by_person = load_person_wikidata()
    umbrellas = load_nation_umbrellas()
    bio_links_count = 0

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
        nats = nationalities_by_person.get(rid, [])
        roles = roles_by_person.get(rid, [])
        wd = wd_by_person.get(rid)

        # Broad biographical search links (Lex.dk / Deutsche Biographie /
        # VIAF) — a research aid, not an identification, so this ONLY
        # applies when no authority-file link already exists (wd here, or
        # a future persons_wikidata.csv entry — see load_person_wikidata()).
        # See docs/data-model/person-bio-search-links.md for the full rule.
        bio_links = [] if wd else bio_search_links(label, born, died, nats, roles, umbrellas)
        if bio_links:
            bio_links_count += 1

        generated[rid] = {
            "label":         label,
            "description":   (r.get("description") or "").strip() or None,
            "born":          born,
            "died":          died,
            "era":           era_for(born, died),
            "refs":          ref_count.get(rid, 0),
            "nationalities": nats,
            # Afledt facet-værdi, ikke en registreret oplysning — se
            # docs/data-model/person-gender-facet.md. genderConf bæres med,
            # så en senere UI kan skelne "høj sikkerhed" fra "sandsynlig"
            # uden at genberegne noget.
            "gender":       gender_by_person.get(rid, (None, None))[0],
            "genderConf":   gender_by_person.get(rid, (None, None))[1],
            "roles":        roles,
            "wd":           wd,
            "bioLinks":     bio_links,
        }

    print(f"  generated {len(generated):,} entries")
    print(f"  {bio_links_count:,} persons with a suggested biographical search link "
          f"(docs/data-model/person-bio-search-links.md)")

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
