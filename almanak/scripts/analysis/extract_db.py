#!/usr/bin/env python3
"""
extract_db.py — undersøgelsesværktøj: træk tabellen `almanak` ud af
MySQL-dumpet hca_db.sql (phpMyAdmin 5.1.2, juni 2023) til CSV.

Tabellen har tre kolonner — `Dato` varchar(20) PRIMARY KEY, `Tekst` text,
`Timestamp` — og ingen fremmednøgler. Én række = én dag.

Genbruger SQL-parseren fra scripts/migration/migrate_tidstavle_sql.py
(parse_table), der allerede håndterer semikolon og escapes inde i
strengværdier. Dumpet er erklæret latin1, men indholdet er UTF-8 (samme
iagttagelse som i migrate_tidstavle_sql.py).

Output (gitignoreret — fuld tekst, se almanak/README.md om rettigheder):
  almanak/data/extracted/almanak_db.csv          Dato, Tekst, Timestamp
  almanak/data/extracted/almanak_db.manifest.json sha256 af dumpet + tællinger

Brug (PowerShell, fra repo-roden):
  python almanak/scripts/analysis/extract_db.py
  python almanak/scripts/analysis/extract_db.py --sql D:\\dumps\\hca_db.sql
"""

import argparse
import collections
import csv
import datetime
import hashlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "migration"))
from migrate_tidstavle_sql import parse_table  # noqa: E402

DEFAULT_SQL = REPO_ROOT / "raw" / "hca_db.sql"
DEFAULT_OUT = REPO_ROOT / "almanak" / "data" / "extracted" / "almanak_db.csv"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--sql", type=Path, default=DEFAULT_SQL)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    if not args.sql.exists():
        sys.exit(f"Finder ikke {args.sql} (hca_db.sql er gitignoreret; angiv --sql)")

    rows = parse_table(args.sql.read_text(encoding="utf-8"), "almanak")
    bad_width = [r for r in rows if len(r) != 3]
    if bad_width:
        sys.exit(f"{len(bad_width)} rækker har ikke 3 felter — parseren skal efterses")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Dato", "Tekst", "Timestamp"])
        w.writerows(rows)

    invalid = []
    for d, _, _ in rows:
        try:
            datetime.date.fromisoformat(d)
        except ValueError:
            invalid.append(d)
    manifest = {
        "source": str(args.sql),
        "source_sha256": sha256(args.sql),
        "table": "almanak",
        "rows": len(rows),
        "invalid_dates": invalid,
        "empty_text": [d for d, t, _ in rows if not t.strip()],
        "rows_per_year": dict(sorted(collections.Counter(d[:4] for d, _, _ in rows).items())),
        "timestamps_by_day": dict(collections.Counter(ts[:10] for _, _, ts in rows).most_common(10)),
        "extracted_at": datetime.datetime.now().isoformat(timespec="seconds"),
    }
    args.out.with_suffix(".manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(rows)} rækker -> {args.out}")
    print(f"ugyldige datoer: {invalid}; tomme tekster: {manifest['empty_text']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
