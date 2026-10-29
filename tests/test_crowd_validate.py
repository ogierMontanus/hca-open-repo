"""Server-side validation of crowd submissions, against the cases shared
with the browser validator (tests/fixtures/crowd_cases.json,
tests/js/crowd-validate.test.js)."""
import base64
import datetime as dt
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "crowdsource"))
import validate  # noqa: E402

FX = json.loads((ROOT / "tests" / "fixtures" / "crowd_cases.json").read_text(encoding="utf-8"))
TODAY = dt.date.fromisoformat(FX["today"])


@pytest.mark.parametrize("case", FX["cases"], ids=[c["name"] for c in FX["cases"]])
def test_shared_cases(case):
    _clean, errs = validate.validate_submission(case["payload"], today=TODAY)
    assert sorted([e["path"], e["code"]] for e in errs) == case["errors"]


def _valid():
    return json.loads(json.dumps(FX["cases"][0]["payload"]))


def test_clean_copy_is_normalised_and_drops_unknown_keys():
    p = _valid()
    p["fields"][0]["value"] = "  Pe\u0000der   "
    p["evil"] = "<script>"
    p["fields"][0]["extra"] = 1
    clean, errs = validate.validate_submission(p, today=TODAY)
    assert not errs
    assert clean["fields"][0]["value"] == "Peder"
    assert "evil" not in clean and "extra" not in clean["fields"][0]


def test_attachment_limits():
    p = _valid()
    p["sources"][0]["attachment"] = {"name": "a.png", "type": "image/png", "data": base64.b64encode(b"x" * 10).decode()}
    assert not validate.validate_submission(p, today=TODAY)[1]
    p["sources"][0]["attachment"]["type"] = "text/html"
    assert [e["code"] for e in validate.validate_submission(p, today=TODAY)[1]] == ["bad_type"]
    p["sources"][0]["attachment"] = {"name": "a.pdf", "type": "application/pdf",
                                     "data": base64.b64encode(b"x" * (4 * 1024 * 1024 + 1)).decode()}
    assert [e["code"] for e in validate.validate_submission(p, today=TODAY)[1]] == ["too_big"]
    p["sources"][0]["attachment"]["data"] = "!!!not base64!!!"
    assert [e["code"] for e in validate.validate_submission(p, today=TODAY)[1]] == ["bad_data"]
    p["sources"][0]["attachment"] = {"name": "../../etc/passwd.png", "type": "image/png", "data": base64.b64encode(b"x").decode()}
    clean, errs = validate.validate_submission(p, today=TODAY)
    assert not errs and "/" not in clean["sources"][0]["attachment"]["name"]
