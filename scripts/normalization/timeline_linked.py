"""timeline_linked.py — the printed Tidstavle with its register links, next to
the diary, for the cross-checks of plan-tidstavle-data.md steps 1.4 and 1.5.

  load_entries()   workbook rows + links + kind, nothing after 1875-12-31
  load_diary()     Diary: date -> pages, page -> dates / text
  load_refs()      (vol, page) -> {entity ids}

Entry dict: id, v, a, b (ISO), pa/pb (d|m|y), kind (rejse|ophold|begivenhed), text, pages,
places / persons / works (sets of register ids).
"""

import bisect
import csv
import sys
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "build_mockup"))
sys.path.insert(0, str(REPO_ROOT / "scripts" / "normalization"))

import build_timeline as bt  # noqa: E402
import event_bounds  # noqa: E402

NORM = REPO_ROOT / "data" / "normalized"
KIND_OF = {"p": "places", "s": "persons", "w": "works"}

csv.field_size_limit(10 ** 9)


def load_entries() -> list[dict]:
    mt = bt.Matcher()
    out = []
    for r in bt.read_workbook(bt.find_workbook()):
        status, end = event_bounds.check(r["a"], r["b"])
        if status == "out":
            continue
        segs = mt.link(r["text"], r["v"], int(r["a"][:4]))
        e = dict(id=r["id"], v=r["v"], a=r["a"], b=end, pa=r["pa"], pb=r["pb"], text=r["text"],
                 pages=r["pages"], kind=bt.classify(r["text"], segs),
                 places=set(), persons=set(), works=set())
        for s in segs:
            if isinstance(s, list):
                e[KIND_OF[s[1]]].add(s[2])
        out.append(e)
    return out


def days(a: str, b: str):
    d, end = date.fromisoformat(a), date.fromisoformat(b)
    while d <= end:
        yield d.isoformat()
        d += timedelta(days=1)


class Diary:
    """One row of diary.csv is one dated heading on a printed page."""

    def __init__(self):
        with (NORM / "diary.csv").open(encoding="utf-8-sig", newline="") as f:
            rows = list(csv.DictReader(f))
        self.text: dict[tuple, str] = defaultdict(str)
        self.page_dates: dict[tuple, set] = defaultdict(set)
        self.date_pages: dict[str, set] = defaultdict(set)
        self.volumes: dict[str, list] = defaultdict(list)
        for r in rows:
            key = (r["vol"], r["page"])
            self.text[key] += "\n" + r["text"]
            self.volumes[r["vol"]].append(int(r["page"]) if r["page"].isdigit() else 0)
            d = r["date"]
            if len(d) == 10 and "X" not in d:
                self.page_dates[key].add(d)
                self.date_pages[d].add(key)
        self.dates = sorted(self.date_pages)

    def pages_between(self, a: str, b: str) -> set:
        lo = bisect.bisect_left(self.dates, a)
        hi = bisect.bisect_right(self.dates, b)
        return {p for d in self.dates[lo:hi] for p in self.date_pages[d]}

    def nearest_date(self, d: str, dates: set):
        """(date, signed distance in days) of the date in `dates` closest to d."""
        n = date.fromisoformat(d).toordinal()
        best = min(dates, key=lambda x: abs(date.fromisoformat(x).toordinal() - n))
        return best, date.fromisoformat(best).toordinal() - n


def load_refs(prefix: str) -> dict:
    """(vol, page) -> entity ids starting with prefix ('Reg' or 'LOC')."""
    out = defaultdict(set)
    with (NORM / "references.csv").open(encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            if r["entity_id"].startswith(prefix) and r["vol"]:
                out[(r["vol"], r["page"])].add(r["entity_id"])
    return out


def load_labels() -> dict:
    with (NORM / "entities.csv").open(encoding="utf-8-sig", newline="") as f:
        return {r["entity_id"]: r["label"].replace("\n", " ").strip()
                for r in csv.DictReader(f)}
