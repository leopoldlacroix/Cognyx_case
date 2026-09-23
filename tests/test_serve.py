"""Proposal buttons save through the local site, without a web framework."""
import json
import threading
from http.server import HTTPServer
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener, urlopen

import sqlite3


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _pending(conn) -> int:
    conn.execute(
        """
        INSERT INTO source_component (
            source_system, source_reference, normalized_reference, description,
            source_record_type, source_record_id, created_at
        ) VALUES ('PLM', 'CTRL-AIR01', 'CTRL-AIR-01', '', 'BOM_LINE', 1, '2026-01-01')
        """
    )
    source_id = conn.execute("SELECT id FROM source_component").fetchone()["id"]
    evidence = json.dumps({"relationship": "identity", "canonical_ref": "CTRL-AIR-01"})
    conn.execute(
        """
        INSERT INTO component_reconciliation (
            source_component_id, status, method, confidence, rationale, evidence_json, created_at
        ) VALUES (?, 'PENDING', 'NORMALIZED', 0.95, 'alias cluster', ?, '2026-01-01')
        """,
        (source_id, evidence),
    )
    conn.commit()
    return conn.execute("SELECT id FROM component_reconciliation").fetchone()["id"]


def test_apply_review_form_accepts_pending_row(conn):
    from app.backend.serve import apply_review_form

    recon_id = _pending(conn)
    apply_review_form(conn, {"entity": "component", "id": str(recon_id), "action": "accept"})
    status = conn.execute(
        "SELECT status FROM component_reconciliation WHERE id = ?", (recon_id,)
    ).fetchone()["status"]
    assert status == "ACCEPTED"


def test_apply_review_form_reject_requires_a_reason(conn):
    from app.backend.serve import apply_review_form
    import pytest

    recon_id = _pending(conn)
    with pytest.raises(ValueError, match="rationale"):
        apply_review_form(conn, {"entity": "component", "id": str(recon_id), "action": "reject"})


def test_post_decide_rewrites_the_page(conn, tmp_path):
    from app.backend.serve import make_handler
    from app.services.html_pages import write_site

    recon_id = _pending(conn)
    directory = tmp_path / "site"
    write_site(conn, directory)
    shared = sqlite3.connect(conn.execute("PRAGMA database_list").fetchone()[2], check_same_thread=False)
    shared.row_factory = sqlite3.Row
    server = HTTPServer(("127.0.0.1", 0), make_handler(shared, directory))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = server.server_address[1]
    try:
        body = urlencode(
            {"entity": "component", "id": str(recon_id), "action": "accept", "rationale": "same part"}
        ).encode()
        request = Request(f"http://127.0.0.1:{port}/review/decide", data=body, method="POST")
        opener = build_opener(_NoRedirect())
        try:
            response = opener.open(request)
        except HTTPError as exc:
            response = exc
        assert response.status == 303
        assert response.headers["Location"] == "/proposals.html"
        page = urlopen(f"http://127.0.0.1:{port}/proposals.html").read().decode()
        assert "ACCEPTED" in page
        assert f'value="{recon_id}"' not in page
    finally:
        server.shutdown()
        shared.close()
