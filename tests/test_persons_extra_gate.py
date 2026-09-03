"""
Regression guard for mockup/data/persons-extra.js.

The file itself is a generated build artifact and stays out of git (see
.gitignore — works-extra.js, places-extra.js, cooccurrence.js and the
rest are ignored on the same grounds: they are regenerated in seconds and
every consumer degrades gracefully without them). That means there is no
diff between builds to inspect, so the two things worth protecting are
asserted here instead:

  1. Non-individuals stay OUT. `Collin, Familien`, the bankier firm
     `Behrens` and the register's one dog are proper names, not people;
     giving them a gender or a nationality in the person facets is a
     category error. build_persons_extra.py gates them on
     29_entityType from data/curated/person_entity_types.tsv.

  2. The population does not collapse. A gate that accidentally matches
     far too much would silently empty the facets — which looks exactly
     like a working build.

Skips (does not fail) when the artifact has not been built, matching how
the pipeline treats every other optional build output.
"""
import json
import pathlib
import re

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "mockup" / "data" / "persons-extra.js"
ENTITY_TYPES = ROOT / "data" / "curated" / "person_entity_types.tsv"

# Measured at 10,146 on 2026-09-03. A wide band: the register itself grows
# as the parsing is cleaned up, so this guards against collapse, not drift.
MIN_PERSONS = 9_000
MAX_PERSONS = 12_000


@pytest.fixture(scope="module")
def persons():
    if not ARTIFACT.exists():
        pytest.skip(f"{ARTIFACT.relative_to(ROOT)} not built — "
                    "run scripts/build_mockup/build_persons_extra.py")
    text = ARTIFACT.read_text(encoding="utf-8")
    m = re.search(r"^const PERSONS_EXTRA = (\{.*?\});\s*$", text,
                  re.MULTILINE | re.DOTALL)
    assert m, "PERSONS_EXTRA object not found — did the generator's output shape change?"
    return json.loads(m.group(1))


def test_population_is_plausible(persons):
    assert MIN_PERSONS <= len(persons) <= MAX_PERSONS, (
        f"{len(persons):,} persons in persons-extra.js is outside the expected "
        f"range {MIN_PERSONS:,}-{MAX_PERSONS:,}. Far below means the entityType "
        "gate is over-matching and emptying the facets; far above means it "
        "stopped filtering."
    )


def test_known_non_individuals_are_gated(persons):
    """Families and firms must not carry person facets."""
    labels = {p.get("label", "") for p in persons.values()}
    for name in ("Collin, Familien", "Behrens", "Barberini, Familien"):
        assert name not in labels, (
            f"{name!r} is in persons-extra.js but is not an individual. "
            "The 29_entityType gate in build_persons_extra.py is not filtering "
            "it — see docs/data-model/person-master-files.md."
        )


def test_gate_data_is_present_and_used(persons):
    """The gate degrades silently to a no-op when its data file is missing,
    so assert the data is actually there AND that it bit."""
    if not ENTITY_TYPES.exists():
        pytest.skip(f"{ENTITY_TYPES.relative_to(ROOT)} absent — gate cannot run")

    gated_labels = set()
    with ENTITY_TYPES.open(encoding="utf-8") as f:
        header = f.readline().rstrip("\n").split("\t")
        title_i = header.index("RegistryTitle")
        for line in f:
            cells = line.rstrip("\n").split("\t")
            if len(cells) > title_i:
                gated_labels.add(cells[title_i])

    assert gated_labels, "person_entity_types.tsv has no rows to gate on"

    present = {p.get("label", "") for p in persons.values()} & gated_labels
    assert not present, (
        f"{len(present)} non-individual(s) reached persons-extra.js: "
        f"{sorted(present)[:5]}"
    )
