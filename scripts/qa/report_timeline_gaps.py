"""report_timeline_gaps.py — plan-tidstavle-data.md step 1.5.

Days on which the printed Tidstavle places Andersen (an `ophold` or `rejse`
entry) but the diary has no dated entry, within the diary's own date range
(first to last dated heading, never after 1875-12-31).

Each run of consecutive gap days gets a category that separates a hole in
the SOURCE from a hole in OUR transcription:

  i_bind      the day lies inside the date range of one printed volume: the
              volume prints no entry for it (Andersen wrote nothing, or the
              entry is lost) — a gap in the source
  mellem_bind the day lies between two volumes' date ranges — the diary is
              silent between the volumes
  vores_hul   a printed page of volumes I-X without transcribed text. Page
              numbers of diary.csv are checked for gaps; today there are none
              (every page 1..N of every volume has text), so no run gets this
              category. Register references to pages BEYOND the text
              (commentary, vol. XI) are a different matter: see
              scripts/build_mockup/report_untranscribed_pages.py

Writes data/normalized/timeline_gaps.csv (one row per run) and prints the
per-volume summary used in docs/data-model/timeline-gaps.md.

Usage: python scripts/qa/report_timeline_gaps.py
"""

import csv
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "normalization"))

import timeline_linked as tl  # noqa: E402

OUT = REPO_ROOT / "data" / "normalized" / "timeline_gaps.csv"
FIELDS = ["start", "end", "n_days", "category", "volume", "prev_diary_date",
          "next_diary_date", "stay_entries"]
VOL_ORDER = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"]


def missing_pages(diary: tl.Diary) -> dict:
    """Printed pages 1..N of a volume that have no row in diary.csv."""
    out = {}
    for vol, pages in diary.volumes.items():
        have = set(pages)
        out[vol] = [p for p in range(1, max(have) + 1) if p not in have]
    return out


def main() -> None:
    entries = tl.load_entries()
    diary = tl.Diary()
    first, last = diary.dates[0], diary.dates[-1]

    span = {}                                    # volume -> (first, last) dated heading
    for page, ds in diary.page_dates.items():
        lo, hi = span.get(page[0], (min(ds), max(ds)))
        span[page[0]] = (min(lo, min(ds)), max(hi, max(ds)))
    ordered = sorted(span.items(), key=lambda kv: VOL_ORDER.index(kv[0]) if kv[0] in VOL_ORDER else 99)

    stay_by_day = defaultdict(set)
    for e in entries:
        if e["kind"] in ("ophold", "rejse") and e["b"] >= first and e["a"] <= last:
            for d in tl.days(max(e["a"], first), min(e["b"], last)):
                stay_by_day[d].add(e["id"])

    def category(d: str):
        for vol, (lo, hi) in ordered:
            if lo <= d <= hi:
                return "i_bind", vol
        return "mellem_bind", ""

    gap_days = sorted(d for d in stay_by_day if d not in diary.date_pages)
    runs, cur = [], None
    for d in gap_days:
        cat, vol = category(d)
        nxt = tl.date.fromisoformat(cur["end"]).toordinal() + 1 if cur else None
        if cur and tl.date.fromisoformat(d).toordinal() == nxt and (cat, vol) == (cur["category"], cur["volume"]):
            cur["end"], cur["n_days"] = d, cur["n_days"] + 1
            cur["_ids"] |= stay_by_day[d]
        else:
            if cur:
                runs.append(cur)
            cur = dict(start=d, end=d, n_days=1, category=cat, volume=vol, _ids=set(stay_by_day[d]))
    if cur:
        runs.append(cur)

    dates = diary.dates
    for r in runs:
        before = [x for x in dates if x < r["start"]]
        after = [x for x in dates if x > r["end"]]
        r["prev_diary_date"] = before[-1] if before else ""
        r["next_diary_date"] = after[0] if after else ""
        r["stay_entries"] = ";".join(sorted(r.pop("_ids")))

    with OUT.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(runs)

    stay_days = len(stay_by_day)
    gaps = Counter()
    for r in runs:
        gaps[(r["category"], r["volume"])] += r["n_days"]
    print(f"diary range {first} .. {last}; {stay_days:,} days with a stay/travel entry, "
          f"{len(gap_days):,} without a diary entry ({len(gap_days) / stay_days:.0%}); "
          f"{len(runs)} runs -> {OUT.relative_to(REPO_ROOT)}")
    stay_in_vol = Counter()
    for d in stay_by_day:
        stay_in_vol[category(d)[1] or "mellem"] += 1
    print("volume  range                       stay-days  gap-days  share")
    for vol, (lo, hi) in ordered:
        g = gaps[("i_bind", vol)]
        s = stay_in_vol[vol]
        print(f"{vol:6}  {lo} .. {hi}   {s:8}  {g:8}  {g / s if s else 0:.0%}")
    gm = gaps[("mellem_bind", "")]
    print(f"between volumes: {stay_in_vol['mellem']:,} stay-days, {gm:,} gap-days")
    mp = missing_pages(diary)
    print("printed pages without transcribed text, vols I-X:",
          {v: len(p) for v, p in mp.items() if p} or "none")
    longest = sorted(runs, key=lambda r: -r["n_days"])[:5]
    print("longest runs:", [(r["start"], r["end"], r["n_days"], r["category"], r["volume"]) for r in longest])


if __name__ == "__main__":
    main()
