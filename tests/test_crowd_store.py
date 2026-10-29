"""The file store, the HTTP API and the export of the crowdsourcing prototype
(scripts/crowdsource/, docs/crowdsourcing.md §5–6). All against a temp dir and
a throw-away server on an ephemeral port — no repo data is written."""
import json
import sys
import threading
import urllib.error
import urllib.request
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "crowdsource"))
import export_approved as ex  # noqa: E402
import server as srv_mod  # noqa: E402
import validate  # noqa: E402
from register import Register  # noqa: E402
from store import Conflict, FileStore, Forbidden, NotFound  # noqa: E402

FX = json.loads((ROOT / "tests" / "fixtures" / "crowd_cases.json").read_text(encoding="utf-8"))


def payload(**over):
    p = json.loads(json.dumps(FX["cases"][0]["payload"]))
    p["context"] = {"area": "Danmark", "doubt": False, "level": "fragmentarisk", "gaps": ["identity"]}
    p.update(over)
    return p


class FakeRegister(Register):
    """A register with two persons, so nothing depends on the repo's CSVs."""
    def __init__(self):
        super().__init__()
        self._persons = {"Reg0030030": ("Aagaard", "»ude fra Kalundborg-Kanten(?)« (19.5.1872)"),
                         "Reg0030040": ("Aagaard, C.F. (1833–1895)", "Landskabsmaler.")}
        self._refs = {"Reg0030030": {("IX", "280")}, "Reg0030040": {("IX", "344"), ("X", "55")}}


@pytest.fixture
def store(tmp_path):
    return FileStore(tmp_path / "crowd")


def submit(store, token=None, name="Anne", **over):
    p = payload(**over)
    p["contributor"] = {"name": name, "public_credit": True}
    clean, errs = validate.validate_submission(p)
    assert not errs, errs
    return store.create(clean, token, FakeRegister().snapshot(clean["person_id"]))


def decide(store, sid, **dec):
    return store.review(sid, "Holger", {"fields": {"0": {"decision": "accept"}, "1": {"decision": "accept"}}, **dec})


# ── store ──────────────────────────────────────────────────────────────────
def test_create_issues_a_token_once_and_keeps_only_its_hash(store):
    sub, token = submit(store)
    assert token and sub["status"] == "submitted" and sub["revision"] == 1
    assert token not in (store.contrib_file.read_text(encoding="utf-8"))
    assert store.contributor_by_token(token)["id"] == sub["contributor"]["id"]
    sub2, token2 = submit(store, token)
    assert token2 is None and sub2["contributor"]["id"] == sub["contributor"]["id"]
    assert sub["register_snapshot"]["refs_signature"] == "IX:280"


def test_ids_are_validated_before_touching_the_filesystem(store):
    for bad in ["../x", "CS-1", "CS-20261029-ZZZZZZ", ""]:
        with pytest.raises(NotFound):
            store.get(bad)


def test_review_all_accepted_approves_and_edited_value_is_kept(store):
    sub, _ = submit(store)
    out = store.review(sub["id"], "Holger", {"fields": {"0": {"decision": "accept"},
                       "1": {"decision": "accept_edited", "final_value": "1821", "final_confidence": "proposed"}}}, "ok")
    assert out["status"] == "approved"
    assert out["review"]["fields"]["1"]["final_value"] == "1821"
    assert out["review"]["fields"]["0"]["final_confidence"] == "probable"


def test_review_partial_and_rejected(store):
    a, _ = submit(store)
    assert store.review(a["id"], "H", {"fields": {"0": {"decision": "accept"}, "1": {"decision": "reject"}}})["status"] == "partially_approved"
    b, _ = submit(store)
    assert store.review(b["id"], "H", {"fields": {"0": {"decision": "reject"}, "1": {"decision": "reject"}}})["status"] == "rejected"


def test_review_demands_a_decision_for_every_field(store):
    sub, _ = submit(store)
    with pytest.raises(ValueError, match="no decision"):
        store.review(sub["id"], "H", {"fields": {"0": {"decision": "accept"}}})
    with pytest.raises(ValueError, match="final_value"):
        store.review(sub["id"], "H", {"fields": {"0": {"decision": "accept_edited"}, "1": {"decision": "accept"}}})
    with pytest.raises(ValueError, match="note is required"):
        store.review(sub["id"], "H", {}, "", "request_changes")
    assert store.get(sub["id"])["status"] == "submitted"       # nothing half-applied


def test_identification_only_submissions_need_their_own_decision(store):
    p = payload(identification={"status": "unidentifiable", "summary": "søgt i DDD", "same_as": ""}, fields=[], overall_confidence="")
    p["sources"][0]["result"] = "intet_fund"
    clean, errs = validate.validate_submission(p)
    assert not errs
    sub, _ = store.create(clean, None)
    with pytest.raises(ValueError, match="identification"):
        store.review(sub["id"], "H", {"fields": {}})
    out = store.review(sub["id"], "H", {"fields": {}, "identification": {"decision": "accept"}})
    assert out["status"] == "approved"


def test_changes_requested_then_contributor_revises(store):
    sub, token = submit(store)
    out = store.review(sub["id"], "H", {}, "Mangler kilde til fødselsåret", "request_changes")
    assert out["status"] == "needs_changes"
    clean, _ = validate.validate_submission(payload())
    clean["fields"][1]["value"] = "1821"
    rev = store.update(sub["id"], clean, token)
    assert rev["status"] == "submitted" and rev["revision"] == 2 and rev["review"] is None
    assert rev["history"][-1]["previous"]["review"]["note"].startswith("Mangler")
    assert rev["fields"][1]["value"] == "1821"


def test_only_the_owner_can_revise_or_withdraw_and_only_while_open(store):
    sub, token = submit(store)
    _other, other_token = submit(store, None, name="Bo")
    clean, _ = validate.validate_submission(payload())
    with pytest.raises(Forbidden):
        store.update(sub["id"], clean, other_token)
    with pytest.raises(Forbidden):
        store.withdraw(sub["id"], other_token)
    store.withdraw(sub["id"], token)
    with pytest.raises(Conflict):
        store.withdraw(sub["id"], token)
    assert store.get(sub["id"])["status"] == "withdrawn"


def test_contributors_only_see_their_own_submissions_and_not_the_history(store):
    a, ta = submit(store)
    b, tb = submit(store, None, name="Bo")
    mine = store.mine(ta)
    assert [s["id"] for s in mine] == [a["id"]]
    assert "history" not in mine[0] and "register_snapshot" not in mine[0]
    assert store.mine("wrong-token") == []


def test_conflicts_show_other_live_claims_with_a_different_value(store):
    a, _ = submit(store)
    p = payload()
    p["fields"][0]["value"] = "Peter"
    p["contributor"] = {"name": "Bo", "public_credit": False}
    b, _ = store.create(validate.validate_submission(p)[0], None)
    c = store.conflicts(store.get(a["id"]))
    assert [(x["field"], x["value"]) for x in c] == [("given_names", "Peter")]
    store.review(b["id"], "H", {"fields": {"0": {"decision": "reject"}, "1": {"decision": "reject"}}})
    assert store.conflicts(store.get(a["id"])) == []


def test_stats_count_reviewed_work_and_badges_follow(store):
    sub, token = submit(store)
    assert store.contributor_stats()[0]["badges"] == []
    decide(store, sub["id"])
    s = store.contributor_stats()[0]
    assert (s["approved_submissions"], s["accepted_fields"], s["persons"]) == (1, 2, 1)
    assert s["badges"] == ["first_accepted"]
    assert store.person_status() == {"Reg0030030": {"pending": 0, "approved": 1}}


def test_incorporated_submissions_are_locked(store):
    sub, _ = submit(store)
    decide(store, sub["id"])
    store.mark_incorporated(sub["id"], "B-test")
    with pytest.raises(Conflict):
        decide(store, sub["id"])


def test_attachments_are_stored_outside_the_json_and_path_checked(store):
    import base64
    p = payload()
    p["sources"][0]["attachment"] = {"name": "folketaelling.png", "type": "image/png", "data": base64.b64encode(b"\x89PNG....").decode()}
    clean, errs = validate.validate_submission(p)
    assert not errs
    sub, _ = store.create(clean, None)
    meta = sub["sources"][0]["attachment"]
    assert "data" not in json.dumps(store.get(sub["id"]))
    assert store.attachment_path(sub["id"], meta["file"]).read_bytes() == b"\x89PNG...."
    for bad in ["../contributors.json", "..", "a/b"]:
        with pytest.raises(NotFound):
            store.attachment_path(sub["id"], bad)


def test_revision_keeps_earlier_attachments_for_unchanged_sources(store):
    import base64
    p = payload()
    p["sources"][0]["attachment"] = {"name": "a.png", "type": "image/png", "data": base64.b64encode(b"\x89PNG").decode()}
    clean, _ = validate.validate_submission(p)
    sub, token = store.create(clean, None)
    store.review(sub["id"], "H", {}, "uddyb venligst", "request_changes")
    q = payload()
    clean2, _ = validate.validate_submission(q)         # same source, no new attachment
    clean2["fields"][0]["value"] = "Peter"
    rev = store.update(sub["id"], clean2, token)
    assert rev["sources"][0]["attachment"]["file"].endswith("a.png")
    assert store.attachment_path(sub["id"], rev["sources"][0]["attachment"]["file"]).exists()


# ── import from the browser-local mode ─────────────────────────────────────
def local_submission(status="submitted", review=None):
    return {"id": "CS-20261029-abc123", "person_id": "Reg0030030", "person_label": "Aagaard", "status": status,
            "identification": {"status": "identified", "summary": "", "same_as": ""}, "overall_confidence": "probable",
            "fields": payload()["fields"], "sources": payload()["sources"], "comment": "", "consent": True, "revision": 1,
            "contributor": {"id": "C-local-1234abcd", "name": "Anne", "public_credit": True}, "review": review}


def test_import_recomputes_status_from_decisions_instead_of_trusting_it(store):
    review = {"reviewer": "H", "decided": "2026-10-29T10:00:00Z", "note": "",
              "fields": {"0": {"decision": "accept", "final_confidence": "probable"}, "1": {"decision": "reject"}}, "identification": None}
    assert store.import_submission(local_submission("approved", review)) == "added"   # claims approved…
    assert store.get("CS-20261029-abc123")["status"] == "partially_approved"           # …decisions say otherwise


def test_import_rejects_invalid_or_forged_files(store):
    bad = local_submission()
    bad["sources"] = []
    with pytest.raises(ValueError):
        store.import_submission(bad)
    undecided = local_submission("approved", {"reviewer": "H", "fields": {"0": {"decision": "accept"}}})
    with pytest.raises(ValueError, match="every field"):
        store.import_submission(undecided)
    with pytest.raises(ValueError, match="bad submission id"):
        store.import_submission({**local_submission(), "id": "../../etc"})


def test_import_never_overwrites_incorporated_or_newer(store):
    store.import_submission(local_submission())
    store.mark_incorporated("CS-20261029-abc123", "B")
    assert store.import_submission(local_submission()) == "unchanged"


# ── export ─────────────────────────────────────────────────────────────────
def approved_store(store):
    sub, _ = submit(store)
    store.review(sub["id"], "Holger", {"fields": {"0": {"decision": "accept"},
                 "1": {"decision": "accept_edited", "final_value": "1821", "final_confidence": "proposed", "note": "kun året"}}}, "ok")
    return sub


def test_export_rows_carry_provenance_and_the_register_guard(store):
    sub = approved_store(store)
    rows = ex.build_rows(store, FakeRegister())
    assert [(r["field"], r["emended"], r["confidence"]) for r in rows] == [("given_names", "Peder", "probable"), ("birth_date", "1821", "proposed")]
    r = rows[0]
    assert (r["person_id"], r["match_surname"], r["match_refs"], r["source"]) == ("Reg0030030", "Aagaard", "IX:280", "CROWD")
    assert r["contributor"] == "Anne" and r["reviewer"] == "Holger" and r["submission_id"] == sub["id"] and r["guard"] == "ok"
    assert "ddd.dda.dk" in r["source_detail"]
    assert "Redaktionen har rettet" in rows[1]["notes"]
    assert rows[1]["emend_field"] == "birth_year"
    # the register changed under the contribution → flagged, never silently applied
    changed = FakeRegister()
    changed._persons["Reg0030030"] = ("Aagaard, Peder", "")
    assert ex.build_rows(store, changed)[0]["guard"].startswith("register_changed")


def test_export_skips_unapproved_and_incorporated(store):
    submit(store)
    assert ex.build_rows(store, FakeRegister()) == []
    sub = approved_store(store)
    store.mark_incorporated(sub["id"], "B")
    assert ex.build_rows(store, FakeRegister()) == []
    assert len(ex.build_rows(store, FakeRegister(), include_incorporated=True)) == 2


def test_tsv_is_one_line_per_row_and_merge_is_idempotent(store):
    approved_store(store)
    rows = ex.build_rows(store, FakeRegister())
    tsv = ex.rows_to_tsv(rows)
    lines = tsv.rstrip("\n").split("\n")
    assert lines[0].split("\t") == ex.COLUMNS and len(lines) == 3
    merged = ex.merge_rows(ex.merge_rows([], rows), rows)
    assert len(merged) == 2
    edited = [dict(rows[0], emended="Peter")] + rows[1:]
    assert [r["emended"] for r in ex.merge_rows(merged, edited) if r["field"] == "given_names"] == ["Peter"]


def test_tsv_cells_cannot_break_the_format(store):
    row = {c: "" for c in ex.COLUMNS}
    row.update(person_id="Reg1", notes="a\tb\nc")
    out = ex.rows_to_tsv([row])
    assert len(out.rstrip("\n").split("\n")) == 2 and out.count("\t") == 2 * (len(ex.COLUMNS) - 1)


def test_xlsx_has_person_rows_colours_and_comments(store):
    openpyxl = pytest.importorskip("openpyxl")
    approved_store(store)
    import io
    data = ex.rows_to_xlsx_bytes(ex.build_rows(store, FakeRegister()), FakeRegister(), crosswalk={"Reg0030030": "PER1000300"})
    wb = openpyxl.load_workbook(io.BytesIO(data))
    assert wb.sheetnames == ["Læsevejledning", "Personer", "Godkendte felter"]
    ws = wb["Personer"]
    head = [c.value for c in ws[1]]
    row = {h: c for h, c in zip(head, ws[2])}
    assert row["PersonID*"].value == "PER1000300" and row["Register-ID"].value == "Reg0030030"
    assert row["GivenNames"].value == "Peder" and row["BirthYear"].value == "1821"
    assert row["GivenNames"].fill.fgColor.rgb.endswith("FFEB9C")            # probable = yellow
    assert "DDD" in row["GivenNames"].comment.text or "Demografisk" in row["GivenNames"].comment.text
    assert row["Person* (som i registret)"].value == "Aagaard"


# ── HTTP API ───────────────────────────────────────────────────────────────
@pytest.fixture
def api(tmp_path):
    site = tmp_path / "site"
    site.mkdir()
    (site / "index.html").write_text("<p>hello</p>", encoding="utf-8")
    (tmp_path / "secret.txt").write_text("nope", encoding="utf-8")
    server = srv_mod.make_server("127.0.0.1", 0, data_dir=tmp_path / "crowd", directory=site, admin_token="adm")
    server.register = FakeRegister()
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    port = server.server_address[1]

    def call(method, path, body=None, token=None, raw=False):
        req = urllib.request.Request(f"http://127.0.0.1:{port}{path}", method=method,
                                     data=None if body is None else json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json", **({"Authorization": f"Bearer {token}"} if token else {})})
        try:
            with urllib.request.urlopen(req) as r:
                data = r.read()
                return r.status, (data if raw else json.loads(data)), r.headers
        except urllib.error.HTTPError as e:
            data = e.read()
            return e.code, (data if raw else json.loads(data)), e.headers

    yield call
    server.shutdown()
    server.server_close()


def body(name="Anne"):
    p = payload()
    p["contributor"] = {"name": name, "public_credit": True}
    return p


def test_api_full_cycle(api):
    assert api("GET", "/api/crowd/health")[1]["mode"] == "api"
    s, r, _ = api("POST", "/api/crowd/submissions", body())
    assert s == 201 and r["contributor"]["token"] and r["submission"]["status"] == "submitted"
    token, sid = r["contributor"]["token"], r["submission"]["id"]
    assert api("GET", "/api/crowd/mine", token=token)[1]["submissions"][0]["id"] == sid
    assert api("GET", "/api/crowd/mine")[1]["submissions"] == []

    # the review endpoints are closed to everyone but the editor
    assert api("GET", "/api/crowd/admin/submissions")[0] == 401
    assert api("GET", "/api/crowd/admin/submissions", token=token)[0] == 401     # a contributor token is not an editor token
    s, r, _ = api("GET", "/api/crowd/admin/submissions?status=submitted", token="adm")
    assert s == 200 and [x["id"] for x in r["submissions"]] == [sid]
    s, r, _ = api("GET", f"/api/crowd/admin/submissions/{sid}", token="adm")
    assert r["register"]["refs_signature"] == "IX:280" and r["contributor"]["name"] == "Anne"
    s, r, _ = api("POST", f"/api/crowd/admin/submissions/{sid}/review", {"reviewer": "Holger", "decisions": {"fields": {"0": {"decision": "accept"}, "1": {"decision": "accept"}}}}, token="adm")
    assert s == 200 and r["submission"]["status"] == "approved"
    # the contributor sees the verdict, the public stats count it
    mine = api("GET", "/api/crowd/mine", token=token)[1]
    assert mine["submissions"][0]["status"] == "approved" and mine["submissions"][0]["review"]["reviewer"] == "Holger"
    st = api("GET", "/api/crowd/stats", token=token)[1]
    assert st["approved"] == 1 and st["me"]["badges"] == ["first_accepted"] and st["contributors"][0]["name"] == "Anne"
    # export: TSV and JSON
    s, tsv, h = api("GET", "/api/crowd/admin/export?format=tsv", token="adm", raw=True)
    assert s == 200 and tsv.decode().startswith("person_id\t") and "text/tab-separated-values" in h["Content-Type"]
    assert len(api("GET", "/api/crowd/admin/export?format=json", token="adm")[1]["rows"]) == 2
    assert api("GET", "/api/crowd/admin/export", token=None)[0] == 401


def test_api_rejects_bad_input(api):
    s, r, _ = api("POST", "/api/crowd/submissions", {**body(), "sources": []})
    assert s == 422 and {e["code"] for e in r["errors"]} >= {"required"}
    s, r, _ = api("POST", "/api/crowd/submissions", {**body(), "person_id": "Reg9999999"})
    assert s == 422 and r["errors"][0]["code"] == "unknown_person"
    s, r, _ = api("POST", "/api/crowd/submissions", {**body(), "identification": {"status": "duplicate", "summary": "", "same_as": "Reg9999999"}, "fields": [], "overall_confidence": ""})
    assert s == 422 and r["errors"][0]["path"] == "identification.same_as"
    assert api("POST", "/api/crowd/submissions", [1, 2])[0] == 422
    assert api("GET", "/api/crowd/nope")[0] == 404
    assert api("POST", "/api/crowd/admin/submissions/CS-20261029-zzzzzz/review", {}, token="adm")[0] == 404


def test_api_other_contributor_cannot_touch_my_submission(api):
    _s, r, _ = api("POST", "/api/crowd/submissions", body())
    sid = r["submission"]["id"]
    _s, r2, _ = api("POST", "/api/crowd/submissions", body("Bo"))
    other = r2["contributor"]["token"]
    assert api("POST", f"/api/crowd/submissions/{sid}/withdraw", token=other)[0] == 403
    assert api("PUT", f"/api/crowd/submissions/{sid}", body(), token=other)[0] == 403


def test_api_review_errors_are_400_and_leave_the_submission_alone(api):
    _s, r, _ = api("POST", "/api/crowd/submissions", body())
    sid = r["submission"]["id"]
    s, r, _ = api("POST", f"/api/crowd/admin/submissions/{sid}/review", {"reviewer": "H", "decisions": {"fields": {}}}, token="adm")
    assert s == 400
    assert api("GET", f"/api/crowd/admin/submissions/{sid}", token="adm")[1]["submission"]["status"] == "submitted"


def test_static_files_are_served_with_hardening_headers_and_no_traversal(api):
    s, data, h = api("GET", "/index.html", raw=True)
    assert s == 200 and b"hello" in data and h["X-Content-Type-Options"] == "nosniff"
    assert api("GET", "/../secret.txt", raw=True)[0] in (400, 404)
    assert api("GET", "/%2e%2e/secret.txt", raw=True)[0] in (400, 404)
    assert api("POST", "/index.html", {})[0] == 405


# ── the whole hand-off: approve → export --write → site layer ──────────────
def test_export_write_updates_curated_files_marks_incorporated_and_feeds_the_site(tmp_path, monkeypatch, capsys):
    sys.path.insert(0, str(ROOT / "scripts" / "build_mockup"))
    import build_crowd_queue as bq
    store = FileStore(tmp_path / "crowd")
    approved_store(store)
    cur = tmp_path / "curated"
    monkeypatch.setattr(ex, "CURATED", cur)
    monkeypatch.setattr(ex, "TSV_PATH", cur / "person_crowd_approved.tsv")
    monkeypatch.setattr(ex, "XLSX_PATH", cur / "person_crowd_approved.xlsx")
    monkeypatch.setattr(ex, "Register", FakeRegister)
    monkeypatch.setattr(ex, "workbook_crosswalk", lambda reg: {"Reg0030030": "PER1000300"})
    monkeypatch.setattr(sys, "argv", ["export_approved.py", "--data-dir", str(tmp_path / "crowd"), "--write"])
    ex.main()
    assert (cur / "person_crowd_approved.tsv").exists()
    rows = ex.read_tsv(cur / "person_crowd_approved.tsv")
    assert [r["field"] for r in rows] == ["birth_date", "given_names"] and rows[0]["workbook_person_id"] == "PER1000300"
    assert store.all()[0]["incorporated"]["batch"].startswith("B-")
    # second run: nothing new, nothing lost
    ex.main()
    assert len(ex.read_tsv(cur / "person_crowd_approved.tsv")) == 2
    # the site layer picks the curated rows up, attributed
    monkeypatch.setattr(bq, "APPROVED_TSV", str(cur / "person_crowd_approved.tsv"))
    claims = bq.load_approved()["Reg0030030"]
    assert {(c["f"], c["v"], c["by"]) for c in claims} == {("given_names", "Peder", "Anne"), ("birth_date", "1821", "Anne")}
