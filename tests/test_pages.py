"""Workflow and check pages stay honest about what is not built yet."""
from datetime import datetime, timezone
import json
import re

from app.services.html_pages import (
    render_compare,
    render_normalize,
    render_proposals,
    render_workflow,
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _source_file(conn, file_name: str = "bom_export.csv") -> int:
    cur = conn.execute(
        """
        INSERT INTO source_file (source_system, file_name, file_hash, ingested_at)
        VALUES ('PLM', ?, 'hash-test', ?)
        """,
        (file_name, _now()),
    )
    conn.commit()
    return cur.lastrowid


def _insert_variant(conn, source_file_id: int, ref: str) -> None:
    conn.execute(
        """
        INSERT INTO plm_variant (
            source_file_id, source_row, variant_ref_raw, variant_name_raw,
            variant_ref_normalized, variant_name_normalized
        ) VALUES (?, 1, ?, ?, ?, ?)
        """,
        (source_file_id, ref, ref, ref, ref),
    )
    conn.commit()


def _insert_source_assembly(conn, source_reference: str) -> None:
    conn.execute(
        """
        INSERT INTO source_assembly (
            source_system, source_reference, normalized_reference,
            description, source_record_type, source_record_id, created_at
        ) VALUES ('PLM', ?, ?, 'assembly', 'TEST', 1, ?)
        """,
        (source_reference, source_reference, _now()),
    )
    conn.commit()


def _insert_source_component(conn, source_reference: str) -> int:
    cur = conn.execute(
        """
        INSERT INTO source_component (
            source_system, source_reference, normalized_reference,
            description, source_record_type, source_record_id, created_at
        ) VALUES ('PLM', ?, ?, 'component', 'TEST', 1, ?)
        """,
        (source_reference, source_reference, _now()),
    )
    conn.commit()
    return cur.lastrowid


def _insert_bom_line(
    conn,
    *,
    source_file_id: int,
    variant_ref: str,
    assembly_ref: str,
    component_ref: str,
    source_row: int,
) -> None:
    conn.execute(
        """
        INSERT INTO plm_bom_line (
            source_file_id, source_row,
            variant_ref_raw, assembly_ref_raw, component_ref_raw,
            quantity_raw, uom_raw,
            variant_ref_normalized, assembly_ref_normalized, component_ref_normalized,
            quantity_normalized, uom_normalized
        ) VALUES (?, ?, ?, ?, ?, '1', 'EA', ?, ?, ?, 1.0, 'EA')
        """,
        (
            source_file_id,
            source_row,
            variant_ref,
            assembly_ref,
            component_ref,
            variant_ref,
            assembly_ref,
            component_ref,
        ),
    )
    conn.commit()


def _insert_note(
    conn,
    *,
    source_file_id: int,
    object_reference: str,
    note_text: str,
    source_row: int,
) -> None:
    conn.execute(
        """
        INSERT INTO engineering_note (
            source_file_id, source_row, object_reference_raw, object_type,
            language, author, date, note_text
        ) VALUES (?, ?, ?, 'component', 'en', 'N-064', '2026-03-03', ?)
        """,
        (source_file_id, source_row, object_reference, note_text),
    )
    conn.commit()


def test_workflow_says_canonical_model_is_missing(conn):
    page = render_workflow(conn)
    assert "Canonical model" in page
    assert "Not yet" in page
    assert "Interactive workbench" in page
    assert "ground_truth" not in page


def test_normalize_page_shows_raw_and_cleaned_reference(conn):
    conn.execute(
        "INSERT INTO source_file (source_system, file_name, file_hash, ingested_at) VALUES ('PLM', 'x.csv', 'abc', '2026-01-01')"
    )
    source_file_id = conn.execute("SELECT id FROM source_file").fetchone()["id"]
    conn.execute(
        """
        INSERT INTO plm_bom_line (
            source_file_id, source_row, variant_ref_raw, assembly_ref_raw, component_ref_raw,
            variant_ref_normalized, assembly_ref_normalized, component_ref_normalized,
            uom_raw, uom_normalized
        ) VALUES (?, 1, 'REGIO-STD', 'HVAC-M01', 'CTRL-AIR01', 'REGIO-STD', 'HVAC-M01', 'CTRL-AIR-01', 'pcs', 'EA')
        """,
        (source_file_id,),
    )
    conn.commit()
    page = render_normalize(conn)
    assert "CTRL-AIR01" in page
    assert "CTRL-AIR-01" in page
    assert "pcs" in page
    assert "EA" in page


def test_proposals_page_leaves_canonical_id_empty(conn):
    conn.execute(
        "INSERT INTO source_file (source_system, file_name, file_hash, ingested_at) VALUES ('PLM', 'x.csv', 'abc', '2026-01-01')"
    )
    source_file_id = conn.execute("SELECT id FROM source_file").fetchone()["id"]
    conn.execute(
        """
        INSERT INTO source_component (
            source_system, source_reference, normalized_reference, description,
            source_record_type, source_record_id, created_at
        ) VALUES ('PLM', 'CTRL-AIR01', 'CTRL-AIR-01', '', 'BOM_LINE', 1, '2026-01-01')
        """
    )
    source_id = conn.execute("SELECT id FROM source_component").fetchone()["id"]
    evidence = {
        "relationship": "identity",
        "canonical_ref": "CTRL-AIR-01",
        "cluster_members": [{"source_reference": "CTRL-AIR-01"}],
    }
    conn.execute(
        """
        INSERT INTO component_reconciliation (
            source_component_id, status, method, confidence, rationale, evidence_json, created_at
        ) VALUES (?, 'PENDING', 'NORMALIZED', 0.95, 'alias cluster', ?, '2026-01-01')
        """,
        (source_id, json.dumps(evidence)),
    )
    conn.commit()
    _ = source_file_id
    page = render_proposals(conn)
    assert "CTRL-AIR-01" in page
    assert "PENDING" in page
    assert 'action="/review/decide"' in page
    assert "Accept" in page
    # Canonical tables exist (Phase 3); empty component_id still shows as em dash.
    assert "canonical table exists" in page or "no canonical table" in page
    assert "—" in page


def test_compare_page_std_nordic_default_and_high_overlap(conn):
    """STD/NORDIC opens first; ratio and high-overlap class; file/row on blocked row."""
    from app.services.canonicalization import build_canonical_model

    sf = _source_file(conn, "bom_export.csv")
    _insert_variant(conn, sf, "REGIO-STD")
    _insert_variant(conn, sf, "REGIO-NORDIC")
    _insert_source_assembly(conn, "HVAC-M01")
    _insert_source_component(conn, "CTRL-AIR-01")
    _insert_source_component(conn, "FAN-NORDIC-01")
    _insert_bom_line(
        conn,
        source_file_id=sf,
        variant_ref="REGIO-STD",
        assembly_ref="HVAC-M01",
        component_ref="CTRL-AIR-01",
        source_row=1,
    )
    _insert_bom_line(
        conn,
        source_file_id=sf,
        variant_ref="REGIO-NORDIC",
        assembly_ref="HVAC-M01",
        component_ref="CTRL-AIR-01",
        source_row=2,
    )
    _insert_bom_line(
        conn,
        source_file_id=sf,
        variant_ref="REGIO-NORDIC",
        assembly_ref="HVAC-M01",
        component_ref="FAN-NORDIC-01",
        source_row=3,
    )
    _insert_note(
        conn,
        source_file_id=sf,
        object_reference="CTRL-AIR-01",
        note_text="Operating voltage listed as 24 V DC and also 48 V DC — conflict.",
        source_row=64,
    )

    build_canonical_model(conn)
    page = render_compare(conn)

    assert "REGIO-STD" in page
    assert "REGIO-NORDIC" in page
    assert "4 · Compare" in page
    assert "overlap 0.5" in page
    assert "high-overlap" in page
    assert "bom_export.csv" in page
    assert "64" in page or "row 1" in page or "row 2" in page
    assert "24 V DC" in page and "48 V DC" in page

    visible = [
        m
        for m in re.finditer(
            r'<section class="pair-section([^"]*)"[^>]*id="([^"]+)"',
            page,
        )
    ]
    assert visible
    not_hidden = [m for m in visible if "hidden" not in m.group(1)]
    assert len(not_hidden) == 1
    assert not_hidden[0].group(2) == "pair-REGIO-STD-REGIO-NORDIC"


def test_compare_page_lexicographic_default_without_std_nordic(conn):
    """Without REGIO-STD/NORDIC, the first lexicographic pair is visible."""
    from app.services.canonicalization import build_canonical_model

    sf = _source_file(conn, "fixture_bom.csv")
    _insert_variant(conn, sf, "REGIO-COMFORT")
    _insert_variant(conn, sf, "REGIO-EXPORT")
    _insert_source_assembly(conn, "DOOR-M01")
    _insert_source_component(conn, "CTRL-DOOR-01")
    _insert_bom_line(
        conn,
        source_file_id=sf,
        variant_ref="REGIO-COMFORT",
        assembly_ref="DOOR-M01",
        component_ref="CTRL-DOOR-01",
        source_row=10,
    )
    _insert_bom_line(
        conn,
        source_file_id=sf,
        variant_ref="REGIO-EXPORT",
        assembly_ref="DOOR-M01",
        component_ref="CTRL-DOOR-01",
        source_row=11,
    )

    build_canonical_model(conn)
    page = render_compare(conn)

    assert "REGIO-COMFORT" in page
    assert "REGIO-EXPORT" in page
    assert "fixture_bom.csv" in page
    assert "10" in page

    visible = [
        m
        for m in re.finditer(
            r'<section class="pair-section([^"]*)"[^>]*id="([^"]+)"',
            page,
        )
    ]
    not_hidden = [m for m in visible if "hidden" not in m.group(1)]
    assert len(not_hidden) == 1
    assert not_hidden[0].group(2) == "pair-REGIO-COMFORT-REGIO-EXPORT"


def test_report_data_issue_includes_source_file_and_row(conn):
    """Rendered data-issue cards name the fixture file and source row."""
    from app.services.report import build_snapshot, render_report_html

    sf = _source_file(conn, "bom_export.csv")
    conn.execute(
        """
        INSERT INTO quarantine (source_file_id, source_row, raw_data, rejection_reason, created_at)
        VALUES (?, 32, ?, 'Unparseable quantity', ?)
        """,
        (
            sf,
            json.dumps({"component_ref": "HVAC-FILTER-01", "quantity": "one"}),
            _now(),
        ),
    )
    conn.commit()

    page = render_report_html(build_snapshot(conn))
    assert "Already reused" in page
    assert "Worth a look" in page
    assert "Intentional differences" in page
    assert "Blocked" in page
    assert "Data issues" in page
    assert "bom_export.csv" in page
    assert "32" in page
    assert "ground_truth" not in page


def test_analyze_compare_writes_json_with_default_pair(conn, db_path, tmp_path, monkeypatch):
    """analyze compare writes compare.json with default_pair and assembly refs."""
    from app.backend import cli as cli_mod
    from app.services.canonicalization import build_canonical_model

    sf = _source_file(conn, "bom_export.csv")
    _insert_variant(conn, sf, "REGIO-STD")
    _insert_variant(conn, sf, "REGIO-NORDIC")
    _insert_source_assembly(conn, "HVAC-M01")
    _insert_source_component(conn, "CTRL-AIR-01")
    _insert_bom_line(
        conn,
        source_file_id=sf,
        variant_ref="REGIO-STD",
        assembly_ref="HVAC-M01",
        component_ref="CTRL-AIR-01",
        source_row=1,
    )
    _insert_bom_line(
        conn,
        source_file_id=sf,
        variant_ref="REGIO-NORDIC",
        assembly_ref="HVAC-M01",
        component_ref="CTRL-AIR-01",
        source_row=2,
    )
    build_canonical_model(conn)
    conn.commit()
    conn.close()

    processed = tmp_path / "processed"
    processed.mkdir()
    monkeypatch.setattr(cli_mod, "PROCESSED_DIR", processed)
    monkeypatch.setattr(
        "sys.argv",
        ["cli", "analyze", "compare", "--db", db_path],
    )
    cli_mod.main()

    out = processed / "compare.json"
    assert out.is_file()
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["default_pair"] == ["REGIO-STD", "REGIO-NORDIC"]
    assert payload["pairs"]
    assembly_refs = [
        a["assembly_ref"]
        for pair in payload["pairs"]
        for a in pair.get("assemblies") or []
    ]
    assert "HVAC-M01" in assembly_refs
    assert "ground_truth" not in out.read_text(encoding="utf-8")
