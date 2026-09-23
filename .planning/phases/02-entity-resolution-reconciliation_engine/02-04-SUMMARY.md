---
phase: 02-entity-resolution-reconciliation_engine
plan: 04
subsystem: reconciliation
tags: [identity, alias, entity-resolution, RECON-01, SCEN-B, D-2.3]

requires:
  - phase: 02-entity-resolution-reconciliation_engine
    plan: 03
    provides: source_component, source_supplier, component_reconciliation, supplier_reconciliation, reconciliation_run
provides:
  - detect_component_identities() clustering by normalized_reference
  - detect_supplier_identities() with apply_supplier_aliases before match
  - record_reconciliation() idempotent insert helper
  - run_entity_resolution() orchestrator + python -m entry point
affects: [02-05, phase-3-canonical, review-workflow]

tech-stack:
  added: []
  patterns: [source-entity-only identity queries, PENDING/NORMALIZED|EXACT, evidence_json cluster members, idempotent source+method+evidence]

key-files:
  created:
    - app/services/reconciliation.py
    - tests/test_reconciliation.py
  modified: []

key-decisions:
  - "Cluster source_component by normalized_reference; one PENDING row per cluster member with evidence listing other members"
  - "Alias-driven shared normalized_reference → method NORMALIZED; byte-identical after generic norm with no alias → EXACT"
  - "Supplier match key = apply_supplier_aliases(normalized_reference) so SIEMENS ↔ SIEMENS MOBILITY"
  - "MAT-10001 is NOT an identity match under current alias evidence (see Deviations)"

patterns-established:
  - "D-2.3: identity detectors query source_component/source_supplier only"
  - "Idempotency keyed on (source_*_id, method, evidence_json)"
  - "reconciliation_run created before detectors; status COMPLETED with counts"

issues-created: []

duration: 25min
completed: 2026-09-23
---

# Plan 02-04: Entity Resolution — Identity & Alias Detection Summary

**Identity/alias detection runs on `source_component` / `source_supplier` only: clusters share a normalized key, write PENDING reconciliation rows with EXACT/NORMALIZED method and 0.95 confidence, and stay idempotent across re-runs.**

## Performance

- **Duration:** ~25 min
- **Completed:** 2026-09-23
- **Tasks:** 3
- **Files created:** 2

## Accomplishments
- Implemented `record_reconciliation()` inserting into `component_reconciliation` / `supplier_reconciliation` (`component_id`/`supplier_id` NULL; evidence dict → `evidence_json`)
- Implemented `detect_component_identities()`: group by `normalized_reference`; clusters with ≥2 members get one PENDING row each; method EXACT vs NORMALIZED
- Implemented `detect_supplier_identities()` with `apply_supplier_aliases` on both sides before grouping (SIEMENS ↔ SIEMENS MOBILITY)
- Implemented `run_entity_resolution()` creating `reconciliation_run` rows (entity_type component/supplier, COMPLETED + counts) then both detectors; thin `python -m app.services.reconciliation` entry point
- Tests cover shared-normalized clusters, idempotency, D-2.3 (empty raw tables), supplier exact + alias, orchestrator

## Task Commits

1. **Task 2.4.1: Component identity detection** — `717363c` (feat)
2. **Task 2.4.2: Supplier identity detection** — `602fdde` (feat)
3. **Task 2.4.3: Entity resolution orchestrator** — `3946b86` (feat)

## Files Created/Modified
- `app/services/reconciliation.py` — detectors, `record_reconciliation`, `run_entity_resolution`, `__main__`
- `tests/test_reconciliation.py` — identity, supplier alias, orchestrator tests

## Deviations
- **MAT-10001 is not an identity match under current alias evidence.** `reference_aliases` map CTRL-AIR01 / CTRL-AIR-O1 / CTRL-HVAC-001 onto CTRL-AIR-01, so those PLM source components cluster as identity (SCEN-B for this plan). ERP `MAT-10001` is not in `reference_aliases`; its `normalized_reference` stays `MAT-10001`, so it does not share a normalized_reference with CTRL-AIR-01. Description similarity / functional linking is deferred to plan 02-05 — do not force that link here.
- **Clustering scheme (vs plan snippet PLM∩ERP pairwise loop):** group all `source_component` rows by `normalized_reference` (covers same-system alias clusters and cross-system equal norms). One reconciliation row per cluster member.
- **Supplier aliases applied at detection time** (plan sample loaded aliases but never applied them).

## Verification

```
python3 -m pytest tests/ -v -k "reconcil" --tb=short
→ 15 passed, 85 deselected

python3 -m pytest tests/test_extraction.py tests/test_normalization.py tests/test_schema.py -v --tb=short
→ 47 passed
```
