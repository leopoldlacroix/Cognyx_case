"""
Schema verification tests for Phase 2 source-entity and reconciliation tables.
"""
import sqlite3

import pytest


def _table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def _index_names(conn: sqlite3.Connection, table: str) -> set[str]:
    return {
        row[1]
        for row in conn.execute(f"PRAGMA index_list({table})").fetchall()
    }


def test_source_assembly_variant_junction_table(conn):
    """source_assembly_variant exists with FKs, unique constraint, and indexes."""
    columns = _table_columns(conn, "source_assembly_variant")
    assert columns == {
        "id",
        "source_assembly_id",
        "variant_ref_normalized",
        "created_at",
    }

    # source_assembly stays flat — no variant_ref column
    assembly_cols = _table_columns(conn, "source_assembly")
    assert "variant_ref" not in assembly_cols
    assert "variant_ref_normalized" not in assembly_cols
    assert "variant_ref_raw" not in assembly_cols

    indexes = _index_names(conn, "source_assembly_variant")
    assert "idx_source_assembly_variant_assembly" in indexes
    assert "idx_source_assembly_variant_reference" in indexes

    # Unique (source_assembly_id, variant_ref_normalized) — insert a parent, then collide
    now = "2026-01-01T00:00:00Z"
    conn.execute(
        "INSERT INTO source_assembly "
        "(source_system, source_reference, normalized_reference, description, "
        "source_record_type, source_record_id, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("PLM", "ASM-001", "ASM-001", "Test", "ASSEMBLY_MASTER", 1, now),
    )
    conn.execute(
        "INSERT INTO source_assembly_variant "
        "(source_assembly_id, variant_ref_normalized, created_at) VALUES (?, ?, ?)",
        (1, "VAR-A", now),
    )
    conn.commit()

    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO source_assembly_variant "
            "(source_assembly_id, variant_ref_normalized, created_at) VALUES (?, ?, ?)",
            (1, "VAR-A", now),
        )


def test_low_priority_junction_tables_not_created(conn):
    """note_entity_reference and material_supplier are out of scope for Phase 2."""
    tables = {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    assert "note_entity_reference" not in tables
    assert "material_supplier" not in tables


_RECON_SHARED_COLS = {
    "id",
    "status",
    "method",
    "confidence",
    "rationale",
    "evidence_json",
    "reconciliation_run_id",
    "created_at",
    "decided_at",
    "decided_by",
}


def test_reconciliation_run_table(conn):
    """reconciliation_run matches blueprint §3.7."""
    columns = _table_columns(conn, "reconciliation_run")
    assert columns == {
        "id",
        "entity_type",
        "started_at",
        "completed_at",
        "status",
        "items_processed",
        "items_assessed",
        "items_needing_review",
        "error_count",
        "created_by",
    }


def test_component_reconciliation_table(conn):
    """component_reconciliation matches blueprint §3.6 (no FK to missing canonical)."""
    columns = _table_columns(conn, "component_reconciliation")
    assert columns == _RECON_SHARED_COLS | {"source_component_id", "component_id"}

    indexes = _index_names(conn, "component_reconciliation")
    assert "idx_component_reconciliation_source" in indexes
    assert "idx_component_reconciliation_status" in indexes
    assert "idx_component_reconciliation_canonical" in indexes
    assert "idx_component_reconciliation_run" in indexes

    # confidence is REAL — insert and round-trip a float
    now = "2026-01-01T00:00:00Z"
    conn.execute(
        "INSERT INTO source_component "
        "(source_system, source_reference, normalized_reference, description, "
        "source_record_type, source_record_id, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("PLM", "C-1", "C-1", "x", "BOM_LINE", 1, now),
    )
    conn.execute(
        "INSERT INTO component_reconciliation "
        "(source_component_id, component_id, status, method, confidence, "
        "created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (1, None, "PENDING", "NORMALIZED", 0.95, now),
    )
    conn.commit()
    row = conn.execute(
        "SELECT status, method, confidence, component_id FROM component_reconciliation WHERE id = 1"
    ).fetchone()
    assert row["status"] == "PENDING"
    assert row["method"] == "NORMALIZED"
    assert row["confidence"] == pytest.approx(0.95)
    assert row["component_id"] is None


def test_assembly_reconciliation_table(conn):
    """assembly_reconciliation has source/canonical FKs columns and indexes."""
    columns = _table_columns(conn, "assembly_reconciliation")
    assert columns == _RECON_SHARED_COLS | {"source_assembly_id", "assembly_id"}

    indexes = _index_names(conn, "assembly_reconciliation")
    assert "idx_assembly_reconciliation_source" in indexes
    assert "idx_assembly_reconciliation_status" in indexes
    assert "idx_assembly_reconciliation_canonical" in indexes
    assert "idx_assembly_reconciliation_run" in indexes


def test_supplier_reconciliation_table(conn):
    """supplier_reconciliation has source/canonical FKs columns and indexes."""
    columns = _table_columns(conn, "supplier_reconciliation")
    assert columns == _RECON_SHARED_COLS | {"source_supplier_id", "supplier_id"}

    indexes = _index_names(conn, "supplier_reconciliation")
    assert "idx_supplier_reconciliation_source" in indexes
    assert "idx_supplier_reconciliation_status" in indexes
    assert "idx_supplier_reconciliation_canonical" in indexes
    assert "idx_supplier_reconciliation_run" in indexes


def test_canonical_tables_created_without_recon_fks(conn):
    """Phase 3 canonical tables exist; reconciliation still omits FKs to them."""
    tables = {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    assert "component" in tables
    assert "assembly" in tables
    assert "supplier" in tables
    assert "variant" in tables
    assert "bom_relationship" in tables
    assert "technical_fact" in tables

    # No FK from component_reconciliation.component_id → component
    fks = conn.execute("PRAGMA foreign_key_list(component_reconciliation)").fetchall()
    fk_tables = {row[2] for row in fks}
    assert "component" not in fk_tables
