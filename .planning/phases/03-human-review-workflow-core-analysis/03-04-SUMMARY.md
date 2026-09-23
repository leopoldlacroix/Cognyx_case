---
phase: 03-human-review-workflow-core-analysis
plan: 04
subsystem: analysis
tags: [already-reused, reusable-candidates, SCEN-A, SCEN-F, bom_relationship, TDD]

requires:
  - phase: 03-human-review-workflow-core-analysis
    provides: build_canonical_model, decide_reconciliation accept/reject, canonical bom_relationship
provides:
  - already_reused() from bom_relationship (component + assembly, variant_count >= 2)
  - reusable_candidates() from functional_similarity rows + rugged-description ERP pairs
  - Plain-language explanation on every report row (no LLM)
affects: [03-05-cli-quality-report, report-html-sections]

tech-stack:
  added: []
  patterns: [derived reports only, pending identity excluded until accept+rebuild, rugged strip via regex]

key-files:
  created:
    - app/services/analysis.py
    - tests/test_analysis.py
  modified: []

key-decisions:
  - "already_reused reads bom_relationship only; no pending-alias shortcut"
  - "Note ids for SCEN-F come from engineering_note.author when it matches N-### (fixture label); else note-{pk}"
  - "Rugged rule pairs same category_raw after stripping \\brugged\\b; Nordic vs Standard fans stay unpaired"

patterns-established:
  - "already_reused(conn) / reusable_candidates(conn) return list[dict] with explanation"
  - "Functional similarity candidates stay two entities; camera rugged pair is not merged"

issues-created: []

duration: 25min
completed: 2026-09-23
---

# Plan 03-04: Already-Reused & Reusable-Candidate Reports Summary

**`already_reused()` and `reusable_candidates()` report shared canonical BOM entities and reviewable similarity pairs (including SCEN-F rugged cameras) with field-built explanations.**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-09-23T16:52:00Z
- **Completed:** 2026-09-23T17:17:00Z
- **Tasks:** 2 (RED + GREEN; REFACTOR skipped)
- **Files modified:** 2

## Accomplishments
- Listed components and assemblies present on ≥2 variants via `bom_relationship`, with sorted `variant_refs` and `source_bom_line_ids`
- Pending identity omitted until accept + `build_canonical_model`; accepted cluster explanations name identity source refs
- Surfaced `functional_similarity` reconciliation pairs once; excluded `variant_specific`
- SCEN-F: ERP same-category descriptions matching after stripping `rugged` (MAT-10033 / MAT-10034) with notes N-018 / N-019; not a canonical merge

## TDD Cycle

### RED
- Wrote `tests/test_analysis.py` covering singleton reuse, single-variant omit, pending→accepted identity, assembly reuse, functional similarity, variant-specific exclusion, rugged camera + notes, Nordic fan non-pair, ordering, explanations
- `python3 -m pytest tests/test_analysis.py -q` → **10 failed** (ModuleNotFoundError)
- Commit: `7674b66` — `test(03-04): add failing test for reuse reports`

### GREEN
- Implemented `app/services/analysis.py` with `already_reused()` and `reusable_candidates()`
- `python3 -m pytest tests/test_analysis.py tests/test_canonicalization.py -q` → **21 passed**
- Commit: `c28e47d` — `feat(03-04): report already reused and reusable candidates`

### REFACTOR
- Skipped — minor dead-code cleanup folded into GREEN before commit; no separate refactor commit

## Task Commits

1. **RED: Failing reuse/candidate tests** — `7674b66` (test)
2. **GREEN: Analysis reports** — `c28e47d` (feat)

## Files Created/Modified
- `app/services/analysis.py` — `already_reused()`, `reusable_candidates()`
- `tests/test_analysis.py` — behavior coverage for SCEN-A / SCEN-F report shapes

## Decisions Made
- Engineering note labels: author matching `N-###` (fixture convention for dataset note ids) preferred over `note-{pk}` because `note_id` is not persisted by ingest
- Camera-pair note attach: object_reference in `{PASSCOUNT-CAMERA, PASSCOUNT-CAMERA-RUGGED, left_ref, right_ref}`
- Left/right refs always sorted lexicographically before emit

## Deviations from Plan

None - plan executed exactly as written

---

**Total deviations:** 0 auto-fixed, 0 deferred
**Impact on plan:** None

## Issues Encountered
None

## Next Phase Readiness
- Analysis lists ready for CLI `analyze reuse|candidates` and report.html section wiring in 03-05
- Do not auto-link MAT-10001; do not merge rugged camera pair into one component id

---
*Phase: 03-human-review-workflow-core-analysis*
*Completed: 2026-09-23*
