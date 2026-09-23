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
