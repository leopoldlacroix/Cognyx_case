"""
Database schema for Cognyx BOM Reuse Explorer.

Creates all source ingestion tables and source entity tables.
"""
import sqlite3


def _ensure_column(
    conn: sqlite3.Connection,
    table: str,
    column: str,
    col_type: str,
) -> None:
    """Add a column to an existing table if it is missing (safe for already-created DBs)."""
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    existing = {row[1] for row in rows}
    if column not in existing:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")


def create_schema(conn: sqlite3.Connection) -> None:
    """Create all tables for the Cognyx data model."""
    cursor = conn.cursor()

    # Enable foreign key enforcement
    cursor.execute("PRAGMA foreign_keys = ON")

    # ============================================================
    # SOURCE FILE TABLE
    # ============================================================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS source_file (
            id INTEGER PRIMARY KEY,
            source_system TEXT NOT NULL,
            file_name TEXT NOT NULL,
            file_hash TEXT,
            ingested_at DATETIME NOT NULL
        )
    """)

    cursor.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_source_file_system_hash
        ON source_file(source_system, file_hash)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_source_file_hash
        ON source_file(file_hash, source_system)
    """)

    # ============================================================
    # PLM BOM LINE TABLE
    # ============================================================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS plm_bom_line (
            id INTEGER PRIMARY KEY,
            source_file_id INTEGER NOT NULL,
            source_row INTEGER NOT NULL,
            variant_ref_raw TEXT NOT NULL,
            assembly_ref_raw TEXT NOT NULL,
            component_ref_raw TEXT NOT NULL,
            description_raw TEXT,
            quantity_raw TEXT,
            uom_raw TEXT,
            supplier_raw TEXT,
            variant_ref_normalized TEXT,
            assembly_ref_normalized TEXT,
            component_ref_normalized TEXT,
            description_normalized TEXT,
            quantity_normalized REAL,
            uom_normalized TEXT,
            supplier_normalized TEXT,
            FOREIGN KEY (source_file_id) REFERENCES source_file(id)
        )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_plm_bom_line_variant_normalized
        ON plm_bom_line(variant_ref_normalized)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_plm_bom_line_component_normalized
        ON plm_bom_line(component_ref_normalized)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_plm_bom_line_supplier_normalized
        ON plm_bom_line(supplier_normalized)
    """)

    # ============================================================
    # PLM ASSEMBLY TABLE
    # ============================================================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS plm_assembly (
            id INTEGER PRIMARY KEY,
            source_file_id INTEGER NOT NULL,
            source_row INTEGER NOT NULL,
            assembly_ref_raw TEXT NOT NULL,
            assembly_description_raw TEXT,
            variant_ref_raw TEXT,
            revision_raw TEXT,
            lifecycle_raw TEXT,
            assembly_ref_normalized TEXT,
            assembly_description_normalized TEXT,
            variant_ref_normalized TEXT,
            FOREIGN KEY (source_file_id) REFERENCES source_file(id)
        )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_plm_assembly_ref_normalized
        ON plm_assembly(assembly_ref_normalized)
    """)

    # ============================================================
    # PLM VARIANT TABLE
    # ============================================================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS plm_variant (
            id INTEGER PRIMARY KEY,
            source_file_id INTEGER NOT NULL,
            source_row INTEGER NOT NULL,
            variant_ref_raw TEXT NOT NULL,
            variant_name_raw TEXT,
            train_family_raw TEXT,
            market_raw TEXT,
            climate_class_raw TEXT,
            capacity_class_raw TEXT,
            voltage_system_raw TEXT,
            notes_raw TEXT,
            variant_ref_normalized TEXT,
            variant_name_normalized TEXT,
            FOREIGN KEY (source_file_id) REFERENCES source_file(id)
        )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_plm_variant_ref_normalized
        ON plm_variant(variant_ref_normalized)
    """)

    # ============================================================
    # ERP MATERIAL TABLE
    # ============================================================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS erp_material (
            id INTEGER PRIMARY KEY,
            source_file_id INTEGER NOT NULL,
            source_row INTEGER NOT NULL,
            material_id_raw TEXT NOT NULL,
            description_raw TEXT,
            material_type_raw TEXT,
            base_unit_raw TEXT,
            supplier_id_raw TEXT,
            category_raw TEXT,
            status_raw TEXT,
            cost_raw REAL,
            material_id_normalized TEXT,
            description_normalized TEXT,
            supplier_name_normalized TEXT,
            base_unit_normalized TEXT,
            FOREIGN KEY (source_file_id) REFERENCES source_file(id)
        )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_erp_material_id_normalized
        ON erp_material(material_id_normalized)
    """)

    # ============================================================
    # ERP SUPPLIER TABLE
    # ============================================================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS erp_supplier (
            id INTEGER PRIMARY KEY,
            source_file_id INTEGER NOT NULL,
            source_row INTEGER NOT NULL,
            supplier_id_raw TEXT NOT NULL,
            supplier_name_raw TEXT,
            country_raw TEXT,
            supplier_id_normalized TEXT,
            supplier_name_normalized TEXT,
            FOREIGN KEY (source_file_id) REFERENCES source_file(id)
        )
    """)

    # Existing DBs created before supplier_id_normalized: add column if absent
    _ensure_column(conn, 'erp_supplier', 'supplier_id_normalized', 'TEXT')

    # Backfill normalized IDs (strip + upper — same comparison as ERP material lookup)
    cursor.execute("""
        UPDATE erp_supplier
        SET supplier_id_normalized = UPPER(TRIM(supplier_id_raw))
        WHERE supplier_id_normalized IS NULL
          AND supplier_id_raw IS NOT NULL
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_erp_supplier_name_normalized
        ON erp_supplier(supplier_name_normalized)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_erp_supplier_id_normalized
        ON erp_supplier(supplier_id_normalized)
    """)

    # ============================================================
    # ENGINEERING NOTE TABLE
    # ============================================================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS engineering_note (
            id INTEGER PRIMARY KEY,
            source_file_id INTEGER NOT NULL,
            source_row INTEGER NOT NULL,
            object_reference_raw TEXT NOT NULL,
            object_type TEXT NOT NULL,
            language TEXT,
            author TEXT,
            date TEXT,
            note_text TEXT NOT NULL,
            FOREIGN KEY (source_file_id) REFERENCES source_file(id)
        )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_engineering_note_object_ref
        ON engineering_note(object_reference_raw, object_type)
    """)

    # ============================================================
    # QUARANTINE TABLE (for hard validation failures)
    # ============================================================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS quarantine (
            id INTEGER PRIMARY KEY,
            source_file_id INTEGER NOT NULL,
            source_row INTEGER NOT NULL,
            raw_data TEXT NOT NULL,
            rejection_reason TEXT NOT NULL,
            created_at DATETIME NOT NULL,
            FOREIGN KEY (source_file_id) REFERENCES source_file(id)
        )
    """)

    # ============================================================
    # WARNINGS TABLE (for soft validation warnings)
    # ============================================================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS warnings (
            id INTEGER PRIMARY KEY,
            source_table TEXT NOT NULL,
            source_row_id INTEGER NOT NULL,
            warning_type TEXT NOT NULL,
            warning_message TEXT NOT NULL,
            created_at DATETIME NOT NULL
        )
    """)

    # ============================================================
    # SOURCE COMPONENT TABLE
    # ============================================================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS source_component (
            id INTEGER PRIMARY KEY,
            source_system TEXT NOT NULL,
            source_reference TEXT NOT NULL,
            normalized_reference TEXT,
            description TEXT,
            source_record_type TEXT NOT NULL,
            source_record_id INTEGER NOT NULL,
            created_at DATETIME NOT NULL,
            UNIQUE(source_system, source_reference)
        )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_source_component_normalized
        ON source_component(normalized_reference)
    """)

    # ============================================================
    # SOURCE ASSEMBLY TABLE
    # ============================================================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS source_assembly (
            id INTEGER PRIMARY KEY,
            source_system TEXT NOT NULL,
            source_reference TEXT NOT NULL,
            normalized_reference TEXT,
            description TEXT,
            source_record_type TEXT NOT NULL,
            source_record_id INTEGER NOT NULL,
            created_at DATETIME NOT NULL,
            UNIQUE(source_system, source_reference)
        )
    """)

    # ============================================================
    # SOURCE SUPPLIER TABLE
    # ============================================================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS source_supplier (
            id INTEGER PRIMARY KEY,
            source_system TEXT NOT NULL,
            source_reference TEXT NOT NULL,
            normalized_reference TEXT,
            description TEXT,
            source_record_type TEXT NOT NULL,
            source_record_id INTEGER NOT NULL,
            created_at DATETIME NOT NULL,
            UNIQUE(source_system, source_reference)
        )
    """)

    conn.commit()
