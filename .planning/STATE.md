# State: Cognyx BOM Reuse Explorer (PoC)

**Updated:** 2026-09-22
**Current Phase:** None (pre-execution — roadmap just created)
**Next Phase:** Phase 1 — Data Foundation: Ingest & Normalize
**Mode:** MVP (vertical slices)
**Granularity:** Standard

---

## Project Status

| Dimension | Status |
|-----------|--------|
| Project definition | ✅ Complete — `.planning/PROJECT.md` |
- **Requirements** | ✅ Defined — 31 v1 requirements across 6 categories |
| Architecture | ✅ Mapped — `.planning/codebase/ARCHITECTURE.md` (commit 92a308b) |
| Roadmap | ✅ Created — `.planning/ROADMAP.md` (this session) |
| State tracking | ✅ Created — `.planning/STATE.md` (this session) |
| Source data | ✅ Present — 6 CSV files in `data/inputs/` |
| Ground truth | ✅ Present — `data/ground_truth/` (validation only, not client-facing) |
| Codebase | 🔄 Not yet implemented — Phase 1 about to start |
| Web UI | ❌ Not in PoC scope — CLI + report output for demo |

---

## What Is Done

- **PROJECT.md** — Full project definition: value, context, constraints, key decisions, evolution rules
- **REQUIREMENTS.md** — 32 v1 requirements (INGEST-01–03, NORM-01–06, RECON-01–04, REVIEW-01–03, ANALYSIS-01–05, SCEN-A–J) + v2 deferred + out-of-scope
- **config.json** — Workflow preferences: yolo mode, standard granularity, parallel execution, adaptive model profile, Nyquist validation on
- **ARCHITECTURE.md** — 6-layer pipeline architecture: ingestion → normalization → source entity extraction → reconciliation → canonicalization → analysis; SQLite storage; API endpoint contracts; 10 scenario architectural implications
- **ROADMAP.md** — 5 phases derived from requirements, 32/32 traceability, 26 success criteria, MVP vertical slices
- **STATE.md** — This file

---

## What Is Not Done

- **Phase 1 execution** — Ingest 6 CSV files, hard/soft validation, normalize PLM BOM lines + UOM/supplier/reference aliases
- **Phase 2 execution** — Normalize ERP materials + engineering notes, entity resolution, functional similarity, variant-specific detection, reconciliation records
- **Phase 3 execution** — Human review interface, filterable pending reconciliations, canonical propagation, core analysis reports, conflict/lifecycle surfacing
- **Phase 4 execution** — Assembly-level overlap metrics, variant drill-down, blocker evidence trails, data-quality report enrichment
- **Phase 5 execution** — Explainability for all analysis results, full SCEN-G/H/I/J deepening
- **Scenario validation** — Verify all 10 scenarios A–J are demonstrable end-to-end
- **Demo preparation** — 1 email + 1 in-person meeting (1h)

## Phase 1 Plans — READY

All 5 PLAN.md files created in `.planning/phases/01-data-foundation-ingest-normalize/`:
- PLAN-1.1.md — Ingest All 6 CSV Source Files (INGEST-01)
- PLAN-1.2.md — Hard Validation Quarantine (INGEST-02)
- PLAN-1.3.md — Soft Validation Warnings (INGEST-03)
- PLAN-1.4.md — Normalize PLM BOM Lines (NORM-01)
- PLAN-1.5.md — Apply UOM/Supplier/Reference Aliases (NORM-02, NORM-03, NORM-04, SCEN-C)

**Wave 1:** All 5 plans (sequential execution: 1.1 → 1.2 → 1.3 → 1.4 → 1.5)

---

## Current Phase: None

Roadmap has been created. No phase has been executed yet. The project is at the planning threshold — all definition artifacts are in place, roadmap is set, and execution can begin.

### Immediate Next Action

Start **Phase 1: Data Foundation — Ingest & Normalize**.

**Phase 1 plans (in order):**
1. Ingest all 6 CSV source files with provenance (file hash, source_row, raw column preservation)
2. Hard validation quarantine for malformed rows
3. Soft validation warnings for missing description, unknown UOM, empty supplier
4. Normalize PLM BOM lines: whitespace, casing, punctuation
5. Apply UOM, supplier, and reference aliases (config-driven)

---

## Active Requirements

All 31 v1 requirements are **Active** (not yet validated, not yet failed). They are mapped to roadmap phases in REQUIREMENTS.md traceability.

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
- ANALYSIS-05 — Explainability for all results ⬜ (Phase 3)

### Scenario Coverage (10)
- SCEN-A — Obvious cross-variant reuse ⬜ (Phase 3)
- SCEN-B — Hidden cross-source reuse ⬜ (Phase 2)
- SCEN-C — Typo/alias reconciliation ⬜ (Phase 1)
- SCEN-D — Similar-but-not-identical ⬜ (Phase 2)
- SCEN-E — Variant-specific intentional differences ⬜ (Phase 2)
- SCEN-F — Potential reuse requiring review ⬜ (Phase 3)
- SCEN-G — Conflicting evidence ⬜ (Phase 3)
- SCEN-H — Multilingual evidence ⬜ (Phase 2)
- SCEN-I — Data-quality issues ⬜ (Phase 3)
- SCEN-J — Lifecycle mismatch ⬜ (Phase 3)

---

## Key Decisions (Pending)

| Decision | Rationale | Status |
|----------|-----------|--------|
| Layered pipeline with human-in-the-loop | AI proposes, humans decide — auditable, trust-building | Pending execution |
| Three relationship types kept separate | Prevents collapsing identity/alias, functional similarity, variant-specific into single "match" | Pending execution |
| Reconciliation as reviewable relationship, not silent overwrite | Provenance-bearing: source system, raw ID, canonical ID, status, match method, confidence, rationale, evidence | Pending execution |
| SQLite for PoC | Simple, file-based, sufficient for dataset scale | Pending execution |
| Python as sole implementation language | Matches existing codebase, broadens contributor pool | Pending execution |

---

## Constraints Active

- `data/inputs/` is **immutable** — never edit source CSV files
- `data/ground_truth/` is **not client-facing** — exists for pipeline validation only
- Normalized output goes to `data/processed/` — separate from source data
- ~4 hour timebox for demo preparation — prioritize end-to-end working path
- Deliverable: 1 email + 1 in-person meeting (1h: 40min case + 20min Q&A)

---

## What Comes After This Session

1. Execute Phase 1 — ingest + normalize all 6 CSV files
2. Validate Phase 1 success criteria against the data
3. Transition to Phase 2 — entity resolution + reconciliation engine
4. Continue through Phases 3–5
5. Validate all 10 scenarios A–J are demonstrable
6. Prepare demo: email to deon@cognyx.io and francois@cognyx.io, in-person meeting with Bruno Maréchal and Thomas Lindqvist

---

*State updated: 2026-09-22*
*Next update: After Phase 1 execution completes*
