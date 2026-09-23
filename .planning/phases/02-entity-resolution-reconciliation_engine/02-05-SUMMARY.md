---
phase: 02-entity-resolution-reconciliation_engine
plan: 05
subsystem: reconciliation
tags: [functional-similarity, variant-specific, SCEN-D, SCEN-E, RECON-02, RECON-03, RECON-04]

requires:
  - phase: 02-entity-resolution-reconciliation_engine
    plan: 04
    provides: detect_component_identities, detect_supplier_identities, record_reconciliation, run_entity_resolution
provides:
  - detect_functional_similarity() STRUCTURED/0.50 PENDING with review_needed in evidence
  - detect_variant_specific_differences() Nordic-only via source_assembly_variant
  - record_reconciliation() extended with canonical_id/decided_at/decided_by
  - run_full_reconciliation() orchestrator with counts by relationship and status
affects: [phase-3-canonical, review-workflow, cross-variant-reuse]

tech-stack:
  added: []
  patterns: [three relationship types stay separate, review_needed in evidence_json, Nordic exclude from similarity]

key-files:
  created: []
  modified:
    - app/services/reconciliation.py
    - tests/test_reconciliation.py

key-decisions:
  - "Functional similarity uses STRUCTURED/0.50/PENDING — never NORMALIZED/0.95 identity"
  - "Variant-specific uses STRUCTURED/0.95/PENDING with review_needed=false; intentional specialization"
  - "Nordic refs require plm_variant ∩ source_assembly_variant before BOM exclusivity"
  - "component_id stays nullable without FK to missing canonical component table"

patterns-established:
  - "relationship type lives in evidence_json (identity | functional_similarity | variant_specific)"
  - "Idempotency keyed on (source_*_id, method, evidence_json) across all detectors"
  - "run_full_reconciliation reuses 02-04 detectors; run_entity_resolution kept for 02-04 tests"

issues-created: []

duration: 35min
completed: 2026-09-23
---

# Plan 02-05: Functional Similarity, Variant-Specific & Full Reconciliation Summary

**Functional similarity (SCEN-D) and Nordic variant-specific specialization (SCEN-E) are recorded as separate relationship types with STRUCTURED method; `run_full_reconciliation` runs identity → similarity → variant-specific idempotently.**

## Performance

- **Duration:** ~35 min
- **Completed:** 2026-09-23
- **Tasks:** 4
- **Files modified:** 2

## Accomplishments
- Implemented `detect_functional_similarity()`: same-prefix/different-suffix heuristic; STRUCTURED / 0.50 / PENDING; evidence `relationship=functional_similarity`, `review_needed=true`
- Implemented `detect_variant_specific_differences()`: Nordic variants via case-insensitive name match ∩ `source_assembly_variant`, BOM exclusivity; STRUCTURED / 0.95 / PENDING; evidence `relationship=variant_specific`, `review_needed=false`
- Excluded Nordic-only component refs from functional-similarity pairing
- Extended `record_reconciliation()` with optional `canonical_id`, `decided_at`, `decided_by` (assembly entity_type supported); no new FKs to missing canonical tables
- Implemented `run_full_reconciliation()` creating one `reconciliation_run` (entity_type=full) and returning counts by relationship and status

## Task Commits

1. **Task 2.5.1: Functional similarity** — `a03c952` (feat)
2. **Task 2.5.2: Variant-specific Nordic** — `2c279e7` (feat)
3. **Task 2.5.3: record_reconciliation signature** — `60b9a4e` (feat)
4. **Task 2.5.4: Full reconciliation orchestrator** — `44e1e53` (feat)

## Files Created/Modified
- `app/services/reconciliation.py` — similarity, variant-specific, signature extension, `run_full_reconciliation`
- `tests/test_reconciliation.py` — SCEN-D/E tests, schema/signature tests, full pipeline tests

## Deviations
- **SCEN-D test refs vs primary heuristic:** plan sample code only checks first-two-parts equal / last differs (`CTRL-DOOR-01` vs `CTRL-DOOR-EXP`). Plan acceptance example `STANDARD-DOOR-CTRL` vs `EXPORT-DOOR-CTRL` does not match that rule (different first two parts; same last part). Added secondary heuristic: same last two parts, different first part, so the named acceptance example is covered.
- **Plan SQL precedence bug fixed:** parenthesized ORs and used `LOWER(... ) LIKE '%nordic%'` for case-insensitive match; intersected with `source_assembly_variant` as required by acceptance criteria (plan snippet queried BOM via Nordic plm_variant only).
- **Variant-specific without source_component:** detector still returns records for Nordic-only BOM refs; reconciliation rows are written only when a matching `source_component` exists (fixture inserts both).
- **No schema recreation:** verified 02-03 tables already match blueprint §3.6/§3.7; did not add FKs to missing canonical tables.

## Verification

```
27 passed, 83 deselected  # -k "reconcil or similarity or variant"
68 passed                 # extraction + normalization + schema + reconciliation
```
