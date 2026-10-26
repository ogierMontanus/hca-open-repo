#!/usr/bin/env python3
"""Check scripts/build_mockup/build_diary_pdf.py against the real data.

Builds a small PDF and asserts the three things it exists for:
  1. every PDF page of a diary page links to that page's absolute URL;
  2. the footnote entities that were asked for are drawn with a yellow
     background (and only those);
  3. the native outline has the dates as headings, year > month > day.

Needs reportlab and pypdf (pip install reportlab pypdf); skips if absent.
Run from the repo root:  python tests/test_build_diary_pdf.py
"""
import importlib.util
import re
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).parent.parent
SCRIPT = REPO / 'scripts' / 'build_mockup' / 'build_diary_pdf.py'
BASE = 'https://example.test/mockup/'


def _load():
    spec = importlib.util.spec_from_file_location('build_diary_pdf', SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


try:
    import pytest
except ImportError:                 # plain `python tests/test_build_diary_pdf.py`
    pytest = None

if pytest is not None:
    @pytest.fixture
    def mod():
        pytest.importorskip('reportlab')
        pytest.importorskip('pypdf')
        return _load()


def _build(mod, tmp, pages, entities):
    out = Path(tmp) / 'out.pdf'
    mod.main(['--pages', *pages, '--entity', *entities, '-o', str(out), '--base-url', BASE])
    return out


def _flatten(outline, depth=0):
    for node in outline:
        if isinstance(node, list):
            yield from _flatten(node, depth + 1)
        else:
            yield depth, node


def _uris(page):
    return {a.get_object()['/A']['/URI'] for a in page.get('/Annots', [])
            if '/A' in a.get_object()}


def _page_content(page):
    data = page.get_contents().get_data()
    return data.decode('latin-1')


def test_helpers(mod):
    assert mod.page_id('VII', '2') == 'Pag070002'
    assert mod.parse_page_id('Pag070002') == ('VII', '2')
    assert mod.format_date_da('1866-01-03') == 'Onsdag 3. januar 1866'
    assert mod.format_date_da('1866-01-XX') is None
    kind, label, path = mod.classify_row({'date': '1866-01-03'}, 'VII')
    assert kind == 'day' and [t for _, t in path] == ['1866', 'Januar 1866', label]


def test_pdf(mod):
    from pypdf import PdfReader
    pages = ['Pag070002', 'Pag070003', 'Pag030064']      # two dated, one without text
    highlighted = 'LOC1054350'                           # København, on Pag070308 only
    with tempfile.TemporaryDirectory() as tmp:
        reader = PdfReader(str(_build(mod, tmp, pages, [highlighted])))

        # 1. every diary page is linked at an absolute URL, on every PDF page it fills
        for pid in pages:
            url = f'{BASE}diary-pages/{pid}.html'
            assert any(url in _uris(p) for p in reader.pages), f'no link to {url}'
        for p in reader.pages[1:]:
            assert any(u.startswith(BASE + 'diary-pages/') for u in _uris(p)), 'page without link'

        # 3. native outline: dates as headings, years > months > days
        nodes = [(d, n.title) for d, n in _flatten(reader.outline)]
        assert (0, '1866') in nodes and (1, 'Januar 1866') in nodes
        assert (2, 'Tirsdag 2. januar 1866') in nodes
        assert (0, 'Bind III — uden dato') in nodes

    # 2. only the requested entity gets the yellow background (rgb 1 .92 .23)
    ent_page = 'Pag070308'
    with tempfile.TemporaryDirectory() as tmp:
        for ents, expect in (([highlighted], True), (['Reg0082020'], False)):
            reader = PdfReader(str(_build(mod, tmp, [ent_page], ents)))
            # skip the cover page, which shows the legend in yellow either way
            has_yellow = any(re.search(r'(?<![\d.])1 0?\.92\d* 0?\.23\d* rg', _page_content(p))
                             for p in reader.pages[1:])
            assert has_yellow == expect, (ents, has_yellow)


def main():
    try:
        import pypdf  # noqa: F401
        import reportlab  # noqa: F401
    except ImportError:
        print('SKIP — reportlab/pypdf not installed.')
        return 0
    mod = _load()
    test_helpers(mod)
    test_pdf(mod)
    print('OK — build_diary_pdf: links, footnote highlight and date outline verified.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
