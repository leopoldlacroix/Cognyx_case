---
phase: 02-entity-resolution-reconciliation_engine
plan: 01
subsystem: normalization
tags: [erp, supplier-mapping, uom, sqlite, normalization, NORM-05]

requires:
  - phase: 01-data-foundation-ingest-normalize
    provides: schema, ingestion warnings pattern, load_normalization_config, erp_material/erp_supplier tables
provides:
  - erp_supplier.supplier_id_normalized column with safe ALTER/backfill
  - normalize_erp_materials() supplier ID → supplier_name_normalized mapping
  - normalize_erp_materials() UOM standardization via config/normalization.json aliases
  - soft warnings for unmatched suppliers and unknown UOMs
  - db_connection pytest fixture alias
affects: [02-02, 02-03, entity-resolution, reconciliation]

tech-stack:
  added: []
  patterns: [post-ingest normalization pass, soft warnings via add_warning, strip+upper ID compare]

key-files:
  created: []
  modified:
    - app/db/schema.py
    - app/services/normalization.py
    - tests/conftest.py
    - tests/test_normalization.py

key-decisions:
  - "supplier_id_normalized uses UPPER(TRIM(supplier_id_raw)) to match lookup compare (not full normalize_reference punctuation)"
  - "Known UOMs = alias keys ∪ alias values so canonical EA counts as known"
  - "Did not hook normalize_erp_materials into ingest_all_files — mapping stays a separate normalization pass; tests invoke it directly"
  - "db_connection is an alias of conn (smallest fixture fix)"

patterns-established:
  - "ERP supplier ID backfill at schema create (ALTER if absent) and again at start of normalize_erp_materials"
  - "Unknown UOM kept as uppercased raw value with unknown_uom soft warning"

issues-created: []

duration: 25min
completed: 2026-09-23
---

# Plan 02-01: Normalize ERP Materials Summary

**ERP materials get supplier_name_normalized from supplier-master ID lookup and base_unit_normalized from config UOM aliases, with soft warnings for unmatched suppliers and unknown UOMs**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-09-23T16:21:00+02:00
- **Completed:** 2026-09-23T16:45:00+02:00
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Added `erp_supplier.supplier_id_normalized` with CREATE-time definition, safe ALTER for existing DBs, and strip+upper backfill
- `normalize_erp_materials()` maps `supplier_id_raw` → `supplier_name_normalized` (NULL + `unmatched_supplier` warning when no match)
- Same pass standardizes `base_unit_raw` via `config/normalization.json` UOM aliases; unknown UOMs stay uppercased with `unknown_uom` warning
- ERP tests pass via `db_connection` alias and FK-safe source_file setup

## Task Commits

Each task was committed atomically:

1. **Task 2.1.1: ERP supplier ID → supplier name mapping** - `0922a8e` (feat)
2. **Task 2.1.2: ERP material UOM standardization** - `eb512e4` (feat)

## Files Created/Modified
- `app/db/schema.py` — `supplier_id_normalized` column, `_ensure_column`, backfill, index
- `app/services/normalization.py` — `normalize_erp_materials()` supplier + UOM behavior
- `tests/conftest.py` — `db_connection` alias of `conn`
- `tests/test_normalization.py` — ERP supplier/UOM tests (FK parent rows, assertions)

## Decisions Made
- Lookup comparison stays strip+upper (aligned with plan sample), not full `normalize_reference`
- Canonical alias targets (e.g. EA) count as known UOMs so stats match acceptance tests
- Left ingestion alone: no `ingest_all_files` hook; normalization remains a separate callable pass

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Missing `erp_supplier.supplier_id_normalized` column**
- **Found during:** Task 2.1.1 (supplier mapping)
- **Issue:** Draft `normalize_erp_materials()` queried a column that did not exist; plan 02-03 was the original owner, but this blocked 02-01 acceptance
- **Fix:** Added column to CREATE TABLE, `_ensure_column` ALTER when absent, schema backfill + runtime backfill before lookup
- **Files modified:** `app/db/schema.py`, `app/services/normalization.py`
- **Verification:** Supplier mapping tests pass
- **Committed in:** `0922a8e` (Task 2.1.1)

**2. [Rule 3 - Blocking] Missing `db_connection` pytest fixture**
- **Found during:** Task 2.1.1
- **Issue:** ERP tests requested `db_connection`; conftest only provided `conn`
- **Fix:** Added `db_connection` as alias of `conn`
- **Files modified:** `tests/conftest.py`
- **Verification:** Fixture resolves; ERP tests collect and run
- **Committed in:** `0922a8e` (Task 2.1.1)

**3. [Rule 2 - Missing Critical] ERP tests failed FK + wrong material id lookup**
- **Found during:** Task 2.1.1 / 2.1.2
- **Issue:** Inserts used `source_file_id=1` without a `source_file` row (FK failure); match test queried `erp_material.id = 2` for a single inserted row
- **Fix:** Insert `source_file` parent in ERP tests; query by `material_id_raw`
- **Files modified:** `tests/test_normalization.py`
- **Verification:** All three ERP tests pass
- **Committed in:** `0922a8e` / `eb512e4`

**4. [Rule 2 - Missing Critical] Canonical EA counted as unknown UOM**
- **Found during:** Task 2.1.2
- **Issue:** Stats treated only alias *keys* as known, so already-canonical `EA` inflated `uom_unknown`
- **Fix:** Known set = alias keys ∪ alias values; emit `unknown_uom` soft warning for the rest
- **Files modified:** `app/services/normalization.py`, `tests/test_normalization.py`
- **Verification:** `test_erp_uom_standardization` expects 4 normalized / 1 unknown and passes
- **Committed in:** `eb512e4` (Task 2.1.2)

### Deferred Enhancements

None — did not expand into 02-02–02-05 (language, extraction, reconciliation).

---

**Total deviations:** 4 auto-fixed (2 blocking, 2 missing critical), 0 deferred
**Impact on plan:** All fixes required for acceptance criteria / green tests. No architectural expansion.

## Issues Encountered
- Partial draft already present (`normalize_erp_materials` + ERP tests); extended/fixed rather than rewritten
- `ingestion.py` listed in plan `files_modified` but left untouched — separate normalization pass is sufficient

## Next Phase Readiness
- ERP material supplier names and UOMs can be normalized on demand via `normalize_erp_materials(conn)`
- Ready for downstream entity resolution plans that depend on normalized ERP fields
- Note: live pipeline still needs an explicit call to `normalize_erp_materials` after ingest (not wired into `ingest_all_files`)

---
*Phase: 02-entity-resolution-reconciliation_engine*
*Completed: 2026-09-23*
