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
