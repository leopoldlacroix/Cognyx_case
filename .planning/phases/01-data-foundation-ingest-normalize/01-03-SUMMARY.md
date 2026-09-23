---
status: complete
plan: 01-03
phase: 01-data-foundation-ingest-normalize
date: 2026-09-23
---

# SUMMARY: Plan 01-03 — Soft Validation Warnings

**Phase:** 1 — Data Foundation: Ingest & Normalize  
**Status:** ✅ Complete  
**Date:** 2026-09-23

---

## What Was Built

Soft validation warnings system: rows with data-quality issues (missing description, unknown UOM, empty supplier, contradictory quantity) are kept in the main source tables but flagged with warnings stored in a dedicated `warnings` table.

### Components Implemented

1. **`add_warning()` function** (`app/services/ingestion.py`)
   - Inserts soft validation warnings into the `warnings` table
   - Records: source_table, source_row_id, warning_type, warning_message, created_at

2. **`get_warnings()` function** (`app/services/ingestion.py`)
   - Returns all warnings, optionally filtered by source_table and/or source_row_id
   - Returns list of dicts for easy consumption

3. **Soft validation wired into ingestion loop** (`app/services/ingestion.py`)
   - `ingest_csv_file()` calls `check_soft_validation()` after hard validation passes
   - Each warning is recorded via `add_warning()` and counted in stats
   - Row continues to insertion regardless of warnings (warnings don't block)

4. **Integration tests** (`tests/test_validation.py`)
   - `test_bom_export_creates_warnings` — verifies real CSV data produces warnings
   - `test_warnings_count_in_ingestion_stats` — verifies stats match actual warnings table
   - `test_get_warnings_filter_by_source_row` — verifies row-level filtering
   - `test_supplier_master_creates_warnings` — verifies warnings work across tables

5. **Fixture fix** (`tests/test_validation.py`)
   - Removed broken class-level `db_path`/`conn` fixtures that collided with conftest
   - `TestQuarantineIntegration` now uses conftest's shared fixtures correctly

---

## Real Data Results

```
=== INGESTION REPORT ===
  bom_export.csv            PLM          rows= 138  Q= 1  W=172
  assembly_master.csv       PLM          rows=  45  Q= 0  W= 90
  variant_configuration.csv PLM          rows=   5  Q= 0  W= 10
  material_master.csv       ERP          rows=  44  Q= 0  W= 88
  supplier_master.csv       ERP          rows=   6  Q= 0  W=  6
  technical_notes.csv       ENGINEERING  rows=  71  Q= 0  W=142
TOTAL: rows=309  Q=1  W=508

=== WARNINGS BY TABLE ===
  plm_bom_line             : 172 - {missing_description: 137, unknown_uom: 35}
  plm_assembly             :  90 - {missing_description: 45, empty_supplier: 45}
  plm_variant              :  10 - {missing_description: 5, empty_supplier: 5}
  erp_material             :  88 - {missing_description: 44, empty_supplier: 44}
  erp_supplier             :   6 - {missing_description: 6}
  engineering_note         : 142 - {missing_description: 71, empty_supplier: 71}
```

508 total warnings across 309 rows. Warning types match the actual data gaps in the CSVs.

---

## Bug Fixed

**Fixture collision in `TestQuarantineIntegration`**: class-level `db_path` and `conn` fixtures were missing the `self` parameter, causing pytest to pass the test instance instead of a path string to `init_database()`. This caused a `TypeError` on all 3 tests in that class. Fixed by removing the class-level fixtures — the class now uses conftest's shared fixtures.

---

## Deviations from Plan

| Plan Item | Deviation |
|-----------|-----------|
| `check_soft_validation` signature | Already existed from pre-existing work (was in validation.py before 01-03 started) |
| Warning storage | Uses existing `warnings` table in schema.py (created during 01-01/01-02 work) |

---

## must_haves Checklist

- [x] Soft validation warnings stored in `warnings` table for rows with missing description, unknown UOM, empty supplier
- [x] Warning types: missing_description, unknown_uom, empty_supplier, contradictory_field
- [x] Warnings queryable via `get_warnings(conn, source_table, source_row_id)` function
- [x] Rows with warnings are still inserted into main source tables (not quarantined)
- [x] Ingestion report includes `warnings_count`
- [x] Unit tests cover all warning types (8 soft validation tests)
- [x] Integration tests verify warnings created for real CSV data (4 integration tests)

---

## Files Modified

- `app/services/ingestion.py` — Added `add_warning()`, `get_warnings()`, wired soft validation into `ingest_csv_file()` loop, updated imports
- `tests/test_validation.py` — Fixed broken fixtures in `TestQuarantineIntegration`, added `TestSoftValidationIntegration` with 4 integration tests

---

## Next Steps

Plan 01-04 (Normalize PLM BOM Lines) can proceed. The normalization step will populate the `_normalized` columns that already exist in the schema (e.g., `component_ref_normalized`, `uom_normalized`, `supplier_normalized`) using the raw values that have been ingested and flagged.
