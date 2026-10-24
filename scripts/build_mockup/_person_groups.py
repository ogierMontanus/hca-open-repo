"""Which person-register entries are groups, not individuals.

Single source for every pipeline that builds the person index (role chain,
persons-extra.js). The editorial gender review (data/normalized/person_gender.csv)
gives entries that are firms, families, couples, groups and animals the
category »Andet (især firmaer/slægter/øvrige grupper)« — decided per entry.
That column is the authority on which entries are groups; the label-keyed
29_entityType classification (data/curated/person_entity_types.tsv) is a
second, coarser source that build_persons_extra.py unions with it.

Degrades to an empty set when person_gender.csv is absent, like the other
optional enrichments.
"""
import csv
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
GENDER = os.path.join(ROOT, "data", "normalized", "person_gender.csv")

OTHER_GENDER = "Andet (især firmaer/slægter/øvrige grupper)"


def load_group_ids() -> set:
    """entity_ids that person_gender.csv classifies as OTHER_GENDER."""
    if not os.path.exists(GENDER):
        return set()
    with open(GENDER, encoding="utf-8-sig", newline="") as f:
        return {r["entity_id"] for r in csv.DictReader(f)
                if r["koen"].strip() == OTHER_GENDER}
