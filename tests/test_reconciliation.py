"""
Tests for entity resolution / identity detection (Plan 02-04).
"""
from datetime import datetime, timezone

import pytest


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _insert_source_component(
    conn,
    *,
    source_system: str,
    source_reference: str,
    normalized_reference: str,
    description: str = "desc",
) -> int:
    cur = conn.execute(
        """
        INSERT INTO source_component (
            source_system, source_reference, normalized_reference,
            description, source_record_type, source_record_id, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            source_system,
            source_reference,
            normalized_reference,
            description,
            "TEST",
            1,
            _now(),
        ),
    )
    conn.commit()
    return cur.lastrowid


def _insert_source_supplier(
    conn,
    *,
    source_system: str,
    source_reference: str,
    normalized_reference: str,
) -> int:
    cur = conn.execute(
        """
        INSERT INTO source_supplier (
            source_system, source_reference, normalized_reference,
            description, source_record_type, source_record_id, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            source_system,
            source_reference,
            normalized_reference,
            source_reference,
            "TEST",
            1,
            _now(),
        ),
    )
    conn.commit()
    return cur.lastrowid


# ---------------------------------------------------------------------------
# Task 2.4.1 — component identities
# ---------------------------------------------------------------------------


def test_shared_normalized_reference_creates_pending_rows(conn):
    """SCEN-B cluster: distinct source refs sharing normalized_reference."""
    from app.services.reconciliation import detect_component_identities

    _insert_source_component(
        conn,
        source_system="PLM",
        source_reference="CTRL-AIR-01",
        normalized_reference="CTRL-AIR-01",
    )
    _insert_source_component(
        conn,
        source_system="PLM",
        source_reference="CTRL-AIR01",
        normalized_reference="CTRL-AIR-01",
    )
    _insert_source_component(
        conn,
        source_system="PLM",
        source_reference="CTRL-HVAC-001",
        normalized_reference="CTRL-AIR-01",
    )
    # MAT-10001 stays on its own normalized ref — must NOT join the cluster
    _insert_source_component(
        conn,
        source_system="ERP",
        source_reference="MAT-10001",
        normalized_reference="MAT-10001",
    )

    matches = detect_component_identities(conn)
    assert len(matches) == 3

    rows = conn.execute(
        "SELECT * FROM component_reconciliation ORDER BY source_component_id"
    ).fetchall()
    assert len(rows) == 3
    for row in rows:
        assert row["status"] == "PENDING"
        assert row["method"] == "NORMALIZED"
        assert row["confidence"] == pytest.approx(0.95)
        assert row["component_id"] is None
        assert "CTRL-AIR-01" in row["evidence_json"]

    # MAT-10001 must have no reconciliation row
    mat_id = conn.execute(
        "SELECT id FROM source_component WHERE source_reference = 'MAT-10001'"
    ).fetchone()["id"]
    assert (
        conn.execute(
            "SELECT COUNT(*) AS c FROM component_reconciliation "
            "WHERE source_component_id = ?",
            (mat_id,),
        ).fetchone()["c"]
        == 0
    )


def test_detect_component_identities_idempotent(conn):
    from app.services.reconciliation import detect_component_identities

    _insert_source_component(
        conn,
        source_system="PLM",
        source_reference="CTRL-AIR-01",
        normalized_reference="CTRL-AIR-01",
    )
    _insert_source_component(
        conn,
        source_system="PLM",
        source_reference="CTRL-AIR-O1",
        normalized_reference="CTRL-AIR-01",
    )

    detect_component_identities(conn)
    first = conn.execute(
        "SELECT COUNT(*) AS c FROM component_reconciliation"
    ).fetchone()["c"]
    assert first == 2

    detect_component_identities(conn)
    second = conn.execute(
        "SELECT COUNT(*) AS c FROM component_reconciliation"
    ).fetchone()["c"]
    assert second == first


def test_component_exact_method_across_systems(conn):
    """Same source_reference across PLM/ERP after generic norm → EXACT."""
    from app.services.reconciliation import detect_component_identities

    _insert_source_component(
        conn,
        source_system="PLM",
        source_reference="WIDGET-01",
        normalized_reference="WIDGET-01",
    )
    _insert_source_component(
        conn,
        source_system="ERP",
        source_reference="WIDGET-01",
        normalized_reference="WIDGET-01",
    )

    detect_component_identities(conn)
    rows = conn.execute("SELECT method FROM component_reconciliation").fetchall()
    assert len(rows) == 2
    assert all(r["method"] == "EXACT" for r in rows)


def test_component_detection_queries_source_component_only(conn):
    """D-2.3: detection works with empty raw BOM/ERP tables."""
    from app.services.reconciliation import detect_component_identities

    assert (
        conn.execute("SELECT COUNT(*) AS c FROM plm_bom_line").fetchone()["c"] == 0
    )
    assert (
        conn.execute("SELECT COUNT(*) AS c FROM erp_material").fetchone()["c"] == 0
    )

    _insert_source_component(
        conn,
        source_system="PLM",
        source_reference="A-1",
        normalized_reference="A-1",
    )
    _insert_source_component(
        conn,
        source_system="ERP",
        source_reference="A1",
        normalized_reference="A-1",
    )

    matches = detect_component_identities(conn)
    assert len(matches) == 2
    assert (
        conn.execute(
            "SELECT COUNT(*) AS c FROM component_reconciliation"
        ).fetchone()["c"]
        == 2
    )


def test_record_reconciliation_component(conn):
    from app.services.reconciliation import record_reconciliation

    sid = _insert_source_component(
        conn,
        source_system="PLM",
        source_reference="X-1",
        normalized_reference="X-1",
    )
    rid = record_reconciliation(
        conn,
        entity_type="component",
        source_entity_id=sid,
        status="PENDING",
        method="NORMALIZED",
        confidence=0.9,
        rationale="test",
        evidence={"foo": "bar"},
    )
    conn.commit()
    assert rid is not None
    row = conn.execute(
        "SELECT * FROM component_reconciliation WHERE id = ?", (rid,)
    ).fetchone()
    assert row["status"] == "PENDING"
    assert row["method"] == "NORMALIZED"
    assert row["confidence"] == pytest.approx(0.9)
    assert row["component_id"] is None

    # Idempotent on same evidence
    again = record_reconciliation(
        conn,
        entity_type="component",
        source_entity_id=sid,
        status="PENDING",
        method="NORMALIZED",
        confidence=0.9,
        rationale="test",
        evidence={"foo": "bar"},
    )
    assert again is None


def test_record_reconciliation_extended_signature(conn):
    """canonical_id / decided_at / decided_by optional; confidence stays REAL."""
    from app.services.reconciliation import record_reconciliation

    sid = _insert_source_component(
        conn,
        source_system="PLM",
        source_reference="Y-1",
        normalized_reference="Y-1",
    )
    decided = _now()
    rid = record_reconciliation(
        conn,
        entity_type="component",
        source_entity_id=sid,
        canonical_id=None,
        status="ASSESSED",
        method="MANUAL",
        confidence=0.75,
        rationale="reviewed",
        evidence={"relationship": "identity"},
        decided_at=decided,
        decided_by="tester",
    )
    conn.commit()
    assert rid is not None
    row = conn.execute(
        "SELECT * FROM component_reconciliation WHERE id = ?", (rid,)
    ).fetchone()
    assert row["component_id"] is None
    assert row["status"] == "ASSESSED"
    assert row["method"] == "MANUAL"
    assert isinstance(row["confidence"], float)
    assert row["confidence"] == pytest.approx(0.75)
    assert row["decided_at"] == decided
    assert row["decided_by"] == "tester"


def test_reconciliation_tables_and_confidence_numeric(conn):
    """Blueprint §3.6/§3.7 tables exist; confidence column is REAL/numeric."""
    tables = {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    assert "component_reconciliation" in tables
    assert "assembly_reconciliation" in tables
    assert "supplier_reconciliation" in tables
    assert "reconciliation_run" in tables

    # No FK to missing canonical component table
    fk_sql = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' "
        "AND name='component_reconciliation'"
    ).fetchone()["sql"]
    assert "REFERENCES component(" not in fk_sql

    conf_type = {
        row[1]: row[2]
        for row in conn.execute("PRAGMA table_info(component_reconciliation)")
    }
    assert conf_type["confidence"].upper() == "REAL"


# ---------------------------------------------------------------------------
# Task 2.4.2 — supplier identities
# ---------------------------------------------------------------------------


def test_supplier_exact_normalized_name_match(conn):
    from app.services.reconciliation import detect_supplier_identities

    _insert_source_supplier(
        conn,
        source_system="PLM",
        source_reference="FAIVELEY TRANSPORT",
        normalized_reference="FAIVELEY TRANSPORT",
    )
    _insert_source_supplier(
        conn,
        source_system="ERP",
        source_reference="SUP-FT",
        normalized_reference="FAIVELEY TRANSPORT",
    )

    matches = detect_supplier_identities(conn)
    assert len(matches) == 2

    rows = conn.execute("SELECT * FROM supplier_reconciliation").fetchall()
    assert len(rows) == 2
    for row in rows:
        assert row["status"] == "PENDING"
        assert row["method"] == "EXACT"
        assert row["confidence"] == pytest.approx(0.95)
        assert row["supplier_id"] is None


def test_supplier_alias_match_siemens(conn):
    """SIEMENS (PLM) and SIEMENS MOBILITY (ERP) match via supplier_aliases."""
    from app.services.reconciliation import detect_supplier_identities

    _insert_source_supplier(
        conn,
        source_system="PLM",
        source_reference="SIEMENS",
        normalized_reference="SIEMENS",
    )
    _insert_source_supplier(
        conn,
        source_system="ERP",
        source_reference="SUP-001",
        normalized_reference="SIEMENS MOBILITY",
    )

    matches = detect_supplier_identities(conn)
    assert len(matches) == 2

    rows = conn.execute("SELECT * FROM supplier_reconciliation").fetchall()
    assert len(rows) == 2
    for row in rows:
        assert row["status"] == "PENDING"
        assert row["method"] == "NORMALIZED"
        assert row["confidence"] == pytest.approx(0.95)
        assert "SIEMENS MOBILITY" in row["evidence_json"]


def test_detect_supplier_identities_idempotent(conn):
    from app.services.reconciliation import detect_supplier_identities

    _insert_source_supplier(
        conn,
        source_system="PLM",
        source_reference="SIEMENS",
        normalized_reference="SIEMENS",
    )
    _insert_source_supplier(
        conn,
        source_system="ERP",
        source_reference="SUP-001",
        normalized_reference="SIEMENS MOBILITY",
    )

    detect_supplier_identities(conn)
    first = conn.execute(
        "SELECT COUNT(*) AS c FROM supplier_reconciliation"
    ).fetchone()["c"]
    detect_supplier_identities(conn)
    second = conn.execute(
        "SELECT COUNT(*) AS c FROM supplier_reconciliation"
    ).fetchone()["c"]
    assert first == 2
    assert second == first


def test_supplier_detection_queries_source_supplier_only(conn):
    """D-2.3: works with empty erp_supplier / plm_bom_line."""
    from app.services.reconciliation import detect_supplier_identities

    assert (
        conn.execute("SELECT COUNT(*) AS c FROM erp_supplier").fetchone()["c"] == 0
    )
    assert (
        conn.execute("SELECT COUNT(*) AS c FROM plm_bom_line").fetchone()["c"] == 0
    )

    _insert_source_supplier(
        conn,
        source_system="PLM",
        source_reference="THALES",
        normalized_reference="THALES",
    )
    _insert_source_supplier(
        conn,
        source_system="ERP",
        source_reference="SUP-T",
        normalized_reference="THALES GROUND TRANSPORTATION SYSTEMS",
    )

    matches = detect_supplier_identities(conn)
    assert len(matches) == 2


# ---------------------------------------------------------------------------
# Task 2.5.1 — functional similarity (SCEN-D)
# ---------------------------------------------------------------------------


def test_functional_similarity_door_controllers(conn):
    """SCEN-D: STANDARD-DOOR-CTRL vs EXPORT-DOOR-CTRL similar, not identity."""
    from app.services.reconciliation import (
        detect_component_identities,
        detect_functional_similarity,
    )

    _insert_source_component(
        conn,
        source_system="PLM",
        source_reference="STANDARD-DOOR-CTRL",
        normalized_reference="STANDARD-DOOR-CTRL",
    )
    _insert_source_component(
        conn,
        source_system="PLM",
        source_reference="EXPORT-DOOR-CTRL",
        normalized_reference="EXPORT-DOOR-CTRL",
    )

    candidates = detect_functional_similarity(conn)
    assert len(candidates) == 1
    cand = candidates[0]
    refs = {cand["reference_a"], cand["reference_b"]}
    assert refs == {"STANDARD-DOOR-CTRL", "EXPORT-DOOR-CTRL"}
    assert cand["relationship"] == "functional_similarity"
    assert cand["method"] == "STRUCTURED"
    assert cand["confidence"] == pytest.approx(0.50)
    assert cand["status"] == "PENDING"
    assert cand["review_needed"] is True

    rows = conn.execute(
        "SELECT * FROM component_reconciliation ORDER BY source_component_id"
    ).fetchall()
    assert len(rows) == 2
    for row in rows:
        assert row["status"] == "PENDING"
        assert row["method"] == "STRUCTURED"
        assert row["confidence"] == pytest.approx(0.50)
        assert "functional_similarity" in row["evidence_json"]
        assert "review_needed" in row["evidence_json"]
        # Must NOT be identity
        assert row["method"] != "NORMALIZED"
        assert "identity" not in row["evidence_json"] or (
            '"relationship":"functional_similarity"' in row["evidence_json"]
        )

    # Identity detector must not equate the two distinct normalized refs
    detect_component_identities(conn)
    identity_rows = conn.execute(
        """
        SELECT * FROM component_reconciliation
        WHERE method IN ('EXACT', 'NORMALIZED')
        """
    ).fetchall()
    assert len(identity_rows) == 0


def test_functional_similarity_same_prefix_ctrl_door(conn):
    """Primary heuristic: CTRL-DOOR-01 vs CTRL-DOOR-EXP."""
    from app.services.reconciliation import detect_functional_similarity

    _insert_source_component(
        conn,
        source_system="PLM",
        source_reference="CTRL-DOOR-01",
        normalized_reference="CTRL-DOOR-01",
    )
    _insert_source_component(
        conn,
        source_system="PLM",
        source_reference="CTRL-DOOR-EXP",
        normalized_reference="CTRL-DOOR-EXP",
    )

    candidates = detect_functional_similarity(conn)
    assert len(candidates) == 1
    assert candidates[0]["similarity_type"] == "same_prefix_different_suffix"
    assert candidates[0]["confidence"] == pytest.approx(0.50)
    assert candidates[0]["method"] == "STRUCTURED"


def test_functional_similarity_skips_identical_normalized_ref(conn):
    """Shared normalized_reference is identity territory, not similarity."""
    from app.services.reconciliation import detect_functional_similarity

    _insert_source_component(
        conn,
        source_system="PLM",
        source_reference="CTRL-AIR-01",
        normalized_reference="CTRL-AIR-01",
    )
    _insert_source_component(
        conn,
        source_system="PLM",
        source_reference="CTRL-AIR01",
        normalized_reference="CTRL-AIR-01",
    )

    candidates = detect_functional_similarity(conn)
    assert candidates == []
    assert (
        conn.execute(
            "SELECT COUNT(*) AS c FROM component_reconciliation"
        ).fetchone()["c"]
        == 0
    )


def test_functional_similarity_idempotent(conn):
    from app.services.reconciliation import detect_functional_similarity

    _insert_source_component(
        conn,
        source_system="PLM",
        source_reference="STANDARD-DOOR-CTRL",
        normalized_reference="STANDARD-DOOR-CTRL",
    )
    _insert_source_component(
        conn,
        source_system="PLM",
        source_reference="EXPORT-DOOR-CTRL",
        normalized_reference="EXPORT-DOOR-CTRL",
    )

    detect_functional_similarity(conn)
    first = conn.execute(
        "SELECT COUNT(*) AS c FROM component_reconciliation"
    ).fetchone()["c"]
    assert first == 2

    detect_functional_similarity(conn)
    second = conn.execute(
        "SELECT COUNT(*) AS c FROM component_reconciliation"
    ).fetchone()["c"]
    assert second == first


# ---------------------------------------------------------------------------
# Task 2.5.2 — variant-specific differences (SCEN-E)
# ---------------------------------------------------------------------------


def _seed_nordic_fixture(conn):
    """Nordic-only HVAC-NORDIC vs shared CTRL-SHARED across REGIO-NORDIC / REGIO-STD."""
    sf = conn.execute(
        "INSERT INTO source_file (source_system, file_name, file_hash, ingested_at) "
        "VALUES (?, ?, ?, ?)",
        ("PLM", "fixture.csv", "hash-nordic", _now()),
    ).lastrowid

    conn.execute(
        "INSERT INTO plm_variant ("
        "source_file_id, source_row, variant_ref_raw, variant_name_raw, "
        "variant_ref_normalized"
        ") VALUES (?, ?, ?, ?, ?)",
        (sf, 1, "REGIO-NORDIC", "Regio Nordic Climate", "REGIO-NORDIC"),
    )
    conn.execute(
        "INSERT INTO plm_variant ("
        "source_file_id, source_row, variant_ref_raw, variant_name_raw, "
        "variant_ref_normalized"
        ") VALUES (?, ?, ?, ?, ?)",
        (sf, 2, "REGIO-STD", "Regio Standard", "REGIO-STD"),
    )

    asm_id = conn.execute(
        "INSERT INTO source_assembly ("
        "source_system, source_reference, normalized_reference, description, "
        "source_record_type, source_record_id, created_at"
        ") VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("PLM", "ASM-NORDIC", "ASM-NORDIC", "Nordic ASM", "ASSEMBLY_MASTER", 1, _now()),
    ).lastrowid
    conn.execute(
        "INSERT INTO source_assembly_variant "
        "(source_assembly_id, variant_ref_normalized, created_at) VALUES (?, ?, ?)",
        (asm_id, "REGIO-NORDIC", _now()),
    )
    # Also link standard variant so both exist in junction for realism
    asm_std = conn.execute(
        "INSERT INTO source_assembly ("
        "source_system, source_reference, normalized_reference, description, "
        "source_record_type, source_record_id, created_at"
        ") VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("PLM", "ASM-STD", "ASM-STD", "Std ASM", "ASSEMBLY_MASTER", 2, _now()),
    ).lastrowid
    conn.execute(
        "INSERT INTO source_assembly_variant "
        "(source_assembly_id, variant_ref_normalized, created_at) VALUES (?, ?, ?)",
        (asm_std, "REGIO-STD", _now()),
    )

    # Nordic-only component on REGIO-NORDIC
    conn.execute(
        "INSERT INTO plm_bom_line ("
        "source_file_id, source_row, variant_ref_raw, assembly_ref_raw, "
        "component_ref_raw, variant_ref_normalized, component_ref_normalized"
        ") VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            sf, 1, "REGIO-NORDIC", "ASM-NORDIC", "HVAC-NORDIC",
            "REGIO-NORDIC", "HVAC-NORDIC",
        ),
    )
    # Shared component on both variants
    conn.execute(
        "INSERT INTO plm_bom_line ("
        "source_file_id, source_row, variant_ref_raw, assembly_ref_raw, "
        "component_ref_raw, variant_ref_normalized, component_ref_normalized"
        ") VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            sf, 2, "REGIO-NORDIC", "ASM-NORDIC", "CTRL-SHARED",
            "REGIO-NORDIC", "CTRL-SHARED",
        ),
    )
    conn.execute(
        "INSERT INTO plm_bom_line ("
        "source_file_id, source_row, variant_ref_raw, assembly_ref_raw, "
        "component_ref_raw, variant_ref_normalized, component_ref_normalized"
        ") VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            sf, 3, "REGIO-STD", "ASM-STD", "CTRL-SHARED",
            "REGIO-STD", "CTRL-SHARED",
        ),
    )

    nordic_comp = _insert_source_component(
        conn,
        source_system="PLM",
        source_reference="HVAC-NORDIC",
        normalized_reference="HVAC-NORDIC",
        description="Nordic HVAC",
    )
    shared_comp = _insert_source_component(
        conn,
        source_system="PLM",
        source_reference="CTRL-SHARED",
        normalized_reference="CTRL-SHARED",
        description="Shared ctrl",
    )
    # Pair that would look similar to HVAC-NORDIC under prefix heuristic
    _insert_source_component(
        conn,
        source_system="PLM",
        source_reference="HVAC-NORDIC-ALT",
        normalized_reference="HVAC-NORDIC-ALT",
        description="Would-be similar",
    )
    conn.commit()
    return nordic_comp, shared_comp


def test_variant_specific_nordic_components(conn):
    """SCEN-E: Nordic-only components flagged as variant_specific, not merge."""
    from app.services.reconciliation import (
        detect_functional_similarity,
        detect_variant_specific_differences,
    )

    nordic_comp, shared_comp = _seed_nordic_fixture(conn)

    records = detect_variant_specific_differences(conn)
    refs = {r["component_ref"] for r in records}
    assert "HVAC-NORDIC" in refs
    assert "CTRL-SHARED" not in refs

    for rec in records:
        if rec["component_ref"] == "HVAC-NORDIC":
            assert rec["relationship"] == "variant_specific"
            assert rec["status"] == "PENDING"
            assert rec["method"] == "STRUCTURED"
            assert rec["confidence"] == pytest.approx(0.95)
            assert rec["review_needed"] is False

    rows = conn.execute(
        """
        SELECT * FROM component_reconciliation
        WHERE source_component_id = ?
        """,
        (nordic_comp,),
    ).fetchall()
    assert len(rows) == 1
    row = rows[0]
    assert row["status"] == "PENDING"
    assert row["method"] == "STRUCTURED"
    assert row["confidence"] == pytest.approx(0.95)
    assert "variant_specific" in row["evidence_json"]
    assert '"review_needed":false' in row["evidence_json"]

    # Shared component must not get a variant_specific row
    assert (
        conn.execute(
            "SELECT COUNT(*) AS c FROM component_reconciliation "
            "WHERE source_component_id = ?",
            (shared_comp,),
        ).fetchone()["c"]
        == 0
    )

    # Nordic-only refs excluded from functional similarity pairing
    sim = detect_functional_similarity(conn)
    for cand in sim:
        pair = {cand["reference_a"], cand["reference_b"]}
        assert "HVAC-NORDIC" not in pair


def test_variant_specific_idempotent(conn):
    from app.services.reconciliation import detect_variant_specific_differences

    _seed_nordic_fixture(conn)
    detect_variant_specific_differences(conn)
    first = conn.execute(
        "SELECT COUNT(*) AS c FROM component_reconciliation"
    ).fetchone()["c"]
    detect_variant_specific_differences(conn)
    second = conn.execute(
        "SELECT COUNT(*) AS c FROM component_reconciliation"
    ).fetchone()["c"]
    assert first >= 1
    assert second == first


# ---------------------------------------------------------------------------
# Task 2.4.3 — orchestrator
# ---------------------------------------------------------------------------



def test_run_entity_resolution_creates_runs_and_records(conn):
    from app.services.reconciliation import run_entity_resolution

    _insert_source_component(
        conn,
        source_system="PLM",
        source_reference="CTRL-AIR-01",
        normalized_reference="CTRL-AIR-01",
    )
    _insert_source_component(
        conn,
        source_system="PLM",
        source_reference="CTRL-AIR01",
        normalized_reference="CTRL-AIR-01",
    )
    _insert_source_supplier(
        conn,
        source_system="PLM",
        source_reference="SIEMENS",
        normalized_reference="SIEMENS",
    )
    _insert_source_supplier(
        conn,
        source_system="ERP",
        source_reference="SUP-001",
        normalized_reference="SIEMENS MOBILITY",
    )

    summary = run_entity_resolution(conn)

    assert summary["components_matched"] == 1
    assert summary["suppliers_matched"] == 1
    assert summary["total_records"] == 4  # 2 component + 2 supplier rows
    assert summary["component_run_id"] is not None
    assert summary["supplier_run_id"] is not None

    runs = conn.execute(
        "SELECT * FROM reconciliation_run ORDER BY id"
    ).fetchall()
    assert len(runs) == 2
    assert {r["entity_type"] for r in runs} == {"component", "supplier"}
    for run in runs:
        assert run["status"] == "COMPLETED"
        assert run["started_at"] is not None
        assert run["completed_at"] is not None
        assert run["items_needing_review"] == 2

    assert (
        conn.execute(
            "SELECT COUNT(*) AS c FROM component_reconciliation "
            "WHERE reconciliation_run_id = ?",
            (summary["component_run_id"],),
        ).fetchone()["c"]
        == 2
    )
    assert (
        conn.execute(
            "SELECT COUNT(*) AS c FROM supplier_reconciliation "
            "WHERE reconciliation_run_id = ?",
            (summary["supplier_run_id"],),
        ).fetchone()["c"]
        == 2
    )


def test_run_entity_resolution_idempotent_records(conn):
    from app.services.reconciliation import run_entity_resolution

    _insert_source_component(
        conn,
        source_system="PLM",
        source_reference="W-1",
        normalized_reference="W-1",
    )
    _insert_source_component(
        conn,
        source_system="ERP",
        source_reference="W-1",
        normalized_reference="W-1",
    )

    first = run_entity_resolution(conn)
    second = run_entity_resolution(conn)

    assert first["total_records"] == 2
    assert second["total_records"] == 2
    assert (
        conn.execute(
            "SELECT COUNT(*) AS c FROM component_reconciliation"
        ).fetchone()["c"]
        == 2
    )
    # Two runs each call (component + supplier) → 4 run rows after two calls
    assert (
        conn.execute(
            "SELECT COUNT(*) AS c FROM reconciliation_run"
        ).fetchone()["c"]
        == 4
    )
