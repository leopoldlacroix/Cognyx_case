"""Local site so proposal buttons can save a decision.

No web framework. Bind to localhost only. Static files still live in data/processed/.
"""
from __future__ import annotations

import sqlite3
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Dict
from urllib.parse import parse_qs, unquote, urlparse


def apply_review_form(conn: sqlite3.Connection, form: Dict[str, str]) -> None:
    """Save one Accept, Reject, or Redirect from a proposals-page form."""
    from app.services.review import decide_reconciliation

    entity = (form.get("entity") or "component").strip()
    action = (form.get("action") or "").strip()
    raw_id = (form.get("id") or "").strip()
    if not raw_id.isdigit():
        raise ValueError("Proposal id is missing")
    rationale = (form.get("rationale") or "").strip() or None
    redirect_raw = (form.get("redirect_to") or "").strip()
    if redirect_raw and not redirect_raw.isdigit():
        raise ValueError("Redirect target must be a source id number")
    redirect_source_id = int(redirect_raw) if redirect_raw else None
    decide_reconciliation(
        conn,
        entity,
        int(raw_id),
        action,
        rationale=rationale,
        redirect_source_id=redirect_source_id,
        decided_by="operator",
    )


def _safe_file(directory: Path, url_path: str) -> Path | None:
    name = unquote(url_path).lstrip("/") or "workflow.html"
    if name.endswith("/"):
        name += "workflow.html"
    if "/" in name or "\\" in name or name.startswith("."):
        return None
    path = (directory / name).resolve()
    if path.parent != directory.resolve() or not path.is_file():
        return None
    if path.suffix not in {".html", ".json"}:
        return None
    return path


def _error_page(message: str) -> bytes:
    from html import escape

    body = (
        "<!DOCTYPE html><html><body>"
        f"<p>Could not save the decision: {escape(message)}</p>"
        '<p><a href="/proposals.html">Back to proposals</a></p>'
        "</body></html>"
    )
    return body.encode("utf-8")


def make_handler(conn: sqlite3.Connection, directory: Path):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            target = _safe_file(directory, urlparse(self.path).path)
            if target is None:
                self.send_error(404)
                return
            data = target.read_bytes()
            kind = "application/json" if target.suffix == ".json" else "text/html; charset=utf-8"
            self.send_response(200)
            self.send_header("Content-Type", kind)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_POST(self) -> None:
            if urlparse(self.path).path != "/review/decide":
                self.send_error(404)
                return
            length = int(self.headers.get("Content-Length", "0") or "0")
            if length > 100_000:
                self.send_error(413)
                return
            raw = self.rfile.read(length).decode("utf-8", errors="replace")
            parsed = parse_qs(raw, keep_blank_values=True)
            form = {key: values[0] for key, values in parsed.items()}
            try:
                apply_review_form(conn, form)
            except ValueError as exc:
                payload = _error_page(str(exc))
                self.send_response(400)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)
                return
            from app.services.html_pages import write_site

            write_site(conn, directory)
            self.send_response(303)
            self.send_header("Location", "/proposals.html")
            self.end_headers()

        def log_message(self, fmt: str, *args) -> None:
            print(f"[serve] {self.address_string()} {fmt % args}")

    return Handler


def serve_site(conn: sqlite3.Connection, directory: Path, port: int = 8765) -> None:
    """Rewrite the pages, then serve them on localhost until interrupted."""
    from app.services.html_pages import write_site

    directory.mkdir(parents=True, exist_ok=True)
    write_site(conn, directory)
    handler = make_handler(conn, directory)
    server = HTTPServer(("127.0.0.1", port), handler)
    url = f"http://127.0.0.1:{port}/proposals.html"
    print(f"Decisions can be saved at {url}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        server.server_close()
