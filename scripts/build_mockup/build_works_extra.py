#!/usr/bin/env python3
"""
build_works_extra.py
--------------------
Generates mockup/data/works-extra.js — a `WORKS_EXTRA` JS object with
one entry per work in data/normalized/entities.csv. The hand-curated
`WORKS` object inside mockup/work.html keeps precedence; WORKS_EXTRA
fills every other gap so any ?reg=… link resolves to real metadata
instead of an "Ukendt værk" page.

Run after `scripts/normalization/hca_xlsx_to_csv.py`. Stdlib only.
"""

import csv
import json
import os
import re
import sys
from collections import defaultdict

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
ENTITIES = os.path.join(ROOT, "data", "normalized", "entities.csv")
REFS = os.path.join(ROOT, "data", "normalized", "references.csv")
LANGS = os.path.join(ROOT, "data", "normalized", "work_languages.csv")
OUT = os.path.join(ROOT, "mockup", "data", "works-extra.js")

PUB_PAREN_RE = re.compile(r"\(([^()]+?)\)")
YEAR_RE = re.compile(r"\b(1[5-9]\d{2})\b")

# Strip a "se:" / "Se ogsaa:" redirect tail and surrounding punctuation so a
# cross-reference target ("Krøblingen") can be matched against the head of a
# fuller entry label ("Krøblingen (Eventyrbogen)").
SEE_TAIL_RE = re.compile(r"[Ss]e\s+og[s]?aa\s*:|\bse\s*:")
PUNCT_RE = re.compile(r"[*»«\"'.,!?;:\-()\[\]]")
WS_RE = re.compile(r"\s+")


def norm_label(s):
    s = (s or "").replace("\n", " ").lower()
    s = PUNCT_RE.sub(" ", s)
    return WS_RE.sub(" ", s).strip()


def head_label(label):
    return norm_label(SEE_TAIL_RE.split((label or "").replace("\n", " "))[0])


def wing_for(h2, h3):
    h2u = (h2 or "").upper()
    h3l = (h3 or "").lower()
    if "BILLEDKUNST" in h2u or "malerier" in h3l or "skulptur" in h3l or "museer" in h3l:
        return ("billedkunst.html", "Billedkunst")
    if ("MUSIK" in h2u or "opera" in h3l or "ballet" in h3l
            or "vokal" in h3l or "skuespil" in h3l):
        return ("teater-musik.html", "Teater & Musik")
    return ("bibliotek.html", "Bibliotek")


def parse_year(label):
    for m in PUB_PAREN_RE.finditer(label):
        ym = YEAR_RE.search(m.group(1))
        if ym:
            return ym.group(1)
    return None


PAREN_ALL_RE = re.compile(r"\(([^()]+)\)")

# BILLEDKUNST titles that carry no person_derived attribution are usually
# still attributed *in the label itself*: "Abe... (Annibale Carracci, Uffizi,
# Firenze)" — artist, collection, city, comma-separated inside the first
# parenthetical. Empirically (data/normalized/entities.csv, the 672 BILLEDKUNST
# works with no person_derived): 291 titles carry 3 pieces, 160 carry 2, 173
# carry just 1 — always in that same Artist[, Collection][, City] order.
#
# The one place position-alone isn't reliable is exactly where an artist is
# genuinely absent: some titles instead read "(Collection, City)" with no
# artist at all (27x 'M. borbonico, Napoli', 12x 'Capitol, Rom', ...), and a
# bare single-piece parenthetical can be either a lone artist name
# ("Aristokrati og Fattigfolk (Siegwald Dahl)") or a bare place/institution
# ("Alexander-Slaget (Pompeji)") — indistinguishable by position, so both
# get the same name-shape + stoplist screening below regardless of how many
# comma-pieces the group has.
_ARTIST_STOPLIST = {
    # Recurring institution/collection abbreviations that showed up as the
    # FIRST piece — i.e. titles with no artist, just "(Collection, City)".
    "m. borbonico", "m. bonbornico",  # latter is an OCR letter-transposition
    "capitol", "vatikanet", "uffizi", "glyptoteket", "fesch",
    "libreria piccolomini", "palazzo della ragione", "raadhuspladsen",
    "domkirken",
    # Medium/technique descriptors, not names.
    "tegning", "kopi", "selvportræt", "kultegning", "udstillingsmedaljen",
    "arvesynden", "fresko", "karton", "malet buste",
    # Mythological sculpture subjects (the artwork's subject, not its maker).
    "pallas", "hermes", "satyren", "hera farnese", "ilioneus",
    # Room/monument names inside a museum or city, not the maker.
    "aegineter-salen", "arco clementino", "apollo-salen",
    # Places absent from entities.csv's place register under this exact label
    # (place_labels below catches the rest, e.g. Berlin/München/Firenze/Rom).
    "pompeji", "mariekirken", "bregentved park",
}
# Single institution words that also show up buried inside a longer compound
# phrase — "Mercato Nuovo og Uffizi" isn't itself stoplisted, but it contains
# "Uffizi" — so every word of the candidate is checked against this set too,
# not just the whole string.
_INSTITUTION_WORDS = {"uffizi", "capitol", "vatikanet", "glyptoteket", "fesch"}
_FOREIGN_ARTICLES = {"il", "la", "le", "lo", "los", "las", "das", "die", "der", "el"}


def _looks_like_artist(candidate, place_labels):
    c = candidate.strip()
    if not c or c[0].islower() or any(ch.isdigit() for ch in c) or "?" in c or ":" in c:
        return False
    cf = c.casefold()
    if cf in _ARTIST_STOPLIST or cf in place_labels:
        return False
    # A leading segment before a "." also needs the stoplist check — OCR/
    # source punctuation sometimes joins an institution and its city with a
    # period instead of the usual comma ("Glyptoteket. München").
    if cf.split(".", 1)[0].strip() in _ARTIST_STOPLIST:
        return False
    words = re.findall(r"[a-zæøåA-ZÆØÅ]+", cf)
    if any(w in _INSTITUTION_WORDS for w in words):
        return False
    low = c.lower()
    if low.startswith(("den ", "det ", "de ", "palazzo ", "kopi ")):
        return False
    if low.split(" ", 1)[0].strip(".,") in _FOREIGN_ARTICLES:
        return False
    if " fra " in low or low.endswith(("kirke", "kirken")):
        return False
    if len(c.split()) > 5:
        return False
    return True


def artist_from_billedkunst_title(title, place_labels):
    """Recover an artist name from a BILLEDKUNST title's parenthetical(s), or
    None when nothing looks like one — never a guess dressed up as data.

    Some titles carry more than one parenthetical group, and the first one
    isn't always the attribution: "Tre Helgener (Benedikt, Flavia og
    Placidus) (Perugino, Vatikanet, Rom)" lists the depicted saints first,
    the real artist second. A group ending in a real place name is the
    strongest signal that IT is the "Artist[, Collection], City" group, so
    that's tried across every group before falling back to first-group-that-
    looks-plausible order."""
    groups = [[p.strip() for p in g.split(",")] for g in PAREN_ALL_RE.findall(title)]
    groups = [g for g in groups if g and g[0]]
    if not groups:
        return None

    for g in groups:
        if g[-1].casefold() in place_labels and _looks_like_artist(g[0], place_labels):
            return g[0]

    for g in groups:
        if _looks_like_artist(g[0], place_labels):
            return g[0]
    return None


def _person_derived_is_title_subject(person_derived, title):
    """True when person_derived just repeats the work's own subject rather
    than naming who made it — e.g. person_derived='S. Cecilia' on a title
    'S. Cecilia (Carlo Dolci, Manfrin, Venezia)' (the saint depicted, not
    the painter), or 'H. V. Bissen' on 'H. V. Bissen (Carl Peters)' (the
    portrait's sitter, who happens to *also* be a real sculptor elsewhere
    in this register — so this can't be screened by name-shape alone).
    Checked per newline-joined segment (see the multi-value note below) —
    one bad segment is enough to mark the whole value suspect."""
    title = title.strip()
    return any(title.startswith(seg) for seg in (s.strip() for s in person_derived.split("\n")) if seg)


def author_from(genre_h2, h3, title, person_derived, place_labels):
    h2u = (genre_h2 or "").strip().upper()
    if person_derived and person_derived.strip():
        # For BILLEDKUNST specifically: 65 works have a person_derived value
        # that is a prefix of their own title — i.e. the upstream step
        # copied the depicted subject into the attribution field instead of
        # (or in addition to) naming the actual maker. Every one of the 65
        # checked by hand recovers a clean, plausible artist name from the
        # title's own parenthetical instead (see artist_from_billedkunst_title
        # docstring) — e.g. "S. Cecilia" → "Carlo Dolci" for the title above.
        # Only override when that recovery actually succeeds; a title whose
        # subject-echo can't be resolved to anything better keeps the
        # original value rather than losing it for nothing.
        #
        # Known remaining gap: the prefix check only catches the subject
        # when it leads the title ("S. Cecilia (Carlo Dolci, …)"). A subject
        # named mid-title ("...Ruinerne af Byen Nymfa (Harald Jerichau)",
        # person_derived "Byen Nymfa") isn't a title prefix and slips
        # through — 5 known BILLEDKUNST works as of this writing. Widening
        # the check to "title contains person_derived anywhere" was tried
        # and rejected: a CORRECT person_derived is, by construction, also
        # a substring of its own title (it usually came from the same
        # parenthetical), so that version flagged nearly everything as
        # suspect instead of just the handful of real bugs.
        if h2u == "BILLEDKUNST" and _person_derived_is_title_subject(person_derived, title):
            recovered = artist_from_billedkunst_title(title, place_labels)
            if recovered:
                return recovered
        # 158 works across every wing carry a person_derived value with an
        # embedded newline joining two names/values from the upstream
        # normalization step (e.g. "A. W. Moltke\nH. V. Bissen" — a portrait
        # bust's subject and its sculptor both landed in the one field).
        # Which segment is "the" author isn't reliably position-dependent —
        # it's the first name in some rows, the last in others — so this
        # doesn't try to pick a winner; it just makes the value readable
        # (comma-joined) instead of a raw newline, without dropping either
        # name or guessing. Fixing which name is correct is a normalization-
        # pipeline question, not something this script can resolve.
        return re.sub(r"\s*\n\s*", ", ", person_derived.strip())
    if h2u == "BILLEDKUNST":
        h3l = (h3 or "").lower()
        if "museer" in h3l or "samlinger" in h3l:
            return None  # institution/collection entries, not authored works
        return artist_from_billedkunst_title(title, place_labels)
    if h2u and h2u != "MUSIK":
        return genre_h2.strip()
    return None


def load_languages():
    """{entity_id: (lang, method)} from detect_work_language.py. Empty when
    that stage hasn't run — `lang` then stays None exactly as before."""
    out = {}
    if not os.path.exists(LANGS):
        return out
    with open(LANGS, encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            out[r["entity_id"]] = (r["lang"], r["method"])
    return out


def main():
    if not os.path.exists(ENTITIES):
        sys.exit(f"Missing {ENTITIES} — run scripts/normalization/hca_xlsx_to_csv.py first.")

    print(f"Loading {os.path.relpath(ENTITIES, ROOT)}…")
    with open(ENTITIES, encoding="utf-8") as f:
        all_rows = list(csv.DictReader(f))
    rows = [r for r in all_rows if r["entity_type"] == "work"]
    print(f"  {len(rows):,} works")

    # Negative filter for artist_from_billedkunst_title(): a bare place name
    # inside a title's parenthetical ("Alexander-Slaget (Pompeji)") must not
    # be mistaken for an artist with no comma-separated collection/city to
    # disambiguate it from one.
    place_labels = {
        r["label"].strip().casefold()
        for r in all_rows if r["entity_type"] == "place" and r["label"]
    }
    print(f"  {len(place_labels):,} place labels loaded for artist-extraction filtering")

    ref_count = defaultdict(int)
    if os.path.exists(REFS):
        with open(REFS, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                ref_count[r["entity_id"]] += 1
        print(f"  reference counts loaded for {len(ref_count):,} entities")

    work_langs = load_languages()
    if work_langs:
        print(f"  languages loaded for {len(work_langs):,} works")
    else:
        print("  no work_languages.csv — lang stays null "
              "(run scripts/build_mockup/detect_work_language.py)")

    # Index work labels for resolving `see` / `see_also` cross-references to
    # real register IDs. Most targets are the head term of a fuller label
    # (e.g. "Krøblingen" -> "Krøblingen (Eventyrbogen)"), so we keep an exact
    # head-label map plus a (head, rid) list for whole-word prefix fallback.
    head_exact = defaultdict(list)
    head_list = []
    for r in rows:
        h = head_label(r["label"])
        if h:
            head_exact[h].append(r["entity_id"])
            head_list.append((h, r["entity_id"]))

    def resolve_ref(target, self_id):
        t = norm_label(target)
        if not t:
            return None
        cands = [rid for rid in head_exact.get(t, []) if rid != self_id]
        if cands:
            return cands[0]
        # Whole-word prefix: shortest label that starts with the target wins,
        # so "Foraarssang" picks the bare poem over a longer derived title.
        prefixed = [(len(h), rid) for h, rid in head_list
                    if rid != self_id and (h == t or h.startswith(t + " "))]
        if prefixed:
            return min(prefixed)[1]
        return None

    def refs_field(raw, self_id):
        raw = (raw or "").strip()
        if not raw:
            return []
        return [{"label": raw, "rid": resolve_ref(raw, self_id)}]

    def best_year(r):
        # Prefer the normalised derived fields over the label regex.
        dd = (r.get("date_derived") or "").strip()
        if dd:
            ym = re.match(r"(1[5-9]\d{2})", dd)
            if ym:
                return ym.group(1)
        yd = (r.get("year_derived") or "").strip()
        if yd:
            ym = YEAR_RE.search(yd)
            if ym:
                return ym.group(1)
        return parse_year(r["label"])

    # Generate one entry per work, INCLUDING IDs that mockup/work.html
    # also curates. work.html's `ALL_WORKS = Object.assign({}, WORKS_EXTRA,
    # WORKS)` still gives the hand-curated entries precedence; emitting the
    # extras for them too makes EntityRefs (mockup/js/entity-refs.js) see
    # the full catalogue from the other detail pages, where the curated
    # `WORKS` object isn't in scope.
    generated = {}
    for r in rows:
        rid = r["entity_id"]
        h2 = (r.get("genre_h2") or "").strip()
        h3 = (r.get("form_h3") or "").strip()
        wing, wing_label = wing_for(h2, h3)
        generated[rid] = {
            "title": r["label"].strip(),
            "h2": h2 or "ANDRE FORFATTERE",
            "h3": h3 or "—",
            "wing": wing,
            "wingLabel": wing_label,
            "author": author_from(h2, h3, r["label"], r.get("person_derived", ""), place_labels),
            # Derived, not curated — langMethod carries the provenance so the
            # UI can say so. See detect_work_language.py.
            "lang": work_langs.get(rid, (None, None))[0],
            "langMethod": work_langs.get(rid, (None, None))[1],
            "refs": ref_count.get(rid, 0),
            "year": best_year(r),
            "date": (r.get("date_derived") or "").strip() or None,
            "see": refs_field(r.get("see"), rid),
            "seeAlso": refs_field(r.get("see_also"), rid),
            "diary": [],
            "related": [],
            "coPlaces": [],
            "coWorks": [],
        }

    print(f"  generated {len(generated)} entries across all {len(rows)} works")

    billedkunst = [w for w in generated.values() if w["h2"].upper() == "BILLEDKUNST"]
    if billedkunst:
        with_author = sum(1 for w in billedkunst if w["author"])
        print(f"  BILLEDKUNST author coverage: {with_author}/{len(billedkunst)} "
              f"({with_author / len(billedkunst):.0%})")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("// Auto-generated by scripts/build_mockup/build_works_extra.py — do not hand-edit.\n")
        f.write("// Provides minimal placeholder entries so every ?reg=… link from category\n")
        f.write("// pages resolves to real metadata. Hand-curated WORKS in work.html takes\n")
        f.write("// precedence on lookup (see ALL_WORKS merge at the bottom of work.html).\n")
        f.write("const WORKS_EXTRA = ")
        f.write(json.dumps(generated, ensure_ascii=False, indent=2))
        f.write(";\n")
    print(f"  wrote {os.path.relpath(OUT, ROOT)}  "
          f"({os.path.getsize(OUT):,} bytes)")


if __name__ == "__main__":
    main()
