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
    source_table: str = "plm_bom_line",
) -> None:
    conn.execute(
        """
        INSERT INTO warnings (source_table, source_row_id, warning_type, warning_message, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (source_table, source_row_id, warning_type, message, _now()),
    )
    conn.commit()


def _insert_source_component(
    conn,
    *,
    source_reference: str,
    normalized_reference: str | None = None,
    source_system: str = "PLM",
) -> int:
    cur = conn.execute(
        """
        INSERT INTO source_component (
            source_system, source_reference, normalized_reference,
            description, source_record_type, source_record_id, created_at
        ) VALUES (?, ?, ?, ?, 'TEST', 1, ?)
        """,
        (
            source_system,
            source_reference,
            normalized_reference or source_reference,
            "component",
            _now(),
        ),
    )
    conn.commit()
    return cur.lastrowid


def _insert_reconciliation(
    conn,
    *,
    source_component_id: int,
    status: str = "PENDING",
    relationship: str = "identity",
) -> int:
    evidence = {"relationship": relationship, "review_needed": True}
    cur = conn.execute(
        """
        INSERT INTO component_reconciliation (
            source_component_id, component_id, status, method, confidence,
            rationale, evidence_json, created_at
        ) VALUES (?, NULL, ?, 'NORMALIZED', 0.95, 'alias', ?, ?)
        """,
        (source_component_id, status, json.dumps(evidence), _now()),
    )
    conn.commit()
    return cur.lastrowid


def _assert_record_shape(rec: dict) -> None:
    assert set(rec.keys()) >= {"source_table", "source_id", "source_file", "source_row"}
    assert isinstance(rec["source_id"], str)
    assert isinstance(rec["source_row"], int) or rec["source_row"] is None


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
    assert len(row["sources"]) == 2
    for src in row["sources"]:
        assert src["source_type"] == "engineering_note"
        assert src["source_id"] == "N-064"
        assert src["source_file"] == "technical_notes.csv"
        assert src["source_row"] == 64
    assert {s["value"] for s in row["sources"]} == {"24 V DC", "48 V DC"}

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
    mismatch = mismatches[0]
    expl = mismatch["explanation"]
    assert "Prototype" in expl
    assert "Released" in expl
    assert "Obsolete" not in expl
    assert "OBSOLETE" not in expl
    assert mismatch["entity_ref"] == "PAX-COUNT-MOD-E"
    assert mismatch["values"] == ["Prototype", "Released"]
    assert len(mismatch["sources"]) == 2
    by_value = {s["value"]: s for s in mismatch["sources"]}
    assert by_value["Prototype"] == {
        "source_type": "plm_assembly",
        "source_id": "PAX-COUNT-MOD-E",
        "value": "Prototype",
        "source_file": "test.csv",
        "source_row": 1,
    }
    assert by_value["Released"] == {
        "source_type": "plm_assembly",
        "source_id": "PCOUNT-M08",
        "value": "Released",
        "source_file": "test.csv",
        "source_row": 2,
    }


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
        assert len(r["sources"]) == 1
        src = r["sources"][0]
        assert src["source_type"] == "erp_material"
        assert src["source_id"] == r["entity_ref"]
        assert src["value"] == "OBSOLETE"
        assert src["source_file"] == "material_master.csv"
        assert isinstance(src["source_row"], int)
    by_ref = {r["entity_ref"]: r["sources"][0] for r in erp}
    assert by_ref["MAT-20001"]["source_row"] == 1
    assert by_ref["MAT-20002"]["source_row"] == 2
    assert by_ref["MAT-20004"]["source_row"] == 3


# ---------------------------------------------------------------------------
# data_quality_issues (SCEN-I)
# ---------------------------------------------------------------------------


def test_data_quality_invalid_quantity_from_quarantine(conn):
    from app.services.quality import data_quality_issues

    sf = _source_file(conn, "PLM", "bom_export.csv")
    qid = _insert_quarantine(
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
    assert "unresolved_reconciliation_count" in result
    assert result["unresolved_reconciliation_count"] == 0
    issues = result["issues"]
    invalid = [i for i in issues if i["issue_type"] == "invalid_quantity"]
    assert len(invalid) == 1
    assert "BOM-0031" in json.dumps(invalid[0]) or "one" in json.dumps(invalid[0])
    assert "quantity" in invalid[0]["explanation"].lower() or "quantity" in (
        invalid[0].get("detail") or ""
    ).lower()
    assert "records" in invalid[0]
    assert len(invalid[0]["records"]) == 1
    rec = invalid[0]["records"][0]
    _assert_record_shape(rec)
    assert rec["source_table"] == "quarantine"
    assert rec["source_id"] == str(qid)
    assert rec["source_file"] == "bom_export.csv"
    assert rec["source_row"] == 32


def test_data_quality_duplicate_bom_key_after_alias(conn):
    from app.services.quality import data_quality_issues

    sf = _source_file(conn, "PLM", "bom_export.csv")
    bom1 = _insert_bom(
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
    assert "records" in dups[0]
    assert len(dups[0]["records"]) == 2
    rec_ids = {r["source_id"] for r in dups[0]["records"]}
    assert rec_ids == {str(bom1), str(bom2)}
    for rec in dups[0]["records"]:
        _assert_record_shape(rec)
        assert rec["source_table"] == "plm_bom_line"
        assert rec["source_file"] == "bom_export.csv"
        assert rec["source_row"] in (1, 301)


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
        uom_raw="units",
        uom_normalized="EA",
        source_row=2,
    )
    result = data_quality_issues(conn)
    aliased = [i for i in result["issues"] if i["issue_type"] == "uom_aliased"]
    assert len(aliased) == 1
    assert "conflict" not in aliased[0]["issue_type"]
    assert "EA" in json.dumps(aliased[0])
    assert "pcs" in aliased[0]["refs"] or "pcs" in aliased[0]["detail"]
    assert "units" in aliased[0]["refs"] or "units" in aliased[0]["detail"]
    assert "records" in aliased[0]
    # Query has no line id; records may be empty
    assert isinstance(aliased[0]["records"], list)


def test_data_quality_warning_summary_marks_mapping_noise(conn):
    from app.services.quality import data_quality_issues

    sf = _source_file(conn, "PLM", "bom_export.csv")
    for i in range(3):
        row = i + 2  # CSV data rows start at 2
        _insert_bom(
            conn,
            source_file_id=sf,
            variant_ref="REGIO-STD",
            assembly_ref="HVAC-M01",
            component_ref=f"PART-{i}",
            source_row=row,
        )
        _insert_warning(conn, warning_type="missing_description", source_row_id=row)
    _insert_bom(
        conn,
        source_file_id=sf,
        variant_ref="REGIO-STD",
        assembly_ref="HVAC-M01",
        component_ref="PART-SUP",
        source_row=10,
    )
    _insert_warning(conn, warning_type="empty_supplier", source_row_id=10)
    _insert_bom(
        conn,
        source_file_id=sf,
        variant_ref="REGIO-STD",
        assembly_ref="HVAC-M01",
        component_ref="PART-UOM",
        source_row=11,
    )
    _insert_warning(conn, warning_type="unknown_uom", source_row_id=11)

    result = data_quality_issues(conn)
    assert "issues" in result
    assert "ingestion_warning_summary" in result
    assert "unresolved_reconciliation_count" in result
    summary = result["ingestion_warning_summary"]
    assert summary["missing_description"]["count"] == 3
    assert summary["missing_description"]["mapping_noise"] is True
    assert summary["missing_description"]["by_source_file"] == {"bom_export.csv": 3}
    assert summary["empty_supplier"]["count"] == 1
    assert summary["empty_supplier"]["mapping_noise"] is True
    assert summary["empty_supplier"]["by_source_file"] == {"bom_export.csv": 1}
    assert summary["unknown_uom"]["count"] == 1
    assert summary["unknown_uom"]["by_source_file"] == {"bom_export.csv": 1}
    # Not one report row per warning
    warn_rows = [
        i
        for i in result["issues"]
        if i["issue_type"] in ("missing_description", "empty_supplier")
    ]
    assert warn_rows == []


def test_data_quality_by_source_file_two_missing_description(conn):
    from app.services.quality import data_quality_issues

    sf = _source_file(conn, "PLM", "bom_export.csv")
    for row in (2, 3):
        _insert_bom(
            conn,
            source_file_id=sf,
            variant_ref="REGIO-STD",
            assembly_ref="HVAC-M01",
            component_ref=f"PART-R{row}",
            source_row=row,
        )
        _insert_warning(conn, warning_type="missing_description", source_row_id=row)
    # Unknown table name is skipped for by_source_file but still counted
    _insert_warning(
        conn,
        warning_type="missing_description",
        source_row_id=99,
        source_table="not_a_real_table",
    )

    result = data_quality_issues(conn)
    entry = result["ingestion_warning_summary"]["missing_description"]
    assert entry["count"] == 3
    assert entry["by_source_file"] == {"bom_export.csv": 2}


def test_data_quality_duplicate_reference_cross_system(conn):
    from app.services.quality import data_quality_issues

    sc_plm = _insert_source_component(
        conn, source_reference="SHARED-REF", normalized_reference="SHARED-REF", source_system="PLM"
    )
    sc_erp = _insert_source_component(
        conn, source_reference="SHARED-REF-ERP", normalized_reference="SHARED-REF", source_system="ERP"
    )
    # Single-system duplicate normalized ref must not appear
    _insert_source_component(
        conn, source_reference="SINGLE-A", normalized_reference="SINGLE-ONLY", source_system="PLM"
    )
    _insert_source_component(
        conn, source_reference="SINGLE-B", normalized_reference="SINGLE-ONLY", source_system="PLM"
    )
    # CTRL-AIR-01 and MAT-10001 stay distinct unless same normalized string
    _insert_source_component(
        conn, source_reference="CTRL-AIR-01", normalized_reference="CTRL-AIR-01", source_system="PLM"
    )
    _insert_source_component(
        conn, source_reference="MAT-10001", normalized_reference="MAT-10001", source_system="ERP"
    )

    result = data_quality_issues(conn)
    dups = [i for i in result["issues"] if i["issue_type"] == "duplicate_reference"]
    assert len(dups) == 1
    detail = dups[0]["detail"]
    assert "SHARED-REF" in detail
    assert "PLM" in detail and "ERP" in detail
    assert "CTRL-AIR-01" not in detail or "MAT-10001" not in detail
    assert "SINGLE-ONLY" not in detail
    assert len(dups[0]["records"]) == 2
    rec_ids = {r["source_id"] for r in dups[0]["records"]}
    assert rec_ids == {str(sc_plm), str(sc_erp)}
    for rec in dups[0]["records"]:
        _assert_record_shape(rec)
        assert rec["source_table"] == "source_component"


def test_data_quality_conflicting_facts_from_blockers(conn):
    from app.services.quality import blockers, data_quality_issues

    sf = _source_file(conn, "ENGINEERING", "technical_notes.csv")
    _insert_note(conn, source_file_id=sf, object_reference="CTRL-AIR-01", note_text=N064_TEXT)
    # Single OBSOLETE fact must not become conflicting_facts
    sf_erp = _source_file(conn, "ERP", "material_master.csv")
    _insert_material(conn, source_file_id=sf_erp, material_id="MAT-20001", status="OBSOLETE")

    blockers(conn)
    result = data_quality_issues(conn)
    conflicts = [i for i in result["issues"] if i["issue_type"] == "conflicting_facts"]
    assert len(conflicts) >= 1
    voltage = [i for i in conflicts if "24 V DC" in i["detail"] and "48 V DC" in i["detail"]]
    assert len(voltage) == 1
    assert len(voltage[0]["records"]) >= 2
    for rec in voltage[0]["records"]:
        _assert_record_shape(rec)
        assert rec["source_table"] == "engineering_note"
        assert rec["source_id"] == "N-064"
    obsolete_issues = [
        i for i in conflicts if "OBSOLETE" in i["detail"] and "24 V DC" not in i["detail"]
    ]
    assert obsolete_issues == []


def test_data_quality_unresolved_reconciliation_identity(conn):
    from app.services.quality import data_quality_issues

    sc_pending = _insert_source_component(conn, source_reference="CTRL-AIR01")
    sc_rejected = _insert_source_component(conn, source_reference="CTRL-AIRO1")
    sc_accepted = _insert_source_component(conn, source_reference="CTRL-AIR-01")
    sc_sim = _insert_source_component(conn, source_reference="CTRL-DOOR-01")

    rid_p = _insert_reconciliation(conn, source_component_id=sc_pending, status="PENDING")
    rid_r = _insert_reconciliation(conn, source_component_id=sc_rejected, status="REJECTED")
    _insert_reconciliation(conn, source_component_id=sc_accepted, status="ACCEPTED")
    _insert_reconciliation(
        conn, source_component_id=sc_sim, status="PENDING", relationship="functional_similarity"
    )

    result = data_quality_issues(conn)
    assert result["unresolved_reconciliation_count"] == 2
    unresolved = [i for i in result["issues"] if i["issue_type"] == "unresolved_reconciliation"]
    assert len(unresolved) == 1
    assert "2" in unresolved[0]["detail"]
    rec_ids = {r["source_id"] for r in unresolved[0]["records"]}
    assert rec_ids == {str(rid_p), str(rid_r)}
    for rec in unresolved[0]["records"]:
        _assert_record_shape(rec)
        assert rec["source_table"] == "component_reconciliation"


def test_data_quality_alias_summary_from_config(conn):
    from app.services.quality import data_quality_issues
    from app.services.normalization import load_normalization_config

    config = load_normalization_config()
    aliases = config["reference_aliases"]
    assert aliases["CTRL-AIR01"] == "CTRL-AIR-01"

    sf = _source_file(conn, "PLM", "bom_export.csv")
    bom_id = _insert_bom(
        conn,
        source_file_id=sf,
        variant_ref="REGIO-STD",
        assembly_ref="HVAC-M01",
        component_ref="CTRL-AIR01",
        component_ref_normalized="CTRL-AIR-01",
        source_row=5,
    )

    result = data_quality_issues(conn)
    aliases_issues = [i for i in result["issues"] if i["issue_type"] == "alias_summary"]
    assert len(aliases_issues) == 1
    assert "CTRL-AIR01 → CTRL-AIR-01" in aliases_issues[0]["detail"]
    assert any(
        r["source_table"] == "plm_bom_line" and r["source_id"] == str(bom_id)
        for r in aliases_issues[0]["records"]
    )


def test_data_quality_new_issue_types_sorted_after_existing(conn):
    from app.services.quality import blockers, data_quality_issues

    sf = _source_file(conn, "PLM", "bom_export.csv")
    _insert_quarantine(
        conn,
        source_file_id=sf,
        source_row=32,
        raw_data={"plm_row_id": "BOM-0031", "quantity": "one"},
        reason="Unparseable quantity: one",
    )
    _insert_bom(
        conn,
        source_file_id=sf,
        variant_ref="REGIO-STD",
        assembly_ref="HVAC-M01",
        component_ref="CTRL-AIR-01",
        component_ref_normalized="CTRL-AIR-01",
        source_row=1,
    )
    _insert_bom(
        conn,
        source_file_id=sf,
        variant_ref="REGIO-STD",
        assembly_ref="HVAC-M01",
        component_ref="CTRL-AIR01",
        component_ref_normalized="CTRL-AIR-01",
        source_row=301,
    )
    _insert_bom(
        conn,
        source_file_id=sf,
        variant_ref="REGIO-STD",
        assembly_ref="HVAC-M02",
        component_ref="FILTER-HVAC-01",
        uom_raw="pcs",
        uom_normalized="EA",
        source_row=10,
    )
    _insert_bom(
        conn,
        source_file_id=sf,
        variant_ref="REGIO-COMFORT",
        assembly_ref="HVAC-M02",
        component_ref="FILTER-HVAC-01",
        uom_raw="units",
        uom_normalized="EA",
        source_row=11,
    )
    _insert_source_component(
        conn, source_reference="X-A", normalized_reference="X-SHARED", source_system="PLM"
    )
    _insert_source_component(
        conn, source_reference="X-B", normalized_reference="X-SHARED", source_system="ERP"
    )
    sc = _insert_source_component(conn, source_reference="PEND-1")
    _insert_reconciliation(conn, source_component_id=sc, status="PENDING")

    sf_eng = _source_file(conn, "ENGINEERING", "technical_notes.csv")
    _insert_note(conn, source_file_id=sf_eng, object_reference="CTRL-AIR-01", note_text=N064_TEXT)
    blockers(conn)

    result = data_quality_issues(conn)
    types = [i["issue_type"] for i in result["issues"]]
    # Existing three keep relative order; new types appended sorted among themselves
    first_three = [t for t in types if t in ("invalid_quantity", "duplicate_bom_key", "uom_aliased")]
    assert first_three == ["invalid_quantity", "duplicate_bom_key", "uom_aliased"]
    new_types = [
        t
        for t in types
        if t
        in (
            "alias_summary",
            "conflicting_facts",
            "duplicate_reference",
            "unresolved_reconciliation",
        )
    ]
    assert new_types == sorted(new_types)
    # New types appear after the existing three
    last_existing_idx = max(types.index(t) for t in first_three)
    first_new_idx = min(types.index(t) for t in new_types)
    assert first_new_idx > last_existing_idx


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
