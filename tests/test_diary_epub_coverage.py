"""diary.csv must cover every diary page of the EPUB edition, word for word.

Guards the EPUB → diary.csv parser (scripts/normalization/epub_diary_to_csv.py)
against silently dropping pages or text: for each Arabic-numbered page file
the text inside <main> — minus the apparatus notes and figures, which go to
their own columns — must equal the page's text in diary.csv once whitespace
and the "PPP-LL" line stamps are removed.
"""

import csv
import html
import re
from collections import defaultdict
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
EPUB_DIR = ROOT / "raw" / "hcadag-20240911 - Copy.epub" / "EPUB"
DIARY_CSVS = [ROOT / "data" / "normalized" / "diary.csv",
              ROOT / "data" / "normalized_v092" / "diary.csv"]
PAGE_FILE = re.compile(r"hcadag(\d\d)_\d+_(\d+)\.xhtml$")
ROMAN = ["", "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"]


def _squash(s):
    return re.sub(r"\s+", "", s)


def _epub_pages():
    pages = {}
    for f in EPUB_DIR.glob("hcadag*.xhtml"):
        m = PAGE_FILE.search(f.name)
        if not m:
            continue
        body = f.read_text(encoding="utf-8").split("<main", 1)[1]
        body = body.split(">", 1)[1].split("</main>", 1)[0]
        body = re.sub(r"<aside.*?</aside>|<figure.*?</figure>", "", body, flags=re.S)
        pages[(ROMAN[int(m.group(1))], m.group(2))] = _squash(
            html.unescape(re.sub(r"<[^>]+>", "", body)))
    return pages


@pytest.fixture(scope="module")
def epub_pages():
    if not EPUB_DIR.is_dir():
        pytest.skip(f"unzipped EPUB not present: {EPUB_DIR}")
    return _epub_pages()


@pytest.mark.parametrize("diary_csv", DIARY_CSVS, ids=lambda p: p.parent.name)
def test_every_epub_page_is_in_diary_csv(epub_pages, diary_csv):
    text = defaultdict(str)
    with diary_csv.open(encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            lines = (re.sub(r"^\d+-\d+\s+", "", ln) for ln in r["text"].split("\n"))
            text[(r["vol"], r["page"])] += _squash("".join(lines))

    missing = sorted(set(epub_pages) - set(text))
    assert not missing, f"{len(missing)} EPUB pages absent from diary.csv: {missing[:10]}"

    differ = [k for k, src in epub_pages.items() if src != text[k]]
    assert not differ, f"{len(differ)} pages whose text differs from the EPUB: {differ[:10]}"
