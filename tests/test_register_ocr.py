"""OCR-rettelser i almanakregistret (almanak/scripts/parse_register.py, register_repair.py). Syntetiske data."""
import re
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


def test_confusable_years_only_swap_3_5_8_9():
    c = rr.confusable_years(1833)
    assert 1853 in c and 1855 in c and 1839 in c and 1838 in c
    assert 1843 not in c and 1834 not in c           # 4 og 3->4 er ikke en kendt forveksling


def _aligned(tmp_path, days):
    f = tmp_path / "aligned.csv"
    f.write_text("date,pdf_text,db_text\n" + "".join(f"{d},{t},\n" for d, t in days), encoding="utf-8")
    return f


def _ref(rid, year, raw, day, month):
    return dict(reg_id=rid, register="person", year=year, year_raw=raw, day=day, month=month, kind="date", raw=f"{day}.{month}.", valid=1, src="tail", fix="")


def test_unmatched_year_is_repaired_by_name_and_group(tmp_path):
    al = _aligned(tmp_path, [("1853-07-05", "Besøg af Zinn og Hahn"), ("1853-08-09", "Middag hos Zinn"), ("1853-10-01", "Intet"),
                             ("1855-07-05", "Intet"), ("1855-08-09", "Intet")])
    persons = [dict(reg_id="ALMP1", label="Zinn, Ludvig"), dict(reg_id="ALMP2", label="Hahn, Ida")]
    r = [_ref("ALMP1", 1833, "1833", 5, 7), _ref("ALMP1", 1833, "1833", 9, 8),            # 1833 findes ikke: 1853 har navnet
         _ref("ALMP2", 1833, "1833", 5, 7), _ref("ALMP2", 1833, "1833", 1, 10)]          # 1.10.: ingen navnekontrol, gruppen peger på 1853
    by_name, by_group, left = rr.repair_unmatched_years(persons, [], r, al)
    assert [x["year"] for x in r] == [1853, 1853, 1853, 1853]
    assert (by_name, by_group, left) == (3, 1, 0)
    assert r[0]["fix"] == "år-rettet-ved-navnekontrol (1833→1853)" and r[3]["fix"] == "år-rettet-via-gruppe (1833→1853)"


def test_unmatched_year_is_left_when_name_supports_two_years_and_no_group_decides(tmp_path):
    al = _aligned(tmp_path, [("1853-07-05", "Zinn"), ("1855-07-05", "Zinn")])
    r = [_ref("ALMP1", 1833, "1833", 5, 7)]
    out = rr.repair_unmatched_years([dict(reg_id="ALMP1", label="Zinn, Ludvig")], [], r, al)
    assert r[0]["year"] == 1833 and out == (0, 0, 1)


def test_divsign_ocr_forms_are_stripped_from_the_heading():
    for text in ("Moltke, grevinde. 4-, 1845 21.7.", "Hjorhøi, tigger. -5-. 1841 1.11.", "Malz, -r. 1844 2.3.",
                 "Borring, sproglærer. . 1843 31.7."):
        h, flag, r = pr.split_refs(text)
        assert not re.search(r"4-|-5-|-r|\. \.", h), h
        assert r and r[0]["year"] in (1841, 1843, 1844, 1845)
    assert pr.split_refs("Moltke, grevinde. 4-, 1845 21.7.")[1] is True
    assert pr.split_refs("Borring, sproglærer. . 1843 31.7.")[1] is False      # tabt tegn: kun billedet kan se det


def test_divsign_is_assigned_by_line_height_not_x():
    import register_glyphs as rg
    entries = [[(360, (46.0, 100.0, 180.0, 108.0))],                     # opslag 1, venstre spalte
               [(360, (60.0, 110.0, 150.0, 118.0)), (360, (46.0, 120.0, 120.0, 128.0))],
               [(360, (199.6, 100.0, 330.0, 108.0))]]                   # højre spalte
    signs = {360: [(50.0, 112.0, 55.0, 116.5),                           # foran linjens boks (OCR tabte tegnet) -> opslag 2
                   (205.0, 101.5, 210.0, 106.0),                         # højre spalte -> opslag 3
                   (130.0, 130.0, 135.0, 134.5)]}                        # alene på en linje under opslag 2 -> opslag 2
    counts, orphans = rg.assign(signs, entries)
    assert counts == [0, 2, 1] and orphans == []
