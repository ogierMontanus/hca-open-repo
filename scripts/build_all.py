#!/usr/bin/env python3
"""
Run the full mockup build pipeline in order.

Replaces the seven-line copy-paste from scripts/build_mockup/README.md.
Each stage is invoked as a subprocess using the same Python interpreter
that ran this script, so it works under both `python` (Windows /
PowerShell) and `python3` (Linux/macOS) without changes.

Usage (from repo root):
    python scripts/build_all.py            # run every stage
    python scripts/build_all.py --skip-pages   # skip the 4,500-file diary HTML stage
    python scripts/build_all.py --only 4a   # only run that one stage (by id)

Exit code is non-zero on the first failing stage, except Stage 1b
(rejser geocodes), which is treated as optional — mirrors CI's
continue-on-error on the same step.
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

STAGES = [
    # (id, label, path-relative-to-repo-root, optional?)
    ("1a", "xlsx → normalised CSVs",       "scripts/normalization/hca_xlsx_to_csv.py", False),
    ("1b", "parse Rejser HTM (geocodes)",  "scripts/build_web/parse_rejser_htm.py",     True),
    ("2",  "CSVs → web JSON",              "scripts/build_web/build_web_data.py",       False),
    ("3a", "diary pages (≈4,500 HTML)",    "scripts/build_mockup/build_diary_pages.py", False),
    ("3b", "diary index + reverse-index",  "scripts/build_mockup/build_diary_index.py", False),
    ("4a", "works-extra.js",               "scripts/build_mockup/build_works_extra.py", False),
    ("4b", "persons-extra.js",             "scripts/build_mockup/build_persons_extra.py", False),
    ("4c", "places-extra.js",              "scripts/build_mockup/build_places_extra.py", False),
    ("4d", "search-index.js (typeahead)",  "scripts/build_mockup/build_search_index.py", False),
    ("4e", "cooccurrence.js (reciprocal)", "scripts/build_mockup/build_cooccurrence.py", False),
]


def run(stage_id, label, script, optional):
    print(f"\n=== Stage {stage_id} — {label} " + "=" * max(0, 50 - len(label)))
    t0 = time.time()
    rc = subprocess.call([sys.executable, str(REPO_ROOT / script)], cwd=REPO_ROOT)
    dt = time.time() - t0
    if rc != 0:
        if optional:
            print(f"  ⚠ stage {stage_id} failed (rc={rc}) — continuing (optional)  [{dt:.1f}s]")
            return True
        print(f"  ✗ stage {stage_id} failed (rc={rc})  [{dt:.1f}s]")
        return False
    print(f"  ✓ stage {stage_id} done  [{dt:.1f}s]")
    return True


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--only", metavar="ID", help="run only the stage with this id (e.g. 4a)")
    ap.add_argument("--skip-pages", action="store_true",
                    help="skip Stage 3a (the slow 4,500-file diary HTML generator)")
    args = ap.parse_args()

    stages = STAGES
    if args.only:
        stages = [s for s in STAGES if s[0] == args.only]
        if not stages:
            sys.exit(f"unknown stage id: {args.only}  (known: {', '.join(s[0] for s in STAGES)})")
    elif args.skip_pages:
        stages = [s for s in STAGES if s[0] != "3a"]

    t0 = time.time()
    for stage in stages:
        if not run(*stage):
            sys.exit(1)
    print(f"\nAll done in {time.time() - t0:.1f}s.")


if __name__ == "__main__":
    main()
