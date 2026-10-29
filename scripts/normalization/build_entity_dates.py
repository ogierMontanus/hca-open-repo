"""build_entity_dates.py — plan-tidstavle-data.md step 1.5 (second half).

Entity dates (the entity's own life cycle) for the register entries the
Tidstavle touches — the 150 linked persons and 44 linked works — following
docs/data-model/temporal-modelling.md. Mention dates (diary pages) are NOT
here; they stay a join of references.csv and diary.csv.

  persons  birth / death from the register label, only the exact forms
           "(YYYY–YYYY)" and "(død YYYY)"; precision year
  works    publication / reprint from bibliografi (publication_events.csv,
           only where the vid resolves to ONE Reg id by title) and
           publication / premiere / performance from Tidstavle entries that
           link exactly one work and state it with a verb (udkom, premiere,
           opført …). Reviews and translations are other works' events.

Dates of the bibliografi and Tidstavle rows respect the 1875-12-31 limit
(event_bounds.py). Birth/death years come from the label as printed; a death
after 1875 is a fact about the person, not a mapped event, and is kept.

The "Begivenhedsdatoer" button in diaries.html stays off until the model is
reviewed (plan 1.5).

Output: data/normalized/entity_dates.csv
Usage:  python scripts/normalization/build_entity_dates.py
"""

import csv
import re
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "normalization"))

import timeline_linked as tl  # noqa: E402
import event_bounds  # noqa: E402

OUT = REPO_ROOT / "data" / "normalized" / "entity_dates.csv"
PUBLICATIONS = REPO_ROOT / "data" / "normalized_v092" / "publication_events.csv"
FIELDS = ["event_id", "entity_id", "entity_type", "event_type", "date_start",
          "date_end", "precision", "source", "method"]

PERSON_YEARS = re.compile(r"\((\d{4})\s*[–-]\s*(\d{4})\)\s*$")
PERSON_DIED = re.compile(r"\(død (\d{4})\)\s*$")
PRECISION = {"d": "day", "m": "month", "y": "year", "p": "period"}
WORK_VERB = [                       # first match wins; stems, case-insensitive
    ("premiere", re.compile(r"\bpremiere\b", re.I)),
    ("performance", re.compile(r"\bopf[øo]r(t|es|else)\b", re.I)),
    ("publication", re.compile(r"\b(udkom|udkommer|udgivet|udgives|udgav|udkomme)\b", re.I)),
]


def main() -> None:
    entries = tl.load_entries()
    labels = tl.load_labels()
    rows = []

    def add(**kw):
        rows.append(dict(kw))

    persons = sorted({p for e in entries for p in e["persons"]})
    for rid in persons:
        label = labels.get(rid, "")
        m = PERSON_YEARS.search(label)
        d = PERSON_DIED.search(label)
        if m:
            for typ, y in (("birth", m.group(1)), ("death", m.group(2))):
                add(entity_id=rid, entity_type="person", event_type=typ,
                    date_start=f"{y}-01-01", date_end=f"{y}-12-31", precision="year",
                    source="register-label", method="label_parse")
        elif d:
            add(entity_id=rid, entity_type="person", event_type="death",
                date_start=f"{d.group(1)}-01-01", date_end=f"{d.group(1)}-12-31",
                precision="year", source="register-label", method="label_parse")

    works = {w for e in entries for w in e["works"]}
    if PUBLICATIONS.exists():
        with PUBLICATIONS.open(encoding="utf-8", newline="") as f:
            for r in csv.DictReader(f):
                typ = {"publication_first": "publication",
                       "publication_edition": "reprint"}.get(r["event_type"])
                if not typ or r["reg_match"] != "unique" or r["reg_id"] not in works:
                    continue
                add(entity_id=r["reg_id"], entity_type="work", event_type=typ,
                    date_start=r["date_start"], date_end=r["date_end"],
                    precision=PRECISION[r["precision"]],
                    source=f"bibliografi:{r['event_id']}", method="bibliografi_titelmatch")
    for e in entries:
        if len(e["works"]) != 1:
            continue
        typ = next((t for t, rx in WORK_VERB if rx.search(e["text"])), None)
        if not typ:
            continue
        status, end = event_bounds.check(e["a"], e["b"])
        if status == "out":
            continue
        add(entity_id=next(iter(e["works"])), entity_type="work", event_type=typ,
            date_start=e["a"], date_end=end,
            precision=PRECISION[e["pa"]] if e["a"] == end else "period",
            source=f"tidstavle:{e['id']}", method="tidstavle_verbum")

    rows.sort(key=lambda r: (r["entity_type"], r["entity_id"], r["date_start"], r["event_type"], r["source"]))
    for i, r in enumerate(rows, 1):
        r["event_id"] = f"ED{i:05d}"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)

    print(f"wrote {OUT.relative_to(REPO_ROOT)}: {len(rows)} rows")
    print("  by type:", dict(Counter((r["entity_type"], r["event_type"]) for r in rows)))
    have = {r["entity_id"] for r in rows}
    print(f"  persons with a date: {len(have & set(persons))} of {len(persons)}; "
          f"works with a date: {len(have & works)} of {len(works)}")
    print("  deaths after the 1875 limit (kept, see docstring):",
          sum(1 for r in rows if r["event_type"] == "death" and r["date_start"] > event_bounds.CUTOFF))


if __name__ == "__main__":
    main()
