#!/usr/bin/env python3
"""Parse the MUSIK slices of the canonical workbook into a structured
13-column TSV.

See docs/pipeline/stages.md (Stage 2) for context, and
docs/data-model/source-data-characteristics.md for the parenthetical
conventions encoded in the parsing logic below.

Default slice: RegistryCategory='VÆRK-REGISTER', WorkGenre='MUSIK', across
the three RegistryForm values in DEFAULT_FORMS below (Vokal- og
Instrumentalmusik, Operaer og Syngestykker/Skuespil med Musik, Balletter)
-- originally just the first of these; the other two were added once their
own creator column was checked for the same issues found in the ANDRE
FORFATTERE forms (see build_works_extra.py's
load_parsed_creator_overrides()). Pass one or more --form to parse only
specific forms instead (repeatable; overrides the default list entirely).

Usage:
    python parse_music_register.py [--xlsx PATH] [--output PATH] [--form FORM ...]
"""

import argparse
import csv
import pathlib
import re
import sys
from collections import Counter

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _common import load_registry_slice, resolve_ground_truth_xlsx


# ── Patterns ─────────────────────────────────────────────────────────────────

FOLK_RE = re.compile(r"^(norsk|tysk|irsk|svensk|napolitansk|dansk|Folke)", re.I)
NOTE_RE = re.compile(r"^(Hvilken|Sang af|Hvad|Ukendt)", re.I)
OPUS_RE = re.compile(r"^op\.", re.I)
AF_RE = re.compile(r"^af[: ]", re.I)
GUILLEMET = re.compile(r"[»«](.+?)[«»]", re.S)
OPUS_EMBEDDED = re.compile(r",?\s*(op\.\s*\d+[a-z]?(?:\s+nr\.\s*\d+)?)\s*$", re.I)

# Co-author splitting, same rule and same rationale as
# parse_novels_plays_tales.py's split_creators()/strip_role_label(): only
# " og " is reliably splittable (a bare comma list risks being one
# person's name-plus-title, not two people); a leading "Udg."/"Red." role
# label joined by "og" to a second role label ("Udg. og Red.: X") is one
# person with two roles, not two people, so it's stripped first. Smaller
# scope here than the sibling parser -- MUSIK's own creator field rarely
# carries the "efter"/"bearbejdet af" adaptation-credit shape that parser
# handles (checked directly: 12 of 407 creators contain " og ", none of
# the messier compound ones -- left unsplit, same "ask, don't guess"
# discipline).
_ROLE_LABEL_RE = re.compile(
    r"^(?:Udg\.|Red\.)(?:\s+og\s+(?:Udg\.|Red\.))?\s*:\s*", re.IGNORECASE,
)


def split_creators(creator: str) -> str:
    creator = _ROLE_LABEL_RE.sub("", creator, count=1)
    if " og " not in creator:
        return creator
    head, last = creator.rsplit(" og ", 1)
    parts = [p.strip() for p in head.split(",") if p.strip()] + [last.strip()]
    return "; ".join(parts)


# ── Helpers ──────────────────────────────────────────────────────────────────

def extract_parens(s):
    """Extract top-level parenthetical groups from string."""
    groups, depth, cur = [], 0, ""
    for ch in s:
        if ch == "(":
            if depth > 0:
                cur += ch
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                groups.append(cur.strip())
                cur = ""
            else:
                cur += ch
        elif depth > 0:
            cur += ch
    return groups


def is_composer(s):
    return not (
        OPUS_RE.match(s)
        or AF_RE.match(s)
        or FOLK_RE.match(s)
        or NOTE_RE.match(s)
        or s.startswith("»")
        or s.startswith("«")
        or s.startswith("=")
        # A premiere date+venue, common on Operaer/Balletter entries
        # ("18.1.1863, Tours", "9.10.1833, Firenze") -- {1,2} not a fixed
        # {2}, since the source often has a single-digit day or month
        # ("8.4.1843") that a strict two-digit pattern misses, letting the
        # date+venue fall through and get misread as the creator instead.
        or re.search(r"\d{1,2}\.\d{1,2}\.\d{4}", s)
    )


def strip_guillemets(s):
    return re.sub(r"[»««»]", "", s).strip()


def extract_embedded_opus(s):
    """Remove trailing ', op. N' from a string. Returns (cleaned, opus)."""
    m = OPUS_EMBEDDED.search(s)
    return (s[: m.start()].strip(), m.group(1).strip()) if m else (s, "")


def assign_parens(r, parens):
    """Assign parenthetical groups to the correct fields.

    Guillemet rule: guillemet content in a parenthetical is treated as
    part_of (source reference), NOT as incipit — unless incipit is still
    empty AND the parens has no surrounding source text (e.g. 'Sang af').
    """
    remaining = []

    for p in parens:
        if OPUS_RE.match(p):
            r["opus"] = p

        elif AF_RE.match(p):
            r["part_of"] = p

        elif GUILLEMET.search(p):
            outer = GUILLEMET.sub("", p).strip(" -.,")

            if outer:
                r["part_of"] = (r["part_of"] + " | " if r["part_of"] else "") + p
            elif not r["incipit"]:
                r["incipit"] = strip_guillemets(GUILLEMET.search(p).group(1))
            else:
                r["part_of"] = (r["part_of"] + " | " if r["part_of"] else "") + p

        elif FOLK_RE.match(p):
            r["creator"] = p
            r["creator_is_human"] = "False"

        elif NOTE_RE.match(p):
            r["note"] = (r["note"] + " | " if r["note"] else "") + p

        elif p.startswith("="):
            r["note"] = (r["note"] + " | " if r["note"] else "") + f"({p})"

        else:
            remaining.append(p)

    if remaining and is_composer(remaining[-1]):
        r["creator"] = split_creators(remaining.pop())
        r["creator_is_human"] = "True"

    if remaining and not r["original_title"]:
        r["original_title"] = remaining.pop(0)

    for p in remaining:
        r["note"] = (r["note"] + " | " if r["note"] else "") + f"({p})"

    if r["original_title"] and not r["opus"]:
        cleaned, opus = extract_embedded_opus(r["original_title"])
        if opus:
            r["original_title"] = cleaned
            r["opus"] = opus


# ── Main parser ──────────────────────────────────────────────────────────────

def parse(raw, reg_id=""):
    r = dict(
        Posttype="",
        by_Andersen="False",
        genre="VocalAndInstrumentalMusic",
        main_title="",
        incipit="",
        original_title="",
        creator="",
        creator_is_human="",
        opus="",
        part_of="",
        kryds="",
        note="",
        RegistryTitelID=reg_id,
    )
    entry = raw.strip().rstrip(".")

    m = re.match(r"^(.+),\s*\nse:\s*(.+)$", entry, re.DOTALL | re.I)
    if m:
        r["Posttype"] = "krydshenvisning"
        r["main_title"] = m.group(1).strip()
        r["kryds"] = m.group(2).strip().rstrip(".")
        return r

    r["Posttype"] = "standardpost"

    sq = re.match(r"^\[([^\]]+)\](.*)", entry)
    if sq:
        r["main_title"] = f"[{sq.group(1)}]"
        assign_parens(r, extract_parens(sq.group(2).strip()))
        return r

    inc = re.match(r"^[»«](.+?)[«»](.*)", entry, re.S)
    if inc:
        r["incipit"] = inc.group(1).strip()
        assign_parens(r, extract_parens(inc.group(2).strip()))
        return r

    fp = entry.find("(")
    if fp == -1:
        r["main_title"] = entry.strip()
        return r

    r["main_title"] = entry[:fp].strip().rstrip(",").strip()
    assign_parens(r, extract_parens(entry[fp:]))
    return r


# ── I/O ──────────────────────────────────────────────────────────────────────

FIELDNAMES = [
    "01_Posttype",
    "02_by_Andersen",
    "03_genre",
    "04_main_title",
    "04b_incipit",
    "05_original_title",
    "06_creator",
    "06b_creator_is_human",
    "07_opus",
    "08_part_of",
    "09_Krydshenvisning_til",
    "10_Note",
    "RegistryTitelID",
]


# MUSIK forms this parser covers. Vokal- og Instrumentalmusik was the
# original, sole slice; the other two were added once their own output was
# checked for the same digit/year-in-creator defects the ANDRE FORFATTERE
# forms had (see docs/pipeline/stages.md and
# build_works_extra.py's load_parsed_creator_overrides()) -- both came back
# clean, so no parser-logic fix was needed here the way parse_novels_
# plays_tales.py's PREMIERE_DATE_RE/DESCRIPTOR_RE fix was.
DEFAULT_FORMS = (
    "Vokal- og Instrumentalmusik",
    "Operaer og Syngestykker, Skuespil med Musik",
    "Balletter",
)


def run(xlsx: pathlib.Path, dst: pathlib.Path, *, forms: list[str] = None) -> pathlib.Path:
    forms = forms if forms else list(DEFAULT_FORMS)
    results: list[dict] = []
    per_form_counts: list[tuple[str, int, int]] = []  # (form, standardpost, with_creator)

    for form in forms:
        slice_rows = load_registry_slice(
            xlsx,
            category="VÆRK-REGISTER",
            genre="MUSIK",
            form=form,
        )
        form_results = [parse(title, reg_id) for title, reg_id in slice_rows]
        results.extend(form_results)
        std = [r for r in form_results if r["Posttype"] == "standardpost"]
        with_creator = sum(1 for r in std if r["creator"] and r["creator_is_human"] != "False")
        per_form_counts.append((form, len(std), with_creator))

    with open(dst, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(
            f, fieldnames=FIELDNAMES, delimiter="\t", extrasaction="ignore"
        )
        w.writeheader()
        for r in results:
            w.writerow(
                {
                    "01_Posttype": r["Posttype"],
                    "02_by_Andersen": r["by_Andersen"],
                    "03_genre": r["genre"],
                    "04_main_title": r["main_title"],
                    "04b_incipit": r["incipit"],
                    "05_original_title": r["original_title"],
                    "06_creator": r["creator"],
                    "06b_creator_is_human": r["creator_is_human"],
                    "07_opus": r["opus"],
                    "08_part_of": r["part_of"],
                    "09_Krydshenvisning_til": r["kryds"],
                    "10_Note": r["note"],
                    "RegistryTitelID": r["RegistryTitelID"],
                }
            )

    pt = Counter(r["Posttype"] for r in results)
    print(f"Source: {xlsx.name}  (genre: MUSIK)")
    print(f"   To:  {dst}")
    for form, std_n, creator_n in per_form_counts:
        pct = f"{creator_n / std_n:.0%}" if std_n else "n/a"
        print(f"   {form:<50s} {std_n:5d} rows, {creator_n:5d} with a human creator ({pct})")
    print(f" Rows:  {len(results)}  |  {dict(pt)}")
    return dst


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--xlsx",
        type=pathlib.Path,
        default=None,
        help="Path to ground-truth workbook (default: highest version in raw/)",
    )
    ap.add_argument(
        "--output",
        type=pathlib.Path,
        default=pathlib.Path("data/parsed/music_register_parsed.tsv"),
        help="Output TSV path (default: data/parsed/music_register_parsed.tsv)",
    )
    ap.add_argument(
        "--form",
        action="append",
        default=None,
        help="RegistryForm to include; repeatable. Defaults to all three "
             "forms in DEFAULT_FORMS above when omitted.",
    )
    args = ap.parse_args()
    xlsx = args.xlsx or resolve_ground_truth_xlsx()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    forms = args.form if args.form else list(DEFAULT_FORMS)
    run(xlsx, args.output, forms=forms)


if __name__ == "__main__":
    main()
