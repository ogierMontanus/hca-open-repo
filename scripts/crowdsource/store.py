"""File-based store for crowd submissions (docs/crowdsourcing.md §5).

One JSON file per submission under data/crowdsource/submissions/, one
contributors.json, attachments under attachments/<submission id>/, and an
append-only audit.jsonl. Plain files on purpose: the project's pipeline is
CSV/JSON with no database (docs/data-model/october-pipeline.md), the files
diff in git, and the document shapes map one-to-one onto tables when the
PostgreSQL layer arrives (docs/data-model/postgresql-migration.md).

The directory is runtime state and is git-ignored (it holds contributors'
names and contact details). What an editor approves leaves it through
export_approved.py, into data/curated/ — the tracked, reviewed layer.

Thread-safe within one process (a single lock around read-modify-write; writes
are atomic via os.replace). Not safe for several server processes sharing a
directory — a deliberate prototype limit.
"""
from __future__ import annotations

import base64
import datetime as dt
import hashlib
import hmac
import json
import os
import re
import secrets
import threading
from pathlib import Path

import taxonomy as tx

SUBMISSION_ID_RE = re.compile(r"^CS-\d{8}-[0-9a-f]{6}$")


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class NotFound(KeyError):
    pass


class Forbidden(PermissionError):
    pass


class Conflict(ValueError):
    pass


class FileStore:
    def __init__(self, root):
        self.root = Path(root)
        self.sub_dir = self.root / "submissions"
        self.att_dir = self.root / "attachments"
        self.contrib_file = self.root / "contributors.json"
        self.audit_file = self.root / "audit.jsonl"
        self.lock = threading.RLock()
        self.sub_dir.mkdir(parents=True, exist_ok=True)

    # ── low level ─────────────────────────────────────────────────────────
    def _write(self, path: Path, data) -> None:
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        os.replace(tmp, path)

    def _read(self, path: Path, default=None):
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return default

    def _audit(self, actor: str, action: str, **kw) -> None:
        with open(self.audit_file, "a", encoding="utf-8") as f:
            f.write(json.dumps({"ts": now(), "actor": actor, "action": action, **kw}, ensure_ascii=False) + "\n")

    # ── contributors ──────────────────────────────────────────────────────
    def _contributors(self) -> dict:
        return self._read(self.contrib_file, {}) or {}

    def contributor_by_token(self, token: str | None):
        if not token:
            return None
        h = _hash(token)
        for cid, c in self._contributors().items():
            if hmac.compare_digest(c.get("token_hash", ""), h):
                return {"id": cid, **{k: v for k, v in c.items() if k != "token_hash"}}
        return None

    def contributor_profile(self, cid: str) -> dict:
        """Everything known about a contributor except the token hash —
        for editors only (it includes the private contact detail)."""
        c = self._contributors().get(cid) or {}
        return {k: v for k, v in c.items() if k != "token_hash"}

    def _register_contributor(self, info: dict) -> tuple[str, str]:
        token = secrets.token_urlsafe(24)
        cid = "C-" + secrets.token_hex(4)
        cs = self._contributors()
        cs[cid] = {"name": info["name"], "contact": info.get("contact", ""),
                   "affiliation": info.get("affiliation", ""), "expertise": info.get("expertise", ""),
                   "public_credit": bool(info.get("public_credit")), "created": now(),
                   "token_hash": _hash(token)}
        self._write(self.contrib_file, cs)
        self._audit(cid, "contributor_registered")
        return cid, token

    def _update_contributor(self, cid: str, info: dict) -> None:
        cs = self._contributors()
        if cid in cs:
            for k in ("name", "contact", "affiliation", "expertise"):
                if info.get(k) is not None:
                    cs[cid][k] = info[k]
            cs[cid]["public_credit"] = bool(info.get("public_credit"))
            self._write(self.contrib_file, cs)

    # ── submissions ───────────────────────────────────────────────────────
    def _path(self, sid: str) -> Path:
        if not SUBMISSION_ID_RE.match(sid or ""):
            raise NotFound(sid)
        return self.sub_dir / f"{sid}.json"

    def get(self, sid: str) -> dict:
        s = self._read(self._path(sid))
        if s is None:
            raise NotFound(sid)
        return s

    def all(self) -> list:
        out = []
        for p in sorted(self.sub_dir.glob("CS-*.json")):
            s = self._read(p)
            if s:
                out.append(s)
        return out

    def create(self, clean: dict, token: str | None, snapshot: dict | None = None) -> tuple[dict, str | None]:
        """Store a validated submission. Returns (submission, new_token); the
        token is only set when a contributor was registered by this call —
        the client keeps it, the server keeps only its hash."""
        with self.lock:
            existing = self.contributor_by_token(token)
            new_token = None
            if existing:
                cid = existing["id"]
                self._update_contributor(cid, clean["contributor"])
            else:
                cid, new_token = self._register_contributor(clean["contributor"])
            sid = "CS-" + dt.date.today().strftime("%Y%m%d") + "-" + secrets.token_hex(3)
            att_meta = self._store_attachments(sid, clean)
            sub = {
                **{k: clean[k] for k in ("schema", "person_id", "identification", "overall_confidence",
                                         "fields", "comment", "consent")},
                "id": sid,
                "person_label": (snapshot or {}).get("label") or clean["person_label"],
                "register_snapshot": snapshot or {},
                "sources": att_meta,
                "contributor": {"id": cid, "name": clean["contributor"]["name"],
                                "public_credit": clean["contributor"]["public_credit"]},
                "status": "submitted",
                "revision": 1,
                "created": now(),
                "updated": now(),
                "history": [{"ts": now(), "actor": cid, "action": "submitted"}],
                "review": None,
                "incorporated": None,
            }
            self._write(self._path(sid), sub)
            self._audit(cid, "submitted", submission=sid, person=clean["person_id"])
            return sub, new_token

    def _store_attachments(self, sid: str, clean: dict) -> list:
        sources = []
        for i, s in enumerate(clean["sources"]):
            s = dict(s)
            att = s.pop("attachment", None)
            if att:
                d = self.att_dir / sid
                d.mkdir(parents=True, exist_ok=True)
                fname = f"{i}-{att['name']}"
                if not fname.lower().endswith(tx.ATTACHMENT_TYPES[att["type"]]):
                    fname += tx.ATTACHMENT_TYPES[att["type"]]
                (d / fname).write_bytes(base64.b64decode(att["data"]))
                s["attachment"] = {"file": fname, "type": att["type"], "bytes": att["bytes"]}
            sources.append(s)
        return sources

    def update(self, sid: str, clean: dict, token: str) -> dict:
        """Contributor revises a submission that was sent back (or is still
        waiting). The previous version is kept in `history`."""
        with self.lock:
            sub = self.get(sid)
            who = self.contributor_by_token(token)
            if not who or who["id"] != sub["contributor"]["id"]:
                raise Forbidden("not your submission")
            if sub["status"] not in ("submitted", "needs_changes"):
                raise Conflict("only submitted or returned contributions can be revised")
            snapshot = {k: sub[k] for k in ("identification", "overall_confidence", "fields", "comment", "sources", "review")}
            snapshot["revision"] = sub["revision"]
            # A source keeps its earlier attachment unless a new one is sent
            # with it (matched on the citation, so a re-ordered list is safe).
            old_by_citation = {o.get("citation"): o.get("attachment") for o in sub["sources"] if o.get("attachment")}
            att_meta = self._store_attachments(sid, clean)
            for s_ in att_meta:
                if "attachment" not in s_ and old_by_citation.get(s_["citation"]):
                    s_["attachment"] = old_by_citation[s_["citation"]]
            sub.update({k: clean[k] for k in ("identification", "overall_confidence", "fields", "comment")})
            sub["sources"] = att_meta
            sub["status"] = "submitted"
            sub["revision"] += 1
            sub["updated"] = now()
            sub["review"] = None   # the earlier round stays in history[-1]["previous"]
            sub["history"].append({"ts": now(), "actor": who["id"], "action": "revised",
                                   "revision": sub["revision"], "previous": snapshot})
            self._update_contributor(who["id"], clean["contributor"])
            self._write(self._path(sid), sub)
            self._audit(who["id"], "revised", submission=sid)
            return sub

    def withdraw(self, sid: str, token: str) -> dict:
        with self.lock:
            sub = self.get(sid)
            who = self.contributor_by_token(token)
            if not who or who["id"] != sub["contributor"]["id"]:
                raise Forbidden("not your submission")
            if sub["status"] not in ("submitted", "needs_changes"):
                raise Conflict("only open contributions can be withdrawn")
            sub["status"] = "withdrawn"
            sub["updated"] = now()
            sub["history"].append({"ts": now(), "actor": who["id"], "action": "withdrawn"})
            self._write(self._path(sid), sub)
            self._audit(who["id"], "withdrawn", submission=sid)
            return sub

    def mine(self, token: str) -> list:
        who = self.contributor_by_token(token)
        if not who:
            return []
        return [self.public_view(s, owner=True) for s in self.all() if s["contributor"]["id"] == who["id"]]

    @staticmethod
    def public_view(sub: dict, owner=False) -> dict:
        """What a contributor may see of a submission: everything of their
        own, including the reviewer's notes (feedback is the point), but not
        the internal history."""
        out = {k: v for k, v in sub.items() if k not in ("history", "register_snapshot")}
        if sub.get("review"):
            out["review"] = {k: v for k, v in sub["review"].items() if k != "reviewer_id"}
        return out

    # ── review ────────────────────────────────────────────────────────────
    def review(self, sid: str, reviewer: str, decisions: dict, note: str = "",
               action: str = "decide") -> dict:
        """Record an editor's decision.

        action = "decide": `decisions` = {"fields": {"<index>": {decision,
        final_value?, final_confidence?, note?}}, "identification": {decision,
        note?}} — every field (and the identification item, for the status
        values that have no field) must be decided. The submission status
        follows: all accepted → approved, none → rejected, else partially.
        action = "request_changes": status needs_changes, `note` required.
        """
        with self.lock:
            sub = self.get(sid)
            if sub["status"] not in ("submitted", "needs_changes", "approved", "partially_approved", "rejected"):
                raise Conflict(f"cannot review a {sub['status']} contribution")
            if sub.get("incorporated"):
                raise Conflict("already incorporated into the authoritative data; reopen it explicitly first")
            reviewer = (reviewer or "").strip()[:120] or "redaktion"
            note = (note or "").strip()[:tx.LIMITS["comment"]]
            if action == "request_changes":
                if len(note) < 5:
                    raise ValueError("a note is required when asking for changes")
                sub["status"] = "needs_changes"
                sub["review"] = {"reviewer": reviewer, "decided": now(), "note": note,
                                 "fields": {}, "identification": None}
                sub["history"].append({"ts": now(), "actor": reviewer, "action": "changes_requested", "note": note})
            elif action == "decide":
                fdec = decisions.get("fields") or {}
                out_fields, accepted, total = {}, 0, 0
                for i, f in enumerate(sub["fields"]):
                    d = fdec.get(str(i)) or fdec.get(i)
                    if not isinstance(d, dict) or d.get("decision") not in tx.FIELD_DECISIONS:
                        raise ValueError(f"field {i} ({f['field']}) has no decision")
                    entry = {"decision": d["decision"], "note": str(d.get("note") or "").strip()[:tx.LIMITS["comment"]]}
                    if d["decision"] == "accept_edited":
                        fv = str(d.get("final_value") or "").strip()
                        if not fv:
                            raise ValueError(f"field {i}: accept_edited needs final_value")
                        entry["final_value"] = fv[:tx.LIMITS["longtext"]]
                    if d["decision"] in tx.ACCEPTED_DECISIONS:
                        fc = d.get("final_confidence") or f["confidence"]
                        if fc not in tx.CONFIDENCE_KEYS:
                            raise ValueError(f"field {i}: bad final_confidence")
                        entry["final_confidence"] = fc
                        accepted += 1
                    total += 1
                    out_fields[str(i)] = entry
                ident = None
                if sub["identification"]["status"] in ("duplicate", "not_individual", "unidentifiable"):
                    idd = decisions.get("identification") or {}
                    if idd.get("decision") not in ("accept", "reject"):
                        raise ValueError("the identification statement needs a decision")
                    ident = {"decision": idd["decision"], "note": str(idd.get("note") or "").strip()[:tx.LIMITS["comment"]]}
                    total += 1
                    accepted += idd["decision"] == "accept"
                if total == 0:
                    raise ValueError("nothing to decide")
                sub["status"] = ("approved" if accepted == total
                                 else "rejected" if accepted == 0 else "partially_approved")
                sub["review"] = {"reviewer": reviewer, "decided": now(), "note": note,
                                 "fields": out_fields, "identification": ident}
                sub["history"].append({"ts": now(), "actor": reviewer, "action": sub["status"], "note": note})
            else:
                raise ValueError("unknown action")
            sub["updated"] = now()
            self._write(self._path(sid), sub)
            self._audit(reviewer, "review:" + action, submission=sid, status=sub["status"])
            return sub

    def import_submission(self, obj: dict, snapshot: dict | None = None) -> str:
        """Take in a submission made in the browser-local mode (a JSON file a
        contributor sent). It is validated again from scratch, and its status
        is recomputed from the recorded decisions rather than trusted.
        Returns "added", "updated" or "unchanged"; raises ValueError."""
        import validate
        sid = obj.get("id", "")
        if not SUBMISSION_ID_RE.match(sid):
            raise ValueError(f"bad submission id {sid!r}")
        contributor = obj.get("contributor") or {}
        payload = {k: obj.get(k) for k in ("person_id", "identification", "overall_confidence", "fields", "sources", "comment")}
        payload["contributor"] = {"name": contributor.get("name", ""), "public_credit": contributor.get("public_credit", False)}
        payload["consent"] = obj.get("consent") is True
        clean, errs = validate.validate_submission(payload, allow_attachments=False)
        if errs:
            raise ValueError(f"{sid}: " + "; ".join(f"{e['path']} {e['code']}" for e in errs))
        rev = obj.get("review")
        status = obj.get("status")
        if rev and rev.get("fields") is not None and status in ("approved", "partially_approved", "rejected"):
            decided = [rev["fields"].get(str(i)) for i in range(len(clean["fields"]))]
            if any(not d or d.get("decision") not in tx.FIELD_DECISIONS for d in decided):
                raise ValueError(f"{sid}: review does not decide every field")
            for d in decided:
                if d["decision"] == "accept_edited" and not str(d.get("final_value") or "").strip():
                    raise ValueError(f"{sid}: accept_edited without final_value")
                fc = d.get("final_confidence")
                if d["decision"] in tx.ACCEPTED_DECISIONS and fc is not None and fc not in tx.CONFIDENCE_KEYS:
                    raise ValueError(f"{sid}: bad final_confidence")
            items = [d["decision"] in tx.ACCEPTED_DECISIONS for d in decided]
            if clean["identification"]["status"] in ("duplicate", "not_individual", "unidentifiable"):
                idd = rev.get("identification") or {}
                if idd.get("decision") not in ("accept", "reject"):
                    raise ValueError(f"{sid}: identification statement not decided")
                items.append(idd["decision"] == "accept")
            status = "approved" if all(items) else "rejected" if not any(items) else "partially_approved"
        elif status not in ("submitted", "needs_changes", "withdrawn"):
            status = "submitted"
            rev = None
        with self.lock:
            path = self._path(sid)
            existing = self._read(path)
            if existing and existing.get("incorporated"):
                return "unchanged"
            if existing and existing.get("revision", 1) > obj.get("revision", 1):
                return "unchanged"
            sub = {
                **{k: clean[k] for k in ("schema", "person_id", "identification", "overall_confidence", "fields", "comment", "consent")},
                "id": sid, "person_label": obj.get("person_label") or (snapshot or {}).get("label", ""),
                "register_snapshot": {**(obj.get("register_snapshot") or {}), **(snapshot or {})},
                "sources": clean["sources"],
                "contributor": {"id": str(contributor.get("id") or "C-import")[:40], "name": clean["contributor"]["name"],
                                "public_credit": clean["contributor"]["public_credit"]},
                "status": status, "revision": int(obj.get("revision", 1)),
                "created": obj.get("created") or now(), "updated": now(),
                "history": (obj.get("history") or []) + [{"ts": now(), "actor": "import", "action": "imported"}],
                "review": rev if status in ("approved", "partially_approved", "rejected", "needs_changes") else None,
                "incorporated": None,
            }
            cs = self._contributors()
            if sub["contributor"]["id"] not in cs:
                cs[sub["contributor"]["id"]] = {"name": sub["contributor"]["name"], "contact": "", "affiliation": "",
                                                "expertise": "", "public_credit": sub["contributor"]["public_credit"],
                                                "created": now(), "token_hash": ""}
                self._write(self.contrib_file, cs)
            self._write(path, sub)
            self._audit("import", "imported", submission=sid)
            return "updated" if existing else "added"

    def mark_incorporated(self, sid: str, batch: str) -> None:
        with self.lock:
            sub = self.get(sid)
            sub["incorporated"] = {"ts": now(), "batch": batch}
            sub["history"].append({"ts": now(), "actor": "export", "action": "incorporated", "batch": batch})
            self._write(self._path(sid), sub)

    def attachment_path(self, sid: str, filename: str) -> Path:
        self.get(sid)
        if not re.match(r"^[\w.\- ]+$", filename) or ".." in filename:
            raise NotFound(filename)
        p = self.att_dir / sid / filename
        if not p.is_file():
            raise NotFound(filename)
        return p

    # ── queries ───────────────────────────────────────────────────────────
    def conflicts(self, sub: dict) -> list:
        """Other live submissions on the same person that claim a different
        value for a field this one also claims — shown to the reviewer."""
        mine = {f["field"]: f["value"] for f in sub["fields"]}
        out = []
        for o in self.all():
            if o["id"] == sub["id"] or o["person_id"] != sub["person_id"]:
                continue
            if o["status"] in ("withdrawn", "rejected"):
                continue
            for f in o["fields"]:
                if f["field"] in mine and f["value"].strip().lower() != mine[f["field"]].strip().lower():
                    out.append({"submission": o["id"], "status": o["status"], "field": f["field"],
                                "value": f["value"], "confidence": f["confidence"],
                                "contributor": o["contributor"]["name"]})
        return out

    def person_status(self) -> dict:
        """{person_id: {"pending": n, "approved": n}} — public, no content."""
        out: dict = {}
        for s in self.all():
            o = out.setdefault(s["person_id"], {"pending": 0, "approved": 0})
            if s["status"] in ("submitted", "needs_changes"):
                o["pending"] += 1
            elif s["status"] in ("approved", "partially_approved"):
                o["approved"] += 1
        return out

    def contributor_stats(self) -> list:
        """Per contributor, counted from *reviewed* work. No ranking is
        implied: the list is sorted by name."""
        cs = self._contributors()
        agg: dict = {}
        subs = self.all()
        for s in subs:
            cid = s["contributor"]["id"]
            a = agg.setdefault(cid, {"submitted": 0, "approved_submissions": 0, "accepted_fields": 0,
                                     "persons": set(), "sourced": 0, "negative": 0, "doubt": 0,
                                     "areas": {}, "pending": 0})
            if s["status"] == "withdrawn":
                continue
            a["submitted"] += 1
            if s["status"] in ("submitted", "needs_changes"):
                a["pending"] += 1
            if s["status"] in ("approved", "partially_approved"):
                a["approved_submissions"] += 1
                a["persons"].add(s["person_id"])
                rev = (s.get("review") or {})
                n_acc = sum(1 for d in rev.get("fields", {}).values() if d["decision"] in tx.ACCEPTED_DECISIONS)
                a["accepted_fields"] += n_acc
                if any(x.get("result") == "stoetter" and tx.SOURCE_TYPE_BY_KEY.get(x["type"], (0,) * 5)[4] for x in s["sources"]):
                    a["sourced"] += 1
                snap = s.get("register_snapshot") or {}
                if snap.get("doubt"):
                    a["doubt"] += 1
                if snap.get("area"):
                    a["areas"][snap["area"]] = a["areas"].get(snap["area"], 0) + 1
            if s["status"] in ("approved", "partially_approved") and (s.get("review") or {}).get("identification", {}) \
                    and s["identification"]["status"] == "unidentifiable" \
                    and s["review"]["identification"]["decision"] == "accept":
                a["negative"] += 1
        out = []
        for cid, c in cs.items():
            a = agg.get(cid, {"submitted": 0, "approved_submissions": 0, "accepted_fields": 0, "persons": set(),
                              "sourced": 0, "negative": 0, "doubt": 0, "areas": {}, "pending": 0})
            badges = []
            if a["approved_submissions"] >= 1:
                badges.append("first_accepted")
            if a["sourced"] >= 5:
                badges.append("five_sourced")
            if a["negative"] >= 1:
                badges.append("negative_result")
            if a["areas"] and max(a["areas"].values()) >= 5:
                badges.append("local_expert")
            if a["doubt"] >= 1:
                badges.append("resolved_doubt")
            out.append({"id": cid, "name": c["name"], "public_credit": c.get("public_credit", False),
                        "affiliation": c.get("affiliation", ""), "expertise": c.get("expertise", ""),
                        "submitted": a["submitted"], "pending": a["pending"],
                        "approved_submissions": a["approved_submissions"],
                        "accepted_fields": a["accepted_fields"], "persons": len(a["persons"]),
                        "badges": badges})
        return sorted(out, key=lambda x: x["name"].casefold())
