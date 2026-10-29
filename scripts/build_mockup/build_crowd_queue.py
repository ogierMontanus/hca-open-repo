#!/usr/bin/env python3
"""
build_crowd_queue.py
--------------------
Generates the data behind the crowdsourcing interface (crowd.html,
crowd-contribute.html, docs/crowdsourcing.md):

  mockup/data/crowd-queue.js     CROWD_TAXONOMY + CROWD_QUEUE + CROWD_STATS
  mockup/data/crowd-approved.js  CROWD_APPROVED — editor-approved contributions
                                 (from data/curated/person_crowd_approved.tsv)

The queue lists the persons of PERSON-REGISTER whose printed entry is too
thin to identify them, with — for each — the documentation level, the kinds
of information that are missing, a *presumed* country/locality (with the
basis for the presumption), and the diary mentions with direct links to the
page/entry. It reuses, and does not re-derive, what the persons page already
knows: entity-type gate, nationality, gender, role (build_persons_extra.py),
the diary pages and their dates (build_diary_index.py), the place register
(places.csv). Person ids are the register's own `Reg…` ids — the ids in
`persons.html?reg=…` and in `references.csv`.

Stdlib only. Run after build_persons_extra.py's inputs exist (stage 4g in
build_all.py); degrades to an empty queue if they do not.
"""

import csv
import json
import os
import re
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "scripts", "crowdsource"))

import _diary_scope  # noqa: E402
import build_persons_extra as bpe  # noqa: E402
import build_diary_index as bdi  # noqa: E402
import taxonomy as tx  # noqa: E402

NORM = os.path.join(ROOT, "data", "normalized")
CURATED = os.path.join(ROOT, "data", "curated")
ENTITIES = os.path.join(NORM, "entities.csv")
PLACES = os.path.join(NORM, "places.csv")
DIARY = os.path.join(NORM, "diary.csv")
DIARY_HTML = os.path.join(NORM, "diary_html.csv")
KB_LINKS = os.path.join(NORM, "kb_diary_links.csv")
APPROVED_TSV = os.path.join(CURATED, "person_crowd_approved.tsv")
NATION_PLACE_LABELS = os.path.join(CURATED, "nation_place_labels_da.csv")
NATION_UMBRELLAS = os.path.join(CURATED, "nation_umbrellas_da.csv")
COUNTRY_CROSSWALK = os.path.join(CURATED, "steder_country_to_nation_da.csv")
OUT_QUEUE = os.path.join(ROOT, "mockup", "data", "crowd-queue.js")
OUT_APPROVED = os.path.join(ROOT, "mockup", "data", "crowd-approved.js")

MAX_MENTIONS_LISTED = 25
DESC_TRIM = 150

# "– Hans Søster", "– Hendes Søsterdatter": the referent is given by the
# sentence, not by the entry (entityType relationalPlaceholder).
_RELATIONAL_RE = re.compile(r"^\s*[–—\-]\s*(?:Hans|Hendes|Deres)\b")

# ── name / life / description analysis ─────────────────────────────────────

_LIFE_PAREN_RE = re.compile(r"\(([^()]*\d{2,4}[^()]*)\)\s*$")
_YEAR_RE = re.compile(r"\d{2,4}")

# Tokens that stand where a given name should but are not one.
_TITLE_WORDS = {
    "mr.", "mrs.", "miss", "mad.", "madame", "mme", "fru", "frøken", "frk.", "herr",
    "hr.", "baron", "baronesse", "greve", "grevinde", "prins", "prinsesse", "kong",
    "dronning", "hertug", "hertuginde", "fyrst", "fyrstinde", "lord", "lady", "sir",
    "dr.", "pastor", "professor", "kaptajn", "oberst", "general", "doktor",
    "enkefru", "jomfru", "de", "van", "von", "af", "til", "zu",
}
_INITIAL_RE = re.compile(r"^(?:[A-ZÆØÅÖÄÜ][a-z]?\.?)+$")


def life_flags(label: str) -> tuple[bool, bool]:
    """(has_birth, has_death) from the trailing life parenthetical of a
    register label: "(1818–1880)" both, "(1835–?)" birth only, "(død 1873)" /
    "(?–1850)" death only, "(f. 1812)" birth only, no year-bearing
    parenthetical neither. Same label forms as build_persons_extra.parse_life,
    but tolerant of the open-ended ones that function leaves out."""
    m = _LIFE_PAREN_RE.search(label)
    if not m:
        return False, False
    t = m.group(1).strip()
    if re.match(r"^(?:død|d\.)\s", t):
        return False, bool(_YEAR_RE.search(t))
    if re.match(r"^(?:f\.|født|døbt)\s", t):
        return bool(_YEAR_RE.search(t)), False
    parts = re.split(r"\s*[–\-]\s*", t, maxsplit=1)
    if len(parts) == 1:
        return bool(_YEAR_RE.search(parts[0])), False
    return bool(_YEAR_RE.search(parts[0])), bool(_YEAR_RE.search(parts[1]))


def _name_core(label: str) -> str:
    s = bpe._LEADING_SEE_ALSO_RE.sub("", label)
    s = bpe._TRAILING_SEE_RE.sub("", s)
    s = bpe._TRAILING_DATE_PAREN_RE.sub("", s)
    return bpe._MID_NICKNAME_PAREN_RE.sub("", s).strip()


def given_name_state(label: str) -> str:
    """'full'  a given name is spelled out
       'mono'  no comma but life dates: a mononym (Absalon, Alexander III)
       'none'  surname only
       'initials'  only initials or titles stand where the given name should."""
    core = _name_core(label)
    parts = [p.strip() for p in core.split(",")]
    if len(parts) == 1:
        return "mono" if any(life_flags(label)) else "none"
    given = parts[1]
    toks = [t for t in re.split(r"\s+", given) if t]
    if not toks:
        return "none"
    for t in toks:
        if t.lower() in _TITLE_WORDS or _INITIAL_RE.match(t):
            continue
        if t.lower().startswith(("f.", "g.", "d.")) or t.lower().rstrip(".") in ("jun", "sen", "d.æ", "d.y"):
            continue
        if len(re.sub(r"\W", "", t)) >= 3:
            return "full"
    return "initials"


def description_words(desc: str) -> int:
    return len(re.findall(r"\w+", desc or ""))


_DOUBT_RE = re.compile("|".join(tx.DOUBT_PATTERNS), re.I)


def classify(label: str, description: str, *, n_mentions: int, roles: list,
             nationalities: list, gender, uncategorised: str) -> dict:
    """Documentation level, anchors and gaps for one register entry. Pure
    function of its arguments (unit-tested in tests/test_crowd_queue.py)."""
    has_birth, has_death = life_flags(label)
    gstate = given_name_state(label)
    a_name = gstate in ("full", "mono")
    a_life = has_birth or has_death
    a_desc = description_words(description) >= 2
    anchors = int(a_name) + int(a_life) + int(a_desc)
    level = tx.LEVEL_BY_ANCHORS[anchors]

    gaps = []
    if anchors <= 1:
        gaps.append("identity")
    if gstate in ("none", "initials"):
        gaps.append("given_names")
    if not has_birth:
        gaps.append("birth")
    if not has_death:
        gaps.append("death")
    if not a_desc:
        gaps.append("description")
    if not [r for r in roles if r != uncategorised]:
        gaps.append("occupation")
    if not nationalities:
        gaps.append("nationality")
    if gender in (None, "Endnu ubestemt"):
        gaps.append("gender")
    if _DOUBT_RE.search(f"{label} {description or ''}"):
        gaps.append("doubt")

    return {
        "level": level,
        "anchors": anchors,
        "gaps": gaps,
        "fleeting": n_mentions <= tx.FLEETING_MAX_MENTIONS and anchors <= 1,
    }


def mention_bucket(n: int) -> str:
    for key, _da, _en, lo, hi in tx.MENTION_BUCKETS:
        if lo <= n <= hi:
            return key
    return tx.MENTION_BUCKETS[-1][0]


# ── places: presumed country and locality ──────────────────────────────────

def load_places() -> dict:
    """{LOC id: {label, country, category}} from places.csv."""
    out = {}
    if not os.path.exists(PLACES):
        return out
    with open(PLACES, encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            out[r["entity_id"]] = {
                "label": r["label"].strip(),
                "country": (r.get("country") or "").strip(),
                "category": (r.get("category") or "").strip(),
            }
    return out


# Place categories a description is allowed to point at (rivers, mountains,
# churches … name too many unrelated things to say where a person lived).
DESC_PLACE_CATEGORIES = {"City", "Island", "Region", "Country"}


def build_place_lexicon(places: dict) -> dict:
    """{normalised label: LOC id} for labels that name exactly one place of a
    usable category. A label shared by several places (Frederiksborg …) is
    dropped — a wrong locality is worse than none."""
    seen = defaultdict(set)
    for pid, p in places.items():
        if p["category"] not in DESC_PLACE_CATEGORIES:
            continue
        label = re.sub(r"\s*\([^)]*\)", "", p["label"]).strip()
        if len(label) < 4 or not label[0].isupper():
            continue
        seen[label].add(pid)
    return {lab: next(iter(ids)) for lab, ids in seen.items() if len(ids) == 1}


# Capitalised words that are also place labels but, in a description, are far
# more often a title, a surname or an ordinary word.
_PLACE_STOP = {"Holland", "Prinsesse", "Kongen", "Prins", "Kejser", "Dronning"}


def place_in_description(description: str, lexicon: dict, own_surname: str):
    """First LOC id whose label occurs, word-bounded and capitalised, in the
    register's description. None when nothing (unambiguous) matches."""
    if not description:
        return None
    words = re.findall(r"[A-ZÆØÅÖÄÜ][\wÆØÅæøåöäüé\-]+", description)
    for w in words:
        if w in _PLACE_STOP or w == own_surname:
            continue
        # "Københavns Universitet" -> København: a genitive -s is stripped.
        pid = lexicon.get(w) or (lexicon.get(w[:-1]) if w.endswith("s") else None)
        if pid:
            return pid
    # two-word labels ("New York", "Rio de Janeiro", "San Francisco")
    for m in re.finditer(r"([A-ZÆØÅ][\wæøå]+(?:\s+(?:de|di|del|la|le|von|am|an der)?\s*[A-ZÆØÅ][\wæøå]+))", description):
        pid = lexicon.get(re.sub(r"\s+", " ", m.group(1)))
        if pid:
            return pid
    return None


def load_nation_country() -> dict:
    """{nationality_key: modern country name as spelled in places.csv}.

    Route: key → place label (nation_place_labels_da.csv) → country
    (steder_country_to_nation_da.csv read backwards); keys without a label
    (german states, regions …) go through their umbrella
    (nation_umbrellas_da.csv). A key that would map to two countries (the
    deliberately dual Slesvig/Holsten keys) maps to nothing — the person then
    falls through to the next basis."""
    label_to_country = {}
    if os.path.exists(COUNTRY_CROSSWALK):
        with open(COUNTRY_CROSSWALK, encoding="utf-8", newline="") as f:
            for r in csv.DictReader(f):
                lab, c = r["nation_place_label"].strip(), r["xlsx_country"].strip()
                if not lab or not c:
                    continue
                # "England" is the roll-up label for Skotland/Irland: the
                # country with the same name wins.
                if lab not in label_to_country or c == lab:
                    label_to_country[lab] = c
    key_label = {}
    if os.path.exists(NATION_PLACE_LABELS):
        with open(NATION_PLACE_LABELS, encoding="utf-8", newline="") as f:
            for r in csv.DictReader(f):
                key_label[r["nationality_key"]] = r["place_label_da"].strip()
    umbrellas = defaultdict(set)
    if os.path.exists(NATION_UMBRELLAS):
        with open(NATION_UMBRELLAS, encoding="utf-8", newline="") as f:
            for r in csv.DictReader(f):
                lab = (r.get("place_label_da") or "").strip()
                c = label_to_country.get(lab)
                if not c:
                    continue
                for k in (r.get("members") or "").split(";"):
                    if k:
                        umbrellas[k].add(c)
    out = {}
    for k in set(key_label) | set(umbrellas):
        c = label_to_country.get(key_label.get(k, ""))
        if c:
            out[k] = c
        elif len(umbrellas.get(k, ())) == 1:
            out[k] = next(iter(umbrellas[k]))
    return out


# ── diary mentions: pages, dates, entry anchors ────────────────────────────

def load_entry_anchors() -> tuple[dict, dict]:
    """({(vol, page): [(date, normalised_text), …]}, {(vol, page): {date,…}}):
    the dated entries of each diary page, and which of those dates exist as
    an `id="d<date>"` anchor in the generated diary page (diary_html.csv)."""
    entries = defaultdict(list)
    if os.path.exists(DIARY):
        with open(DIARY, encoding="utf-8", newline="") as f:
            for r in csv.DictReader(f):
                d = r.get("date") or ""
                if d and "X" not in d:
                    entries[(r["vol"], r["page"])].append((d, r.get("text") or ""))
    ids = defaultdict(set)
    if os.path.exists(DIARY_HTML):
        with open(DIARY_HTML, encoding="utf-8", newline="") as f:
            for r in csv.DictReader(f):
                for m in re.finditer(r'id="d(\d{4}-\d{2}-\d{2})"', r.get("html") or ""):
                    ids[(r["vol"], r["page"])].add(m.group(1))
    return entries, ids


def entry_anchor(surname: str, vol: str, page: str, entries: dict, ids: dict) -> str:
    """Date of the first entry on the page whose text contains the surname as
    a whole word, if that date is an anchor in the generated page; else ''."""
    if not surname:
        return ""
    pat = re.compile(r"(?<![\wÆØÅæøå])" + re.escape(surname) + r"(?![\wÆØÅæøå])", re.I)
    for d, text in entries.get((vol, page), ()):
        if d in ids.get((vol, page), ()) and pat.search(text):
            return d
    return ""


# ── main ───────────────────────────────────────────────────────────────────

def load_kb_links() -> dict:
    out = {}
    if os.path.exists(KB_LINKS):
        with open(KB_LINKS, encoding="utf-8", newline="") as f:
            for r in csv.DictReader(f):
                out[r["pag_id"]] = r["kb_url"]
    return out


def build() -> tuple[list, dict, dict]:
    if not os.path.exists(ENTITIES):
        sys.exit(f"Missing {ENTITIES} — run scripts/normalization/hca_xlsx_to_csv.py first.")

    non_individuals = bpe.load_non_individuals()
    persons = []
    with open(ENTITIES, encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            if r["entity_type"] != "person":
                continue
            kinds = non_individuals.get(bpe._entity_key(r.get("label", "")), set())
            if kinds and (kinds <= bpe.GATED_KINDS or kinds <= bpe.COLLECTIVE_KINDS
                          or kinds == {"relationalPlaceholder"}):
                continue   # cross-references, families, firms, groups, animals, "Hans Søster"
            if _RELATIONAL_RE.match(r.get("label", "")):
                continue   # same, where the label differs from the typed one by a clause
            persons.append(r)
    person_ids = {p["entity_id"] for p in persons}

    nats_by_person, nat_labels = bpe.load_nationalities()
    gender_by_person = bpe.load_gender()
    roles_by_person, _creators = bpe.load_roles()
    nation_country = load_nation_country()
    places = load_places()
    lexicon = build_place_lexicon(places)
    dates = bdi.load_dates()
    anchors_entries, anchor_ids = load_entry_anchors()
    kb = load_kb_links()

    # references: person → [(vol, page)], page → first place (as DIARY_META.pl)
    person_pages = defaultdict(list)
    page_first_place = {}
    rows = []
    with _diary_scope.open_refs(os.path.join(NORM, "references.csv")) as f:
        for r in csv.DictReader(f):
            if r["vol"] and r["page"]:
                rows.append(r)

    def row_key(r):
        try:
            seq = int(r["seq"])
        except (ValueError, KeyError):
            seq = 0
        return (*bdi.vp_sort_key((r["vol"], r["page"])), seq)
    rows.sort(key=row_key)
    seen = set()
    for r in rows:
        vp = (r["vol"], r["page"])
        eid = r["entity_id"]
        if eid in person_ids and (eid, vp) not in seen:
            seen.add((eid, vp))
            person_pages[eid].append(vp)
        if eid in places and vp not in page_first_place:
            page_first_place[vp] = eid

    queue = []
    level_counts = Counter()
    by_basis = Counter()
    for p in persons:
        rid = p["entity_id"]
        pages = person_pages.get(rid, [])
        if not pages:
            continue               # nothing to link to — no diary context
        label = (p.get("label") or "").strip()
        desc = (p.get("description") or "").strip()
        info = classify(
            label, desc,
            n_mentions=len(pages),
            roles=roles_by_person.get(rid, []),
            nationalities=nats_by_person.get(rid, []),
            gender=gender_by_person.get(rid, (None, None))[0],
            uncategorised=bpe.UNCATEGORISED_ROLE,
        )
        level_counts[info["level"]] += 1
        if info["level"] not in tx.QUEUED_LEVELS and "doubt" not in info["gaps"]:
            continue

        surname = bpe.surname_from_label(label)

        # Mentions, with the entry anchor where the surname is found in one.
        mentions = []
        for vol, page in pages[:MAX_MENTIONS_LISTED]:
            pag = bdi.pid(vol, page)
            date, year = dates.get((vol, page), ("", ""))
            ent = entry_anchor(surname, vol, page, anchors_entries, anchor_ids)
            pl_id = page_first_place.get((vol, page))
            mentions.append([pag, ent or "", (date or "")[:10] if date and "X" not in date else (year or ""),
                             places[pl_id]["label"] if pl_id else ""])
        years = sorted({int(m[2][:4]) for m in mentions if re.match(r"^\d{4}", m[2] or "")})
        # (years above covers only the listed mentions; recompute for all pages)
        all_years = sorted({int(y) for vp in pages
                            for y in [dates.get(vp, ("", ""))[1]] if y and str(y).isdigit()})

        # Presumed country / locality, strongest basis first. The country and
        # the locality each remember what they were taken from (cb / lb).
        country = locality = loc_id = None
        basis = loc_basis = ""
        nats = nats_by_person.get(rid, [])
        nat_countries = {nation_country[k] for k in nats if k in nation_country}
        desc_place = place_in_description(desc, lexicon, surname)
        if desc_place:
            locality, loc_id, loc_basis = places[desc_place]["label"], desc_place, "beskr"
        if len(nat_countries) == 1:
            country, basis = next(iter(nat_countries)), "nat"
        elif desc_place and places[desc_place]["country"]:
            country, basis = places[desc_place]["country"], "beskr"
        if not locality or not country:
            page_places = Counter(page_first_place[vp] for vp in pages if vp in page_first_place)
            if page_places:
                top = page_places.most_common(1)[0][0]
                if not locality:
                    locality, loc_id, loc_basis = places[top]["label"], top, "side"
                if not country and places[top]["country"]:
                    country, basis = places[top]["country"], "side"
        by_basis[basis] += 1

        rec = {
            "id": rid,
            "l": label,
            "ds": (desc[:DESC_TRIM].rstrip() + "…") if len(desc) > DESC_TRIM else desc,
            "lv": info["level"],
            "g": info["gaps"],
            "n": len(pages),
            "nb": mention_bucket(len(pages)),
            "fl": 1 if info["fleeting"] else 0,
            "c": country,
            "lc": locality,
            "lid": loc_id,
            "cb": basis,
            "lb": loc_basis,
            "nat": [nat_labels.get(k, k) for k in nats],
            "ys": all_years,
            "y0": all_years[0] if all_years else None,
            "m": mentions,
        }
        queue.append(rec)

    meta = {
        "persons": len(persons),
        "withMentions": sum(level_counts.values()),
        "levels": dict(level_counts),
        "queued": len(queue),
        "fleeting": sum(1 for q in queue if q["fl"]),
        "basis": {k or "none": v for k, v in by_basis.items()},
    }
    return queue, meta, kb


def load_approved() -> dict:
    """{person id: [claim,…]} from data/curated/person_crowd_approved.tsv —
    one claim per accepted field of an approved submission."""
    out = defaultdict(list)
    if not os.path.exists(APPROVED_TSV):
        return {}
    with open(APPROVED_TSV, encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f, delimiter="\t"):
            out[r["person_id"]].append({
                "f": r["field"],
                "v": r["emended"],
                "c": r["confidence"],
                "s": r["source_detail"],
                "by": r["contributor"],
                "d": r["date"],
                "sub": r["submission_id"],
                "n": r["notes"],
            })
    return dict(out)


def write_js(path: str, header: str, consts: dict) -> None:
    """Each value is assigned to window.<NAME> (a top-level `const` would not
    be a window property, and the crowd scripts read window.CROWD_*)."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(header)
        for name, value in consts.items():
            f.write(f"window.{name} = ")
            f.write(json.dumps(value, ensure_ascii=False, separators=(",", ":")))
            f.write(";\n")


def main() -> None:
    queue, meta, kb = build()
    approved = load_approved()
    for q in queue:
        q["ap"] = len(approved.get(q["id"], ()))
    meta["approvedPersons"] = len(approved)

    print(f"  {meta['persons']:,} individual persons, {meta['withMentions']:,} with diary mentions")
    print(f"  levels: {meta['levels']}")
    print(f"  queued: {meta['queued']:,}  (fleeting mentions: {meta['fleeting']:,})")
    print(f"  presumed-country basis: {meta['basis']}")

    # KB facsimile link per diary page (4,413 — the contribute page serves any
    # person, queued or not, so it needs them all).
    kb_links = {p: kb[p] for p in sorted(kb)}

    write_js(
        OUT_QUEUE,
        "// Auto-generated by scripts/build_mockup/build_crowd_queue.py — do not hand-edit.\n"
        "// The crowdsourcing work queue: persons whose printed register entry is too\n"
        "// thin to identify them. See docs/crowdsourcing.md for every field.\n"
        "// m = mentions [pag, entry-date-anchor, date, place-on-page]; cb / lb = what the\n"
        "// presumed country c / locality lc were taken from (nat | beskr | side).\n",
        {
            "CROWD_TAXONOMY": tx.taxonomy_for_js(),
            "CROWD_STATS": meta,
            "CROWD_KB_LINKS": kb_links,
            "CROWD_QUEUE": queue,
            "CROWD_ROLE_BUCKETS": bpe.load_role_order(),
            "CROWD_NATIONALITIES": sorted(bpe.load_nationalities()[1].values()),
        },
    )
    print(f"  wrote {os.path.relpath(OUT_QUEUE, ROOT)}  ({os.path.getsize(OUT_QUEUE)/1024:.0f} KB)")

    write_js(
        OUT_APPROVED,
        "// Auto-generated by scripts/build_mockup/build_crowd_queue.py — do not hand-edit.\n"
        "// Editor-approved crowd contributions, from data/curated/person_crowd_approved.tsv.\n"
        "// Shown on persons.html as a separate, attributed layer — the register's own\n"
        "// text is never overwritten (docs/data-model/person-editorial-emendations.md).\n",
        {"CROWD_APPROVED": approved,
         # labels for js/crowd-link.js on persons.html, which does not load the queue
         "CROWD_FIELD_LABELS": {f[0]: f[1] for f in tx.FIELDS},
         "CROWD_CONF_LABELS": {c[0]: c[1] for c in tx.CONFIDENCE}},
    )
    print(f"  wrote {os.path.relpath(OUT_APPROVED, ROOT)}  ({len(approved)} persons with approved claims)")


if __name__ == "__main__":
    main()
