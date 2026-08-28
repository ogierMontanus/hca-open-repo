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
import unicodedata
import urllib.parse
from collections import Counter, defaultdict

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
ENTITIES = os.path.join(ROOT, "data", "normalized", "entities.csv")
REFS = os.path.join(ROOT, "data", "normalized", "references.csv")
LANGS = os.path.join(ROOT, "data", "normalized", "work_languages.csv")
WD_OVERLAY = os.path.join(ROOT, "data", "curated", "works_wikidata.csv")
PARSED_DIR = os.path.join(ROOT, "data", "parsed")
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


def split_container_chain(title):
    """Split a title on its LAST top-level ' - ' separator (outside any
    parenthetical), returning (parent_segment, tail_segment) or None.

    H. C. Andersen's own works re-list every reprint/translation of a
    collection as its own register row, chained onto the collection's
    title with ' - ' ("Nye Eventyr og Historier ... (1858-66) - 1. Samling
    (1858) - 4 Opl. (1865)") -- a WEMI part_of relation the printed
    register spells out positionally rather than with a "Se ogsaa" marker.
    A dash inside a parenthetical subtitle ("Skilles og mødes (Spanierne i
    Odense - Fem og tyve Aar derefter)") or inside a quoted poem incipit
    ("*»Hun er saa foraarsfrisk at see - «") is not this relation --
    filtered out by requiring paren-depth 0 and rejecting quote-led
    titles. Verified against the full H. C. Andersen slice (775 rows): 57
    real chain rows recovered, 0 false positives from either excluded
    shape.
    """
    t = title.lstrip("*").strip()
    if t.startswith("»") or t.startswith("«"):
        return None
    depth = 0
    last = -1
    for i in range(len(title) - 2):
        c = title[i]
        if c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
        elif depth == 0 and title[i:i + 3] == " - ":
            last = i
    if last == -1:
        return None
    return title[:last].strip(), title[last + 3:].strip()


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
    "m. borbonico", "m. bonbornico", "m. borbon.ico",  # OCR variants
    "capitol", "vatikanet", "uffizi", "glyptoteket", "fesch",
    "libreria piccolomini", "palazzo della ragione", "raadhuspladsen",
    "domkirken",
    # Medium/technique descriptors, not names.
    "tegning", "kopi", "selvportræt", "kultegning", "udstillingsmedaljen",
    "arvesynden", "fresko", "karton", "malet buste", "skitse",
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


_VENUE_REJECT_RE = re.compile(r"^n\.?\s*n\.?$", re.I)


def _looks_like_venue(candidate):
    """Screens a would-be venue/gallery piece the same way _looks_like_artist
    screens an author candidate, but far more permissively — venues in this
    data are institution names, so the artist function's name-shape checks
    (no digits, not an article, ≤5 words, …) would reject real ones
    ("Teatro Vittorio Emanuele", "Her Majesty's Theatre"). Still rejects:
    - TEATER & MUSIK's "N.N." placeholder for an unknown author leaking into
      the venue slot when a title has no date to anchor the split
      ("Forseent (N.N., Odense)");
    - the same medium/technique and bare-institution _ARTIST_STOPLIST
      entries, which leak into the venue slot exactly as they do into the
      artist slot ("Rom (..., Kultegning, Villa Farnesina)" — "Kultegning"
      is a drawing technique, not a venue);
    - a "kaldet <alias>", "Kopi af <artist>", "fuldført af <artist>", or
      "efter <source>" clause — an artist-alias, copyist, completion, or
      source-work note that happens to share a comma-separated slot with
      the real venue ("Rom (..., kaldet il Grechetto, Doria-P., Rom)",
      "Madrid (..., fuldført af Pietro Tacca, Plaza Mayor, Madrid)")."""
    c = candidate.strip().strip(".")
    if not c or _VENUE_REJECT_RE.match(c):
        return False
    cf = c.casefold()
    if cf in _ARTIST_STOPLIST:
        return False
    if cf.startswith(("kaldet ", "kopi af ", "udkast", "fuldført af ", "efter ")):
        return False
    return True


def place_from_billedkunst_title(title, place_labels):
    """Recover (city, venue) from a BILLEDKUNST title's own parenthetical,
    using the same "group whose last piece is a real place name" signal as
    artist_from_billedkunst_title() — see that function's docstring for why
    every group is tried rather than just the first. Unlike the artist
    extraction, this doesn't require the leading piece to look like a name:
    "Alexander-Slaget (Pompeji)" (bare place, no recoverable artist) still
    yields city="Pompeji", venue=None here, deliberately — the reader wants
    a Sted facet entry for that work even when authorship isn't recoverable.
    Returns (None, None) when no group's last piece is a known place."""
    groups = [[p.strip() for p in g.split(",")] for g in PAREN_ALL_RE.findall(title)]
    groups = [g for g in groups if g and g[0]]
    for g in groups:
        if g[-1].casefold() in place_labels:
            venue_parts = [p for p in g[1:-1] if _looks_like_venue(p)]
            return g[-1], (", ".join(venue_parts) or None)
    return None, None


# TEATER & MUSIK titles that DO carry a premiere location state it as
# "(DD.MM.YYYY, Venue, City)" — e.g. "Il Bandocani (19.1.1834, Teatro Fiano,
# Rom)". Only ~38 of 1,257 titles have this (most just name the composer/
# playwright), but every hit is a real, checkable premiere.
#
# The date isn't always the group's first piece — "La finta strega (efter
# W. Scott: »Guy Mannering«, 12.6.1846, Teatro Fiorentini, Napoli)" has a
# "efter <source>" note ahead of it — so this SEARCHES for the date instead
# of anchoring to the start, and keeps only what comes AFTER it; whatever
# precedes the date (a note, or nothing) is discarded either way, never
# folded into the venue. The first date's own year is optional so a
# compound "16.1. og 25.1.1841" (two performance dates, one title) still
# matches as a whole rather than stopping at the year-less first fragment.
_TEATER_DATE_RE = re.compile(
    r"\d{1,2}\.\s*\d{1,2}\.?\s*(?:\d{4}\.?)?"
    r"(?:\s*og\s*\d{1,2}\.\s*\d{1,2}\.\d{4}\.?)?"
)


def place_from_teater_title(title, place_labels):
    """Recover (city, venue) from a TEATER & MUSIK title's own parenthetical
    when it states a premiere location — see _TEATER_DATE_RE above. Unlike
    BILLEDKUNST there's no leading-artist piece to skip past on purpose;
    this just wants the first group whose last piece is a real place, after
    cutting that group down to whatever follows its date (or the group
    as-is when it has no date at all — "Forseent (N.N., Odense)"). Returns
    (None, None) for the ~97% of titles with no such parenthetical (or one
    that doesn't resolve to a known place).

    Known remaining gap: a title that jams two distinct premieres (two
    dates, two venues, two cities) into one parenthetical — one seen case,
    "Cracovienne (... 21.3.1846, Teatro grande, Trieste. - 13.6.1849. Kgl.
    Teater, Stockholm)" — still yields a venue that runs on into the second
    performance's own venue/date text. Splitting that generally is a
    data-curation question (which premiere is "the" one?), not something a
    single regex should guess at."""
    for raw in PAREN_ALL_RE.findall(title):
        m = _TEATER_DATE_RE.search(raw)
        rest = raw[m.end():] if m else raw
        rest = rest.lstrip(" ,.")
        parts = [p.strip() for p in rest.split(",") if p.strip()]
        if parts and parts[-1].casefold() in place_labels:
            venue_parts = [p for p in parts[:-1] if _looks_like_venue(p)]
            return parts[-1], (", ".join(venue_parts) or None)
    return None, None


def format_place(city, venue):
    """"City" alone, or "City — Venue" — chosen so that a plain alphabetical
    sort of the formatted string already clusters every venue under its city
    (a bare "Rom" sorts immediately next to "Rom — Vatikanet" etc.), with no
    separate sort key needed in the front end."""
    if not city:
        return None
    return city if not venue else f"{city} — {venue}"


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


def author_from(genre_h2, h3, title, person_derived, place_labels, tsv_creator=None):
    h2u = (genre_h2 or "").strip().upper()
    # A dedicated, WEMI-rule-based parser (scripts/parsers/) has already
    # extracted this row's creator from its own title parenthetical — see
    # load_parsed_creator_overrides()'s docstring for why this takes
    # priority even over a non-empty person_derived, not just fills gaps.
    if tsv_creator:
        return tsv_creator
    # H. C. ANDERSEN's own genre never trusts person_derived as an author
    # override -- checked directly: of 149 rows in this H2 with a non-empty
    # value, the overwhelming majority name an illustrator (V. Pedersen,
    # Lorenz Frølich), translator (H. Zeise, Karl Bäckman), or dedicatee
    # (Dorothea Melchior), never a genuinely different creator -- Andersen
    # wrote his own oeuvre by construction of the H2 itself. Left
    # unguarded, e.g. Reg001312 "Fodreise fra Holmens Kanal til Østpynten
    # af Amager" got person_derived = 'Østpynten af Amager' (a fragment of
    # its own title, not a person at all) and that string displaced "H. C.
    # Andersen" as this row's "author" -- visible directly in bibliotek
    # .html's Forfatter facet. Falls through to the literal-H2 return below
    # instead, same as every h2 with no person_derived at all.
    if h2u != "H. C. ANDERSEN" and person_derived and person_derived.strip():
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


def load_wikidata_overlay():
    """{entity_id: (wd, image_url, attribution_note)} from
    data/curated/works_wikidata.csv — hand-verified rows only (see
    scripts/parsers/wikidata_lookup.py, which proposes candidates but never
    writes here itself). image_filename is the bare Commons filename as it
    appears in the "File:" page title; percent-encoding it here means the
    CSV can stay copy-pasteable from a Commons URL without the person
    adding a row needing to think about escaping unicode/parens/commas in
    the filename themselves.

    attribution_note is the ONLY column from this CSV meant for readers —
    e.g. "Tilskrives i dag ikke længere Rafael — Sebastiano del Piombo…"
    when the register's historical attribution no longer matches current
    scholarship (see docs/data-model/wikidata-hero-images.md's "diary
    register isn't a catalogue raisonné" policy). The `notes` column is
    editorial/verification commentary for whoever maintains this CSV — how
    a match was confirmed, what was ruled out — and is deliberately NOT
    loaded here, so it can never leak onto the site."""
    out = {}
    if not os.path.exists(WD_OVERLAY):
        return out
    with open(WD_OVERLAY, encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            rid = r["rid"].strip()
            wd = r.get("wd", "").strip() or None
            filename = r.get("image_filename", "").strip()
            image = (
                "https://commons.wikimedia.org/wiki/Special:FilePath/" + urllib.parse.quote(filename)
                if filename else None
            )
            attribution_note = r.get("attribution_note", "").strip() or None
            out[rid] = (wd, image, attribution_note)
    return out


# ── Person-key matching (Python mirror of entity-refs.js's nameKey()) ──────
# Needed here, not just client-side, for resolve_shared_surname() below: a
# split co-author list sometimes has a bare given name whose surname is
# only stated once, shared across the list ("Georg og Edvard Brandes" ->
# ["Georg", "Edvard Brandes"] -- Georg and Edvard Brandes are two distinct,
# real, separately-registered brothers; "Dupeuty, Fontan og Davrigny" has
# the shared surname FIRST instead of last -- checked directly, neither
# Dupeuty nor Fontan nor Davrigny exist in the register at all, so that
# specific trio can't resolve yet regardless, but the mechanism itself is
# validated against the Brandes case, which does). Keep this in exact sync
# with nameKey() in mockup/js/entity-refs.js -- same diacritic fold (added
# there specifically so "Oehlenschlaeger"-style German-vs-Danish spellings
# key the same), same NFD-strip, same surname/initials split.
_NAME_KEY_KEEP_RE = re.compile("[^a-zæøå]")
_COMBINING_MARKS_RE = re.compile("[̀-ͯ]")


def _person_name_fold(x):
    x = (
        x.replace("ä", "æ").replace("Ä", "Æ")   # ä->æ, Ä->Æ
         .replace("ö", "ø").replace("Ö", "Ø")   # ö->ø, Ö->Ø
         .replace("ü", "y").replace("Ü", "Y")             # ü->y, Ü->Y
    )
    x = unicodedata.normalize("NFD", x.lower())
    return _COMBINING_MARKS_RE.sub("", x)


def person_name_key(s):
    """Mirrors mockup/js/entity-refs.js's nameKey(): 'surname|initials',
    e.g. 'brandes|g' for both "Georg Brandes" and "Brandes, Georg (...)"."""
    if not s:
        return None
    s = re.split(r"[(（\[]", s)[0].strip()
    if not s:
        return None
    if "," in s:
        parts = s.split(",")
        surname, given = parts[0], " ".join(parts[1:])
    else:
        toks = s.split()
        if not toks:
            return None
        surname, given = toks[-1], " ".join(toks[:-1])
    sk = _NAME_KEY_KEEP_RE.sub("", _person_name_fold(surname))
    if not sk:
        return None
    given_folded = _person_name_fold(given)
    # Every initial, NOT deduplicated -- "E. E. Schmidt" -> "ee", matching
    # nameKey()'s own .sort().join('') over the raw (non-Set) array.
    inits = sorted(t[0] for t in re.split(r"[\s.]+", given_folded) if t)
    return sk + "|" + "".join(inits)


def build_person_keys(all_rows, ref_count):
    """{nameKey: entity_id} from every PERSON-REGISTER row, mirroring
    entity-refs.js's own _PERSON_KEY_REG: on a same-surname/same-initial
    collision (several "Collin, H..." family members, say), the person
    with more diary references wins -- a pre-existing, documented
    limitation of that collision strategy, not something
    resolve_shared_surname() introduces."""
    out, out_refs = {}, {}
    for r in all_rows:
        if r["entity_type"] != "person":
            continue
        label = (r.get("label") or "").strip()
        if not label:
            continue
        k = person_name_key(label)
        if not k:
            continue
        refs = ref_count.get(r["entity_id"], 0)
        if k not in out_refs or refs > out_refs[k]:
            out[k] = r["entity_id"]
            out_refs[k] = refs
    return out


def resolve_shared_surname(segments, person_keys):
    """A bare single-word segment ("Georg") that doesn't resolve on its
    own is retried as "<segment> <surname>" against every OTHER segment
    in the same split list (checked both directions -- see the module
    note above for why: the shared surname sits last in "Georg og Edvard
    Brandes" but first in "Dupeuty, Fontan og Davrigny"). Only ever
    upgrades a guess the register already confirms; a segment nothing
    resolves for is returned unchanged, same as today.

    Restricted to exactly 2-element lists: a bare surname's own initial
    letter is enough for the borrowed-surname candidate to accidentally
    collide with a real, unrelated person once a THIRD name is in the
    mix -- "Abrahamson; Nyerup; Rahbek" (three separate 18th/19th-century
    scholars co-editing a ballad anthology, not siblings) upgraded the
    unresolved bare "Rahbek" to "Rahbek Nyerup", which happens to satisfy
    nameKey()'s surname-last parsing as "Nyerup, R." -- coincidentally
    matching the real Rasmus Nyerup (Reg0097130) even though the two
    have nothing to do with each other. The 2-sibling scenario this was
    built for (Brandes brothers, Dupeuty siblings) never has this
    problem since there's only ever one other segment to borrow from."""
    if len(segments) != 2:
        return segments
    resolved = list(segments)
    for i, seg in enumerate(segments):
        if " " in seg or "." in seg:
            continue  # already more than a bare single word -- leave it
        if person_name_key(seg) in person_keys:
            continue  # resolves alone already
        for j, other in enumerate(segments):
            if j == i:
                continue
            other_toks = other.split()
            if not other_toks:
                continue
            candidate = f"{seg} {other_toks[-1]}"
            if person_name_key(candidate) in person_keys:
                resolved[i] = candidate
                break
    return resolved


def join_authors(authors):
    """Danish list convention for redisplaying a split authors list --
    "A, B og C", not "A og B og C" ("og" only before the last name)."""
    if not authors:
        return ""
    if len(authors) == 1:
        return authors[0]
    return ", ".join(authors[:-1]) + " og " + authors[-1]


CREATOR_OVERRIDE_FILES = (
    "novels_plays_tales_parsed.tsv",
    "music_register_parsed.tsv",
    "non_fiction_parsed.tsv",
)


def load_parsed_creator_overrides(person_keys):
    """{entity_id: {"authors": [name, ...], "adapted_from": name_or_None}}
    from CREATOR_OVERRIDE_FILES above -- dedicated, WEMI-rule-based
    section parsers (scripts/parsers/, see docs/data-model/
    wemi-and-relations.md "Parsing rules summarised" §2: the creator sits
    in the title's own parenthetical, e.g. "Grannarne (Fredrika Bremer)"
    → creator "Fredrika Bremer"). Since the coverage-expansion-plan
    follow-up (see git history, 2026-08-28), those parsers also isolate
    individual co-authors ("P. C. Asbjørnsen; Jørgen Moe", "; "-joined in
    06_creator) and, separately, an adaptation source into
    12_adapted_from_creator -- both handled here into their own fields
    rather than left as one raw string. resolve_shared_surname() (see its
    own docstring) additionally upgrades a bare given-name segment to its
    full "Given Surname" form when the person register confirms it, using
    person_keys (build_person_keys()'s output — pass a fresh one built
    from the same entities.csv/ref_count this run is already using).

    This exists because author_from() below falls back to the literal H2
    string (e.g. "ANDRE FORFATTERE") whenever entities.csv's own
    person_derived column is empty for a row. For novels_plays_tales_parsed
    .tsv's "Romaner, Noveller, Eventyr" slice that was 136 of 229 works, as
    of this writing, none showing a real name; the TSV recovers 124 of
    those. Checked against the 93 rows where person_derived is ALSO
    already populated there: only 73 agree, and every disagreement
    inspected by hand was the TSV correcting a defect already documented
    elsewhere in this file -- person_derived's own newline-joined-values
    problem (see author_from's docstring), an unresolved pseudonym ("M.
    Rowel" vs. its real name "Valdemar Thisted"), or a truncated name ("P.
    Chr" vs. "P. Chr. Asbjørnsen") -- never the reverse, so the TSV value
    is trusted with priority over person_derived wherever both exist, not
    just used to fill gaps. See the disagreement log this function's
    caller prints for the full list to review, since a few (e.g.
    Reg001878: "Paul Winther" vs. "Clara Andersen") are genuine conflicts
    this script cannot itself resolve — WEMI doc rule #8: "when ambiguous,
    ask, do not guess."

    music_register_parsed.tsv's own three MUSIK forms were spot-checked
    the same way before being added to CREATOR_OVERRIDE_FILES -- both
    Operaer og Syngestykker and Balletter came back clean (0 flagged rows
    after fixing a matching date-regex bug in parse_music_register.py's
    own is_composer(), the same class of defect
    PREMIERE_DATE_RE/DESCRIPTOR_RE below fixed for novels_plays_tales).
    Rows flagged 06b_creator_is_human=False (a folk/traditional
    attribution like "norsk Folkevise", not a person) are skipped --
    author_from()'s contract is to name a creator EntityRefs.personRid()
    can resolve, not a genre label; novels_plays_tales_parsed.tsv has no
    such column, so .get() defaulting to None (never "False") is a no-op
    for it.

    Only standardpost rows count (inferred_container/krydshenvisning rows
    either have no real RegistryTitelID or aren't a work in their own
    right). Returns {} if none of the files exist yet (fresh clone,
    parsers not run)."""
    year_re = re.compile(r"\b(1[4-9]\d{2}|20\d{2})\b")
    out = {}
    for filename in CREATOR_OVERRIDE_FILES:
        path = os.path.join(PARSED_DIR, filename)
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8", newline="") as f:
            for r in csv.DictReader(f, delimiter="\t"):
                if r.get("01_Posttype") != "standardpost":
                    continue
                if r.get("06b_creator_is_human") == "False":
                    continue
                rid = (r.get("RegistryTitelID") or "").strip()
                creator = (r.get("06_creator") or "").strip()
                if not rid or not creator:
                    continue
                segments = [p.strip() for p in creator.split("; ") if p.strip()]
                # Backstop against a publication/premiere citation slipping
                # through as a "creator" (e.g. "Koldingposten 30.1.1866",
                # "21.5.1854, Dresden") -- every bad value found by
                # hand-reviewing these overrides' output contained a
                # plausible year (1400-2099) somewhere, and no real
                # creator name in this dataset does, so this is precise
                # with no risk of excluding a legitimate one. Checked per
                # segment, not the joined string -- one bad element (e.g.
                # a stray date fragment produced by splitting a garbled
                # premiere-date-list on " og ") must not let its clean
                # siblings through as a partial author list; the whole
                # row is skipped instead, same conservative behaviour the
                # single-string check already had. Each parser's own
                # DESCRIPTOR_RE/PREMIERE_DATE_RE/is_composer() already
                # catch the more structured cases; this is the general
                # backstop for whatever shape slips past those.
                if any(year_re.search(seg) for seg in segments):
                    continue
                segments = resolve_shared_surname(segments, person_keys)
                adapted_from = (r.get("12_adapted_from_creator") or "").strip() or None
                out[rid] = {"authors": segments, "adapted_from": adapted_from}
    return out


def main():
    if not os.path.exists(ENTITIES):
        sys.exit(f"Missing {ENTITIES} — run scripts/normalization/hca_xlsx_to_csv.py first.")

    print(f"Loading {os.path.relpath(ENTITIES, ROOT)}…")
    with open(ENTITIES, encoding="utf-8") as f:
        all_rows = list(csv.DictReader(f))
    # A handful of source titles carry a literal non-breaking space (U+00A0)
    # instead of a plain one -- a copy-paste artifact in the original
    # workbook, e.g. Reg000635 "De fire Aarstider (Fr.\xa0Albani), ..." --
    # normalised here, once, for every entity, so every downstream string
    # comparison (facet dedup, artist_from_billedkunst_title(), etc.) sees
    # the same "Fr. Albani" a plain-space sibling title already produces.
    # Every dedicated parser under scripts/parsers/ already does this same
    # normalisation on its own raw label at load time; this file reads
    # entities.csv directly instead, so it needs its own pass.
    if any("\xa0" in (r.get("label") or "") for r in all_rows):
        for r in all_rows:
            if r.get("label"):
                r["label"] = r["label"].replace("\xa0", " ")
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

    # Needed before load_parsed_creator_overrides() -- see
    # resolve_shared_surname()'s docstring for what this is for.
    person_keys = build_person_keys(all_rows, ref_count)
    print(f"  {len(person_keys):,} person name-keys indexed for shared-surname "
          f"co-author resolution")

    work_langs = load_languages()
    if work_langs:
        print(f"  languages loaded for {len(work_langs):,} works")
    else:
        print("  no work_languages.csv — lang stays null "
              "(run scripts/build_mockup/detect_work_language.py)")

    wd_overlay = load_wikidata_overlay()
    if wd_overlay:
        print(f"  {len(wd_overlay):,} hand-verified Wikidata entries loaded from "
              f"{os.path.relpath(WD_OVERLAY, ROOT)}")

    creator_overrides = load_parsed_creator_overrides(person_keys)
    if creator_overrides:
        print(f"  {len(creator_overrides):,} creator(s) loaded from "
              f"{os.path.relpath(PARSED_DIR, ROOT)}/{{{', '.join(CREATOR_OVERRIDE_FILES)}}}")
        n_multi = sum(1 for v in creator_overrides.values() if len(v["authors"]) > 1)
        n_adapt = sum(1 for v in creator_overrides.values() if v["adapted_from"])
        print(f"    {n_multi:,} with more than one co-author, "
              f"{n_adapt:,} with a separated adaptation source")
        # Disagreements against entities.csv's own person_derived are worth a
        # human glance even though the TSV wins by default (see
        # load_parsed_creator_overrides()'s docstring) -- logged, not
        # silently resolved, per WEMI doc rule #8 ("when ambiguous: ask, do
        # not guess").
        disagreements = []
        for r in rows:
            rid = r["entity_id"]
            override = creator_overrides.get(rid)
            tsv_c = join_authors(override["authors"]) if override else None
            pd = (r.get("person_derived") or "").strip()
            if tsv_c and pd and pd.casefold() != tsv_c.casefold():
                disagreements.append((rid, pd, tsv_c))
        if disagreements:
            print(f"  {len(disagreements)} disagree with person_derived "
                  f"(TSV value used; review if any look wrong):")
            for rid, pd, tsv_c in disagreements:
                print(f"    {rid}: person_derived={pd!r}  tsv={tsv_c!r}")

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

    # Exact full-label index for H. C. Andersen's own part_of container
    # chains (split_container_chain() above) -- deliberately exact-match,
    # not the fuzzy head-term resolve_ref() above: a chain's parent segment
    # ("Nye Eventyr og Historier ... (1858-66)") is itself another row's
    # complete label, byte-for-byte, when that row exists at all. Scoped to
    # H. C. ANDERSEN and built with a duplicate-label guard (a label owned
    # by >1 row -- e.g. a poem's quoted incipit reused across two Digte
    # rows -- can't be resolved unambiguously, so it's left out rather than
    # guessed at).
    hca_label_counts = Counter(
        r["label"].strip() for r in rows
        if (r.get("genre_h2") or "").strip() == "H. C. ANDERSEN"
    )
    hca_label_exact = {
        r["label"].strip(): r["entity_id"] for r in rows
        if (r.get("genre_h2") or "").strip() == "H. C. ANDERSEN"
        and hca_label_counts[r["label"].strip()] == 1
    }

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
        wd, image, attribution_note = wd_overlay.get(rid, (None, None, None))

        # Sted (venue/city) — see place_from_billedkunst_title() and
        # place_from_teater_title() above. Museer og Samlinger is excluded
        # from the BILLEDKUNST extraction the same way author_from() already
        # excludes it: those titles are bare museum names, not "Subject
        # (Artist[, Venue], City)" shaped, so there's nothing to parse.
        h3l = h3.lower()
        place_city = place_venue = None
        if wing == "billedkunst.html" and "museer" not in h3l and "samlinger" not in h3l:
            place_city, place_venue = place_from_billedkunst_title(r["label"], place_labels)
        elif wing == "teater-musik.html":
            place_city, place_venue = place_from_teater_title(r["label"], place_labels)

        override = creator_overrides.get(rid)
        tsv_creator_str = join_authors(override["authors"]) if override else None

        # H. C. Andersen's own part_of container chain (see
        # split_container_chain() above) -- rid is null when the parent
        # segment is a language/edition group header with no row of its
        # own ("Tyske", "Engelske", ...), same "label always, rid when
        # resolvable" shape as see/seeAlso above.
        part_of_ref = None
        if h2 == "H. C. ANDERSEN":
            chain = split_container_chain(r["label"])
            if chain:
                parent_label = chain[0]
                part_of_ref = {"label": parent_label, "rid": hca_label_exact.get(parent_label)}

        generated[rid] = {
            "title": r["label"].strip(),
            "h2": h2 or "ANDRE FORFATTERE",
            "h3": h3 or "—",
            "wing": wing,
            "wingLabel": wing_label,
            "author": author_from(h2, h3, r["label"], r.get("person_derived", ""), place_labels,
                                   tsv_creator=tsv_creator_str),
            # Derived, not curated — langMethod carries the provenance so the
            # UI can say so. See detect_work_language.py.
            "lang": work_langs.get(rid, (None, None))[0],
            "langMethod": work_langs.get(rid, (None, None))[1],
            "refs": ref_count.get(rid, 0),
            "year": best_year(r),
            "date": (r.get("date_derived") or "").strip() or None,
            "see": refs_field(r.get("see"), rid),
            "seeAlso": refs_field(r.get("see_also"), rid),
            "partOf": part_of_ref,
            "contains": [],
            # Hand-verified only — see data/curated/works_wikidata.csv and
            # scripts/parsers/wikidata_lookup.py. null for every work not in
            # that file, same as every other unresolved field here.
            "wd": wd,
            "image": image,
            # Reader-facing caveat (e.g. a historical Raphael attribution
            # scholarship no longer accepts) — work.html's detail view shows
            # this; list/facet/card views never read this field, by design,
            # so it can't surface as noise while browsing. See
            # load_wikidata_overlay()'s docstring for why this is a
            # separate field from the CSV's internal `notes` column.
            "attributionNote": attribution_note,
            "place": format_place(place_city, place_venue),
            "diary": [],
            "related": [],
            "coPlaces": [],
            "coWorks": [],
        }
        # authors: individually-linkable co-authors (see entity-refs.js's
        # worksByAuthor(), which now iterates this instead of the single
        # "author" display string above) -- from the TSV override when one
        # exists, else the single computed "author" string as a one-element
        # list (or [] when there's no author at all), so every caller can
        # rely on this field existing without a None/undefined check.
        # adaptedFrom is the WEMI adaptation source (see
        # extract_adaptation() in the novels/plays/tales parser) -- purely
        # descriptive, not linked to a person entity.
        if override:
            generated[rid]["authors"] = override["authors"]
            generated[rid]["adaptedFrom"] = override["adapted_from"]
        else:
            a = generated[rid]["author"]
            generated[rid]["authors"] = [a] if a else []
            generated[rid]["adaptedFrom"] = None

    print(f"  generated {len(generated)} entries across all {len(rows)} works")

    # ── H. C. Andersen part_of container chains ─────────────────────────────
    # Backfill the reverse direction: every resolved child -> parent link
    # above also earns the parent a "contains" entry pointing at the child,
    # so a collection's own page can list its printings/translations
    # without a separate lookup.
    n_part_of = n_part_of_resolved = 0
    for rid, w in generated.items():
        po = w.get("partOf")
        if not po:
            continue
        n_part_of += 1
        parent_rid = po.get("rid")
        if parent_rid and parent_rid in generated:
            n_part_of_resolved += 1
            generated[parent_rid]["contains"].append({"label": w["title"], "rid": rid})
    if n_part_of:
        print(f"  {n_part_of} H. C. Andersen work(s) carry a part_of container "
              f"relation ({n_part_of_resolved} resolve to a sibling register row)")

    # ── Reciprocal cross-references ─────────────────────────────────────────
    # entities.csv's see/see_also columns are written by hand against ONE
    # side of a pair -- e.g. Reg002779's see_also names "La Fille du régiment"
    # (Reg001983), but Reg001983's own see/see_also columns are empty, even
    # though ITS label also reads "...se ogsaa: Regimentets Datter". The
    # register compiler evidently trusted a reader to notice the connection
    # from either entry in the printed index; the digitised see/see_also
    # columns only capture the direction someone happened to type. Confirmed
    # systemic, not a one-off: of 193 rows with either field set, most have
    # no reciprocal pointer on the target's own row.
    #
    # This pass restores the missing direction: for every resolved A -> B,
    # if B has no pointer back to A in EITHER of its own fields, one is
    # added to B's seeAlso (never `see` -- that field's stronger "this IS
    # that" framing is reserved for what a human actually typed; an inferred
    # backlink only ever claims the softer "see also"). Pairwise only, no
    # transitive closure: A -> B -> C does not imply A -> C.
    added_backlinks = 0
    for rid, w in list(generated.items()):
        for field in ("see", "seeAlso"):
            for ref in w[field]:
                target = ref.get("rid")
                if not target or target not in generated:
                    continue  # unresolved label, or resolved to a non-work id
                tgt = generated[target]
                already = any(b.get("rid") == rid for b in tgt["see"] + tgt["seeAlso"])
                if already:
                    continue
                tgt["seeAlso"].append({
                    "label": w["title"], "rid": rid, "inferred": True,
                })
                added_backlinks += 1
    if added_backlinks:
        print(f"  {added_backlinks} reciprocal cross-reference(s) added "
              f"(source data only recorded one direction)")

    billedkunst = [w for w in generated.values() if w["h2"].upper() == "BILLEDKUNST"]
    if billedkunst:
        with_author = sum(1 for w in billedkunst if w["author"])
        print(f"  BILLEDKUNST author coverage: {with_author}/{len(billedkunst)} "
              f"({with_author / len(billedkunst):.0%})")
        with_place = sum(1 for w in billedkunst if w["place"])
        print(f"  BILLEDKUNST Sted coverage: {with_place}/{len(billedkunst)} "
              f"({with_place / len(billedkunst):.0%})")

    teater = [w for w in generated.values() if w["wing"] == "teater-musik.html"]
    if teater:
        with_place = sum(1 for w in teater if w["place"])
        print(f"  TEATER & MUSIK Sted coverage: {with_place}/{len(teater)} "
              f"({with_place / len(teater):.0%})")

    # "Real name" vs. the literal H2 group string ("ANDRE FORFATTERE", "H. C.
    # ANDERSEN") author_from() falls back to when nothing better is
    # available — the gap load_parsed_creator_overrides() exists to close,
    # and what's left is exactly what a new scripts/parsers/parse_*.py slice
    # (see docs/pipeline/stages.md) would need to cover next.
    generic_h2_labels = {"ANDRE FORFATTERE", "H. C. ANDERSEN"}
    non_billedkunst = [w for w in generated.values() if w["h2"].upper() != "BILLEDKUNST"]
    if non_billedkunst:
        generic = sum(1 for w in non_billedkunst if w["author"] in generic_h2_labels)
        real = sum(1 for w in non_billedkunst if w["author"] and w["author"] not in generic_h2_labels)
        print(f"  Non-BILLEDKUNST author coverage: {real:,}/{len(non_billedkunst):,} real "
              f"({real / len(non_billedkunst):.0%}), {generic:,} still fall back to the "
              f"literal H2 group label")

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
