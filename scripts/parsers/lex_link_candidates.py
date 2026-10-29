#!/usr/bin/env python3
"""
lex_link_candidates.py
----------------------
Turns the raw answers of a run of scripts/parsers/lex_chatbot_query.js
(https://spoerg.lex.dk/ — Lex's own AI chatbot) into PROPOSED lex.dk links for
register persons. It is a proposal tool, not an auto-writer: it never edits
entity data, and nothing it writes is promoted to the site without review
(same rule as wikidata_lookup.py and CLAUDE.md's "Faktakontrol").

Why verification is needed
  The chatbot is an AI ("AI kan lave fejl", its own disclaimer). Asked only for
  a "link" it INVENTS slugs (J.P.E.Hartmann, Niels_W.Gade; the real ones are
  J.P.E._Hartmann and Niels_W._Gade). Asked a plain question it cites real
  articles as source cards — but a card can belong to a neighbouring article
  and an article that merely MENTIONS the person is a source too. So:

  1. Only hrefs that occur as source cards are considered (never URLs found
     only in the free text of the answer).
  2. Identity is decided from the article URL slug: every name token of the
     query ("Niels W. Gade") must be in the slug (a full token may match as
     its initial: H.C._Ørsted).
  3. Each surviving URL is fetched ONCE (a normal page request, 1 per second,
     identifying User-Agent) and the page's own title / lead is checked for the
     register's birth AND death year. Only title, years found and HTTP status
     are stored — no article text.

  verdict: confirmed — HTTP 200 and both register years found in the lead
           likely    — HTTP 200, name matches, years not both found (check by hand)
           mismatch  — HTTP 200 but the years contradict (a namesake) — kept for audit
           dead      — HTTP error

Priority of works (the brief: Dansk Biografisk Leksikon first, then other
detailed works): DBL > Dansk Kvindebiografisk Leksikon > Weilbach > Den Store
Danske > Danmarkshistorien > other lex.dk.

The raw answers quote lex.dk article text and are deliberately NOT committed.

Usage (from repo root):
  python scripts/parsers/lex_link_candidates.py RAW.jsonl [--queries lex_queries.json]
         [--sample data/curated/lex/persons_sample100.csv] [--no-fetch]
"""

import argparse
import csv
import json
import re
import sys
import time
import unicodedata
import urllib.request
from datetime import date
from html import unescape
from pathlib import Path
from urllib.parse import unquote, urlparse

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "data" / "curated" / "lex" / "persons_lex_links.csv"
UA = "hca-open-repo-link-check/1.0 (+https://github.com/ogierMontanus/hca-open-repo; one request per candidate)"

WORKS = [  # (host fragment, key, label, priority)
    ("kvindebiografiskleksikon.lex.dk", "dkbl", "Dansk Kvindebiografisk Leksikon", 2),
    ("biografiskleksikon.lex.dk", "dbl", "Dansk Biografisk Leksikon", 1),
    ("weilbach", "weilbach", "Weilbachs Kunstnerleksikon", 3),
    ("denstoredanske.lex.dk", "dsd", "Den Store Danske", 4),
    ("danmarkshistorien.lex.dk", "dh", "Danmarkshistorien", 5),
    ("teaterleksikon", "teater", "Gyldendals Teaterleksikon", 5),
]


def fold(s: str) -> str:
    s = (s.replace("ä", "æ").replace("ö", "ø").replace("ü", "y")
          .replace("Ä", "Æ").replace("Ö", "Ø").replace("Ü", "Y"))
    s = unicodedata.normalize("NFD", s.lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def work_of(url: str):
    host = urlparse(url).netloc
    for frag, key, label, prio in WORKS:
        if frag in host:
            return key, label, prio
    if host in ("lex.dk", "www.lex.dk"):
        return "lex", "lex.dk (øvrige)", 6
    return None


def life_years(label: str):
    m = re.search(r"\((?:ca\.\s*)?(\d{4})\s*[–-]\s*(\d{4})\)", label)
    return (m.group(1), m.group(2)) if m else (None, None)


PARTICLES = {"von", "van", "af", "de", "der", "den", "du", "la", "le", "zu", "i", "og"}


def name_tokens(query_name: str):
    """'Niels W. Gade (1817–1890), komponist' → ['niels', 'w', 'gade']."""
    head = re.split(r"[(,]", query_name)[0]
    toks = [t for t in re.split(r"[\s.\-]+", fold(head)) if t and t not in PARTICLES]
    return toks


def slug_matches(url: str, toks) -> bool:
    slug = fold(unquote(urlparse(url).path.strip("/")))
    st = [t for t in re.split(r"[^a-zæøå0-9]+", slug) if t]
    singles = {t for t in st if len(t) == 1}
    if not toks:
        return False
    for t in toks:
        if t in st:
            continue
        if len(t) >= 3 and t[0] in singles:        # Hans Christian → H.C.
            continue
        if len(t) >= 3 and any(len(x) >= 2 and t.startswith(x) for x in st):   # Fr. → Frederik
            continue
        if len(t) == 1 and any(x.startswith(t) for x in st):                    # C. E. → Carl Emil
            continue
        return False
    return True


def fetch_check(url: str, born: str, died: str):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "da"})
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            status = r.status
            html = r.read(400_000).decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return {"status": e.code, "title": "", "years": "", "verdict": "dead"}
    except Exception as e:  # noqa: BLE001
        return {"status": 0, "title": str(e)[:60], "years": "", "verdict": "dead"}
    m = re.search(r"<title>(.*?)</title>", html, re.S | re.I)
    title = unescape(re.sub(r"\s+", " ", m.group(1))).strip()[:90] if m else ""
    body = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.S | re.I)
    text = unescape(re.sub(r"<[^>]+>", " ", body))
    text = re.sub(r"\s+", " ", text)
    # Lead = the title plus the first 1500 characters of the article body (after the first
    # <h1>), so a namesake whose article merely MENTIONS the years elsewhere is not confirmed.
    h1 = re.search(r"<h1[^>]*>", body, re.I)
    lead_text = re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", body[h1.start():]))) if h1 else text
    lead = title + " " + lead_text[:1500]
    found = sorted(set(re.findall(r"\b(1[4-9]\d\d)\b", lead)))
    ok_b = bool(born and born in lead)
    ok_d = bool(died and died in lead)
    verdict = "confirmed" if (ok_b and ok_d) else "likely"
    if (born and died) and found and not ok_b and not ok_d and len(found) >= 2:
        verdict = "mismatch"
    return {"status": status, "title": title, "years": f"{'F' if ok_b else '-'}{'D' if ok_d else '-'}", "verdict": verdict}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("raw")
    ap.add_argument("--queries", required=True, help="the QUERIES.json given to lex_chatbot_query.js")
    ap.add_argument("--sample", default=str(REPO / "data/curated/lex/persons_sample100.csv"))
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--no-fetch", action="store_true")
    ap.add_argument("--cache", help="JSON file caching page checks, so re-runs make no repeat requests")
    args = ap.parse_args()

    sample = {r["rid"]: r for r in csv.DictReader(open(args.sample, encoding="utf-8"))}
    qname = {q["rid"]: q["name"] for q in json.load(open(args.queries, encoding="utf-8"))}
    today = date.today().isoformat()
    rows, persons = [], 0
    cache = json.load(open(args.cache, encoding="utf-8")) if args.cache and Path(args.cache).exists() else {}
    for line in open(args.raw, encoding="utf-8"):
        rec = json.loads(line)
        s = sample.get(rec["rid"])
        if not s or not rec.get("ok"):      # skip persons whose query errored
            continue
        persons += 1
        born, died = life_years(s["label"])
        toks = name_tokens(qname.get(rec["rid"], s["label"]))
        seen = set()
        for l in rec.get("links", []):
            url = unquote(l["href"])
            w = work_of(url)
            if not w or url in seen or not slug_matches(url, toks):
                continue
            seen.add(url)
            if args.no_fetch:
                chk = {"status": "", "title": re.sub(r"\s+", " ", l.get("card", ""))[:60], "years": "", "verdict": "unchecked"}
            else:
                if l["href"] not in cache:
                    time.sleep(1.0)
                    cache[l["href"]] = fetch_check(l["href"], born, died)
                chk = cache[l["href"]]
            rows.append({"rid": rec["rid"], "label": s["label"], "work": w[0], "work_label": w[1],
                         "priority": w[2], "url": url, "page_title": chk["title"], "http": chk["status"],
                         "years_found": chk["years"], "verdict": chk["verdict"], "queried_on": today})

    if args.cache:
        json.dump(cache, open(args.cache, "w", encoding="utf-8"), ensure_ascii=False)
    order = {"confirmed": 0, "likely": 1, "unchecked": 1, "mismatch": 2, "dead": 3}
    rows.sort(key=lambda r: (r["rid"], order[r["verdict"]], r["priority"]))
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    cols = ["rid", "label", "work", "work_label", "priority", "url", "page_title", "http",
            "years_found", "verdict", "queried_on"]
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    conf = {r["rid"] for r in rows if r["verdict"] == "confirmed"}
    dbl = {r["rid"] for r in rows if r["verdict"] == "confirmed" and r["work"] == "dbl"}
    print(f"wrote {args.out}: {len(rows)} candidate links for {persons} persons; "
          f"confirmed for {len(conf)} persons, confirmed DBL for {len(dbl)}")


if __name__ == "__main__":
    sys.exit(main())
