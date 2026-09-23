---
phase: 04-cross-variant-reuse-analysis-deep-reports
plan: 01
subsystem: analysis
tags: [compare-variants, assembly-overlap, bom_relationship, TDD, ANALYSIS-01]

requires:
  - phase: 03-human-review-workflow-core-analysis
    provides: build_canonical_model, already_reused, reusable_candidates, blockers
provides:
  - compare_variants() assembly overlap with shared/left/right/unresolved/blocked/candidate labels
  - all_variant_pairs() lexicographic unordered variant pairs
  - Overlap ratio shared/union with high_overlap at >= 0.5
affects: [04-02-variant-drill-down, 04-04-compare-page]

tech-stack:
  added: []
  patterns: [label priority unresolved>blocked>variant_specific>reuse_candidate>reused>left_only>right_only, pending identity outside ratio]

key-files:
  created:
    - tests/test_compare.py
  modified:
    - app/services/analysis.py

key-decisions:
  - "Overlap uses canonical component ids on bom_relationship only; pending identity is unresolved"
  - "Blocked shared parts stay in shared_count; label is blocked so conflict stays visible"
  - "candidate_count is pair count on the assembly, not component row count"

patterns-established:
  - "compare_variants(conn, left_ref, right_ref) → {left_ref, right_ref, assemblies[]}"
  - "all_variant_pairs(conn) → [(left, right), ...] with left < right"

issues-created: []

duration: 4min
completed: 2026-09-23
---

# Phase 4 Plan 01: Assembly Overlap Summary

**`compare_variants()` and `all_variant_pairs()` report per-assembly shared/left/right canonical overlap with unresolved, blocked, variant-specific, and reuse-candidate labels.**

## Performance

- **Duration:** 4 min
- **Started:** 2026-09-23T20:35:04Z
- **Completed:** 2026-09-23T20:39:03Z
- **Tasks:** 2 (RED + GREEN; REFACTOR skipped)
- **Files modified:** 2

## Accomplishments
- Assembly-level comparison of two variants: shared, left-only, right-only, unresolved, conflicts, candidates, overlap ratio
- Label priority keeps identity pending, blockers, Nordic variant-specific, and similarity pairs distinct
- `all_variant_pairs` derives pairs from `variant` table (not hardcoded REGIO refs)
- Existing `already_reused` / `reusable_candidates` return keys unchanged

## TDD Cycle

### RED
- Wrote `tests/test_compare.py` covering half/full/zero overlap, pending unresolved, variant-specific, similarity candidates, blocked shared, one-sided assembly, left/right swap, MAT-10001 distinctness, and `all_variant_pairs`
- `python3 -m pytest tests/test_compare.py -q` → **11 failed** (ImportError: missing `compare_variants` / `all_variant_pairs`)
- Commit: `cd5ca29` — `test(04-01): add failing test for assembly overlap`

### GREEN
- Implemented `compare_variants()` and `all_variant_pairs()` in `app/services/analysis.py`
- Reads `bom_relationship` + unresolved `plm_bom_line`; calls `reusable_candidates()` and `blockers()` for labels; does not call `build_canonical_model` or insert reconciliations
- `python3 -m pytest tests/test_compare.py tests/test_analysis.py -q` → **21 passed**
- Commit: `4c2107b` — `feat(04-01): implement assembly overlap for two variants`

### REFACTOR
- Skipped — GREEN implementation was clear enough; no separate cleanup commit

## Task Commits

1. **RED: Failing compare tests** — `cd5ca29` (test)
2. **GREEN: Assembly overlap** — `4c2107b` (feat)

## Files Created/Modified
- `tests/test_compare.py` — behavior coverage for `compare_variants` / `all_variant_pairs`
- `app/services/analysis.py` — `compare_variants()`, `all_variant_pairs()`, label/anchor helpers

## Decisions Made
- None beyond plan constraints — followed constraining decisions exactly (overlap ratio, label priority, blockers still shared, MAT-10001 not CTRL-AIR-01, Nordic not a candidate)

## Deviations from Plan

None - plan executed exactly as written.

---

**Total deviations:** 0 auto-fixed, 0 deferred
**Impact on plan:** None

## Issues Encountered
None

## Next Phase Readiness
- `compare_variants` ready for compare HTML page (04-04) and any drill-down that consumes assembly rows
- Do not merge similarity into one canonical id; do not treat MAT-10001 as CTRL-AIR-01

---
*Phase: 04-cross-variant-reuse-analysis-deep-reports*
*Completed: 2026-09-23*
