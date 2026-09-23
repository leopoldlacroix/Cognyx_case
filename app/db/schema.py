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
            line_status_raw TEXT,
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

    # Existing databases created before line_status_raw was added.
    _ensure_column(conn, "plm_bom_line", "line_status_raw", "TEXT")

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
            language_normalized TEXT,
            author TEXT,
            date TEXT,
            note_text TEXT NOT NULL,
            note_text_normalized TEXT,
            FOREIGN KEY (source_file_id) REFERENCES source_file(id)
        )
    """)

    # Existing DBs created before note normalization columns: add if absent
    _ensure_column(conn, 'engineering_note', 'language_normalized', 'TEXT')
    _ensure_column(conn, 'engineering_note', 'note_text_normalized', 'TEXT')

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
    # SOURCE ASSEMBLY VARIANT JUNCTION (variant linkage only here)
    # ============================================================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS source_assembly_variant (
            id INTEGER PRIMARY KEY,
            source_assembly_id INTEGER NOT NULL,
            variant_ref_normalized TEXT NOT NULL,
            created_at DATETIME NOT NULL,
            FOREIGN KEY (source_assembly_id) REFERENCES source_assembly(id),
            UNIQUE(source_assembly_id, variant_ref_normalized)
        )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_source_assembly_variant_assembly
        ON source_assembly_variant(source_assembly_id)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_source_assembly_variant_reference
        ON source_assembly_variant(variant_ref_normalized)
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

    # ============================================================
    # RECONCILIATION RUN (batch execution traceability)
    # ============================================================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reconciliation_run (
            id INTEGER PRIMARY KEY,
            entity_type TEXT NOT NULL,
            started_at DATETIME NOT NULL,
            completed_at DATETIME,
            status TEXT NOT NULL DEFAULT 'QUEUED',
            items_processed INTEGER NOT NULL DEFAULT 0,
            items_assessed INTEGER NOT NULL DEFAULT 0,
            items_needing_review INTEGER NOT NULL DEFAULT 0,
            error_count INTEGER NOT NULL DEFAULT 0,
            created_by TEXT
        )
    """)

    # ============================================================
    # COMPONENT RECONCILIATION
    # Deviation (Phase 2): component_id is nullable without FK to
    # canonical `component` (created in Phase 3). FKs to
    # source_component and reconciliation_run are enforced.
    # Status: PENDING | ASSESSED | ACCEPTED | REJECTED
    # Method: EXACT | NORMALIZED | STRUCTURED | SEMANTIC | LLM | MANUAL
    # ============================================================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS component_reconciliation (
            id INTEGER PRIMARY KEY,
            source_component_id INTEGER NOT NULL,
            component_id INTEGER,
            status TEXT NOT NULL DEFAULT 'PENDING',
            method TEXT,
            confidence REAL,
            rationale TEXT,
            evidence_json TEXT,
            reconciliation_run_id INTEGER,
            created_at DATETIME NOT NULL,
            decided_at DATETIME,
            decided_by TEXT,
            FOREIGN KEY (source_component_id) REFERENCES source_component(id),
            FOREIGN KEY (reconciliation_run_id) REFERENCES reconciliation_run(id)
        )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_component_reconciliation_source
        ON component_reconciliation(source_component_id)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_component_reconciliation_status
        ON component_reconciliation(status)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_component_reconciliation_canonical
        ON component_reconciliation(component_id)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_component_reconciliation_run
        ON component_reconciliation(reconciliation_run_id)
    """)

    # ============================================================
    # ASSEMBLY RECONCILIATION
    # Deviation: assembly_id nullable without FK to canonical assembly.
    # ============================================================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS assembly_reconciliation (
            id INTEGER PRIMARY KEY,
            source_assembly_id INTEGER NOT NULL,
            assembly_id INTEGER,
            status TEXT NOT NULL DEFAULT 'PENDING',
            method TEXT,
            confidence REAL,
            rationale TEXT,
            evidence_json TEXT,
            reconciliation_run_id INTEGER,
            created_at DATETIME NOT NULL,
            decided_at DATETIME,
            decided_by TEXT,
            FOREIGN KEY (source_assembly_id) REFERENCES source_assembly(id),
            FOREIGN KEY (reconciliation_run_id) REFERENCES reconciliation_run(id)
        )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_assembly_reconciliation_source
        ON assembly_reconciliation(source_assembly_id)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_assembly_reconciliation_status
        ON assembly_reconciliation(status)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_assembly_reconciliation_canonical
        ON assembly_reconciliation(assembly_id)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_assembly_reconciliation_run
        ON assembly_reconciliation(reconciliation_run_id)
    """)

    # ============================================================
    # SUPPLIER RECONCILIATION
    # Deviation: supplier_id nullable without FK to canonical supplier.
    # ============================================================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS supplier_reconciliation (
            id INTEGER PRIMARY KEY,
            source_supplier_id INTEGER NOT NULL,
            supplier_id INTEGER,
            status TEXT NOT NULL DEFAULT 'PENDING',
            method TEXT,
            confidence REAL,
            rationale TEXT,
            evidence_json TEXT,
            reconciliation_run_id INTEGER,
            created_at DATETIME NOT NULL,
            decided_at DATETIME,
            decided_by TEXT,
            FOREIGN KEY (source_supplier_id) REFERENCES source_supplier(id),
            FOREIGN KEY (reconciliation_run_id) REFERENCES reconciliation_run(id)
        )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_supplier_reconciliation_source
        ON supplier_reconciliation(source_supplier_id)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_supplier_reconciliation_status
        ON supplier_reconciliation(status)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_supplier_reconciliation_canonical
        ON supplier_reconciliation(supplier_id)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_supplier_reconciliation_run
        ON supplier_reconciliation(reconciliation_run_id)
    """)

    # ============================================================
    # CANONICAL ENTITY TABLES (Phase 3)
    # FKs from reconciliation component_id / assembly_id / supplier_id
    # stay omitted — SQLite cannot add them without a rebuild; Phase 2
    # left them off on purpose.
    # ============================================================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS component (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            category TEXT,
            normalized_reference TEXT,
            created_at DATETIME NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS assembly (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            category TEXT,
            normalized_reference TEXT,
            created_at DATETIME NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS supplier (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            country TEXT,
            normalized_reference TEXT,
            created_at DATETIME NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS variant (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            train_family TEXT,
            market TEXT,
            climate_class TEXT,
            capacity_class TEXT,
            voltage_system TEXT,
            normalized_reference TEXT,
            created_at DATETIME NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bom_relationship (
            id INTEGER PRIMARY KEY,
            variant_id INTEGER NOT NULL,
            assembly_id INTEGER NOT NULL,
            component_id INTEGER NOT NULL,
            quantity REAL,
            unit TEXT,
            source_bom_line_id INTEGER,
            created_at DATETIME NOT NULL,
            UNIQUE(variant_id, assembly_id, component_id, source_bom_line_id)
        )
    """)

    # technical_fact.status: OBSERVED | VALIDATED | CONFLICTING
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS technical_fact (
            id INTEGER PRIMARY KEY,
            entity_type TEXT NOT NULL,
            entity_id INTEGER NOT NULL,
            attribute TEXT NOT NULL,
            value TEXT,
            unit TEXT,
            source_type TEXT,
            source_id TEXT,
            confidence REAL,
            status TEXT NOT NULL,
            created_at DATETIME NOT NULL
        )
    """)

    conn.commit()
