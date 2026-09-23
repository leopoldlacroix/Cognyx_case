---
phase: 01
plan: 01-01
subsystem: ingestion
tags: [ingestion, schema, cli, provenance]
key_files:
  created:
    - app/db/schema.py
    - app/db/connection.py
    - app/services/ingestion.py
    - app/backend/cli.py
    - tests/test_ingestion.py
    - tests/conftest.py
    - pyproject.toml
  modified: []
requires:
  - INGEST-01
provides:
  - Database schema for all 6 source tables
  - CSV ingestion with SHA-256 file hashing
  - Full provenance tracking (source_file_id, source_row)
  - Idempotent re-ingestion
  - CLI for ingest and status commands
---

# Phase 01 Plan 01-01: Ingest All 6 CSV Source Files — Summary

**Duration:** ~45 min | **Completed:** 2026-09-23

## One-liner

Built the complete ingestion pipeline: SQLite schema for 6 source tables, SHA-256 file hashing with idempotency, CSV row ingestion preserving raw values with full provenance, and a CLI entry point — all 33 tests passing.

## What was built

### Database schema (`app/db/schema.py`)
- 12 tables: `source_file`, `plm_bom_line`, `plm_assembly`, `plm_variant`, `erp_material`, `erp_supplier`, `engineering_note`, `quarantine`, `warnings`, `source_component`, `source_assembly`, `source_supplier`
- All foreign keys with PRAGMA foreign_keys = ON
- Indexes on normalized reference columns and source_file_hash

### Connection utilities (`app/db/connection.py`)
- `get_connection(db_path)` — sqlite3 connection with foreign_keys pragma and Row factory
- `init_database(db_path)` — creates directory, calls create_schema

### Ingestion service (`app/services/ingestion.py`)
- `compute_file_hash(file_path)` — SHA-256 hex digest
- `register_source_file(conn, system, name, hash, ingested_at)` — INSERT OR IGNORE with duplicate detection via UNIQUE index on (source_system, file_hash)
- `ingest_csv_file(conn, file_path, system, table, column_map)` — CSV parsing with DictReader, source_row starting at 2, NULL for missing optional fields
- `ingest_all_files(conn, base_path)` — discovers and ingests all 6 CSV files
- `get_ingestion_status(conn)` — aggregated row counts per source file
- `get_quarantine_report(conn)` / `get_quarantine_count(conn)` — quarantine queries with provenance JOIN

### CLI (`app/backend/cli.py`)
- `python -m app.backend.cli ingest --db <path>` — ingests all 6 files
- `python -m app.backend.cli status --db <path>` — shows ingestion summary

### Tests (`tests/test_ingestion.py` + `tests/conftest.py`)
- 10 tests covering hash computation (3), file registration (2), CSV ingestion (3), ingestion status (2)
- Fixtures: `db_path`, `conn` (fresh DB with schema), `sample_csv`

### Configuration (`pyproject.toml`)
- pytest configuration with testpaths and naming conventions

## Verification results

All 33 tests pass (10 ingestion + 23 validation, with validation tests added in Plan 01-02).

End-to-end ingestion verified:
- 6 source files registered with SHA-256 hashes
- 138 BOM lines, 45 assemblies, 5 variants, 44 materials, 6 suppliers, 71 engineering notes = 309 total rows
- Raw values byte-identical to CSV: `CTRL-AIR01` typo preserved (source_row=29), `one` quantity preserved (source_row=32), French `Référence` text preserved
- Provenance: every row links to source_file via FK
- Idempotency: re-ingesting same file does not duplicate rows

## Deviations from Plan

None — plan executed exactly as written.

## Requirements completed

- INGEST-01: All 6 CSV files ingested with full provenance

## Commit: docs(01-01): complete ingestion pipeline plan
