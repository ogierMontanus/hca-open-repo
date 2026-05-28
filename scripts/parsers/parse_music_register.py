#!/usr/bin/env python3
"""Parse the vocal-and-instrumental-music slice of the canonical workbook
into a structured 13-column TSV.

See docs/pipeline/stages.md (Stage 2) for context, and
docs/data-model/source-data-characteristics.md for the parenthetical
conventions encoded in the parsing logic below.

Default slice: RegistryCategory='VÆRK-REGISTER',
WorkGenre='MUSIK', RegistryForm='Vokal- og Instrumentalmusik'.

Usage:
    python parse_music_register.py [--xlsx PATH] [--output PATH]
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
        or re.search(r"\d{2}\.\d{2}\.\d{4}", s)
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
        r["creator"] = remaining.pop()
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


def run(xlsx: pathlib.Path, dst: pathlib.Path) -> pathlib.Path:
    slice_rows = load_registry_slice(
        xlsx,
        category="VÆRK-REGISTER",
        genre="MUSIK",
        form="Vokal- og Instrumentalmusik",
    )

    results = [parse(title, reg_id) for title, reg_id in slice_rows]

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
    print(f"Source: {xlsx.name}  (slice: MUSIK / Vokal- og Instrumentalmusik)")
    print(f"   To:  {dst}")
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
    args = ap.parse_args()
    xlsx = args.xlsx or resolve_ground_truth_xlsx()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    run(xlsx, args.output)


if __name__ == "__main__":
    main()
