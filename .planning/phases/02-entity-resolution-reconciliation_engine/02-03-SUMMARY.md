---
phase: 02-entity-resolution-reconciliation_engine
plan: 03
subsystem: schema-extraction
tags: [source-entities, reconciliation, extraction, junction-table, NORM-05, NORM-06, RECON-04, SCEN-B]

requires:
  - phase: 02-entity-resolution-reconciliation_engine
    provides: supplier_id_normalized, engineering note normalized columns, db_connection fixture (02-01/02-02)
provides:
  - source_assembly_variant junction table
  - reconciliation_run + component/assembly/supplier_reconciliation tables
  - app/services/extraction.py populating source_component/assembly/supplier
  - Downstream plan alignment (02-04 queries source_*; 02-05 canonical status/method/confidence)
affects: [02-04, 02-05, phase-3-canonical]

tech-stack:
  added: []
  patterns: [INSERT OR IGNORE idempotent extraction, nullable canonical FK without Phase-3 table]

key-files:
  created:
    - app/services/extraction.py
    - tests/test_extraction.py
    - tests/test_schema.py
  modified:
    - app/db/schema.py
    - .planning/phases/02-entity-resolution-reconciliation_engine/02-04-PLAN.md
    - .planning/phases/02-entity-resolution-reconciliation_engine/02-05-PLAN.md

key-decisions:
  - "Task 2.3.1 already satisfied by 02-01/02-02 — no empty commit"
  - "Canonical component/assembly/supplier FKs omitted until Phase 3; nullable id columns kept"
  - "ERP source_supplier.normalized_reference prefers supplier_name_normalized for cross-source name matching"

patterns-established:
  - "source_assembly stays flat; variant linkage only in source_assembly_variant"
  - "Reconciliation status PENDING/ASSESSED/ACCEPTED/REJECTED; method EXACT/NORMALIZED/STRUCTURED/SEMANTIC/LLM/MANUAL; confidence REAL"

issues-created: []

duration: 35min
completed: 2026-09-23
---

# Plan 02-03: Schema Refinement + Source Entity Extraction Summary

**Source entity layer completed: junction + reconciliation tables created; extraction populates source_component/assembly/supplier idempotently from normalized raw tables.**

## Performance

- **Duration:** ~35 min
- **Completed:** 2026-09-23
- **Tasks:** 5 (4 commits + 1 already-satisfied)
- **Files modified:** 6

## Accomplishments
- Confirmed Task 2.3.1 schema columns/index/`_ensure_column`/db_connection already delivered by 02-01/02-02
- Added `source_assembly_variant` junction (unique on assembly+variant; source_assembly remains flat)
- Created `reconciliation_run` and three reconciliation tables per blueprint §3.6/§3.7 with indexes
- Implemented `extract_source_*` + `run_source_extraction` with INSERT OR IGNORE idempotency
- Patched 02-04/02-05 plans to query source entities and use canonical reconciliation fields
- Full suite green: extraction + schema + normalization (47 tests)

## Task Commits

1. **Task 2.3.1: Schema columns** — already satisfied, no commit (delivered by 02-01/02-02)
2. **Task 2.3.2: source_assembly_variant** — `e3771fb` (feat)
3. **Task 2.3.3: Reconciliation tables** — `b5b1721` (feat)
4. **Task 2.3.4: Source extraction** — `ffa491c` (feat)
5. **Task 2.3.5: Downstream plan patches** — `12f9740` (docs)

## Files Created/Modified
- `app/db/schema.py` — junction + reconciliation tables
- `app/services/extraction.py` — source entity extraction
- `tests/test_schema.py` — schema verification
- `tests/test_extraction.py` — extraction cases from plan
- `02-04-PLAN.md` / `02-05-PLAN.md` — D-2.3 + canonical schema alignment

## Deviations
- **No FK to canonical `component` / `assembly` / `supplier`:** those tables do not exist until Phase 3. Nullable `component_id` / `assembly_id` / `supplier_id` columns are present without FOREIGN KEY; FKs to `source_*` and `reconciliation_run` are enforced.
- **Task 2.3.1 skipped empty commit** because columns, index, helper, and `db_connection` already existed.
- **ERP supplier normalized_reference** uses `supplier_name_normalized` (fallback `supplier_id_normalized`) so 02-04 name-based identity matching can work against PLM `supplier_normalized`.

## Verification

```
python3 -m pytest tests/test_extraction.py tests/test_schema.py tests/test_normalization.py -v --tb=short
→ 47 passed
```
