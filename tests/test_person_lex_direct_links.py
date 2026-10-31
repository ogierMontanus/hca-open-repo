"""
Guards the direct lex.dk links in «Biografiske opslag» (build_persons_extra.load_lex_direct_links /
bio_search_links): a verified article replaces the Lex.dk *search* link; nothing unverified gets in.

Skips when the curated DBL file has not been built.
"""
import csv
import importlib.util
import pathlib
import sys
from urllib.parse import unquote, urlparse

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
ADDED = ROOT / "data" / "curated" / "person_nationality_added.csv"

pytestmark = pytest.mark.skipif(not ADDED.exists(), reason="person_nationality_added.csv not built")


@pytest.fixture(scope="module")
def mod():
    sys.path.insert(0, str(ROOT / "scripts" / "build_mockup"))   # sibling import _diary_scope
    spec = importlib.util.spec_from_file_location(
        "build_persons_extra", ROOT / "scripts" / "build_mockup" / "build_persons_extra.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


@pytest.fixture(scope="module")
def direct(mod):
    return mod.load_lex_direct_links()


def test_every_dbl_person_gets_the_dbl_article_first(direct):
    with open(ADDED, encoding="utf-8", newline="") as f:
        rows = [r for r in csv.DictReader(f) if r["nat_basis"] == "dbl_optagelse"]
    assert rows
    for r in rows:
        first = direct[r["rid"]][0]
        assert first["label"] == "Dansk Biografisk Leksikon", r
        assert unquote(first["url"]) == r["source_url"], r


def test_only_lex_hosts_and_encoded(direct):
    for rid, links in direct.items():
        assert links and len({l["label"] for l in links}) == len(links), rid
        for l in links:
            u = urlparse(l["url"])
            assert u.scheme == "https" and (u.netloc == "lex.dk" or u.netloc.endswith(".lex.dk")), l
            assert l["direct"] is True
            assert ".search" not in u.path and all(ord(c) < 128 for c in l["url"]), l
            assert "danmarkshistorien" not in u.netloc, l     # chapters, not biographies


def test_no_article_shared_between_persons_outside_dbl_aliases(direct):
    seen = {}
    for rid, links in direct.items():
        for l in links:
            if l["label"] == "Dansk Biografisk Leksikon":
                continue          # DBL sharing is reviewed (accept_alias) in build_person_nationality_added
            assert seen.setdefault(l["url"], rid) == rid, l


def test_direct_replaces_lex_search_but_keeps_other_resources(mod):
    d = [{"label": "Dansk Biografisk Leksikon", "url": "https://biografiskleksikon.lex.dk/X", "direct": True}]
    umb = {"dansk": {"dansk"}, "tysk": {"tysk"}}
    danish = mod.bio_search_links("Test, Ole (1800–1860)", "1800", "1860", ["dansk"], [], umb, d)
    assert danish == d
    assert any(l["url"].startswith(mod.LEX_SEARCH)
               for l in mod.bio_search_links("Test, Ole (1800–1860)", "1800", "1860", ["dansk"], [], umb))
    both = mod.bio_search_links("Test, Ole (1800–1860)", "1800", "1860", ["dansk", "tysk"], [], umb, d)
    assert both[0] == d[0] and len(both) == 2 and "deutsche-biographie" in both[1]["url"]
    unknown = mod.bio_search_links("Test, Ole (1800–1860)", "1800", "1860", [], [], umb, d)
    assert unknown == d
