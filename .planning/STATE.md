---
gsd_state_version: "1.0"
milestone: v1
milestone_name: "Requirements: 32 total"
current_phase: 04
status: phase_3_complete
last_updated: "2026-09-23T18:00:00.000Z"
progress:
  total_phases: 5
  completed_phases: 3
  total_plans: 15
  completed_plans: 15
  percent: 60
current_phase_name: Cross-Variant Reuse Analysis — Deep Reports
---

# State: Cognyx BOM Reuse Explorer (PoC)

**Updated:** 2026-09-23
**Current Phase:** 03 complete
**Next Phase:** Phase 4 — Cross-Variant Reuse Analysis — Deep Reports
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
| Codebase | ✅ Phase 3 complete — review decisions, canonical BOM, reuse/blocker/quality reports, CLI |
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

- **Phase 2: Entity Resolution & Reconciliation Engine** ✅ COMPLETE (2026-09-23)
  - NORM-05: ERP supplier mapping + UOM standardization
  - NORM-06 / SCEN-H: FR/EN/DE language detection; raw note text preserved
  - RECON-04: reconciliation tables + source_assembly_variant + source extraction
  - RECON-01 / SCEN-B: identity on shared normalized_reference (CTRL-AIR-01 alias cluster). MAT-10001 is not an identity match under current alias evidence
  - RECON-02 / SCEN-D: functional similarity surfaced, not merged
  - RECON-03 / SCEN-E: Nordic-only components recorded as variant-specific
  - Tests: 110 passed

- **PROJECT.md** — Full project definition
- **REQUIREMENTS.md** — 31 v1 requirements
- **config.json** — Workflow preferences
- **ARCHITECTURE.md** — 6-layer pipeline architecture
- **ROADMAP.md** — 5 phases, 31/31 traceability
- **STATE.md** — This file

---

## What Is Not Done

- **Phase 3: Human Review Workflow + Core Analysis** ✅ COMPLETE (2026-09-23)
  - REVIEW-01: `decide_reconciliation` accept / reject / redirect; canonical tables created
  - REVIEW-02: `list_reconciliations` filters by status, confidence band, method, source system, relationship
  - REVIEW-03: `build_canonical_model` from accepted identity plus singletons; pending/rejected identity stays unresolved
  - ANALYSIS-01 / SCEN-A: `already_reused` from `bom_relationship`
  - ANALYSIS-02 / SCEN-F: `reusable_candidates` (functional similarity + rugged camera pair, not merged)
  - ANALYSIS-03 / SCEN-G / SCEN-J: `blockers` keeps both voltages and separates Prototype vs Released from ERP obsolete
  - ANALYSIS-04 / SCEN-I: `data_quality_issues` for invalid quantity, duplicate BOM keys, UOM aliases, mapping-noise warning summary
  - CLI `review` and `analyze` write JSON under `data/processed/`; one-page report sections read those functions
  - Tests: 180 passed
- **Phase 4 execution** — Assembly-level overlap metrics, variant drill-down, compare page
- **Phase 5 execution** — Explainability for all analysis results, full SCEN-G/H/I/J deepening
- **Scenario validation** — Verify all 10 scenarios A–J are demonstrable end-to-end
- **Demo preparation** — 1 email + 1 in-person meeting (1h)

---

## Phase 1 Summary

**Status:** Phase 3 complete
**Date:** 2026-09-23  
**Plans executed:** 15/15 (01-01 through 01-05, 02-01 through 02-05, 03-01 through 03-05)  
**Tests passing:** 180/180  
**Real data:** 309 rows ingested, 1 quarantined, 508 soft warnings, aliases applied

---

## Phase 2: Entity Resolution & Reconciliation Engine

**Status:** Complete (2026-09-23)  
**Plans executed:** 02-01 through 02-05  
**Tests:** 110 passed

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

## Phase 3: Human Review Workflow + Core Analysis

**Status:** Complete (2026-09-23)  
**Plans executed:** 03-01 through 03-05  
**Tests:** 180 passed

### Phase 3 Plans — COMPLETED

| Plan | Status | Commits |
|------|--------|---------|
| 03-01: Review decisions | ✅ | `0fd5998` test, `8cf4cdb` feat |
| 03-02: Filterable queue | ✅ | `f536fe8` test, `d2c61ca` feat |
| 03-03: Canonical BOM | ✅ | `7faa2ec` test, `3839a33` feat |
| 03-04: Reuse reports | ✅ | `7674b66` test, `c28e47d` feat |
| 03-05: Blockers, quality, CLI | ✅ | `102358e` test, `d644426` feat |

---

## Current Phase: Phase 3 (Complete)

Phase 3 execution completed 2026-09-23. All 5 plans executed. Wave 1 was 03-01. Wave 2 ran 03-02 and 03-03 together. 03-04 followed 03-03. 03-05 followed 03-02 and 03-04.

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
- NORM-05 — Normalize ERP materials ✅ (Phase 2)
- NORM-06 — Normalize engineering notes ✅ (Phase 2)

### Reconciliation (4)

- RECON-01 — Identity/alias detection ✅ (Phase 2)
- RECON-02 — Functional similarity detection ✅ (Phase 2)
- RECON-03 — Variant-specific difference detection ✅ (Phase 2)
- RECON-04 — Complete reconciliation record schema ✅ (Phase 2)

### Review Workflow (3)

- REVIEW-01 — Human review interface ✅ (Phase 3)
- REVIEW-02 — Filterable pending reconciliations ✅ (Phase 3)
- REVIEW-03 — Accepted → canonical, rejected → recorded ✅ (Phase 3)

### Cross-Variant Reuse Analysis (5)

- ANALYSIS-01 — "Already reused" report ✅ (Phase 3; Phase 4 deepens)
- ANALYSIS-02 — "Reusable candidates" report ✅ (Phase 3; Phase 4 deepens)
- ANALYSIS-03 — "Blockers" report ✅ (Phase 3; Phase 4 deepens)
- ANALYSIS-04 — "Data-quality issues" report ✅ (Phase 3; Phase 4 deepens)
- ANALYSIS-05 — Explainability for all results ✅ initial (Phase 3); deepen in Phase 5

### Scenario Coverage (10)

- SCEN-A — Obvious cross-variant reuse ✅ (Phase 3)
- SCEN-B — Hidden cross-source reuse ✅ (Phase 2) — CTRL-AIR-01 alias cluster; MAT-10001 is not an identity match under current alias evidence
- SCEN-C — Typo/alias reconciliation ✅ (Phase 1)
- SCEN-D — Similar-but-not-identical ✅ (Phase 2)
- SCEN-E — Variant-specific intentional differences ✅ (Phase 2)
- SCEN-F — Potential reuse requiring review ✅ (Phase 3)
- SCEN-G — Conflicting evidence ✅ (Phase 3; Phase 5 deepens)
- SCEN-H — Multilingual evidence ✅ (Phase 2) — FR/EN/DE detection and normalized text; original note_text kept
- SCEN-I — Data-quality issues ✅ (Phase 3; Phase 5 deepens)
- SCEN-J — Lifecycle mismatch ✅ (Phase 3; Phase 5 deepens)

---

## Key Decisions

| Decision | Rationale | Status |
|----------|-----------|--------|
| Layered pipeline with human-in-the-loop | AI proposes, humans decide — auditable, trust-building | Validated in Phase 1 |
| Three relationship types kept separate | Prevents collapsing identity/alias, functional similarity, variant-specific into single "match" | Validated in Phase 1 |
| Reconciliation as reviewable relationship, not silent overwrite | Provenance-bearing: source system, raw ID, canonical ID, status, match method, confidence, rationale, evidence | Validated in Phase 2 |
| SQLite for PoC | Simple, file-based, sufficient for dataset scale | Validated in Phase 1 |
| Python as sole implementation language | Matches existing codebase, broadens contributor pool | Validated in Phase 1 |
| Canonical BOM from accepted identity plus singletons | Pending or rejected identity stays out of `bom_relationship`; no identity row is a singleton, so obvious reuse is visible before every line is reviewed | Validated in Phase 3 |
| Similarity and variant-specific decisions do not share a component id | Functional similarity stays two entities; Nordic parts stay their own canonical component | Validated in Phase 3 |

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
4. ✅ Execute Phase 2
5. ✅ Execute Phase 3
6. Continue through Phases 4–5
7. Validate all 10 scenarios A–J are demonstrable
8. Prepare demo: email to deon@cognyx.io and francois@cognyx.io, in-person meeting with Bruno Maréchal and Thomas Lindqvist

---

*State updated: 2026-09-23*
*Phase 3 complete. Next: Phase 4 — Cross-Variant Reuse Analysis — Deep Reports.*
