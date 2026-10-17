#!/usr/bin/env python3
"""
parse_person_ethnic_descriptors.py
-----------------------------------
Scans the PERSON-REGISTER rows of the canonical Repository workbook
(data/raw/HCA REPOSITORY V0.82/HCA-Repository V0.82.xlsx, sheet
"Registry") for ethnic/national adjectives (svensk, tysk, jødisk, …) in
each row's RegistryDescription — the free-text subfield that follows the
entry's name/date-range in RegistryTitle.

The canonical adjective table lives in data/curated/ethnic_adjectives_da.csv
(surface forms grouped by nationality key and category — national,
german_state, border_region, regional_danish, colonial, historical_polity,
regional_foreign, ethnolinguistic, religious_ethnic, supranational). It is
hand-curated but grounded in an actual frequency scan of this corpus — see
docs/data-model/person-ethnic-descriptors.md for the methodology and the
false-positive families that were deliberately excluded (academic-field
adjectives like "romansk Filolog", religious terms like "katolsk",
title/agent nouns like "marsk"/"husholderske", and surname-derived
"-ske" adjectives like "Anckerske" that are morphologically identical to
an ethnic plural but name a person's estate/foundation, not a nationality).

Matching is whitelist-only (never a bare "-sk/-isk" suffix heuristic) so
none of those false-positive families can slip through by construction.
Every token is still checked, and unmatched "-sk/-iske"-shaped candidates
above a frequency threshold are written to a review CSV so new vocabulary
(or transcription typos, see docs) surfaces on every re-run instead of
silently vanishing.

For every match this script records whether the adjective was the very
first token of the description (all but certainly describing the
register person) or appeared further in ("embedded") — plus a best-effort
heuristic for *why* it might not describe the subject (a relation marker
like "gift med" / "søn af", or a definite article suggesting it modifies
an institution, e.g. "Præst for den tyske Menighed"). This heuristic is a
triage aid for human review, not a classifier — see the docs page.

Writes:
  data/normalized/person_ethnic_descriptors.csv         — every match
  data/normalized/person_ethnic_descriptors_review.csv  — unmatched
                                                            "-sk/-iske"
                                                            candidates,
                                                            for ongoing
                                                            manual review

Stdlib + openpyxl.
"""

import csv
import os
import re
import sys

import openpyxl

ROOT       = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
WORKBOOK   = os.path.join(ROOT, "data", "raw", "HCA REPOSITORY V0.82", "HCA-Repository V0.82.xlsx")
ADJ_TABLE  = os.path.join(ROOT, "data", "curated", "ethnic_adjectives_da.csv")
EXPANSIONS = os.path.join(ROOT, "data", "curated", "ethnic_adjective_expansions_da.csv")
OUT        = os.path.join(ROOT, "data", "normalized", "person_ethnic_descriptors.csv")
REVIEW_OUT = os.path.join(ROOT, "data", "normalized", "person_ethnic_descriptors_review.csv")

# Any Unicode letter run, plus internal ASCII hyphens for compounds like
# "tysk-fransk". Using \w-minus-digits (not a hand-enumerated accent
# list) so names with ü/ö/ñ/ç etc. tokenize correctly — an earlier draft
# hand-listed accented letters and silently mis-split "württembergsk"
# into "W" + "rttembergsk" at the ü. See docs for the full story.
WORD_RE = re.compile(r"[^\W\d_]+(?:-[^\W\d_]+)*", re.UNICODE)

# Compounds that name ONE historical/political entity, not two ethnicities
# of the person — e.g. "tysk-romersk Kejser" = Holy Roman Emperor, not
# "German and Roman". These are matched (and categorised) as a whole
# token via the adjective table itself (see ethnic_adjectives_da.csv);
# every OTHER hyphenated token is split and treated as genuine dual
# nationality (both parts really do describe the person — e.g.
# "czekisk-dansk Violoncellist").
FIXED_COMPOUND_NOTE = {
    "tysk-romersk", "tysk-romerske",
    "dansk-vestindisk", "dansk-vestindiske",
    "holsten-lauenborgsk", "holsten-lauenborgske",
    "slesvig-holstensk", "slesvig-holstenske",
    "slesvig-holsten-lauenborgsk", "slesvig-holsten-lauenborgske",
    "slesvig-holsten-lauenburgske",
}

# Markers checked in the 1-3 tokens immediately before an EMBEDDED match
# (position > 0) to flag it as likely describing someone/something other
# than the register subject. Best-effort triage, not a classifier.
RELATION_MARKERS = {
    "g", "gift", "m", "med", "enke", "enkemand", "søn", "datter",
    "broder", "søster", "hustru", "ægtefælle", "svigersøn", "svigerdatter",
}
INSTITUTION_ARTICLES = {"det", "den", "de"}


def load_expansions(path):
    """{key: [target_key, …]} from data/curated/ethnic_adjective_expansions_da.csv.
    Optional: absent file = no dissolved categories."""
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8", newline="") as f:
        return {row["key"]: [t.strip() for t in row["expands_to"].split(";") if t.strip()]
                for row in csv.DictReader(f)}


def load_adjective_table(path, expansions_path=EXPANSIONS):
    """Returns (form_lookup, labels) where form_lookup maps a casefolded
    surface form to a LIST of (key, label_da, category) hits, and labels
    maps key -> label_da (for reporting).

    A key listed in the expansions file is a dissolved collective
    category: it has no key of its own in the output, and each of its
    forms yields one hit per target key instead (preussisk -> tysk +
    polsk). Targets must be ordinary rows of the adjective table."""
    if not os.path.exists(path):
        sys.exit(f"Missing {path}")
    with open(path, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    by_key = {row["key"]: row for row in rows}
    expansions = load_expansions(expansions_path)
    form_lookup = {}
    labels = {}
    for row in rows:
        targets = expansions.get(row["key"])
        if targets:
            bad = [t for t in targets if t not in by_key or t in expansions]
            if bad:
                sys.exit(f"{row['key']}: expansion targets must be ordinary keys, got {bad}")
            hits = [(t, by_key[t]["label_da"], by_key[t]["category"]) for t in targets]
        else:
            labels[row["key"]] = row["label_da"]
            hits = [(row["key"], row["label_da"], row["category"])]
        for form in row["forms"].split(";"):
            form = form.strip()
            if form:
                form_lookup[form.casefold()] = hits
    return form_lookup, labels


def load_person_rows(path):
    if not os.path.exists(path):
        sys.exit(f"Missing {path}")
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb["Registry"]
    rows_iter = ws.iter_rows(values_only=True)
    header = next(rows_iter)
    idx = {name: i for i, name in enumerate(header)}
    out = []
    for r in rows_iter:
        if r[idx["RegistryCategory (H1)"]] == "PERSON-REGISTER":
            out.append({
                "entity_id":   r[idx["PKRegistryTitelID"]],
                "label":       r[idx["RegistryTitle"]] or "",
                "description": r[idx["RegistryDescription"]] or "",
            })
    wb.close()
    return out


def classify_referent(tokens, match_index):
    """Best-effort triage hint for an embedded (non-leading) match —
    NOT a semantic classifier. See module docstring."""
    window = [t.casefold() for t in tokens[max(0, match_index - 3):match_index]]
    if any(w in RELATION_MARKERS for w in window):
        return "possible_relation"
    if match_index > 0 and tokens[match_index - 1].casefold() in INSTITUTION_ARTICLES:
        return "possible_institution"
    return "unclear"


def parse_matches(persons, form_lookup):
    matches = []
    for p in persons:
        desc = p["description"]
        tokens = [m.group(0) for m in WORD_RE.finditer(desc)]
        for i, tok in enumerate(tokens):
            lt = tok.casefold()
            position_type = "leading" if i == 0 else "embedded"

            def emit(hits, matched_form, match_type):
                referent = "subject" if position_type == "leading" else classify_referent(tokens, i)
                for key, label_da, category in hits:
                    matches.append({
                        "entity_id": p["entity_id"], "label": p["label"],
                        "matched_form": matched_form, "nationality_key": key,
                        "nationality_label": label_da, "category": category,
                        "position_index": i, "position_type": position_type,
                        "match_type": match_type, "referent_hint": referent,
                        "description": desc,
                    })

            hit = form_lookup.get(lt)
            if hit is not None:
                emit(hit, tok, "fixed_compound" if lt in FIXED_COMPOUND_NOTE else "single")
                continue

            if "-" in lt:
                for part in lt.split("-"):
                    if part in form_lookup:
                        emit(form_lookup[part], f"{tok} (part: {part})", "hyphen_compound")
                continue

            # No-hyphen dual-nationality compound, e.g. "svensknorsk" =
            # "svensk" + "norsk" written solid. Only worth the O(len)
            # split-point scan for tokens already shaped like an
            # adjective (the -sk/-iske review scan's own filter), so this
            # never fires on ordinary long words.
            if re.search(r"(sk|ske)$", lt) and len(lt) > 6:
                for cut in range(3, len(lt) - 2):
                    left, right = lt[:cut], lt[cut:]
                    if left in form_lookup and right in form_lookup:
                        for part in (left, right):
                            emit(form_lookup[part], f"{tok} (part: {part})", "solid_compound")
                        break
    return matches


def find_review_candidates(persons, form_lookup, min_count=1):
    """Every '-sk/-iske'-shaped token NOT covered by the whitelist —
    surfaced so new vocabulary or transcription typos (see docs, e.g.
    'fiansk' for 'fransk') don't silently disappear on future runs."""
    candidate_re = re.compile(r"(sk|ske)$")
    counts = {}
    examples = {}
    for p in persons:
        desc = p["description"]
        for tok in WORD_RE.finditer(desc):
            t = tok.group(0)
            lt = t.casefold()
            if len(lt) <= 3 or not candidate_re.search(lt):
                continue
            if lt in form_lookup:
                continue
            if "-" in lt and any(part in form_lookup for part in lt.split("-")):
                continue
            if len(lt) > 6 and any(
                lt[:cut] in form_lookup and lt[cut:] in form_lookup
                for cut in range(3, len(lt) - 2)
            ):
                continue
            counts[lt] = counts.get(lt, 0) + 1
            if lt not in examples:
                start = tok.start()
                examples[lt] = f"{p['label']}: …{desc[max(0, start - 20):start + len(t) + 15]}…"
    rows = [
        {"candidate": k, "count": v, "example": examples[k]}
        for k, v in counts.items() if v >= min_count
    ]
    rows.sort(key=lambda r: (-r["count"], r["candidate"]))
    return rows


def main():
    print(f"Loading {os.path.relpath(ADJ_TABLE, ROOT)}…")
    form_lookup, labels = load_adjective_table(ADJ_TABLE)
    print(f"  {len(labels):,} nationality keys, {len(form_lookup):,} surface forms")

    print(f"Loading {os.path.relpath(WORKBOOK, ROOT)}…")
    persons = load_person_rows(WORKBOOK)
    print(f"  {len(persons):,} PERSON-REGISTER rows")

    matches = parse_matches(persons, form_lookup)
    leading = sum(1 for m in matches if m["position_type"] == "leading")
    embedded = sum(1 for m in matches if m["position_type"] == "embedded")
    rows_with_match = len({m["entity_id"] for m in matches})
    print(f"  {len(matches):,} matches on {rows_with_match:,} rows "
          f"({rows_with_match / len(persons):.1%} of the register)")
    print(f"    leading (description's first word): {leading:,}")
    print(f"    embedded (further into the description): {embedded:,}")
    referent_counts = {}
    for m in matches:
        if m["position_type"] == "embedded":
            referent_counts[m["referent_hint"]] = referent_counts.get(m["referent_hint"], 0) + 1
    for hint, n in sorted(referent_counts.items(), key=lambda x: -x[1]):
        print(f"      {hint}: {n:,}")

    with open(OUT, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=[
            "entity_id", "label", "matched_form", "nationality_key", "nationality_label",
            "category", "position_index", "position_type", "match_type", "referent_hint",
            "description",
        ])
        w.writeheader()
        w.writerows(matches)
    print(f"  wrote {os.path.relpath(OUT, ROOT)}")

    review = find_review_candidates(persons, form_lookup)
    with open(REVIEW_OUT, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["candidate", "count", "example"])
        w.writeheader()
        w.writerows(review)
    print(f"  wrote {os.path.relpath(REVIEW_OUT, ROOT)}  ({len(review):,} unmatched candidates for review)")


if __name__ == "__main__":
    main()
