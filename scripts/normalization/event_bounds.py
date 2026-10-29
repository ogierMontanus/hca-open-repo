"""event_bounds.py — the hard upper date limit for all event mapping.

Decision 2026-10-28: nothing dated after 31 Dec 1875 is mapped as an event
(timeline crosswalk, publication events, and anything built on them).
Andersen died 4 Aug 1875; later first printings (posthumous letters,
modern editions, research literature in `bibliografi`) are out of scope.

Rule for a period [start, end] (ISO YYYY-MM-DD, inclusive):
  start > CUTOFF            -> "out"      (dropped; callers count it)
  start <= CUTOFF < end     -> "clamped"  (kept; end cut to CUTOFF)
  otherwise                 -> "in"

Import:
  sys.path.insert(0, "<repo>/scripts/normalization"); import event_bounds
"""

CUTOFF = "1875-12-31"


def check(start: str, end: str | None = None) -> tuple[str, str]:
    """Return (status, end) with status in {"in", "clamped", "out"}."""
    end = end or start
    if start > CUTOFF:
        return "out", end
    if end > CUTOFF:
        return "clamped", CUTOFF
    return "in", end
