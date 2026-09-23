"""Pilot snapshot report: sections a client can read, and a single HTML page."""
import json
from pathlib import Path

from app.services.report import build_snapshot, render_report_html, write_report


def test_snapshot_lists_shared_part_and_escapes_html(conn):
    conn.execute(
        "INSERT INTO source_file (source_system, file_name, file_hash, ingested_at) VALUES ('PLM', 'x.csv', 'abc', '2026-01-01')"
    )
    source_file_id = conn.execute("SELECT id FROM source_file").fetchone()["id"]
    conn.execute(
        """
        INSERT INTO plm_variant (
            source_file_id, source_row, variant_ref_raw, variant_name_raw, variant_ref_normalized
        ) VALUES (?, 1, 'REGIO-STD', 'Regional Standard', 'REGIO-STD'),
                 (?, 2, 'REGIO-EXPORT', 'Regional Export', 'REGIO-EXPORT')
        """,
        (source_file_id, source_file_id),
    )
    conn.execute(
        """
        INSERT INTO plm_bom_line (
            source_file_id, source_row, variant_ref_raw, assembly_ref_raw, component_ref_raw,
            variant_ref_normalized, assembly_ref_normalized, component_ref_normalized
        ) VALUES
            (?, 1, 'REGIO-STD', 'HVAC-M01', 'CTRL-AIR-01', 'REGIO-STD', 'HVAC-M01', 'CTRL-AIR-01'),
            (?, 2, 'REGIO-EXPORT', 'HVAC-EXP01', 'CTRL-AIR01', 'REGIO-EXPORT', 'HVAC-EXP01', 'CTRL-AIR-01')
        """,
        (source_file_id, source_file_id),
    )
    conn.execute(
        """
        INSERT INTO quarantine (source_file_id, source_row, raw_data, rejection_reason, created_at)
        VALUES (?, 31, ?, 'Unparseable quantity', '2026-01-01')
        """,
        (source_file_id, json.dumps({"component_ref": "HVAC-FILTER-01", "quantity": "one"})),
    )
    conn.commit()

    snapshot = build_snapshot(conn)
    assert snapshot["already_reused"][0]["ref"] == "CTRL-AIR-01"
    assert "CTRL-AIR01" in snapshot["already_reused"][0]["explanation"]
    assert any("HVAC-FILTER-01" in item["title"] for item in snapshot["data_issues"])
    assert "ground_truth" not in json.dumps(snapshot)

    page = render_report_html(
        {
            **snapshot,
            "title": "Safe <script>",
        }
    )
    assert "<script>" not in page
    assert "Safe &lt;script&gt;" in page
    assert "CTRL-AIR-01" in page


def test_write_report_creates_html(conn, tmp_path: Path):
    conn.execute(
        "INSERT INTO source_file (source_system, file_name, file_hash, ingested_at) VALUES ('PLM', 'x.csv', 'abc', '2026-01-01')"
    )
    conn.commit()
    output = tmp_path / "report.html"
    written = write_report(conn, output)
    assert written == output
    text = output.read_text(encoding="utf-8")
    assert "Which parts are reused" in text
    assert "ground_truth" not in text
