---
status: complete
plan: 01-04
phase: 01-data-foundation-ingest-normalize
date: 2026-09-23
---

# SUMMARY: Plan 01-04 — Normalize PLM BOM Lines

**Phase:** 1 — Data Foundation: Ingest & Normalize  
**Status:** ✅ Complete  
**Date:** 2026-09-23

---

## What Was Built

Normalization service that applies deterministic, explainable transformations to ingested data: whitespace collapse, casing standardization (uppercase for identifiers, preserved for descriptions), punctuation harmonization (underscores/dashes/periods → single dash).

### Components Implemented

1. **`app/services/normalization.py`** — normalization module with:
   - `normalize_whitespace(s)` — collapse multiple whitespace to single space, trim
   - `normalize_punctuation(s)` — harmonize `[-_]+` → `-`, collapse whitespace around dashes, strip leading/trailing punctuation
   - `normalize_reference(raw)` — whitespace → uppercase → punctuation (for identifiers)
   - `normalize_description(raw)` — whitespace collapse, preserve case (for descriptions)
   - `normalize_uom(raw)` — whitespace → uppercase (aliases in PLAN-1.5)
   - `normalize_supplier(raw)` — whitespace collapse, preserve case (aliases in PLAN-1.5)
   - All functions handle None/empty gracefully, all deterministic

2. **`_apply_normalization()` in `app/services/ingestion.py`** — called during `ingest_csv_file()` after raw values are mapped, populates `*_normalized` columns:
   - **plm_bom_line**: variant_ref, assembly_ref, component_ref → normalized; description → trimmed; uom → uppercase; supplier → trimmed; quantity → parsed as REAL
   - **plm_assembly**: assembly_ref, variant_ref → normalized; description → trimmed
   - **plm_variant**: variant_ref → normalized; variant_name → trimmed
   - **erp_material**: material_id → normalized; description → trimmed

3. **Tests** (`tests/test_normalization.py`) — 26 tests:
   - Reference normalization: uppercase, whitespace collapse, punctuation harmonization (underscore/double-dash), trim, None/empty handling
   - Description normalization: case preservation, whitespace collapse, trim, None/empty
   - UOM: uppercase, whitespace trim, None
   - Supplier: whitespace collapse, trim, None
   - Determinism: same input → same output
   - Helper functions: whitespace collapse, punctuation harmonization

---

## Key Behavior

| Input | normalize_reference | normalize_description |
|-------|---------------------|----------------------|
| `'  Ctrl_AIR-01  '` | `'CTRL-AIR-01'` | `'Ctrl_AIR-01'` |
| `'CTRL  -  AIR-01'` | `'CTRL-AIR-01'` | `'CTRL  -  AIR-01'` |
| `'CTRL__AIR__01'` | `'CTRL-AIR-01'` | `'CTRL__AIR__01'` |
| `'HVAC   Control  Unit'` | `'HVAC   CONTROL   UNIT'` | `'HVAC Control Unit'` |
| `None` | `None` | `None` |

References get uppercase + punctuation harmonization. Descriptions get whitespace cleanup only (case preserved).

---

## Real Data Results (from test suite verification)

64/64 tests pass across all three test files (ingestion + normalization + validation).

---

## Deviations from Plan

| Plan Item | Deviation |
|-----------|-----------|
| `normalize_reference` whitespace handling | Plan said `normalize_whitespace` then `upper()` then `normalize_punctuation`. The punctuation function now also collapses whitespace around dashes (e.g., `'CTRL  -  AIR-01'` → `'CTRL-AIR-01'`) — this is strictly better than the plan's two-step approach |
| `normalize_bom_row()` function | Not created as a separate function; normalization is inlined in `_apply_normalization()` which handles all tables uniformly |

---

## must_haves Checklist

- [x] Normalization functions for reference, description, UOM, supplier fields
- [x] Generic rules: whitespace collapse, casing standardization (uppercase for identifiers), punctuation harmonization
- [x] Normalized values stored in `*_normalized` columns alongside raw values
- [x] Raw values preserved exactly as in CSV
- [x] quantity_normalized parsed as REAL when possible
- [x] All normalization functions are deterministic
- [x] Unit tests verify each normalization function (26 tests)
- [x] Integration verified via existing ingestion tests that query normalized columns

---

## Files Modified

- `app/services/normalization.py` — new module with normalization functions
- `app/services/ingestion.py` — added imports, `_apply_normalization()`, call in ingest loop
- `tests/test_normalization.py` — 26 unit tests for normalization

---

## Next Steps

Plan 01-05 (Apply UOM/Supplier/Reference Aliases) can proceed. This will add config-driven alias mapping on top of the generic normalization already in place — e.g., mapping `CTRL-AIR-01` → `CTRL-AIR-001` or `PCS` → `EA` via a configuration file.
