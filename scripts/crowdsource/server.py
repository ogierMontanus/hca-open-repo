#!/usr/bin/env python3
"""Reference server for the crowdsourcing prototype (docs/crowdsourcing.md §5).

Serves the static mockup/ tree and a small JSON API under /api/crowd/ that
stores contributions in data/crowdsource/ (see store.py). Standard library
only, in line with the rest of the repo's scripts.

    python scripts/crowdsource/server.py
    python scripts/crowdsource/server.py --port 8765 --host 127.0.0.1

Contributors are identified by a token issued on their first submission (the
server keeps only its hash). Editors use the admin token from the
HCA_CROWD_ADMIN_TOKEN environment variable; if it is not set a random one is
generated and printed at start-up — the review endpoints are never open.

This is a prototype server: one process, plain HTTP, bound to 127.0.0.1 by
default. Put TLS and a real identity provider in front of it before exposing
it (docs/crowdsourcing.md §9).

Without this server the pages fall back to a browser-local mode
(mockup/js/crowd-store.js): contributions stay in the contributor's browser
and travel as a JSON file.
"""
from __future__ import annotations

import argparse
import hmac
import json
import os
import re
import secrets
import sys
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import export_approved  # noqa: E402
import taxonomy as tx  # noqa: E402
import validate  # noqa: E402
from register import Register  # noqa: E402
from store import Conflict, FileStore, Forbidden, NotFound  # noqa: E402

ROOT = HERE.parents[1]
MOCKUP = ROOT / "mockup"
DATA_DIR = ROOT / "data" / "crowdsource"
API = "/api/crowd/"
MAX_BODY = 8 * 1024 * 1024
SID = r"(CS-\d{8}-[0-9a-f]{6})"


class CrowdServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, addr, store: FileStore, admin_token: str, register: Register, directory: Path):
        self.store = store
        self.admin_token = admin_token
        self.register = register
        self.directory = directory
        super().__init__(addr, Handler)


class Handler(SimpleHTTPRequestHandler):
    server_version = "HCACrowd/0.1"

    def __init__(self, request, client_address, server):
        super().__init__(request, client_address, server, directory=str(server.directory))

    # ── plumbing ──────────────────────────────────────────────────────────
    def log_message(self, fmt, *args):
        if self.path.startswith(API) or os.environ.get("HCA_CROWD_VERBOSE"):
            super().log_message(fmt, *args)

    def end_headers(self):
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        if self.path.startswith(API):
            self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def _json(self, obj, status=200):
        body = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _bytes(self, data: bytes, ctype: str, filename: str | None = None):
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        if filename:
            self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.end_headers()
        self.wfile.write(data)

    def _error(self, status, code, msg, **extra):
        self._json({"error": code, "message": msg, **extra}, status)

    def _body(self):
        try:
            n = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            n = -1
        if n < 0 or n > MAX_BODY:
            raise ValueError("body too large")
        raw = self.rfile.read(n) if n else b"{}"
        try:
            return json.loads(raw.decode("utf-8") or "{}")
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise ValueError("body is not valid JSON")

    def _token(self):
        auth = self.headers.get("Authorization", "")
        return auth[7:].strip() if auth.lower().startswith("bearer ") else None

    def _is_admin(self) -> bool:
        t = self._token()
        return bool(t) and hmac.compare_digest(t, self.server.admin_token)

    # ── routing ───────────────────────────────────────────────────────────
    def do_GET(self):
        if self.path.startswith(API):
            return self._api("GET")
        return super().do_GET()

    def do_HEAD(self):
        if self.path.startswith(API):
            return self._error(405, "method", "HEAD is not supported on the API")
        return super().do_HEAD()

    def do_POST(self):
        return self._api("POST") if self.path.startswith(API) else self._error(405, "method", "POST only on the API")

    def do_PUT(self):
        return self._api("PUT") if self.path.startswith(API) else self._error(405, "method", "PUT only on the API")

    def _api(self, method):
        u = urlparse(self.path)
        route = u.path[len(API):].strip("/")
        q = {k: v[0] for k, v in parse_qs(u.query).items()}
        st: FileStore = self.server.store
        try:
            return self._dispatch(method, route, q, st)
        except NotFound:
            self._error(404, "not_found", "Findes ikke.")
        except Forbidden:
            self._error(403, "forbidden", "Det er ikke dit bidrag.")
        except Conflict as e:
            self._error(409, "conflict", str(e))
        except ValueError as e:
            self._error(400, "bad_request", str(e))
        except Exception as e:                                  # noqa: BLE001
            sys.stderr.write(f"crowd api error: {e!r}\n")
            self._error(500, "server_error", "Uventet serverfejl.")

    def _need_admin(self) -> bool:
        if not self._is_admin():
            self._error(401, "admin_required", "Redaktør-adgang kræves.")
            return False
        return True

    def _dispatch(self, method, route, q, st: FileStore):
        # public ----------------------------------------------------------
        if method == "GET" and route == "health":
            return self._json({"ok": True, "mode": "api", "schema": tx.SCHEMA,
                               "register": self.server.register.known()})
        if method == "GET" and route == "stats":
            subs = [s for s in st.all() if s["status"] != "withdrawn"]
            me = st.contributor_by_token(self._token())
            contribs = st.contributor_stats()
            return self._json({
                "submissions": len(subs),
                "pending": sum(1 for s in subs if s["status"] in ("submitted", "needs_changes")),
                "approved": sum(1 for s in subs if s["status"] in ("approved", "partially_approved")),
                "persons": len({s["person_id"] for s in subs}),
                "contributors": [c for c in contribs if c["public_credit"] and c["approved_submissions"]],
                "me": next((c for c in contribs if me and c["id"] == me["id"]), None),
                "personStatus": st.person_status(),
            })
        if method == "GET" and route == "mine":
            return self._json({"submissions": st.mine(self._token() or ""),
                               "me": next((c for c in st.contributor_stats()
                                           if (m := st.contributor_by_token(self._token())) and c["id"] == m["id"]), None)})
        if method == "POST" and route == "submissions":
            return self._create(st)
        m = re.fullmatch(r"submissions/" + SID, route)
        if m and method == "PUT":
            clean, errs = self._validated(self._body())
            if errs:
                return self._error(422, "invalid", "Bidraget har fejl.", errors=errs)
            sub = st.update(m.group(1), clean, self._token() or "")
            return self._json({"submission": FileStore.public_view(sub, owner=True)})
        m = re.fullmatch(r"submissions/" + SID + "/withdraw", route)
        if m and method == "POST":
            sub = st.withdraw(m.group(1), self._token() or "")
            return self._json({"submission": FileStore.public_view(sub, owner=True)})

        # admin -----------------------------------------------------------
        if route.startswith("admin/"):
            if not self._need_admin():
                return
            return self._admin(method, route[len("admin/"):], q, st)
        self._error(404, "not_found", "Ukendt rute.")

    def _validated(self, payload):
        clean, errs = validate.validate_submission(payload)
        if not errs and self.server.register.known() and not self.server.register.person(clean["person_id"]):
            errs.add("person_id", "unknown_person", "Person-ID'et findes ikke i registret.")
        if not errs and clean["identification"]["status"] == "duplicate" and self.server.register.known() \
                and not self.server.register.person(clean["identification"]["same_as"]):
            errs.add("identification.same_as", "unknown_person", "Det andet person-ID findes ikke i registret.")
        return clean, errs

    def _create(self, st: FileStore):
        clean, errs = self._validated(self._body())
        if errs:
            return self._error(422, "invalid", "Bidraget har fejl.", errors=errs)
        snap = self.server.register.snapshot(clean["person_id"])
        snap.update({k: clean["context"][k] for k in ("area", "doubt", "level", "gaps")})
        sub, new_token = st.create(clean, self._token(), snap)
        out = {"submission": FileStore.public_view(sub, owner=True)}
        if new_token:
            out["contributor"] = {"id": sub["contributor"]["id"], "token": new_token}
        self._json(out, 201)

    def _admin(self, method, route, q, st: FileStore):
        if method == "GET" and route == "submissions":
            subs = st.all()
            if q.get("status"):
                subs = [s for s in subs if s["status"] == q["status"]]
            if q.get("person"):
                subs = [s for s in subs if s["person_id"] == q["person"]]
            if q.get("contributor"):
                subs = [s for s in subs if s["contributor"]["id"] == q["contributor"]]
            subs.sort(key=lambda s: s["created"], reverse=True)
            return self._json({"submissions": [{k: s[k] for k in (
                "id", "person_id", "person_label", "status", "created", "updated", "revision",
                "contributor", "incorporated")} | {"identification": s["identification"]["status"],
                                                   "n_fields": len(s["fields"])} for s in subs]})
        m = re.fullmatch(r"submissions/" + SID, route)
        if m and method == "GET":
            sub = st.get(m.group(1))
            return self._json({"submission": sub, "conflicts": st.conflicts(sub),
                               "contributor": st.contributor_profile(sub["contributor"]["id"]),
                               "register": self.server.register.snapshot(sub["person_id"])})
        m = re.fullmatch(r"submissions/" + SID + "/review", route)
        if m and method == "POST":
            body = self._body()
            sub = st.review(m.group(1), body.get("reviewer", ""), body.get("decisions") or {},
                            body.get("note", ""), body.get("action", "decide"))
            return self._json({"submission": sub})
        m = re.fullmatch(r"attachments/" + SID + r"/([\w.\- ]+)", route)
        if m and method == "GET":
            from urllib.parse import unquote
            p = st.attachment_path(m.group(1), unquote(m.group(2)))
            ctype = {".pdf": "application/pdf", ".png": "image/png", ".webp": "image/webp",
                     ".gif": "image/gif"}.get(p.suffix.lower(), "image/jpeg")
            return self._bytes(p.read_bytes(), ctype)
        if method == "GET" and route == "contributors":
            return self._json({"contributors": st.contributor_stats()})
        if method == "GET" and route == "export":
            fmt = q.get("format", "tsv")
            rows = export_approved.build_rows(st, self.server.register, include_incorporated=True)
            if fmt == "json":
                return self._json({"rows": rows})
            if fmt == "tsv":
                return self._bytes(export_approved.rows_to_tsv(rows).encode("utf-8"),
                                   "text/tab-separated-values; charset=utf-8", "person_crowd_approved.tsv")
            if fmt == "xlsx":
                data = export_approved.rows_to_xlsx_bytes(rows, self.server.register)
                if data is None:
                    return self._error(501, "no_openpyxl", "openpyxl er ikke installeret på serveren.")
                return self._bytes(data, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                   "person_crowd_approved.xlsx")
            raise ValueError("format must be tsv, json or xlsx")
        self._error(404, "not_found", "Ukendt rute.")


def make_server(host="127.0.0.1", port=8765, data_dir=DATA_DIR, directory=MOCKUP, admin_token=None):
    token = admin_token or os.environ.get("HCA_CROWD_ADMIN_TOKEN") or secrets.token_urlsafe(18)
    store = FileStore(data_dir)
    srv = CrowdServer((host, port), store, token, Register(), Path(directory))
    srv.generated_token = not (admin_token or os.environ.get("HCA_CROWD_ADMIN_TOKEN"))
    return srv


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--data-dir", default=str(DATA_DIR))
    args = ap.parse_args()
    srv = make_server(args.host, args.port, args.data_dir)
    print(f"HCA crowdsourcing server — http://{args.host}:{args.port}/crowd.html")
    print(f"  data directory : {args.data_dir}")
    if srv.generated_token:
        print(f"  admin token    : {srv.admin_token}   (generated; set HCA_CROWD_ADMIN_TOKEN to fix it)")
    else:
        print("  admin token    : from HCA_CROWD_ADMIN_TOKEN")
    print("  Ctrl+C to stop")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print()


if __name__ == "__main__":
    main()
