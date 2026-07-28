#!/usr/bin/env python3
"""
Run the full mockup build pipeline in order.

The source selection step has been factored out so the rest of the
pipeline doesn't care which release version it is reading:

  Default behaviour: scan data/raw/ for folders named "HCA REPOSITORY V*"
  and pick the highest version number. The chosen folder's content
  decides which ingester runs:

    - A single .xlsx inside  → V0.82-shaped flat workbook
      → scripts/normalization/hca_xlsx_to_csv.py --input <folder>
    - Several .xlsx files inside → V0.92-shaped nine-file release
      → scripts/normalization/hca_v092_to_csv.py
      (the V0.92 ingester knows its own hard-coded folder path; CSVs
       go to data/normalized_v092/, not data/normalized/, so the rest
       of the pipeline keeps reading the V0.82 outputs until works
       ship in V0.9x)

Usage (from repo root):
    python scripts/build_all.py                  # auto-pick highest source
    python scripts/build_all.py --source DIR     # explicit folder
    python scripts/build_all.py --skip-pages     # skip the 4,500-file diary HTML stage
    python scripts/build_all.py --only 4a        # only run that one stage (by id)
    python scripts/build_all.py --list-sources   # show what source folders exist

Exit code is non-zero on the first failing stage, except Stages 1b
(rejser geocodes) and 1c (SV14 place reconciliation), which are treated
as optional — mirrors CI's continue-on-error on the same steps.
"""

import argparse
import re
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = REPO_ROOT / "data" / "raw"

# Stages 2 onwards never care about the source path — they read
# data/normalized/*.csv. Only stage 1a (the ingester) is parameterised
# by source.
STAGES_AFTER_INGEST = [
    # (id, label, path-relative-to-repo-root, optional?)
    ("1b", "parse Rejser HTM (geocodes)",  "scripts/build_web/parse_rejser_htm.py",     True),
    ("1c", "reconcile SV14 places (geocodes)", "scripts/build_mockup/reconcile_sv14_geo.py", True),
    ("2",  "CSVs -> web JSON",             "scripts/build_web/build_web_data.py",       False),
    ("3a", "diary pages (~4,500 HTML)",    "scripts/build_mockup/build_diary_pages.py", False),
    ("3b", "diary index + reverse-index",  "scripts/build_mockup/build_diary_index.py", False),
    ("4a", "works-extra.js",               "scripts/build_mockup/build_works_extra.py", False),
    ("4b", "persons-extra.js",             "scripts/build_mockup/build_persons_extra.py", False),
    ("4c", "places-extra.js",              "scripts/build_mockup/build_places_extra.py", False),
    ("4d", "search-index.js (typeahead)",  "scripts/build_mockup/build_search_index.py", False),
    ("4e", "cooccurrence.js (reciprocal)", "scripts/build_mockup/build_cooccurrence.py", False),
]

V082_INGESTER = "scripts/normalization/hca_xlsx_to_csv.py"
V092_INGESTER = "scripts/normalization/hca_v092_to_csv.py"

VERSION_RE = re.compile(r"V(\d+)\.(\d+)$", re.IGNORECASE)


# ── source discovery ────────────────────────────────────────────────────────

def _version_key(folder: Path):
    """Sort key from 'HCA REPOSITORY V0.92' → (0, 92). Returns (-1, -1)
    when the folder name does not match, so unmatched dirs sort below
    every real release."""
    m = VERSION_RE.search(folder.name)
    if not m:
        return (-1, -1)
    return (int(m.group(1)), int(m.group(2)))


def discover_sources():
    """All 'HCA REPOSITORY V*' folders under data/raw/, highest first."""
    if not RAW_DIR.exists():
        return []
    candidates = [p for p in RAW_DIR.iterdir() if p.is_dir() and VERSION_RE.search(p.name)]
    return sorted(candidates, key=_version_key, reverse=True)


def pick_source(explicit: str | None) -> Path:
    if explicit:
        p = Path(explicit)
        if not p.is_absolute():
            p = REPO_ROOT / p
        if not p.exists():
            sys.exit(f"--source not found: {p}")
        return p
    sources = discover_sources()
    if not sources:
        sys.exit(
            "No 'HCA REPOSITORY V*' folder found under data/raw/. "
            "Add one or pass --source explicitly."
        )
    return sources[0]


def classify_source(folder: Path):
    """Return ('v082', xlsx_path) or ('v092', folder)."""
    xlsxes = sorted(folder.glob("*.xlsx"))
    if not xlsxes:
        sys.exit(f"No .xlsx files in source folder: {folder}")
    if len(xlsxes) == 1:
        return ("v082", xlsxes[0])
    # Heuristic: the V0.92 release has DiaryFactDim alongside DimPer etc.
    return ("v092", folder)


def ingest_stage(source: Path):
    """Return the (id, label, argv, optional) tuple for stage 1a."""
    kind, target = classify_source(source)
    if kind == "v082":
        return (
            "1a", f"xlsx -> normalised CSVs (V0.82 flat: {target.name})",
            [sys.executable, str(REPO_ROOT / V082_INGESTER),
             "--input", str(source)],
            False,
        )
    return (
        "1a", f"xlsx -> normalised CSVs (V0.92 multi-file: {source.name})",
        [sys.executable, str(REPO_ROOT / V092_INGESTER),
         "--source", str(source)],
        False,
    )


# ── pipeline runner ─────────────────────────────────────────────────────────

def run(stage_id, label, argv, optional):
    print(f"\n=== Stage {stage_id} - {label} " + "=" * max(0, 50 - len(label)))
    t0 = time.time()
    rc = subprocess.call(argv, cwd=REPO_ROOT)
    dt = time.time() - t0
    if rc != 0:
        if optional:
            print(f"  [!] stage {stage_id} failed (rc={rc}) - continuing (optional)  [{dt:.1f}s]")
            return True
        print(f"  [x] stage {stage_id} failed (rc={rc})  [{dt:.1f}s]")
        return False
    print(f"  [ok] stage {stage_id} done  [{dt:.1f}s]")
    return True


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--source", metavar="DIR",
                    help="Explicit source folder (overrides version auto-pick)")
    ap.add_argument("--list-sources", action="store_true",
                    help="Print discovered source folders (highest version first) and exit")
    ap.add_argument("--only", metavar="ID",
                    help="run only the stage with this id (e.g. 4a)")
    ap.add_argument("--skip-pages", action="store_true",
                    help="skip Stage 3a (the slow 4,500-file diary HTML generator)")
    args = ap.parse_args()

    if args.list_sources:
        for p in discover_sources():
            kind, target = classify_source(p)
            shape = ("V0.82 flat workbook" if kind == "v082"
                     else "V0.92 multi-file release")
            print(f"  {p.relative_to(REPO_ROOT)}   ({shape})")
        return

    source = pick_source(args.source)
    print(f"Source: {source.relative_to(REPO_ROOT)}")
    ingest = ingest_stage(source)
    all_stages = [ingest] + [
        (i, label, [sys.executable, str(REPO_ROOT / script)], opt)
        for (i, label, script, opt) in STAGES_AFTER_INGEST
    ]

    if args.only:
        stages = [s for s in all_stages if s[0] == args.only]
        if not stages:
            sys.exit(f"unknown stage id: {args.only}  "
                     f"(known: {', '.join(s[0] for s in all_stages)})")
    elif args.skip_pages:
        stages = [s for s in all_stages if s[0] != "3a"]
    else:
        stages = all_stages

    t0 = time.time()
    for stage in stages:
        if not run(*stage):
            sys.exit(1)
    print(f"\nAll done in {time.time() - t0:.1f}s.")


if __name__ == "__main__":
    main()
