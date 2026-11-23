"""OCR-rettelser i almanakregistret (almanak/scripts/parse_register.py, register_repair.py). Syntetiske data."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "almanak" / "scripts"))
import parse_register as pr  # noqa: E402
import register_repair as rr  # noqa: E402


def refs(text):
    h, nx, r = pr.split_refs(text)
    return h, [(x["year"], x["month"], x["day"], x["valid"], x["src"]) for x in r]


def test_hyphen_as_period_and_trailing_noise():
    _, r = refs("Zinn, Ludvig. 1843 7-5- 19.5, 21.3.- 1846 3-1-")
    assert [(y, m, d) for y, m, d, v, _ in r if v] == [(1843, 5, 7), (1843, 5, 19), (1843, 3, 21), (1846, 1, 3)]


def test_glued_and_comma_joined_dates():
    _, r = refs("Hahn, Ida. 1844 5.7, 13.7.1845 14.1. 1846 20.11,30.11.")
    assert [(y, m, d) for y, m, d, v, _ in r if v] == [(1844, 7, 5), (1844, 7, 13), (1845, 1, 14), (1846, 11, 20), (1846, 11, 30)]


def test_garbled_year_is_read_from_last_two_digits_not_inherited():
    _, r = refs("Dahlstrom, Frits. 1833 2.11. ‘859 30.6, 12.7.")
    assert (1833, 11, 2, 1, "tail") in r and (1859, 6, 30, 1, "tail") in r


def test_date_in_heading_becomes_a_reference():
    h, r = refs("Romanen, 26.9. og 29.9.1838 planlagt")
    assert [(y, m, d) for y, m, d, v, s in r if s == "label"] == [(1838, 9, 26), (1838, 9, 29)]
    assert h.endswith("29.9.1838 planlagt")          # opslagsordet er uændret
    _, r = refs("Storfyrsten, 27.-30.6.1838")
    assert [d for _, _, d, _, _ in r] == [27, 28, 29, 30]


def test_ambiguous_year_stays_invalid_without_corroboration():
    _, r = refs("Bredahl, Christian. 1830 20.5.")
    assert r == [(None, 5, 20, 0, "tail")]


def test_year_candidates_differ_by_one_digit():
    c = rr.year_candidates("1899")
    assert 1859 in c and 1839 in c and all(sum(a != b for a, b in zip(str(y), "1899")) == 1 for y in c)


def test_name_corrections_whole_word_and_label_ocr(tmp_path):
    f = tmp_path / "c.tsv"
    f.write_text("reg_id\tfra\ttil\tbegrundelse\n*\tWulfT\tWulff\tOCR\nALMP9\tBücher\tBlicher\tOCR\n", encoding="utf-8")
    rows = [dict(reg_id="ALMP1", label="WulfT, Peter", description="WulfT, Peter.", see=""),
            dict(reg_id="ALMP9", label="Bücher, Steen", description="Bücher, Steen.", see=""),
            dict(reg_id="ALMP2", label="Bücher, X", description="", see="")]
    rr.apply_name_corrections(rows, f)
    assert rows[0]["label"] == "Wulff, Peter" and rows[0]["label_ocr"] == "WulfT, Peter"
    assert rows[1]["label"] == "Blicher, Steen" and rows[2]["label"] == "Bücher, X"
