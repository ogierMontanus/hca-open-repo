"""Read-only lookups into the normalised register CSVs, shared by the server
(snapshot at submission time) and the exporter (match keys, guards).

Everything here is derived from data/normalized/*.csv — the same files the
rest of the pipeline reads. Nothing is cached on disk.
"""
from __future__ import annotations

import csv
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
NORM = ROOT / "data" / "normalized"

_ROMAN = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6, "VII": 7, "VIII": 8, "IX": 9, "X": 10, "XI": 11}

_TRAILING_PAREN = re.compile(r"\s*\([^)]*\)\s*$")
_SEE_TAIL = re.compile(r",?\s*\bse\s*:.*$", re.I)


def surname_of(label: str) -> str:
    s = _SEE_TAIL.sub("", label or "")
    s = _TRAILING_PAREN.sub("", s).strip()
    return s.split(",")[0].strip()


def _page_key(vp):
    vol, page = vp
    try:
        return (_ROMAN.get(vol, 99), int(page))
    except ValueError:
        return (_ROMAN.get(vol, 99), 10**6)


class Register:
    """Lazy {person id → label, description, refs signature}."""

    def __init__(self, norm_dir: Path = NORM):
        self.norm = Path(norm_dir)
        self._persons = None
        self._refs = None

    def _load(self):
        if self._persons is not None:
            return
        self._persons, refs = {}, defaultdict(set)
        ents = self.norm / "entities.csv"
        if ents.exists():
            with open(ents, encoding="utf-8", newline="") as f:
                for r in csv.DictReader(f):
                    if r["entity_type"] == "person":
                        self._persons[r["entity_id"]] = (r["label"].strip(), (r.get("description") or "").strip())
        rf = self.norm / "references.csv"
        if rf.exists():
            with open(rf, encoding="utf-8", newline="") as f:
                for r in csv.DictReader(f):
                    if r["entity_id"] in self._persons and r["vol"] and r["page"]:
                        refs[r["entity_id"]].add((r["vol"], r["page"]))
        self._refs = refs

    def known(self) -> bool:
        self._load()
        return bool(self._persons)

    def person(self, pid: str):
        self._load()
        return self._persons.get(pid)

    def refs_signature(self, pid: str) -> str:
        """`II:422;II:424;IV:127` — vol:page of every register reference, in
        book order. Stable under renumbering, which entity ids and positional
        entry ids are not (docs/data-model/person-master-files.md)."""
        self._load()
        return ";".join(f"{v}:{p}" for v, p in sorted(self._refs.get(pid, ()), key=_page_key))

    def snapshot(self, pid: str) -> dict:
        """The register as it stood when a contribution was made — kept with
        the submission as the guard the emendation model calls `original`."""
        got = self.person(pid)
        if not got:
            return {}
        label, desc = got
        return {"label": label, "description": desc, "surname": surname_of(label),
                "refs_signature": self.refs_signature(pid)}
