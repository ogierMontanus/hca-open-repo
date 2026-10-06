"""
Regression guard for mockup/data/persons-extra.js.

The file itself is a generated build artifact and stays out of git (see
.gitignore — works-extra.js, places-extra.js, cooccurrence.js and the
rest are ignored on the same grounds: they are regenerated in seconds and
every consumer degrades gracefully without them). That means there is no
diff between builds to inspect, so the two things worth protecting are
asserted here instead:

  1. Cross-references stay OUT; families, firms and groups stay IN with
     the gender category »Andet (især firmaer/slægter/øvrige grupper)«.
     `Collin, Familien`, the bankier firm `Behrens` and the register's one
     dog are proper names, not people, so they never get a personal
     gender. build_persons_extra.py reads 29_entityType from
     data/curated/person_entity_types.tsv.

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


OTHER_GENDER = "Andet (især firmaer/slægter/øvrige grupper)"


def test_known_collectives_are_shown_as_other(persons):
    """Families and firms are listed, but never with a personal gender."""
    by_label = {p.get("label", ""): p for p in persons.values()}
    for name in ("Collin, Familien", "Barberini, Familien"):
        assert name in by_label, f"{name!r} is missing from persons-extra.js"
        assert by_label[name].get("gender") == OTHER_GENDER, (
            f"{name!r} has gender {by_label[name].get('gender')!r}, "
            f"expected {OTHER_GENDER!r}"
        )


def test_gate_data_is_present_and_used(persons):
    """The gate degrades silently to a no-op when its data file is missing,
    so assert the data is actually there AND that it bit."""
    if not ENTITY_TYPES.exists():
        pytest.skip(f"{ENTITY_TYPES.relative_to(ROOT)} absent — gate cannot run")

    kinds_by_label = {}
    with ENTITY_TYPES.open(encoding="utf-8") as f:
        header = f.readline().rstrip("\n").split("\t")
        title_i = header.index("RegistryTitle")
        kind_i = header.index("29_entityType")
        for line in f:
            cells = line.rstrip("\n").split("\t")
            if len(cells) > kind_i:
                kinds_by_label.setdefault(cells[title_i], set()).add(cells[kind_i])
    # A label that also names a family etc. (`Horn`) is not gated.
    gated_labels = {label for label, kinds in kinds_by_label.items()
                    if all(k.startswith("crossReference") for k in kinds)}

    assert gated_labels, "person_entity_types.tsv has no cross-references to gate on"

    present = {p.get("label", "") for p in persons.values()} & gated_labels
    assert not present, (
        f"{len(present)} cross-reference(s) reached persons-extra.js: "
        f"{sorted(present)[:5]}"
    )
