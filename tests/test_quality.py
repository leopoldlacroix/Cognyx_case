"""
Tests for blockers, data-quality issues, and CLI reports (Plan 03-05).
"""
from datetime import datetime, timezone
import json
import sqlite3
from pathlib import Path

import pytest

N064_TEXT = (
    "One legacy BOM extract lists 48V DC, but the current engineering specification "
    "and ERP material are 24V DC. Flag for review rather than silently normalizing."
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _source_file(conn, system: str = "PLM", name: str = "test.csv") -> int:
    cur = conn.execute(
        """
        INSERT INTO source_file (source_system, file_name, file_hash, ingested_at)
        VALUES (?, ?, 'hash-q', ?)
        """,
        (system, name, _now()),
    )
    conn.commit()
    return cur.lastrowid


def _insert_note(
    conn,
    *,
    source_file_id: int,
    object_reference: str,
    note_text: str,
    source_row: int = 64,
    author: str = "N-064",
) -> int:
    cur = conn.execute(
        """
        INSERT INTO engineering_note (
            source_file_id, source_row, object_reference_raw, object_type,
            language, author, date, note_text
        ) VALUES (?, ?, ?, 'component', 'en', ?, '2026-05-12', ?)
        """,
        (source_file_id, source_row, object_reference, author, note_text),
    )
    conn.commit()
    return cur.lastrowid


def _insert_assembly(
    conn,
    *,
    source_file_id: int,
    assembly_ref: str,
    lifecycle: str,
    variant_ref: str = "REGIO-EXPORT",
    source_row: int = 1,
) -> int:
    cur = conn.execute(
        """
        INSERT INTO plm_assembly (
            source_file_id, source_row, assembly_ref_raw, assembly_description_raw,
            variant_ref_raw, revision_raw, lifecycle_raw,
            assembly_ref_normalized, variant_ref_normalized
        ) VALUES (?, ?, ?, ?, ?, 'B', ?, ?, ?)
        """,
        (
            source_file_id,
            source_row,
            assembly_ref,
            "Passenger counting assembly",
            variant_ref,
            lifecycle,
            assembly_ref,
            variant_ref,
        ),
    )
    conn.commit()
    return cur.lastrowid


def _insert_material(
    conn,
    *,
    source_file_id: int,
    material_id: str,
    status: str,
    description: str = "legacy",
    source_row: int = 1,
) -> int:
    cur = conn.execute(
        """
        INSERT INTO erp_material (
            source_file_id, source_row, material_id_raw, description_raw,
            material_type_raw, base_unit_raw, supplier_id_raw, category_raw,
            status_raw, cost_raw
        ) VALUES (?, ?, ?, ?, 'COMPONENT', 'EA', 'SUP-001', 'HVAC', ?, '100')
        """,
        (source_file_id, source_row, material_id, description, status),
    )
    conn.commit()
    return cur.lastrowid


def _insert_bom(
    conn,
    *,
    source_file_id: int,
    variant_ref: str,
    assembly_ref: str,
    component_ref: str,
    component_ref_normalized: str | None = None,
    uom_raw: str = "EA",
    uom_normalized: str = "EA",
    source_row: int = 1,
    quantity_raw: str = "1",
) -> int:
    cur = conn.execute(
        """
        INSERT INTO plm_bom_line (
            source_file_id, source_row, variant_ref_raw, assembly_ref_raw,
            component_ref_raw, quantity_raw, uom_raw,
            variant_ref_normalized, assembly_ref_normalized, component_ref_normalized,
            uom_normalized, quantity_normalized
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1.0)
        """,
        (
            source_file_id,
            source_row,
            variant_ref,
            assembly_ref,
            component_ref,
            quantity_raw,
            uom_raw,
            variant_ref,
            assembly_ref,
            component_ref_normalized or component_ref,
            uom_normalized,
        ),
    )
    conn.commit()
    return cur.lastrowid


def _insert_quarantine(
    conn,
    *,
    source_file_id: int,
    source_row: int,
    raw_data: dict,
    reason: str,
) -> int:
    cur = conn.execute(
        """
        INSERT INTO quarantine (source_file_id, source_row, raw_data, rejection_reason, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (source_file_id, source_row, json.dumps(raw_data), reason, _now()),
    )
    conn.commit()
    return cur.lastrowid


def _insert_warning(
    conn,
    *,
    warning_type: str,
    source_row_id: int = 1,
    message: str = "warn",
) -> None:
    conn.execute(
        """
        INSERT INTO warnings (source_table, source_row_id, warning_type, warning_message, created_at)
        VALUES ('plm_bom_line', ?, ?, ?, ?)
        """,
        (source_row_id, warning_type, message, _now()),
    )
    conn.commit()


# ---------------------------------------------------------------------------
# extract_voltage_facts
# ---------------------------------------------------------------------------


def test_extract_voltage_facts_normalizes_and_dedupes():
    from app.services.quality import extract_voltage_facts

    assert extract_voltage_facts("") == set()
    assert extract_voltage_facts(None) == set()
    assert extract_voltage_facts("48V DC and 24 V") == {"48 V DC", "24 V DC"}
    assert extract_voltage_facts("24V") == {"24 V DC"}
    assert extract_voltage_facts("24 V DC") == {"24 V DC"}
    assert extract_voltage_facts("24V and 24 V DC") == {"24 V DC"}
    assert extract_voltage_facts(N064_TEXT) == {"24 V DC", "48 V DC"}


# ---------------------------------------------------------------------------
# blockers — conflicting evidence (SCEN-G)
# ---------------------------------------------------------------------------


def test_blockers_conflicting_voltage_from_n064_style_note(conn):
    from app.services.quality import blockers

    sf = _source_file(conn, "ENGINEERING", "technical_notes.csv")
    _insert_note(conn, source_file_id=sf, object_reference="CTRL-AIR-01", note_text=N064_TEXT)

    rows = blockers(conn)
    conflicts = [r for r in rows if r["issue_type"] == "conflicting_evidence"]
    assert len(conflicts) == 1
    row = conflicts[0]
    assert row["entity_ref"] == "CTRL-AIR-01"
    assert row["attribute"] == "operating_voltage"
    assert row["values"] == ["24 V DC", "48 V DC"]
    assert "kept" in row["explanation"].lower() or "both" in row["explanation"].lower()
    assert "winner" not in row["explanation"].lower()
    # Do not attach MAT-10001
    blob = json.dumps(row)
    assert "MAT-10001" not in blob

    facts = conn.execute(
        "SELECT attribute, value, status, source_type, source_id FROM technical_fact"
    ).fetchall()
    assert len(facts) >= 2
    assert all(f["status"] == "CONFLICTING" for f in facts if f["attribute"] == "operating_voltage")
    values = sorted(f["value"] for f in facts if f["attribute"] == "operating_voltage")
    assert values == ["24 V DC", "48 V DC"]


def test_blockers_single_voltage_is_not_a_conflict(conn):
    from app.services.quality import blockers

    sf = _source_file(conn, "ENGINEERING", "notes.csv")
    _insert_note(
        conn,
        source_file_id=sf,
        object_reference="CTRL-AIR-01",
        note_text="Supply is 24V DC only.",
        author="N-001",
    )
    rows = blockers(conn)
    conflicts = [
        r
        for r in rows
        if r["issue_type"] == "conflicting_evidence" and r["entity_ref"] == "CTRL-AIR-01"
    ]
    assert conflicts == []


def test_blockers_idempotent_facts(conn):
    from app.services.quality import blockers

    sf = _source_file(conn, "ENGINEERING", "notes.csv")
    _insert_note(conn, source_file_id=sf, object_reference="CTRL-AIR-01", note_text=N064_TEXT)

    blockers(conn)
    first = conn.execute("SELECT COUNT(*) AS n FROM technical_fact").fetchone()["n"]
    blockers(conn)
    second = conn.execute("SELECT COUNT(*) AS n FROM technical_fact").fetchone()["n"]
    assert first == second
    assert first >= 2


# ---------------------------------------------------------------------------
# blockers — lifecycle (SCEN-J)
# ---------------------------------------------------------------------------


def test_blockers_lifecycle_mismatch_prototype_vs_released(conn):
    from app.services.quality import blockers

    sf = _source_file(conn)
    _insert_assembly(
        conn, source_file_id=sf, assembly_ref="PAX-COUNT-MOD-E", lifecycle="Prototype", source_row=1
    )
    _insert_assembly(
        conn,
        source_file_id=sf,
        assembly_ref="PCOUNT-M08",
        lifecycle="Released",
        variant_ref="REGIO-STD",
        source_row=2,
    )

    rows = blockers(conn)
    mismatches = [r for r in rows if r["issue_type"] == "lifecycle_mismatch"]
    assert len(mismatches) == 1
    expl = mismatches[0]["explanation"]
    assert "Prototype" in expl
    assert "Released" in expl
    assert "Obsolete" not in expl
    assert "OBSOLETE" not in expl
    assert mismatches[0]["entity_ref"] == "PAX-COUNT-MOD-E"


def test_blockers_erp_obsolete_separate_from_assembly(conn):
    from app.services.quality import blockers

    sf_plm = _source_file(conn, "PLM", "assembly_master.csv")
    sf_erp = _source_file(conn, "ERP", "material_master.csv")
    _insert_assembly(
        conn, source_file_id=sf_plm, assembly_ref="PAX-COUNT-MOD-E", lifecycle="Prototype"
    )
    _insert_assembly(
        conn,
        source_file_id=sf_plm,
        assembly_ref="PASSCOUNT-MOD-01",
        lifecycle="Released",
        variant_ref="REGIO-COMFORT",
        source_row=2,
    )
    _insert_material(conn, source_file_id=sf_erp, material_id="MAT-20001", status="OBSOLETE")
    _insert_material(
        conn, source_file_id=sf_erp, material_id="MAT-20002", status="OBSOLETE", source_row=2
    )
    _insert_material(
        conn, source_file_id=sf_erp, material_id="MAT-20004", status="OBSOLETE", source_row=3
    )
    _insert_material(
        conn,
        source_file_id=sf_erp,
        material_id="MAT-10001",
        status="ACTIVE",
        source_row=4,
        description="active",
    )

    rows = blockers(conn)
    erp = [r for r in rows if r["issue_type"] == "erp_lifecycle"]
    refs = {r["entity_ref"] for r in erp}
    assert "MAT-20001" in refs
    assert "MAT-20002" in refs
    assert "MAT-20004" in refs
    assert "MAT-10001" not in refs
    # Not merged into the Prototype assembly blocker
    for r in erp:
        assert "Prototype" not in r.get("explanation", "")
        assert r["entity_ref"].startswith("MAT-")


# ---------------------------------------------------------------------------
# data_quality_issues (SCEN-I)
# ---------------------------------------------------------------------------


def test_data_quality_invalid_quantity_from_quarantine(conn):
    from app.services.quality import data_quality_issues

    sf = _source_file(conn)
    _insert_quarantine(
        conn,
        source_file_id=sf,
        source_row=32,
        raw_data={
            "plm_row_id": "BOM-0031",
            "component_ref": "HVAC-FILTER-01",
            "quantity": "one",
        },
        reason="Unparseable quantity: one",
    )
    # Must not also appear as a BOM line
    result = data_quality_issues(conn)
    issues = result["issues"]
    invalid = [i for i in issues if i["issue_type"] == "invalid_quantity"]
    assert len(invalid) == 1
    assert "BOM-0031" in json.dumps(invalid[0]) or "one" in json.dumps(invalid[0])
    assert "quantity" in invalid[0]["explanation"].lower() or "quantity" in (
        invalid[0].get("detail") or ""
    ).lower()


def test_data_quality_duplicate_bom_key_after_alias(conn):
    from app.services.quality import data_quality_issues

    sf = _source_file(conn)
    _insert_bom(
        conn,
        source_file_id=sf,
        variant_ref="REGIO-STD",
        assembly_ref="HVAC-M01",
        component_ref="CTRL-AIR-01",
        component_ref_normalized="CTRL-AIR-01",
        source_row=1,
    )
    # same normalized key via alias CTRL-AIR01 → CTRL-AIR-01
    bom2 = _insert_bom(
        conn,
        source_file_id=sf,
        variant_ref="REGIO-STD",
        assembly_ref="HVAC-M01",
        component_ref="CTRL-AIR01",
        component_ref_normalized="CTRL-AIR-01",
        source_row=301,
        uom_raw="EA",
    )
    result = data_quality_issues(conn)
    dups = [i for i in result["issues"] if i["issue_type"] == "duplicate_bom_key"]
    assert len(dups) == 1
    refs_blob = json.dumps(dups[0]["refs"])
    assert str(bom2) in refs_blob or "CTRL-AIR" in refs_blob
    assert "CTRL-AIR-01" in json.dumps(dups[0]) or "CTRL-AIR01" in json.dumps(dups[0])


def test_data_quality_uom_aliased_not_conflict(conn):
    from app.services.quality import data_quality_issues

    sf = _source_file(conn)
    _insert_bom(
        conn,
        source_file_id=sf,
        variant_ref="REGIO-STD",
        assembly_ref="HVAC-M01",
        component_ref="FILTER-HVAC-01",
        uom_raw="pcs",
        uom_normalized="EA",
        source_row=1,
    )
    _insert_bom(
        conn,
        source_file_id=sf,
        variant_ref="REGIO-COMFORT",
        assembly_ref="HVAC-M02",
        component_ref="FILTER-HVAC-01",
        uom_raw="EA",
        uom_normalized="EA",
        source_row=2,
    )
    result = data_quality_issues(conn)
    aliased = [i for i in result["issues"] if i["issue_type"] == "uom_aliased"]
    assert len(aliased) == 1
    assert "conflict" not in aliased[0]["issue_type"]
    assert "EA" in json.dumps(aliased[0])


def test_data_quality_warning_summary_marks_mapping_noise(conn):
    from app.services.quality import data_quality_issues

    for i in range(3):
        _insert_warning(conn, warning_type="missing_description", source_row_id=i + 1)
    _insert_warning(conn, warning_type="empty_supplier", source_row_id=10)
    _insert_warning(conn, warning_type="unknown_uom", source_row_id=11)

    result = data_quality_issues(conn)
    assert "issues" in result
    assert "ingestion_warning_summary" in result
    summary = result["ingestion_warning_summary"]
    assert summary["missing_description"]["count"] == 3
    assert summary["missing_description"]["mapping_noise"] is True
    assert summary["empty_supplier"]["count"] == 1
    assert summary["empty_supplier"]["mapping_noise"] is True
    assert summary["unknown_uom"]["count"] == 1
    # Not one report row per warning
    warn_rows = [
        i
        for i in result["issues"]
        if i["issue_type"] in ("missing_description", "empty_supplier")
    ]
    assert warn_rows == []


# ---------------------------------------------------------------------------
# Ingestion: BOM description + line_status columns
# ---------------------------------------------------------------------------


def test_ingest_maps_component_description_and_line_status(conn, tmp_path):
    from app.services.ingestion import ingest_csv_file

    csv_path = tmp_path / "bom_export.csv"
    csv_path.write_text(
        "plm_row_id,variant_ref,assembly_ref,component_ref,component_description,"
        "quantity,uom,supplier_name,line_status\n"
        "BOM-1,REGIO-STD,HVAC-M01,CTRL-AIR-01,HVAC control unit,1,EA,Siemens,Released\n"
    )
    stats = ingest_csv_file(
        conn,
        csv_path,
        "PLM",
        "plm_bom_line",
        {
            "variant_ref": "variant_ref_raw",
            "assembly_ref": "assembly_ref_raw",
            "component_ref": "component_ref_raw",
            "component_description": "description_raw",
            "quantity": "quantity_raw",
            "uom": "uom_raw",
            "supplier_name": "supplier_raw",
            "line_status": "line_status_raw",
        },
        {"variant_ref", "assembly_ref", "component_ref"},
    )
    assert stats["quarantined_count"] == 0
    row = conn.execute("SELECT description_raw, line_status_raw FROM plm_bom_line").fetchone()
    assert row["description_raw"] == "HVAC control unit"
    assert row["line_status_raw"] == "Released"


# ---------------------------------------------------------------------------
# CLI — review + analyze (tmp_path only, no real CSV folder)
# ---------------------------------------------------------------------------


def test_cli_analyze_blockers_writes_json(conn, db_path, tmp_path, monkeypatch):
    from app.backend import cli as cli_mod

    sf = _source_file(conn, "ENGINEERING", "notes.csv")
    _insert_note(conn, source_file_id=sf, object_reference="CTRL-AIR-01", note_text=N064_TEXT)
    conn.close()

    processed = tmp_path / "processed"
    processed.mkdir()
    monkeypatch.setattr(cli_mod, "PROCESSED_DIR", processed)

    monkeypatch.setattr(
        "sys.argv",
        ["cli", "analyze", "blockers", "--db", db_path],
    )
    cli_mod.main()

    out = processed / "blockers.json"
    assert out.is_file()
    data = json.loads(out.read_text())
    assert isinstance(data, list)
    assert any(r.get("issue_type") == "conflicting_evidence" for r in data)


def test_cli_review_list_prints_count(conn, db_path, monkeypatch, capsys):
    from app.backend import cli as cli_mod

    cur = conn.execute(
        """
        INSERT INTO source_component (
            source_system, source_reference, normalized_reference,
            description, source_record_type, source_record_id, created_at
        ) VALUES ('PLM', 'CTRL-AIR01', 'CTRL-AIR-01', 'x', 'TEST', 1, ?)
        """,
        (_now(),),
    )
    source_id = cur.lastrowid
    evidence = {"relationship": "identity", "review_needed": True}
    conn.execute(
        """
        INSERT INTO component_reconciliation (
            source_component_id, component_id, status, method, confidence,
            rationale, evidence_json, created_at
        ) VALUES (?, NULL, 'PENDING', 'NORMALIZED', 0.95, 'alias', ?, ?)
        """,
        (source_id, json.dumps(evidence), _now()),
    )
    conn.commit()
    conn.close()

    monkeypatch.setattr(
        "sys.argv",
        ["cli", "review", "list", "--entity", "component", "--status", "PENDING", "--db", db_path],
    )
    cli_mod.main()
    captured = capsys.readouterr()
    assert "1" in captured.out or "PENDING" in captured.out
