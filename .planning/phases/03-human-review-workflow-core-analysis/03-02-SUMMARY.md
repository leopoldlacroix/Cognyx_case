---
phase: 03-human-review-workflow-core-analysis
plan: 02
subsystem: review-workflow
tags: [reconciliation, review, filters, confidence-bands, json_extract, SQLite, TDD]

requires:
  - phase: 03-human-review-workflow-core-analysis
    provides: decide_reconciliation(), canonical tables, PENDING reconciliation rows with evidence_json.relationship
provides:
  - list_reconciliations() filterable queue by entity_type, status, confidence_band, method, source_system, relationship
  - CONFIDENCE_BANDS dict (strong/likely/uncertain/weak) for shared report import
affects: [03-05-cli-review, core-reports]

tech-stack:
  added: []
  patterns: [json_extract on evidence_json, join recon→source for source_system, AND-combined optional filters]

key-files:
  created: []
  modified:
    - app/services/review.py
    - tests/test_review.py

key-decisions:
  - "CONFIDENCE_BANDS kept as one module-level dict: strong>=0.90, likely 0.75–0.89, uncertain 0.50–0.74, weak<0.50"
  - "source_system filtered via JOIN to source_* table, never from reconciliation row"
  - "review_needed from json_extract normalized 0/1 → bool; missing key stays None"

patterns-established:
  - "list_reconciliations(conn, entity_type, ...) → {rows, count} with count==len(rows)"
  - "ORDER BY confidence DESC, id ASC"
  - "Unknown entity_type or confidence_band raises ValueError"

issues-created: []

duration: 20min
completed: 2026-09-23
---

# Plan 03-02: Filterable Reconciliation Queue Summary

**`list_reconciliations()` returns a filtered pending queue with confidence bands, source-system join, and relationship/review_needed extracted from evidence_json.**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-09-23T16:45:00Z
- **Completed:** 2026-09-23T17:05:00Z
- **Tasks:** 2 (RED + GREEN; REFACTOR skipped)
- **Files modified:** 2

## Accomplishments
- Added `list_reconciliations()` with AND-combined optional filters (status, confidence_band, method, source_system, relationship)
- Exposed `CONFIDENCE_BANDS` for later report reuse
- Joined source entity tables so source_system / references appear on each row
- Covered empty results, ordering, assembly/supplier entity types, and combined filters without CSV ingest

## TDD Cycle

### RED
- Extended `tests/test_review.py` with fixture seeding and filter cases (entity type, status, bands, method, source system, relationship, combined, order, row shape)
- `python3 -m pytest tests/test_review.py -q` → **15 failed** (ImportError: list_reconciliations), **16 passed** (03-01 intact)
- Commit: `f536fe8` — `test(03-02): add failing test for reconciliation filters`

### GREEN
- Implemented `list_reconciliations()` and `CONFIDENCE_BANDS` in `app/services/review.py`
- Did not change `decide_reconciliation` semantics; no CLI
- `python3 -m pytest tests/test_review.py -q` → **31 passed**
- Commit: `d2c61ca` — `feat(03-02): filter reconciliation queue`

### REFACTOR
- Skipped — GREEN implementation was already clear enough

## Task Commits

1. **RED: Failing filter tests** — `f536fe8` (test)
2. **GREEN: list_reconciliations** — `d2c61ca` (feat)

## Files Created/Modified
- `app/services/review.py` — `list_reconciliations()` + `CONFIDENCE_BANDS`
- `tests/test_review.py` — filter queue coverage (03-01 tests unchanged)

## Decisions Made
- Used SQLite `json_extract` for relationship and review_needed
- Normalized JSON boolean 0/1 from `json_extract` to Python `bool`; absent key remains `None`
- Confidence band bounds live only in `CONFIDENCE_BANDS` in this module

## Deviations from Plan

None - plan executed exactly as written

**Note:** Commit command used `git commit -m "..." -- <path>` (message before `--`) because `git commit -- <path> -m` treats `-m` as a pathspec. Intent preserved: commit only the named path.

---

**Total deviations:** 0 auto-fixed, 0 deferred
**Impact on plan:** None

## Issues Encountered
None

## Next Phase Readiness
- Filterable queue ready for CLI flags in 03-05
- `CONFIDENCE_BANDS` importable by report builders
- `decide_reconciliation` behavior unchanged

---
*Phase: 03-human-review-workflow-core-analysis*
*Completed: 2026-09-23*
