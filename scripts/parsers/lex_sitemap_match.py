#!/usr/bin/env python3
"""
lex_sitemap_match.py
--------------------
Route 1 of docs/plan-lex-dk-links.md: proposes lex.dk articles for register persons by
matching their name against the URL slugs in lex.dk's own sitemap (no chatbot), then
verifies each candidate with ONE normal page request (1 request/second, cached):
the page's title/lead must contain the register's birth AND death year.

  python scripts/parsers/lex_sitemap_match.py --tier A --limit 30 [--offset 0]

Inputs
  data/raw/lex/sitemap1..6.xml     downloaded once from https://lex.dk/.sitemap/sitemap.xml
                                   (gitignored; re-download at most monthly)
  data/curated/lex/persons_tiers.csv   from screen_persons_for_lex.py
Outputs
  data/curated/lex/persons_lex_sitemap.csv   proposals (links + verification flags, no Lex text)
  data/raw/lex/page_cache.json               page checks (gitignored) — re-runs repeat no request

Works in priority order: DBL > Dansk Kvindebiografisk > Weilbach > lex.dk (Den Store Danske et al.)
> Dansk Teaterleksikon > Danmarkshistorien / Dansk litteraturs historie. Women: Kvindebiografisk
is tried before Weilbach/lex.dk (and DBL still first when present).
A proposal is never promoted automatically (CLAUDE.md "Faktakontrol").
"""

import argparse
import csv
import json
import re
import sys
import time
from collections import defaultdict
from datetime import date
from pathlib import Path
from urllib.parse import unquote, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lex_link_candidates import fetch_check, fold, life_years, name_tokens, slug_matches  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
RAW = REPO / "data" / "raw" / "lex"
TIERS = REPO / "data" / "curated" / "lex" / "persons_tiers.csv"
OUT = REPO / "data" / "curated" / "lex" / "persons_lex_sitemap.csv"
CACHE = RAW / "page_cache.json"

# host → (key, label, priority, max extra slug tokens beyond the name)
HOSTS = {
    "biografiskleksikon.lex.dk": ("dbl", "Dansk Biografisk Leksikon", 1, 2),
    "kvindebiografiskleksikon.lex.dk": ("dkbl", "Dansk Kvindebiografisk Leksikon", 2, 2),
    "weilbach.lex.dk": ("weilbach", "Weilbachs Kunstnerleksikon", 3, 2),
    "lex.dk": ("lex", "lex.dk (Den Store Danske m.fl.)", 4, 1),
    "teaterleksikon.lex.dk": ("teater", "Dansk Teaterleksikon", 5, 1),
    "danmarkshistorien.lex.dk": ("dh", "Danmarkshistorien", 6, 1),
    "dansklitteraturshistorie.lex.dk": ("dlh", "Dansk litteraturs historie", 6, 1),
}
PARTICLES = {"von", "van", "af", "de", "der", "den", "du", "la", "le", "zu", "i", "og"}
TITLES = {"sir", "lord", "lady", "graf", "grev", "greve", "furst", "baron", "baronesse", "friherre", "dr",
          "madame", "mme", "herr", "frk", "fru"}   # honorifics are not part of a lex.dk article title
MAX_VERIFY_PER_WORK = 3
MAX_VERIFY_TOTAL = 7


def load_index():
    """→ (entries, token_index). entry = (host, url, tokens)."""
    entries, index = [], defaultdict(list)
    for f in sorted(RAW.glob("sitemap?.xml")):
        text = f.read_text(encoding="utf-8")
        for m in re.finditer(r"<loc>([^<]+)</loc>", text):
            url = m.group(1)
            host = urlparse(url).netloc
            if host not in HOSTS:
                continue
            slug = fold(unquote(urlparse(url).path.strip("/")))
            toks = [t for t in re.split(r"[^a-zæøå0-9]+", slug) if t]
            if not toks:
                continue
            i = len(entries)
            entries.append((host, url, toks))
            for t in set(toks):
                index[t].append(i)
    return entries, index


def parse_name(name: str):
    """'Jonas d.Æ. Collin' → (['jonas'], ['collin']); 'Adam Gottlob Moltke-Hvitfeldt' →
    (['adam','gottlob'], ['moltke','hvitfeldt']). Generation tags (d.Æ./d.Y.) are dropped:
    lex slugs carry a disambiguator instead ("Jonas_Collin_-_finansdeputeret")."""
    head = re.split(r"[(,]", name)[0]
    head = re.sub(r"\bd\.\s?[ÆYJÄ]\.?", " ", head)
    words = [w for w in re.split(r"\s+", head.strip()) if w]
    words = [w for w in words if fold(w.strip(".")) not in PARTICLES | TITLES]
    if not words:
        return [], []
    if re.fullmatch(r"\d+\.?", words[-1]) and len(words) >= 2:      # royals: "Christian 9."
        return [], [fold(words[-2].strip(".")), words[-1].strip(".")]
    sur = [t for t in re.split(r"[\-.]+", fold(words[-1])) if t]
    given = [t for t in re.split(r"[\s.\-]+", fold(" ".join(words[:-1]))) if t]
    return given, sur


def slug_score(given, sur, st, name_part=None):
    """None if the slug cannot be this person; else (extra_tokens, -matched). Rules: at least one
    surname part present exactly; the FIRST given token compatible (exact, initial, or
    abbreviation); later given tokens optional (DBL drops middle names)."""
    name_part = st if name_part is None else name_part
    if sur and sur[-1].isdigit():                    # "Christian 9." needs both parts
        return (len(st) - 2, -2) if all(t in st for t in sur) else None
    if not any(t in st for t in sur):
        return None
    singles = {t for t in st if len(t) == 1}
    matched = sum(1 for t in sur if t in st)
    if given:
        others = [x for x in st if x not in sur]            # an initial must not match the surname itself
        initials_slug = [x for x in others if len(x) == 1]   # "J.P.E._Hartmann" → j, p, e

        def compat(g):
            return (g in st or (len(g) == 1 and any(x.startswith(g) for x in others))
                    or (len(g) >= 3 and (g[0] in singles or any(len(x) >= 2 and g.startswith(x) for x in others))))
        # The FIRST given name must fit (kin share surnames: Emil Hartmann ≠ J.P.E. Hartmann), and a
        # slug written with initials must have every initial accounted for by the person's given names.
        if not compat(given[0]):
            return None
        # Every full first-name word in the slug's NAME part (before a "_-_ disambiguator") must be
        # explained by the person's own given names — "Carl_Berendt_Lorck" is not Carl Julius Lorck.
        for x in name_part:
            if len(x) >= 3 and x not in sur and x not in {"jr", "sen", "den", "ældre", "yngre"} \
                    and not any(x == g or (len(g) >= 3 and (x.startswith(g) or g.startswith(x)))
                                or (len(g) == 1 and x.startswith(g)) for g in given):
                return None
        gi = {g[0] for g in given if g}
        if initials_slug and (any(i not in gi for i in initials_slug) or len(initials_slug) > len(given)):
            return None            # "C.C._Hall" has two initials; "Carl Hall" supplies one
        matched += sum(1 for g in given if compat(g))
    return (len(st) - matched, -matched)


def candidates(name: str, entries, index):
    given, sur = parse_name(name)
    pivots = [t for t in sur if (len(t) >= 3 or t.isdigit()) and t in index]
    if not sur or not pivots:
        return []
    # union of the surname parts' postings (Moltke-Hvitfeldt is "Adam_Gottlob_Moltke" in lex.dk);
    # royals need the rarer part only
    ids = set()
    if sur[-1].isdigit():
        ids = set(index[min(pivots, key=lambda t: len(index[t]))])
    else:
        for t in pivots:
            ids |= set(index[t])
    out = []
    for i in ids:
        host, url, st = entries[i]
        npart = [t for t in re.split(r"[^a-zæøå0-9]+", fold(unquote(urlparse(url).path.strip("/")).split("_-_")[0])) if t]
        sc = slug_score(given, sur, st, npart)
        if sc is None or sc[0] > HOSTS[host][3]:
            continue
        out.append((HOSTS[host][2], sc[0], sc[1], host, url))
    out.sort()
    return [(p, e, h, u) for p, e, _m, h, u in out]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tier", default="A")
    ap.add_argument("--limit", type=int, default=30)
    ap.add_argument("--offset", type=int, default=0)
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--no-fetch", action="store_true")
    ap.add_argument("--merge", action="store_true", help="keep rows of earlier runs for other rids")
    args = ap.parse_args()

    persons = [r for r in csv.DictReader(open(TIERS, encoding="utf-8")) if r["tier"] == args.tier]
    persons = persons[args.offset:args.offset + args.limit]
    entries, index = load_index()
    print(f"index: {len(entries):,} candidate articles on {len(HOSTS)} hosts; persons: {len(persons)}")
    cache = json.load(open(CACHE, encoding="utf-8")) if CACHE.exists() else {}
    today = date.today().isoformat()
    requests_made, rows = 0, []
    t0 = time.time()
    for p in persons:
        born, died = life_years(p["label"])
        cands = candidates(p["search_name"], entries, index)
        if p["gender"] == "Kvindelig":          # women: Kvindebiografisk before Weilbach/lex.dk
            cands.sort(key=lambda c: (c[0] if c[0] <= 1 else (2 if c[2].startswith("kvinde") else c[0] + 1), c[1]))
        per_work, verified = defaultdict(int), 0
        have = False
        for prio, extra, host, url in cands:
            key = HOSTS[host][0]
            if per_work[key] >= MAX_VERIFY_PER_WORK or verified >= MAX_VERIFY_TOTAL:
                continue
            if key != "dbl" and any(r["rid"] == p["rid"] and r["verdict"] == "confirmed" and r["work"] == key for r in rows):
                continue                          # one confirmed link per work is enough
            if args.no_fetch:
                chk = {"status": "", "title": "", "years": "", "verdict": "unchecked"}
            else:
                ck = url + "#v2"                         # v2: lead window after the first <h1>
                if ck not in cache:
                    time.sleep(1.0)
                    cache[ck] = fetch_check(url, born, died)
                    requests_made += 1
                chk = cache[ck]
            per_work[key] += 1
            verified += 1
            rows.append({"rid": p["rid"], "tier": p["tier"], "label": p["label"], "search_name": p["search_name"],
                         "gender": p["gender"], "work": key, "work_label": HOSTS[host][1], "priority": prio,
                         "url": unquote(url), "page_title": chk["title"], "http": chk["status"],
                         "years_found": chk["years"], "verdict": chk["verdict"], "queried_on": today})
            if chk["verdict"] == "confirmed" and key == "dbl":
                have = True
        # reaching here with nothing at all for the person = a miss, recorded in the summary below
        p["_n_cands"] = len(cands)
        if requests_made and requests_made % 50 == 0:
            json.dump(cache, open(CACHE, "w", encoding="utf-8"), ensure_ascii=False)
    RAW.mkdir(parents=True, exist_ok=True)
    json.dump(cache, open(CACHE, "w", encoding="utf-8"), ensure_ascii=False)

    # Two different confirmed articles of the same work for one person means a namesake or a relative
    # whose lead repeats the years ("J.L. Heiberg" mentions Johanne Luise's): keep the slug that spells
    # the person's given names out in full, downgrade the others to "likely" for manual review.
    groups = defaultdict(list)
    for r in rows:
        if r["verdict"] == "confirmed":
            groups[(r["rid"], r["work"])].append(r)
    for (rid, _w), grp in groups.items():
        if len(grp) > 1:
            given, _sur = parse_name(grp[0]["search_name"])
            def full_hits(r):
                st = fold(unquote(urlparse(r["url"]).path)).replace("_", " ")
                return sum(1 for g in given if len(g) >= 3 and g in st.split())
            best = max(full_hits(r) for r in grp)
            keep = [r for r in grp if full_hits(r) == best][:1]
            for r in grp:
                if r not in keep:
                    r["verdict"] = "likely"
                    r["years_found"] = r["years_found"] + "*"      # * = ambiguous with another confirmed article

    # merge with earlier runs (staged 30 → 90 → …): rows of the current persons replace old ones
    cols = ["rid", "tier", "label", "search_name", "gender", "work", "work_label", "priority", "url",
            "page_title", "http", "years_found", "verdict", "queried_on"]
    old = []
    if args.merge and Path(args.out).exists():
        cur = {p["rid"] for p in persons}
        old = [r for r in csv.DictReader(open(args.out, encoding="utf-8")) if r["rid"] not in cur]
    order = {"confirmed": 0, "likely": 1, "unchecked": 1, "mismatch": 2, "dead": 3}
    allrows = old + rows
    allrows.sort(key=lambda r: (r["rid"], order[r["verdict"]], int(r["priority"])))
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(allrows)

    by = defaultdict(list)
    for r in rows:
        by[r["rid"]].append(r)
    n = len(persons)
    anyc = sum(1 for p in persons if p["_n_cands"])
    conf = sum(1 for p in persons if any(x["verdict"] == "confirmed" for x in by[p["rid"]]))
    dbl = sum(1 for p in persons if any(x["verdict"] == "confirmed" and x["work"] == "dbl" for x in by[p["rid"]]))
    print(f"persons {n}: with slug candidate {anyc} · confirmed any {conf} · confirmed DBL {dbl} · "
          f"page requests {requests_made} · {time.time() - t0:0.0f}s")
    miss = [p for p in persons if not any(x["verdict"] == "confirmed" for x in by[p["rid"]])]
    print("no confirmed link:")
    for p in miss[:60]:
        print(f"  {p['rid']} {p['search_name'][:34]:34} cands={p['_n_cands']} "
              f"{[(x['work'], x['verdict']) for x in by[p['rid']]][:3]}")


if __name__ == "__main__":
    main()
