"""sql_inventory.py — list every table in the hca_db.sql MySQL dump with
columns and row count (plan-tidstavle-data.md step 1.0).

Usage:
  python scripts/qa/sql_inventory.py [--sql PATH] [--json OUT.json]

Reuses the VALUES parser from scripts/migration/migrate_tidstavle_sql.py.
Prints a markdown table (table · columns · rows). With --json, also writes
columns and the first 3 rows per table, for manual inspection.
"""

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "migration"))

from migrate_tidstavle_sql import parse_table  # noqa: E402

DEFAULT_SQL = REPO_ROOT / "raw" / "hca_db.sql"

_CREATE_RE = re.compile(r"CREATE TABLE `([^`]+)` \((.*?)\n\) ENGINE", re.S)
_COL_RE = re.compile(r"^\s*`([^`]+)`\s+(\S+)", re.M)


def table_columns(sql_text: str) -> dict[str, list[tuple[str, str]]]:
    tables: dict[str, list[tuple[str, str]]] = {}
    for m in _CREATE_RE.finditer(sql_text):
        tables[m.group(1)] = _COL_RE.findall(m.group(2))
    return tables


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sql", type=Path, default=DEFAULT_SQL)
    ap.add_argument("--json", type=Path)
    args = ap.parse_args()

    sql_text = args.sql.read_text(encoding="utf-8", errors="replace")
    tables = table_columns(sql_text)
    out = {}
    print("| tabel | kolonner | rækker |")
    print("|---|---|---:|")
    for name, cols in tables.items():
        rows = parse_table(sql_text, name)
        out[name] = {"columns": cols, "rows": len(rows), "sample": rows[:3]}
        print(f"| {name} | {', '.join(c for c, _ in cols)} | {len(rows)} |")
    if args.json:
        args.json.write_text(json.dumps(out, ensure_ascii=False, indent=1),
                             encoding="utf-8")


if __name__ == "__main__":
    main()
