"""check_kb_links.py — plan-tidstavle-data.md step 2.3.

Polite link check (one HEAD request per second, GET only if HEAD is refused)
of the distinct Det Kgl. Bibliotek EPUB pages the Tidstavle entries point at.
Writes data/curated/kb_link_status.csv; build_timeline.py leaves out links
whose status is 404 or 410 (dead) and keeps all others, including unreachable
ones (a network problem is not proof of a dead link).

Run rarely — it contacts a third party. Nothing in the site calls KB at runtime.

Usage: python scripts/qa/check_kb_links.py [--delay 1.0] [--limit N]
"""

import argparse
import csv
import sys
import time
import urllib.error
import urllib.request
from collections import Counter
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "build_mockup"))

import build_timeline as bt  # noqa: E402

OUT = REPO_ROOT / "data" / "curated" / "kb_link_status.csv"
FIELDS = ["url", "status", "final_url", "checked_on", "n_entries"]
UA = "hca-open-repo-linkcheck/1.0 (research project, SDU; polite 1 req/s)"


def probe(url: str) -> tuple[str, str]:
    for method in ("HEAD", "GET"):
        req = urllib.request.Request(url, method=method, headers={"User-Agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return str(r.status), r.geturl()
        except urllib.error.HTTPError as e:
            if method == "HEAD" and e.code in (403, 405, 501):
                continue
            return str(e.code), url
        except Exception as e:                      # DNS, timeout, TLS …
            return "error:" + type(e).__name__, url
    return "error", url


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--delay", type=float, default=1.0)
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    n = Counter()
    for r in bt.read_workbook(bt.find_workbook()):
        if r["url"]:
            n[r["url"].split("#")[0]] += 1
    urls = sorted(n)[: args.limit or None]
    rows = []
    for i, u in enumerate(urls, 1):
        status, final = probe(u)
        rows.append(dict(url=u, status=status, final_url=final if final != u else "",
                         checked_on=date.today().isoformat(), n_entries=n[u]))
        print(f"{i:3}/{len(urls)} {status:>6}  {u}", flush=True)
        time.sleep(args.delay)
    with OUT.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    print(dict(Counter(r["status"] for r in rows)), "->", OUT.relative_to(REPO_ROOT))


if __name__ == "__main__":
    main()
