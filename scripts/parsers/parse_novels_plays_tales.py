#!/usr/bin/env python3
"""Parse the novels/plays/tales slice of the canonical workbook into a
structured 12-column TSV.

See docs/pipeline/stages.md (Stage 2) for context, and
docs/data-model/source-data-characteristics.md / wemi-and-relations.md for
the parenthetical conventions and Se-ogsaa semantics encoded below.

Default slice: RegistryCategory='VÆRK-REGISTER',
WorkGenre='ANDRE FORFATTERE', RegistryForm='Romaner, Noveller, Eventyr'.
A different RegistryForm (e.g. 'Skuespil', 'Digte') can be selected via --form.

Column schema
-------------
01_Posttype          : standardpost | krydshenvisning | inferred_container
02_by_Andersen       : False throughout (all other-author works)
03_genre             : NovelsPlaysTales
04_main_title        : Primary title
05_original_title    : Alternative / original-language title (plain 2nd paren)
06_creator           : Author
07_part_of           : Container work (from af: / guillemet pattern)
08_Se_ogsaa          : WEMI relation (- Se ogsaa:)
09_Krydshenvisning_til: Cross-reference target
10_cited_directly    : True = Andersen cited this directly; False = inferred container
11_Note              : Year, descriptor, source, or other note
RegistryTitelID      : From source workbook

Inferred containers
-------------------
Whenever part_of is populated, a second row is emitted immediately after the
source row with Posttype=inferred_container and cited_directly=False.
These represent the container works that Andersen did NOT cite directly — he
cited a subsection, not the whole.

Usage:
    python parse_novels_plays_tales.py [--xlsx PATH] [--output PATH]
                                       [--form FORM] [--genre GENRE]
"""

import argparse
import csv
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _common import load_registry_slice, resolve_ground_truth_xlsx


COLUMNS = [
    "01_Posttype", "02_by_Andersen", "03_genre",
    "04_main_title", "05_original_title", "06_creator",
    "07_part_of", "08_Se_ogsaa", "09_Krydshenvisning_til",
    "10_cited_directly", "11_Note", "RegistryTitelID",
]
GENRE = "NovelsPlaysTales"

# ── Patterns ─────────────────────────────────────────────────────────────────

KRYDS_RE = re.compile(r"^(.+?),\s*se:\s*(.+)$", re.IGNORECASE | re.DOTALL)

SE_OGSAA_RE = re.compile(r"\s*-\s*Se ogsaa:\s*(.+?)\.?\s*$", re.IGNORECASE)

# af: / af »Title« inside a parenthesis → part_of
AF_PAREN_RE = re.compile(
    r"\([^)]*?\baf(?::\s*|\s+(?=»))(?:»([^«]+)«[^)]*|([^)]*?))\)",
    re.IGNORECASE,
)

PAREN_RE = re.compile(r"\(([^)]+)\)")

# Single-word generic terms and bare years → Note rather than original_title
DESCRIPTOR_RE = re.compile(
    r"^(\d{4}|Skolebog|Anonym|Folkebogen|Anonymus|Uddrag)$",
    re.IGNORECASE,
)

KNOWN_TITLES: set[str] = set()


# ── Helpers ──────────────────────────────────────────────────────────────────

def make_row(
    posttype: str,
    main_title: str,
    *,
    original_title: str = "",
    creator: str = "",
    part_of: str = "",
    se_ogsaa: str = "",
    kryds_til: str = "",
    cited_directly: str = "True",
    note: str = "",
    reg_id: str = "",
) -> dict:
    return {
        "01_Posttype": posttype,
        "02_by_Andersen": "False",
        "03_genre": GENRE,
        "04_main_title": main_title,
        "05_original_title": original_title,
        "06_creator": creator,
        "07_part_of": part_of,
        "08_Se_ogsaa": se_ogsaa,
        "09_Krydshenvisning_til": kryds_til,
        "10_cited_directly": cited_directly,
        "11_Note": note,
        "RegistryTitelID": reg_id,
    }


def classify_plain_paren(content: str) -> str:
    if DESCRIPTOR_RE.match(content.strip()):
        return "note"
    if content.strip() in KNOWN_TITLES:
        return "part_of"
    return "original_title"


def strip_parens(label: str, matches: list) -> str:
    result = label
    for m in sorted(matches, key=lambda x: x.start(), reverse=True):
        result = result[: m.start()] + result[m.end() :]
    return re.sub(r"\s+", " ", result).strip().rstrip("., ")


# ── Parser ───────────────────────────────────────────────────────────────────

def parse_row(raw_label: str, reg_id: str) -> list[dict]:
    label = raw_label.replace("\xa0", " ").strip()
    out: list[dict] = []

    km = KRYDS_RE.match(label)
    if km:
        out.append(make_row(
            "krydshenvisning",
            km.group(1).strip(),
            kryds_til=km.group(2).strip().rstrip("."),
            reg_id=reg_id,
        ))
        return out

    se_ogsaa = ""
    sm = SE_OGSAA_RE.search(label)
    if sm:
        se_ogsaa = sm.group(1).strip()
        label = label[: sm.start()].strip()

    part_of = ""
    af_m = AF_PAREN_RE.search(label)
    if af_m:
        part_of = (af_m.group(1) or af_m.group(2) or "").strip()
        label = (label[: af_m.start()] + label[af_m.end() :]).strip()

    remaining = list(PAREN_RE.finditer(label))

    original_title = ""
    creator = ""
    note_parts: list[str] = []

    if remaining:
        creator = remaining[-1].group(1).strip()
        earlier = remaining[:-1]

        for p in earlier:
            content = p.group(1).strip()
            role = classify_plain_paren(content)
            if role == "part_of" and not part_of:
                part_of = content
            elif role == "original_title" and not original_title:
                original_title = content
            else:
                note_parts.append(content)

    main_title = strip_parens(label, remaining)
    note = "; ".join(note_parts)

    out.append(make_row(
        "standardpost",
        main_title,
        original_title=original_title,
        creator=creator,
        part_of=part_of,
        se_ogsaa=se_ogsaa,
        cited_directly="True",
        note=note,
        reg_id=reg_id,
    ))

    if part_of:
        out.append(make_row(
            "inferred_container",
            part_of,
            creator=creator,
            cited_directly="False",
        ))

    return out


# ── Main ─────────────────────────────────────────────────────────────────────

def run(
    xlsx: pathlib.Path,
    dst: pathlib.Path,
    *,
    genre: str,
    form: str,
) -> pathlib.Path:
    slice_rows = load_registry_slice(
        xlsx,
        category="VÆRK-REGISTER",
        genre=genre,
        form=form,
    )

    KNOWN_TITLES.clear()
    for title, _ in slice_rows:
        bare = PAREN_RE.sub("", title).strip().rstrip("., ")
        KNOWN_TITLES.add(bare)

    output: list[dict] = []
    for title, reg_id in slice_rows:
        output.extend(parse_row(title, reg_id))

    with open(dst, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS, delimiter="\t")
        w.writeheader()
        for r in output:
            w.writerow(r)

    n_std = sum(1 for r in output if r["01_Posttype"] == "standardpost")
    n_kryd = sum(1 for r in output if r["01_Posttype"] == "krydshenvisning")
    n_inf = sum(1 for r in output if r["01_Posttype"] == "inferred_container")
    n_pof = sum(1 for r in output if r["07_part_of"])
    n_orig = sum(1 for r in output if r["05_original_title"])

    print(f"Source : {xlsx.name}  (slice: {genre} / {form})")
    print(f"Written: {dst}")
    print(f"Rows   : {len(output)}")
    print(f"  standardpost      : {n_std}")
    print(f"  krydshenvisning   : {n_kryd}")
    print(f"  inferred_container: {n_inf}  (cited_directly=False)")
    print(f"  with part_of      : {n_pof}")
    print(f"  with original_title: {n_orig}")
    return dst


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--xlsx", type=pathlib.Path, default=None)
    ap.add_argument(
        "--output",
        type=pathlib.Path,
        default=pathlib.Path("data/parsed/novels_plays_tales_parsed.tsv"),
    )
    ap.add_argument("--genre", default="ANDRE FORFATTERE")
    ap.add_argument("--form", default="Romaner, Noveller, Eventyr")
    args = ap.parse_args()
    xlsx = args.xlsx or resolve_ground_truth_xlsx()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    run(xlsx, args.output, genre=args.genre, form=args.form)


if __name__ == "__main__":
    main()
