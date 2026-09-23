---
gsd_state_version: "1.0"
milestone: v1
milestone_name: "Requirements: 32 total"
current_phase: 02
status: executing
last_updated: "2026-09-23T11:21:25.753Z"
state_head: 6100c12c776e4a120cefb9401f7add7e0ec67887
progress:
  total_phases: 5
  completed_phases: 0
  total_plans: 9
  completed_plans: 5
  percent: 0
current_phase_name: Entity Resolution & Reconciliation Engine
---

# State: Cognyx BOM Reuse Explorer (PoC)

**Updated:** 2026-09-23
**Current Phase:** 02
**Next Phase:** Phase 2 — Entity Resolution & Reconciliation Engine
**Mode:** MVP (vertical slices)
**Granularity:** Standard

---

## Project Status

| Dimension | Status |
|-----------|--------|
| Project definition | ✅ Complete — `.planning/PROJECT.md` |
| Requirements | ✅ Defined — 31 v1 requirements across 6 categories |
| Architecture | ✅ Mapped — `.planning/codebase/ARCHITECTURE.md` |
| Roadmap | ✅ Created — `.planning/ROADMAP.md` |
| State tracking | ✅ Created — `.planning/STATE.md` |
| Source data | ✅ Present — 6 CSV files in `data/inputs/` |
| Ground truth | ✅ Present — `data/ground_truth/` (validation only, not client-facing) |
| Codebase | ✅ Phase 1 complete — ingestion + normalization pipeline working |
| Web UI | ❌ Not in PoC scope — CLI + report output for demo |

---

## What Is Done

- **Phase 1: Data Foundation — Ingest & Normalize** ✅ COMPLETE
  - INGEST-01: All 6 CSV files ingested with provenance
  - INGEST-02: Hard validation quarantine (1 row quarantined: BOM-0031, quantity "one")
  - INGEST-03: Soft validation warnings (508 warnings across 309 rows)
  - NORM-01: PLM BOM line normalization (whitespace, casing, punctuation)
  - NORM-02: UOM aliases (pcs → EA, units → EA)
  - NORM-03: Supplier aliases (SIEMENS → SIEMENS MOBILITY, etc.)
  - NORM-04: Reference aliases (CTRL-AIR01 → CTRL-AIR-01)
  - SCEN-C: Typo/alias reconciliation verified

- **PROJECT.md** — Full project definition
- **REQUIREMENTS.md** — 31 v1 requirements
- **config.json** — Workflow preferences
- **ARCHITECTURE.md** — 6-layer pipeline architecture
- **ROADMAP.md** — 5 phases, 31/31 traceability
- **STATE.md** — This file

---

## What Is Not Done

- **Phase 2 execution** — Normalize ERP materials + engineering notes, entity resolution, functional similarity, variant-specific detection, reconciliation records
- **Phase 3 execution** — Human review interface, filterable pending reconciliations, canonical propagation, core analysis reports
- **Phase 4 execution** — Assembly-level overlap metrics, variant drill-down, blocker evidence trails
- **Phase 5 execution** — Explainability for all analysis results, full SCEN-G/H/I/J deepening
- **Scenario validation** — Verify all 10 scenarios A–J are demonstrable end-to-end
- **Demo preparation** — 1 email + 1 in-person meeting (1h)

---

## Phase 1 Summary

**Status:** Executing Phase 02
**Date:** 2026-09-23  
**Plans executed:** 5/5 (01-01 through 01-05)  
**Tests passing:** 68/68  
**Real data:** 309 rows ingested, 1 quarantined, 508 soft warnings, aliases applied

---

## Phase 2: Entity Resolution & Reconciliation Engine

**Status:** Not started  
**Plans needed:** 4-5 plans covering NORM-05, NORM-06, RECON-01 through RECON-04, SCEN-B, SCEN-D, SCEN-E, SCEN-H

### Requirements to cover

- NORM-05 — Normalize ERP materials (supplier ID mapping, UOM standardization)
- NORM-06 — Normalize engineering notes (language detection FR/EN/DE, text extraction)
- RECON-01 — Identity/alias detection with confidence scoring
- RECON-02 — Functional similarity detection (surface, don't merge)
- RECON-03 — Variant-specific intentional difference detection
- RECON-04 — Complete reconciliation record schema
- SCEN-B — Hidden cross-source reuse
- SCEN-D — Similar-but-not-identical (must not merge)
- SCEN-E — Variant-specific intentional differences
- SCEN-H — Multilingual evidence (FR/EN/DE)

---

## Current Phase: Phase 1 (Complete)

Phase 1 execution completed 2026-09-23. All 5 plans executed successfully.

### Phase 1 Plans — COMPLETED

| Plan | Status | Date |
|------|--------|------|
| 01-01: Ingest All 6 CSV Source Files | ✅ | 2026-09-22 |
| 01-02: Hard Validation Quarantine | ✅ | 2026-09-23 |
| 01-03: Soft Validation Warnings | ✅ | 2026-09-23 |
| 01-04: Normalize PLM BOM Lines | ✅ | 2026-09-23 |
| 01-05: Apply UOM/Supplier/Reference Aliases | ✅ | 2026-09-23 |

---

## Active Requirements

### Ingestion (3)

- INGEST-01 — Ingest all 6 source CSV files ✅
- INGEST-02 — Hard validation quarantine ✅
- INGEST-03 — Soft validation warnings ✅

### Normalization (6)

- NORM-01 — Normalize PLM BOM lines ✅
- NORM-02 — UOM aliases ✅
- NORM-03 — Supplier name aliases ✅
- NORM-04 — Reference aliases ✅
- NORM-05 — Normalize ERP materials ⬜ (Phase 2)
- NORM-06 — Normalize engineering notes ⬜ (Phase 2)

### Reconciliation (4)

- RECON-01 — Identity/alias detection ⬜ (Phase 2)
- RECON-02 — Functional similarity detection ⬜ (Phase 2)
- RECON-03 — Variant-specific difference detection ⬜ (Phase 2)
- RECON-04 — Complete reconciliation record schema ⬜ (Phase 2)

### Review Workflow (3)

- REVIEW-01 — Human review interface ⬜ (Phase 3)
- REVIEW-02 — Filterable pending reconciliations ⬜ (Phase 3)
- REVIEW-03 — Accepted → canonical, rejected → recorded ⬜ (Phase 3)

### Cross-Variant Reuse Analysis (5)

- ANALYSIS-01 — "Already reused" report ⬜ (Phase 3)
- ANALYSIS-02 — "Reusable candidates" report ⬜ (Phase 3)
- ANALYSIS-03 — "Blockers" report ⬜ (Phase 3)
- ANALYSIS-04 — "Data-quality issues" report ⬜ (Phase 3)
- ANALYSIS-05 — Explainability for all results ⬜ (Phase 5)

### Scenario Coverage (10)

- SCEN-A — Obvious cross-variant reuse ⬜ (Phase 3)
- SCEN-B — Hidden cross-source reuse ⬜ (Phase 2)
- SCEN-C — Typo/alias reconciliation ✅ (Phase 1)
- SCEN-D — Similar-but-not-identical ⬜ (Phase 2)
- SCEN-E — Variant-specific intentional differences ⬜ (Phase 2)
- SCEN-F — Potential reuse requiring review ⬜ (Phase 3)
- SCEN-G — Conflicting evidence ⬜ (Phase 3)
- SCEN-H — Multilingual evidence ⬜ (Phase 2)
- SCEN-I — Data-quality issues ⬜ (Phase 3)
- SCEN-J — Lifecycle mismatch ⬜ (Phase 3)

---

## Key Decisions

| Decision | Rationale | Status |
|----------|-----------|--------|
| Layered pipeline with human-in-the-loop | AI proposes, humans decide — auditable, trust-building | Validated in Phase 1 |
| Three relationship types kept separate | Prevents collapsing identity/alias, functional similarity, variant-specific into single "match" | Validated in Phase 1 |
| Reconciliation as reviewable relationship, not silent overwrite | Provenance-bearing: source system, raw ID, canonical ID, status, match method, confidence, rationale, evidence | Pending Phase 2 |
| SQLite for PoC | Simple, file-based, sufficient for dataset scale | Validated in Phase 1 |
| Python as sole implementation language | Matches existing codebase, broadens contributor pool | Validated in Phase 1 |

---

## Constraints Active

- `data/inputs/` is **immutable** — never edit source CSV files
- `data/ground_truth/` is **not client-facing** — exists for pipeline validation only
- Normalized output goes to `data/processed/` — separate from source data
- ~4 hour timebox for demo preparation — prioritize end-to-end working path
- Deliverable: 1 email + 1 in-person meeting (1h: 40min case + 20min Q&A)

---

## What Comes After This Session

1. ✅ Execute Phase 1 — ingest + normalize all 6 CSV files
2. ✅ Validate Phase 1 success criteria against the data
3. Create Phase 2 plans — entity resolution + reconciliation engine
4. Execute Phase 2
5. Continue through Phases 3–5
6. Validate all 10 scenarios A–J are demonstrable
7. Prepare demo: email to deon@cognyx.io and francois@cognyx.io, in-person meeting with Bruno Maréchal and Thomas Lindqvist

---

*State updated: 2026-09-23*
*Phase 1 complete. Next: Phase 2 — Entity Resolution & Reconciliation Engine.*
