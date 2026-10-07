"""Shared scope for the diary pages the mockup shows.

Only diary pages with transcribed text (rows in data/normalized/diary.csv,
vols I-X) are shown. references.csv also points at pages that exist only as
register references -- vol XI and pages beyond the diary text in I-X -- and
those are left out everywhere. They are listed in docs/todo-diary-pages.md.

Rows with no vol/page at all (the register's "se:" cross-reference rows) are
not page references and are kept untouched.

Usage in a build script:

    import _diary_scope
    with _diary_scope.open_refs(REFS) as f:
        for row in csv.DictReader(f): ...
"""
import csv
import io
from pathlib import Path

_NORM = Path(__file__).resolve().parents[2] / "data" / "normalized"
DIARY_CSV = _NORM / "diary.csv"
REFS_CSV = _NORM / "references.csv"


def text_pages() -> set:
    """{(vol, page)} for every diary page that has transcribed text."""
    with DIARY_CSV.open(newline="", encoding="utf-8") as f:
        return {(r["vol"], r["page"]) for r in csv.DictReader(f)}


def _keep(row, pages) -> bool:
    vol, page = row.get("vol") or "", row.get("page") or ""
    return (not vol and not page) or (vol, page) in pages


def untranscribed_refs() -> list:
    """references.csv rows whose page has no transcribed text."""
    pages = text_pages()
    with REFS_CSV.open(newline="", encoding="utf-8") as f:
        return [r for r in csv.DictReader(f) if not _keep(r, pages)]


def open_refs(path=None):
    """Text-mode file object over references.csv, minus untranscribed pages."""
    path = Path(path) if path else REFS_CSV
    pages = text_pages()
    out = io.StringIO(newline="")
    with path.open(newline="", encoding="utf-8") as f:
        rdr = csv.DictReader(f)
        w = csv.DictWriter(out, fieldnames=rdr.fieldnames, lineterminator="\n")
        w.writeheader()
        for r in rdr:
            if _keep(r, pages):
                w.writerow(r)
    out.seek(0)
    return out
