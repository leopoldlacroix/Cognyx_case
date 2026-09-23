---
phase: 04-cross-variant-reuse-analysis-deep-reports
plan: 04
subsystem: ui
tags: [compare-html, static-site, analyze-compare, data-issue-trail, ANALYSIS-02]

requires:
  - phase: 04-cross-variant-reuse-analysis-deep-reports
    provides: compare_variants, all_variant_pairs, blockers source trail, data_quality_issues records
  - phase: 03-human-review-workflow-core-analysis
    provides: write_site shell/nav, build_canonical_model, analyze CLI, report.html sections
provides:
  - render_compare() static compare.html with all variant pairs
  - analyze compare → data/processed/compare.json with default_pair
  - report.html data-issues source_file/source_row trail
affects: [05-explainability-evidence, demo-static-site]

tech-stack:
  added: []
  patterns:
    - "All pairs in one HTML file; select toggles hidden class; no fetch"
    - "STD/NORDIC forced left/right even when lex order differs"
    - "body.compare-page widens content; shell default 820px unchanged"

key-files:
  created: []
  modified:
    - app/services/html_pages.py
    - app/services/report.py
    - app/backend/cli.py
    - tests/test_pages.py

key-decisions:
  - "write_site calls build_canonical_model after report prepares DB; render_compare does not ingest"
  - "Mapping-noise warnings stay one summary card; concrete issues keep records trail"

patterns-established:
  - "PAGES includes compare.html labeled 4 · Compare"
  - "compare.json shape {default_pair, pairs: [compare_variants dict, ...]}"

issues-created: []

duration: 4min
completed: 2026-09-23
---

# Phase 4 Plan 04: Compare Page and Report Trail Summary

**Static `compare.html` with all variant pairs (Standard vs Nordic open first), plus `analyze compare` JSON and data-issue file/row trails on the reuse report.**

## Performance

- **Duration:** 4 min
- **Started:** 2026-09-23T20:42:20Z
- **Completed:** 2026-09-23T20:46:01Z
- **Tasks:** 2/2
- **Files modified:** 4

## Accomplishments
- `render_compare` + nav entry; high-overlap assemblies marked; component anchors show source file/row; blocked rows show both values
- Default visible pair is REGIO-STD / REGIO-NORDIC when both exist; otherwise first lexicographic pair
- Report data-issues print each record's `source_file` and `source_row`; mapping noise stays summarized
- `analyze compare` writes `compare.json` with `default_pair` and per-pair `compare_variants` payloads

## Task Commits

1. **Task 1: Write compare.html** — `d6fe666` (feat)
2. **Task 2: Trail on the report and compare JSON** — `6a577ed` (feat)

## Files Created/Modified
- `app/services/html_pages.py` — `render_compare`, PAGES/write_site, optional shell body_class/extra_css
- `app/services/report.py` — data-issue records trail + mapping-noise summary card
- `app/backend/cli.py` — `analyze compare` → compare.json
- `tests/test_pages.py` — compare page, report trail, and compare JSON coverage

## Decisions Made
- None beyond plan constraints — followed STD/NORDIC left-column override, static pair toggle, and no web framework

## Deviations from Plan

None - plan executed exactly as written.

---

**Total deviations:** 0 auto-fixed, 0 deferred
**Impact on plan:** None

## Issues Encountered
None

## Next Phase Readiness
- Phase 4 complete: assembly overlap, blocker trail, quality records, and compare page all ship
- Phase 5 can reuse component anchors and source_file/source_row for explainability / evidence.html
- Do not add Flask/FastAPI or live routes; do not read ground_truth into client pages

---
*Phase: 04-cross-variant-reuse-analysis-deep-reports*
*Completed: 2026-09-23*
