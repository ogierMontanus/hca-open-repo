#!/usr/bin/env python3
"""
apply_cue_splits.py
---------------------
Applies ONLY the rows suggest_cue_splits.py marked SAFE -- those where
xlsx DimPer independently confirms every fragment as its own entry.
MANUAL rows are never touched.

Each SAFE row becomes N rows: the first keeps the original surname and
the original row's years/description/references; each later fragment
becomes a new standardpost whose name and years are taken from the
fragment text, with the years cross-checked against the xlsx title that
matched it. Entry ids are renumbered afterwards, since they are
positional.

Run from the repo root, AFTER suggest_cue_splits.py:
  python scripts/parsers/apply_cue_splits.py
"""
import csv
import os
import re

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PARSED_TSV = os.path.join(ROOT, "data", "parsed", "personregister_xi_parsed.tsv")
REVIEW_TSV = os.path.join(ROOT, "data", "curated", "personregister_xi_cue_split_review.tsv")

# Leading alphabet section divider ("O. Oberlin, ..." -> "Oberlin, ...").
# The letter must match the surname that follows, and that surname must
# be a real word, not another initial: "E. A. (dod 1891)" is Norgaard's
# given names "E. A.", not a divider before a surname "A.".
SECTION_DIVIDER = re.compile(r"^([A-ZÆØÅ])\.\s+(?=([A-ZÆØÅÖÜ][a-zæøåöäü]{2,}))")
# Years as printed in an xlsx title: "(1735-1806)", "(dod 1891)",
# "(ca. 1260-1318)", "(1828-efter 1889)".
XL_YEARS = re.compile(
    r"\((?:ca\.\s*)?(?:(?P<d_only>(?:d\.|død)\s*(?P<dy>\d{3,4}))"
    r"|(?P<b>\d{3,4})\s*[–—-]\s*(?:efter\s*)?(?P<d>\d{3,4}))\)"
)
PARTICLES = {"von", "van", "de", "der", "di", "le", "la", "f", "g", "kaldet", "senere"}
REF_RUN = re.compile(r"((?:I{1,3}|IV|VI{0,3}|IX|X)\s[\d\s\-]*\d)\.\s*$")


def strip_section_divider(frag: str) -> str:
    m = SECTION_DIVIDER.match(frag)
    if m and m.group(1) == m.group(2)[0]:
        return frag[m.end():].strip()
    return frag


def split_name_desc(frag: str):
    """Split a fragment into (name text, description, raw references).

    A fragment reads "<name>[ (years)], <description>. <refs>." -- the
    same shape the main parser expects, so the pieces are recovered the
    same way: references are the trailing roman-numeral run, the name
    ends at the year parenthesis (or at the first comma when there is
    none), and whatever sits between is the description."""
    text = frag.strip()
    refs_raw = ""
    m = REF_RUN.search(text)
    if m:
        refs_raw = text[m.start():].strip()
        text = text[: m.start()].strip().rstrip(",")

    ym = re.search(r"\((?:ca\.\s*)?(?:d\.|død)?\s*\d{2,4}", text)
    if ym:
        close = text.find(")", ym.start())
        cut = close + 1 if close != -1 else ym.start()
        return text[:cut].strip().rstrip(","), text[cut:].strip().lstrip(",").strip(), refs_raw

    # No year parenthesis to cut at (common for the leading fragment of
    # a fused row): the name ends at the first comma-unit that reads as
    # description -- a lowercase word that is not a name particle.
    units = [u.strip() for u in text.split(",")]
    name_units = []
    for i, u in enumerate(units):
        first = u.split()[0] if u.split() else ""
        if i > 0 and first[:1].islower() and first.rstrip(".") not in PARTICLES:
            break
        name_units.append(u)
    # Strip only trailing whitespace/commas -- a trailing period can be
    # part of the name itself ("Bailac, J.").
    name_text = ", ".join(name_units).strip().rstrip(",")
    desc = ", ".join(units[len(name_units):]).strip(" ,")
    return name_text, desc, refs_raw


def parse_refs(raw: str):
    """'VII 343 347 349- 51.' -> ('VII 343 347 349-51.', 'VII:343;...')"""
    out = []
    for m in re.finditer(r"\b(I{1,3}|IV|VI{0,3}|IX|X)\s([\d\s\-]*\d)", raw):
        vol, nums = m.group(1), m.group(2)
        for nm in re.finditer(r"(\d+)(?:\s?-\s?(\d+))?", nums):
            a, b = nm.group(1), nm.group(2)
            if b is None:
                out.append(f"{vol}:{a}")
            else:
                # "398-99" means 398..399, "349-51" means 349..351
                lo, hi = int(a), int(b)
                if hi < lo:
                    hi = int(str(lo)[: len(str(lo)) - len(b)] + b)
                out.extend(f"{vol}:{n}" for n in range(lo, hi + 1))
    return ";".join(out)


def main():
    with open(REVIEW_TSV, encoding="utf-8") as f:
        safe = [r for r in csv.DictReader(f, delimiter="\t") if r["verdict"] == "SAFE"]

    with open(PARSED_TSV, encoding="utf-8") as f:
        rows = list(csv.DictReader(f, delimiter="\t"))
    fieldnames = list(rows[0].keys())

    by_id = {r["min_entry_id"]: r for r in safe}
    out, n_new = [], 0

    for row in rows:
        spec = by_id.get(row["01_entry_id"])
        if not spec:
            out.append(row)
            continue

        frags = spec["fragments"].split(" || ")
        matches = spec["xlsx_matches"].split(" || ")

        # Field ownership in a fused row: the parser matched the year
        # parenthesis of the LAST entry, so 06/07 (years), 09
        # (description) and 10/11 (references) all describe the trailing
        # fragment -- everything belonging to the leading fragment is
        # still sitting as plain text inside 04_given_names. The split
        # therefore hands the row's parsed fields to the LAST fragment
        # and reconstructs the earlier ones from their own text.
        n = len(frags)
        for i, frag in enumerate(frags):
            frag = strip_section_divider(frag)
            is_last = i == n - 1
            is_first = i == 0

            if is_first:
                surname = row["03_surname"]
                name_text, desc, refs_raw = split_name_desc(frag)
                given = name_text
            else:
                name_text, desc, refs_raw = split_name_desc(frag)
                surname = name_text.split(",")[0].strip()
                given = name_text.split(",", 1)[1].strip() if "," in name_text else ""

            if is_last:
                # Inherit the fields the parser already extracted. Its
                # 13_raw_text must keep the description and references
                # those fields hold, so rebuild it rather than reducing
                # it to the (name-only) fragment text.
                new = dict(row)
                new["03_surname"] = surname
                new["04_given_names"] = given
                new["13_raw_text"] = " ".join(
                    x for x in (frag + ",", row["09_description"], row["10_references_raw"]) if x
                ).strip()
            else:
                birth = death = ""
                ym = XL_YEARS.search(matches[i])
                if ym:
                    if ym.group("d_only"):
                        death = ym.group("dy")
                    else:
                        birth, death = ym.group("b"), ym.group("d")
                new = {k: "" for k in fieldnames}
                new.update({
                    "02_entry_type": row["02_entry_type"],
                    "03_surname": surname,
                    "04_given_names": given,
                    "06_birth_year": birth,
                    "07_death_year": death,
                    "09_description": desc,
                    "10_references_raw": refs_raw,
                    "11_references_parsed": parse_refs(refs_raw),
                    "13_raw_text": frag,
                })
                n_new += 1

            new["05_sort_key"] = f"{surname}, {given}".strip().rstrip(",")
            out.append(new)

    for i, r in enumerate(out, start=1):
        r["01_entry_id"] = f"PerXI{i:05d}"

    with open(PARSED_TSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, delimiter="\t")
        w.writeheader()
        w.writerows(out)

    print(f"applied {len(safe)} SAFE splits -> {n_new} new entries")
    print(f"rows: {len(rows)} -> {len(out)}")


if __name__ == "__main__":
    main()
