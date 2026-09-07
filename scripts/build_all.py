#!/usr/bin/env python3
"""
Run the mockup build pipeline in order.

This repository builds the published site. It does not prepare its own
data: cleaning, preprocessing, segmentation and enrichment live in
HCA-Diary-data-cleaning, which publishes the prepared files this build
reads. See docs/pipeline/README.md for the interface.

  raw sources -> HCA-Diary-data-cleaning -> data/normalized/ + data/parsed/
                                            + data/curated/
                                         -> this build -> mockup/ + web/

Refresh the inputs before building, from a checkout of the cleaning repo:

    python scripts/run_pipeline.py
    python scripts/publish.py --into ../hca-open-repo

Usage (from repo root):
    python scripts/build_all.py                  # full build
    python scripts/build_all.py --skip-pages     # skip the 4,500-file diary HTML stage
    python scripts/build_all.py --only 4a        # only run that one stage (by id)
    python scripts/build_all.py --check-inputs   # report missing inputs and exit

Exit code is non-zero on the first failing stage, except the stages marked
optional below, which mirror CI's continue-on-error on the same steps:

  4f  nation index / umbrellas

Every consumer degrades gracefully when an optional prepared input is
absent, so a build still produces a complete mockup from whatever the
cleaning repo last published — it just leaves that facet empty.
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

# (id, label, path-relative-to-repo-root, optional?)
STAGES = [
    ("2",  "prepared CSVs -> web JSON",      "scripts/build_web/build_web_data.py",       False),
    ("3a", "diary pages (~4,500 HTML)",      "scripts/build_mockup/build_diary_pages.py", False),
    ("3b", "diary index + reverse-index",    "scripts/build_mockup/build_diary_index.py", False),
    ("4a", "works-extra.js",                 "scripts/build_mockup/build_works_extra.py", False),
    ("4b", "persons-extra.js",               "scripts/build_mockup/build_persons_extra.py", False),
    ("4c", "places-extra.js",                "scripts/build_mockup/build_places_extra.py", False),
    ("4d", "search-index.js (typeahead)",    "scripts/build_mockup/build_search_index.py", False),
    ("4e", "cooccurrence.js (reciprocal)",   "scripts/build_mockup/build_cooccurrence.py", False),
    ("4f", "nation-index.js (nation mashup)", "scripts/build_mockup/build_nation_index.py", True),
]

# Not a stage: scripts/build_mockup/build_timeline_index.py builds
# mockup/data/timeline-index.js from the prepared
# data/normalized_v092/timeline.csv, but has never been wired into this
# pipeline or into CI, so the deployed site has never carried it. Run it by
# hand; wiring it in is a change to what gets published, not part of the
# repository split.

# Prepared inputs, as published by HCA-Diary-data-cleaning. Required ones
# have no graceful degradation: the build cannot run without them.
REQUIRED_INPUTS = [
    "data/normalized/entities.csv",
    "data/normalized/diary.csv",
    "data/normalized/references.csv",
]
OPTIONAL_INPUTS = [
    "data/normalized/rejser.tsv",
    "data/normalized/rejser_journeys.tsv",
    "data/normalized/sv14_places_reconciled.csv",
    "data/normalized/work_languages.csv",
    "data/normalized/person_ethnic_descriptors.csv",
    "data/normalized/person_gender.csv",
    "data/normalized/person_role.csv",
    "data/normalized/kb_diary_links.csv",
    "data/normalized/steder_verified_categories.csv",
    "data/normalized_v092/timeline.csv",
    "data/parsed/music_register_parsed.tsv",
    "data/parsed/non_fiction_parsed.tsv",
    "data/parsed/novels_plays_tales_parsed.tsv",
    "data/curated/works_wikidata.csv",
    "data/curated/persons_wikidata.csv",
    "data/curated/person_entity_types.tsv",
    "data/curated/breve_person_crosswalk.csv",
    "data/curated/ethnic_adjectives_da.csv",
    "data/curated/nation_place_labels_da.csv",
    "data/curated/nation_umbrellas_da.csv",
    "data/curated/steder_country_to_nation_da.csv",
]

REFRESH_HINT = (
    "Refresh them from a checkout of HCA-Diary-data-cleaning:\n"
    "    python scripts/run_pipeline.py\n"
    "    python scripts/publish.py --into <this repo>"
)


def check_inputs(verbose=True):
    """Report on the prepared inputs. Returns the list of missing required ones."""
    missing = [p for p in REQUIRED_INPUTS if not (REPO_ROOT / p).exists()]
    absent_optional = [p for p in OPTIONAL_INPUTS if not (REPO_ROOT / p).exists()]
    if verbose:
        for p in missing:
            print(f"  [x] missing (required)  {p}")
        for p in absent_optional:
            print(f"  [!] absent (optional)   {p}  — the facet it feeds stays empty")
        if not missing and not absent_optional:
            print("  all prepared inputs present")
    return missing


def run(stage_id, label, script, optional):
    print(f"\n=== Stage {stage_id} - {label} " + "=" * max(0, 50 - len(label)))
    t0 = time.time()
    rc = subprocess.call([sys.executable, str(REPO_ROOT / script)], cwd=REPO_ROOT)
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
    ap.add_argument("--only", metavar="ID",
                    help="run only the stage with this id (e.g. 4a)")
    ap.add_argument("--skip-pages", action="store_true",
                    help="skip Stage 3a (the slow 4,500-file diary HTML generator)")
    ap.add_argument("--check-inputs", action="store_true",
                    help="report on the prepared inputs and exit")
    args = ap.parse_args()

    if args.check_inputs:
        if check_inputs():
            print("\n" + REFRESH_HINT)
            sys.exit(1)
        return

    missing = check_inputs(verbose=False)
    if missing:
        sys.exit("Missing required prepared input(s):\n  "
                 + "\n  ".join(missing) + "\n\n" + REFRESH_HINT)

    if args.only:
        stages = [s for s in STAGES if s[0] == args.only]
        if not stages:
            sys.exit(f"unknown stage id: {args.only}  "
                     f"(known: {', '.join(s[0] for s in STAGES)})")
    elif args.skip_pages:
        stages = [s for s in STAGES if s[0] != "3a"]
    else:
        stages = STAGES

    t0 = time.time()
    for stage in stages:
        if not run(*stage):
            sys.exit(1)
    print(f"\nAll done in {time.time() - t0:.1f}s.")


if __name__ == "__main__":
    main()
