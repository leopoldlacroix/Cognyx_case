---
phase: 03-human-review-workflow-core-analysis
plan: 01
subsystem: review-workflow
tags: [reconciliation, review, accept, reject, redirect, canonical-tables, SQLite, TDD]

requires:
  - phase: 02-entity-resolution-reconciliation_engine
    provides: PENDING reconciliation rows, evidence_json.relationship, record_reconciliation insert-only, nullable component_id/assembly_id/supplier_id without FK
provides:
  - decide_reconciliation() accept/reject/redirect on PENDING rows
  - canonical component, assembly, supplier, variant, bom_relationship, technical_fact tables
  - Identity accept reuses cluster-peer canonical id; functional_similarity stays unmerged; variant_specific gets own canonical
affects: [03-02-canonical-bom, 03-03-core-reports, 03-05-cli-review]

tech-stack:
  added: []
  patterns: [UPDATE for decisions INSERT only for redirect, relationship branching from evidence_json, no FK from recon to canonical]

key-files:
  created:
    - app/services/review.py
    - tests/test_review.py
  modified:
    - app/db/schema.py
    - tests/test_schema.py

key-decisions:
  - "Accept/reject/redirect UPDATE the existing row; never call record_reconciliation for the decision"
  - "Identity accept reuses ACCEPTED peer canonical id when peer source id is in evidence cluster_members"
  - "Functional similarity accept sets ACCEPTED with component_id NULL"
  - "Variant-specific accept always creates a new canonical for that source only"
  - "Redirect REJECTS original with redirected: prefix and INSERTs MANUAL PENDING with redirect evidence"
  - "Canonical FKs from reconciliation id columns stay omitted"

patterns-established:
  - "decide_reconciliation(conn, entity_type, reconciliation_id, action, ...) is the review gate"
  - "Second decision on ACCEPTED/REJECTED raises ValueError (fail closed)"
  - "Canonical create uses source entity normalized_reference as name and normalized_reference"

issues-created: []

duration: 25min
completed: 2026-09-23
---

# Plan 03-01: Reconciliation Accept / Reject / Redirect Summary

**Human review decisions update PENDING reconciliation rows; identity accept shares one canonical id across cluster peers while similarity stays unmerged and variant-specific gets its own component.**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-09-23T16:41:00Z
- **Completed:** 2026-09-23T17:05:00Z
- **Tasks:** 2 (RED + GREEN; REFACTOR skipped)
- **Files modified:** 4

## Accomplishments
- Added canonical tables: `component`, `assembly`, `supplier`, `variant`, `bom_relationship`, `technical_fact` via idempotent `CREATE TABLE IF NOT EXISTS`
- Implemented `decide_reconciliation()` for accept / reject / redirect with relationship-aware canonical assignment
- Identity cluster peers reuse one canonical id; functional_similarity never creates a shared component; variant_specific always creates its own
- Reject requires rationale; redirect rejects original and inserts MANUAL PENDING; decided rows fail closed on re-decision

## TDD Cycle

### RED
- Wrote `tests/test_review.py` covering schema presence, identity accept + peer reuse, functional_similarity null canonical, variant_specific own canonical, reject/redirect, and guard rails
- `python3 -m pytest tests/test_review.py -q` → **16 failed** (ModuleNotFoundError / missing tables)
- Commit: `0fd5998` — `test(03-01): add failing test for reconciliation decisions`

### GREEN
- Extended `app/db/schema.py` with canonical entity tables; commented that FKs from reconciliation id columns stay omitted
- Implemented `app/services/review.py` with UPDATE-based decisions and INSERT only for redirect proposals
- Updated obsolete `test_canonical_tables_not_yet_created` in `tests/test_schema.py` (Phase 2 assertion) so schema suite stays green
- `python3 -m pytest tests/test_review.py tests/test_schema.py tests/test_reconciliation.py -q` → **44 passed**
- Commit: `8cf4cdb` — `feat(03-01): implement accept reject and redirect`

### REFACTOR
- Skipped — no obvious cleanup beyond the GREEN implementation

## Task Commits

1. **RED: Failing review tests** — `0fd5998` (test)
2. **GREEN: Schema + decide_reconciliation** — `8cf4cdb` (feat)

## Files Created/Modified
- `app/services/review.py` — `decide_reconciliation()` accept/reject/redirect
- `app/db/schema.py` — canonical component/assembly/supplier/variant/bom_relationship/technical_fact
- `tests/test_review.py` — behavior coverage for decisions and schema
- `tests/test_schema.py` — assert canonical tables now exist without recon FKs

## Decisions Made
- Followed plan: UPDATE for decisions; INSERT only for redirect MANUAL PENDING row
- Peer reuse looks up ACCEPTED rows whose `source_*_id` appears in evidence `cluster_members` (or `members`)
- Default relationship for redirect evidence is `identity` when original evidence lacks one

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Updated obsolete schema test asserting canonical tables absent**
- **Found during:** GREEN (verification includes `tests/test_schema.py`)
- **Issue:** Phase 2 `test_canonical_tables_not_yet_created` would fail once tables are created
- **Fix:** Renamed/rewrote to `test_canonical_tables_created_without_recon_fks` asserting tables exist and no FK from reconciliation → component
- **Files modified:** `tests/test_schema.py`
- **Verification:** full verification suite 44 passed
- **Committed in:** `8cf4cdb` (GREEN)

---

**Total deviations:** 1 auto-fixed (blocking), 0 deferred
**Impact on plan:** Necessary for verification; no scope creep. Note: critical rules listed only three commit paths; `tests/test_schema.py` was included as Rule 3 blocker fix.

## Issues Encountered
None

## Next Phase Readiness
- `decide_reconciliation()` ready for CLI wiring (03-05) and canonical BOM build (03-02)
- Canonical tables exist for BOM propagation and technical_fact blockers
- Do not run ingestion or `run_full_reconciliation` from review path

---
*Phase: 03-human-review-workflow-core-analysis*
*Completed: 2026-09-23*
