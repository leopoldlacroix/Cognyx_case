---
phase: 03-human-review-workflow-core-analysis
plan: 03
subsystem: canonicalization
tags: [canonical-BOM, identity, singleton, SQLite, TDD, static-HTML]

requires:
  - phase: 03-human-review-workflow-core-analysis
    provides: decide_reconciliation accept/reject, canonical component/assembly/variant/bom_relationship tables
provides:
  - build_canonical_model() idempotent refill of variant/assembly/component/bom_relationship
  - Singleton PLM refs become canonical without an accept click
  - Pending/rejected identity lines stay unresolved; accepted clusters share one component_id
  - canonical.html static page for accepted clusters and unresolved identity lines
affects: [03-04-core-reports, 03-05-cli-review, report-reuse-snapshot]

tech-stack:
  added: []
  patterns: [clear-and-refill derived canonical tables, join BOM on PLM source_reference=component_ref_raw, rebuild accepted component ids on refill]

key-files:
  created:
    - app/services/canonicalization.py
    - tests/test_canonicalization.py
  modified:
    - app/services/html_pages.py

key-decisions:
  - "On each build, DELETE component/assembly/variant/bom_relationship then recreate; UPDATE ACCEPTED identity component_id to new shared ids"
  - "Identity PENDING/ASSESSED → identity_pending; REJECTED → identity_rejected; no identity row → singleton"
  - "functional_similarity and variant_specific neither block nor merge"
  - "Join PLM BOM to source_component on source_system=PLM and source_reference=component_ref_raw"

patterns-established:
  - "build_canonical_model(conn) returns counts plus unresolved[{source_bom_line_id, reason}]"
  - "canonical.html uses the same shell/nav as workflow.html via write_site"

issues-created: []

duration: 35min
completed: 2026-09-23
---

# Plan 03-03: Canonical BOM Propagation Summary

**Idempotent `build_canonical_model` fills canonical BOM from accepted identity clusters plus unambiguous singletons, with pending/rejected identity lines listed as unresolved and a static `canonical.html` check page.**

## Performance

- **Duration:** ~35 min
- **Started:** 2026-09-23T16:45:00Z
- **Completed:** 2026-09-23T17:20:00Z
- **Tasks:** 2 (RED + GREEN; REFACTOR skipped)
- **Files modified:** 3

## Accomplishments
- Built `build_canonical_model(conn)` that clears and refills variant, assembly, component, and bom_relationship without touching reconciliation or raw tables
- Singletons (no identity row) resolve into canonical components and BOM rows; pending/rejected identity stays out of `bom_relationship`
- Accepted identity peers share one `component_id` after rebuild; similarity and variant-specific rows do not merge
- Extended static site with `canonical.html` (accepted clusters + unresolved identity lines) and a nav link

## TDD Cycle

### RED
- Wrote `tests/test_canonicalization.py` covering singleton reuse, pending/partial/full accept, reject, similarity, variant-specific, idempotency, quarantine, MAT-10001 non-link, and canonical HTML
- `python3 -m pytest tests/test_canonicalization.py -q` → **11 failed** (ModuleNotFoundError)
- Commit: `7faa2ec` — `test(03-03): add failing test for canonical BOM`

### GREEN
- Implemented `app/services/canonicalization.py` with clear-and-refill, accepted-cluster component rebuild, and BOM propagation rules from 03-CONTEXT
- Extended `app/services/html_pages.py` with `canonical.html` in `PAGES` / `write_site` / `render_canonical` (kept existing pages)
- `python3 -m pytest tests/test_canonicalization.py tests/test_review.py -q` → **42 passed**
- Commit: `3839a33` — `feat(03-03): build canonical model from accepted identity`

### REFACTOR
- Skipped — GREEN implementation was clear enough; no extra cleanup commit

## Task Commits

1. **RED: Failing canonicalization tests** — `7faa2ec` (test)
2. **GREEN: Canonical model + HTML page** — `3839a33` (feat)

## Files Created/Modified
- `app/services/canonicalization.py` — `build_canonical_model()`
- `app/services/html_pages.py` — `render_canonical`, nav + `write_site` entry for `canonical.html`
- `tests/test_canonicalization.py` — behavior coverage for BOM propagation and page output

## Decisions Made
- Rebuild ACCEPTED identity components after DELETE so cluster peers keep a shared id written back onto reconciliation rows
- Assemblies from `source_assembly.normalized_reference`; variants from `plm_variant.variant_ref_normalized`; no assembly_reconciliation required
- Supplier canonicalization omitted (optional; BOM does not depend on it)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Commit pathspec order for untracked file**
- **Found during:** RED commit
- **Issue:** `git commit -- path -m msg` treats `-m` as a pathspec; untracked file also needed `git add` first
- **Fix:** `git add -- tests/test_canonicalization.py` then `git commit -m "..." -- path`
- **Files modified:** none (process only)
- **Verification:** commit `7faa2ec` succeeded
- **Committed in:** `7faa2ec` (RED)

---

**Total deviations:** 1 auto-fixed (blocking process), 0 deferred
**Impact on plan:** Commit protocol adjusted for untracked files; plan scope unchanged.

## Issues Encountered
None

## Next Phase Readiness
- Canonical BOM ready for reuse / blockers / data-quality reports
- `canonical.html` regenerates with `write_site` when CLI report runs
- Do not auto-link MAT-10001 to CTRL-AIR-01 in downstream analysis

---
*Phase: 03-human-review-workflow-core-analysis*
*Completed: 2026-09-23*
