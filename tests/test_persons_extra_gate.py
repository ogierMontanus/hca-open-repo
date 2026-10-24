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

  2. Every entry the editorial gender review (person_gender.csv) classifies
     as »Andet« is handled as a group: that category, no genderConf, and no
     trade branch. 29_entityType is keyed on label and misses many of them.

  3. The population does not collapse. A gate that accidentally matches
     far too much would silently empty the facets — which looks exactly
     like a working build.

Skips (does not fail) when the artifact has not been built, matching how
the pipeline treats every other optional build output.
"""
import csv
import json
import pathlib
import re

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "mockup" / "data" / "persons-extra.js"
ENTITY_TYPES = ROOT / "data" / "curated" / "person_entity_types.tsv"
GENDER_CSV = ROOT / "data" / "normalized" / "person_gender.csv"

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
UNCATEGORISED_ROLE = "Endnu ukategoriseret/Uden for kategori/Intet kendt lønnet erhverv"


def test_known_collectives_are_shown_as_other(persons):
    """Families and firms are listed, but never with a personal gender."""
    by_label = {p.get("label", ""): p for p in persons.values()}
    for name in ("Collin, Familien", "Barberini, Familien"):
        assert name in by_label, f"{name!r} is missing from persons-extra.js"
        assert by_label[name].get("gender") == OTHER_GENDER, (
            f"{name!r} has gender {by_label[name].get('gender')!r}, "
            f"expected {OTHER_GENDER!r}"
        )


def test_review_groups_are_handled_as_groups(persons):
    """Groups per person_gender.csv get the same treatment as 29_entityType
    collectives, whatever their label's entityType says."""
    if not GENDER_CSV.exists():
        pytest.skip(f"{GENDER_CSV.relative_to(ROOT)} absent")
    with GENDER_CSV.open(encoding="utf-8-sig", newline="") as f:
        groups = [r["entity_id"] for r in csv.DictReader(f)
                  if r["koen"].strip() == OTHER_GENDER]
    assert groups, "person_gender.csv has no »Andet« rows to check against"
    # Entries whose bare label is also a cross-reference are gated out first.
    present = [i for i in groups if i in persons]
    assert len(present) >= len(groups) * 0.9, (
        f"only {len(present)} of {len(groups)} review groups are in persons-extra.js"
    )
    wrong = [i for i in present
             if persons[i].get("gender") != OTHER_GENDER
             or persons[i].get("genderConf") is not None
             or persons[i].get("roles") != [UNCATEGORISED_ROLE]]
    assert not wrong, (
        f"{len(wrong)} review group(s) not handled as groups: "
        f"{[persons[i].get('label') for i in wrong[:5]]}"
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
