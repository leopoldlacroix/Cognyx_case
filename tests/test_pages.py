"""Workflow and check pages stay honest about what is not built yet."""
import json

from app.services.html_pages import render_normalize, render_proposals, render_workflow


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
    # Canonical tables exist (Phase 3); empty component_id still shows as em dash.
    assert "canonical table exists" in page or "no canonical table" in page
    assert "—" in page
