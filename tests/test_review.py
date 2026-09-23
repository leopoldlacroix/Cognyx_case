"""
Tests for human review decisions on reconciliation rows (Plan 03-01).
"""
from datetime import datetime, timezone
import json

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


def _insert_pending_reconciliation(
    conn,
    *,
    source_component_id: int,
    evidence: dict,
    method: str = "NORMALIZED",
    confidence: float = 0.95,
    rationale: str = "pending proposal",
) -> int:
    cur = conn.execute(
        """
        INSERT INTO component_reconciliation (
            source_component_id, component_id, status, method, confidence,
            rationale, evidence_json, created_at
        ) VALUES (?, NULL, 'PENDING', ?, ?, ?, ?, ?)
        """,
        (
            source_component_id,
            method,
            confidence,
            rationale,
            json.dumps(evidence, sort_keys=True, separators=(",", ":")),
            _now(),
        ),
    )
    conn.commit()
    return cur.lastrowid


# ---------------------------------------------------------------------------
# Canonical schema
# ---------------------------------------------------------------------------


def test_canonical_tables_exist(conn):
    """init_database creates component, assembly, supplier, variant, bom, facts."""
    tables = {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    for name in (
        "component",
        "assembly",
        "supplier",
        "variant",
        "bom_relationship",
        "technical_fact",
    ):
        assert name in tables


def test_component_table_columns(conn):
    cols = {
        row[1]
        for row in conn.execute("PRAGMA table_info(component)").fetchall()
    }
    assert cols == {"id", "name", "category", "normalized_reference", "created_at"}


def test_bom_relationship_unique(conn):
    """UNIQUE(variant_id, assembly_id, component_id, source_bom_line_id)."""
    now = _now()
    conn.execute(
        "INSERT INTO variant (name, train_family, market, climate_class, "
        "capacity_class, voltage_system, normalized_reference, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        ("V1", "F", "M", "C", "CAP", "V", "V1", now),
    )
    conn.execute(
        "INSERT INTO assembly (name, category, normalized_reference, created_at) "
        "VALUES (?, ?, ?, ?)",
        ("A1", None, "A1", now),
    )
    conn.execute(
        "INSERT INTO component (name, category, normalized_reference, created_at) "
        "VALUES (?, ?, ?, ?)",
        ("C1", None, "C1", now),
    )
    conn.execute(
        "INSERT INTO bom_relationship "
        "(variant_id, assembly_id, component_id, quantity, unit, "
        "source_bom_line_id, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (1, 1, 1, 1.0, "EA", 10, now),
    )
    conn.commit()
    with pytest.raises(Exception):
        conn.execute(
            "INSERT INTO bom_relationship "
            "(variant_id, assembly_id, component_id, quantity, unit, "
            "source_bom_line_id, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (1, 1, 1, 2.0, "EA", 10, now),
        )


def test_technical_fact_status_values(conn):
    now = _now()
    for status in ("OBSERVED", "VALIDATED", "CONFLICTING"):
        conn.execute(
            "INSERT INTO technical_fact "
            "(entity_type, entity_id, attribute, value, unit, source_type, "
            "source_id, confidence, status, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("component", 1, "voltage", "48V", "V", "note", "N-1", 0.9, status, now),
        )
    conn.commit()
    rows = conn.execute("SELECT status FROM technical_fact ORDER BY id").fetchall()
    assert [r["status"] for r in rows] == ["OBSERVED", "VALIDATED", "CONFLICTING"]


# ---------------------------------------------------------------------------
# decide_reconciliation — accept identity
# ---------------------------------------------------------------------------


def test_accept_identity_creates_canonical_component(conn):
    from app.services.review import decide_reconciliation

    sid = _insert_source_component(
        conn,
        source_system="PLM",
        source_reference="CTRL-AIR-01",
        normalized_reference="CTRL-AIR-01",
    )
    rid = _insert_pending_reconciliation(
        conn,
        source_component_id=sid,
        evidence={
            "relationship": "identity",
            "source_component_id": sid,
            "cluster_members": [],
        },
    )

    row = decide_reconciliation(
        conn, "component", rid, "accept", rationale="confirmed alias"
    )

    assert row["status"] == "ACCEPTED"
    assert row["component_id"] is not None
    assert row["decided_at"] is not None
    assert row["decided_by"] == "operator"
    assert row["rationale"] == "confirmed alias"

    canon = conn.execute(
        "SELECT * FROM component WHERE id = ?", (row["component_id"],)
    ).fetchone()
    assert canon["normalized_reference"] == "CTRL-AIR-01"
    assert canon["name"] == "CTRL-AIR-01"


def test_accept_identity_reuses_cluster_peer_canonical_id(conn):
    from app.services.review import decide_reconciliation

    sid_a = _insert_source_component(
        conn,
        source_system="PLM",
        source_reference="CTRL-AIR-01",
        normalized_reference="CTRL-AIR-01",
    )
    sid_b = _insert_source_component(
        conn,
        source_system="PLM",
        source_reference="CTRL-AIR01",
        normalized_reference="CTRL-AIR-01",
    )
    rid_a = _insert_pending_reconciliation(
        conn,
        source_component_id=sid_a,
        evidence={
            "relationship": "identity",
            "source_component_id": sid_a,
            "cluster_members": [
                {
                    "source_component_id": sid_b,
                    "source_system": "PLM",
                    "source_reference": "CTRL-AIR01",
                }
            ],
        },
    )
    rid_b = _insert_pending_reconciliation(
        conn,
        source_component_id=sid_b,
        evidence={
            "relationship": "identity",
            "source_component_id": sid_b,
            "cluster_members": [
                {
                    "source_component_id": sid_a,
                    "source_system": "PLM",
                    "source_reference": "CTRL-AIR-01",
                }
            ],
        },
    )

    first = decide_reconciliation(conn, "component", rid_a, "accept")
    second = decide_reconciliation(conn, "component", rid_b, "accept")

    assert first["component_id"] == second["component_id"]
    count = conn.execute("SELECT COUNT(*) AS c FROM component").fetchone()["c"]
    assert count == 1


# ---------------------------------------------------------------------------
# accept functional_similarity / variant_specific
# ---------------------------------------------------------------------------


def test_accept_functional_similarity_leaves_component_id_null(conn):
    from app.services.review import decide_reconciliation

    sid = _insert_source_component(
        conn,
        source_system="PLM",
        source_reference="CTRL-DOOR-01",
        normalized_reference="CTRL-DOOR-01",
    )
    rid = _insert_pending_reconciliation(
        conn,
        source_component_id=sid,
        evidence={
            "relationship": "functional_similarity",
            "review_needed": True,
            "reference_a": "CTRL-DOOR-01",
            "reference_b": "CTRL-DOOR-EXP",
        },
        method="STRUCTURED",
        confidence=0.50,
    )

    row = decide_reconciliation(
        conn, "component", rid, "accept", rationale="candidate confirmed"
    )

    assert row["status"] == "ACCEPTED"
    assert row["component_id"] is None
    assert row["rationale"] == "candidate confirmed"
    assert conn.execute("SELECT COUNT(*) AS c FROM component").fetchone()["c"] == 0


def test_accept_variant_specific_creates_own_canonical(conn):
    from app.services.review import decide_reconciliation

    sid_base = _insert_source_component(
        conn,
        source_system="PLM",
        source_reference="BRAKE-STD",
        normalized_reference="BRAKE-STD",
    )
    sid_nordic = _insert_source_component(
        conn,
        source_system="PLM",
        source_reference="BRAKE-NORDIC",
        normalized_reference="BRAKE-NORDIC",
    )
    # Pre-create a canonical for the base part (simulates prior identity accept)
    now = _now()
    conn.execute(
        "INSERT INTO component (name, category, normalized_reference, created_at) "
        "VALUES (?, ?, ?, ?)",
        ("BRAKE-STD", None, "BRAKE-STD", now),
    )
    conn.commit()
    base_canonical_id = 1

    rid = _insert_pending_reconciliation(
        conn,
        source_component_id=sid_nordic,
        evidence={
            "relationship": "variant_specific",
            "review_needed": False,
            "component_ref": "BRAKE-NORDIC",
        },
        method="STRUCTURED",
        confidence=0.95,
    )

    row = decide_reconciliation(conn, "component", rid, "accept")

    assert row["status"] == "ACCEPTED"
    assert row["component_id"] is not None
    assert row["component_id"] != base_canonical_id
    canon = conn.execute(
        "SELECT normalized_reference FROM component WHERE id = ?",
        (row["component_id"],),
    ).fetchone()
    assert canon["normalized_reference"] == "BRAKE-NORDIC"
    # Must not reuse base
    assert (
        conn.execute(
            "SELECT COUNT(*) AS c FROM component WHERE normalized_reference = ?",
            ("BRAKE-STD",),
        ).fetchone()["c"]
        == 1
    )


# ---------------------------------------------------------------------------
# reject
# ---------------------------------------------------------------------------


def test_reject_requires_rationale(conn):
    from app.services.review import decide_reconciliation

    sid = _insert_source_component(
        conn,
        source_system="PLM",
        source_reference="X-1",
        normalized_reference="X-1",
    )
    rid = _insert_pending_reconciliation(
        conn,
        source_component_id=sid,
        evidence={"relationship": "identity", "cluster_members": []},
    )

    with pytest.raises(ValueError, match="rationale"):
        decide_reconciliation(conn, "component", rid, "reject")


def test_reject_sets_rejected_canonical_null(conn):
    from app.services.review import decide_reconciliation

    sid = _insert_source_component(
        conn,
        source_system="PLM",
        source_reference="X-1",
        normalized_reference="X-1",
    )
    rid = _insert_pending_reconciliation(
        conn,
        source_component_id=sid,
        evidence={"relationship": "identity", "cluster_members": []},
    )

    row = decide_reconciliation(
        conn, "component", rid, "reject", rationale="false positive"
    )

    assert row["status"] == "REJECTED"
    assert row["component_id"] is None
    assert row["rationale"] == "false positive"
    assert row["decided_at"] is not None
    assert row["decided_by"] == "operator"


# ---------------------------------------------------------------------------
# redirect
# ---------------------------------------------------------------------------


def test_redirect_rejects_original_and_inserts_manual_pending(conn):
    from app.services.review import decide_reconciliation

    sid_a = _insert_source_component(
        conn,
        source_system="PLM",
        source_reference="CTRL-AIR-01",
        normalized_reference="CTRL-AIR-01",
    )
    sid_b = _insert_source_component(
        conn,
        source_system="ERP",
        source_reference="MAT-99999",
        normalized_reference="MAT-99999",
    )
    rid = _insert_pending_reconciliation(
        conn,
        source_component_id=sid_a,
        evidence={
            "relationship": "identity",
            "source_component_id": sid_a,
            "cluster_members": [],
        },
    )

    result = decide_reconciliation(
        conn,
        "component",
        rid,
        "redirect",
        rationale="wrong peer; link to ERP material",
        redirect_source_id=sid_b,
    )

    original = conn.execute(
        "SELECT * FROM component_reconciliation WHERE id = ?", (rid,)
    ).fetchone()
    assert original["status"] == "REJECTED"
    assert original["component_id"] is None
    assert original["rationale"].startswith("redirected:")
    assert "wrong peer" in original["rationale"]

    # New MANUAL PENDING row
    new_rows = conn.execute(
        "SELECT * FROM component_reconciliation WHERE id != ? ORDER BY id",
        (rid,),
    ).fetchall()
    assert len(new_rows) == 1
    new = new_rows[0]
    assert new["status"] == "PENDING"
    assert new["method"] == "MANUAL"
    assert new["component_id"] is None
    assert new["source_component_id"] == sid_a
    evidence = json.loads(new["evidence_json"])
    assert evidence["relationship"] == "identity"
    assert evidence["redirect_from"] == rid
    assert evidence["target_source_component_id"] == sid_b
    assert evidence["review_needed"] is True

    # Return value should reflect the original (rejected) row
    assert result["id"] == rid
    assert result["status"] == "REJECTED"


def test_redirect_missing_source_id_raises(conn):
    from app.services.review import decide_reconciliation

    sid = _insert_source_component(
        conn,
        source_system="PLM",
        source_reference="X-1",
        normalized_reference="X-1",
    )
    rid = _insert_pending_reconciliation(
        conn,
        source_component_id=sid,
        evidence={"relationship": "identity", "cluster_members": []},
    )

    with pytest.raises(ValueError, match="redirect_source_id"):
        decide_reconciliation(
            conn, "component", rid, "redirect", rationale="move it"
        )


# ---------------------------------------------------------------------------
# Guard rails
# ---------------------------------------------------------------------------


def test_decide_on_accepted_raises(conn):
    from app.services.review import decide_reconciliation

    sid = _insert_source_component(
        conn,
        source_system="PLM",
        source_reference="X-1",
        normalized_reference="X-1",
    )
    rid = _insert_pending_reconciliation(
        conn,
        source_component_id=sid,
        evidence={"relationship": "identity", "cluster_members": []},
    )
    decide_reconciliation(conn, "component", rid, "accept")

    with pytest.raises(ValueError):
        decide_reconciliation(conn, "component", rid, "reject", rationale="nope")


def test_decide_on_rejected_raises(conn):
    from app.services.review import decide_reconciliation

    sid = _insert_source_component(
        conn,
        source_system="PLM",
        source_reference="X-1",
        normalized_reference="X-1",
    )
    rid = _insert_pending_reconciliation(
        conn,
        source_component_id=sid,
        evidence={"relationship": "identity", "cluster_members": []},
    )
    decide_reconciliation(conn, "component", rid, "reject", rationale="no")

    with pytest.raises(ValueError):
        decide_reconciliation(conn, "component", rid, "accept")


def test_unknown_entity_type_raises(conn):
    from app.services.review import decide_reconciliation

    with pytest.raises(ValueError, match="entity_type"):
        decide_reconciliation(conn, "widget", 1, "accept")


def test_unknown_action_raises(conn):
    from app.services.review import decide_reconciliation

    sid = _insert_source_component(
        conn,
        source_system="PLM",
        source_reference="X-1",
        normalized_reference="X-1",
    )
    rid = _insert_pending_reconciliation(
        conn,
        source_component_id=sid,
        evidence={"relationship": "identity", "cluster_members": []},
    )

    with pytest.raises(ValueError, match="action"):
        decide_reconciliation(conn, "component", rid, "approve")
