# Cognyx BOM Reuse Explorer (PoC)

## What This Is

A small internal engineering workbench for Alstom's Valenciennes site (regional trains) that helps engineering teams reuse existing sub-assemblies across train variants instead of re-designing from scratch at every tender. It ingests messy multi-source PLM/ERP/engineering exports, normalizes them, proposes candidate entity reconciliations for human review, and derives cross-variant reuse analysis from the accepted canonical model.

**Not** an autonomous answer engine — it is an auditable, provenance-bearing pipeline where AI proposes and humans decide.

## Core Value

Surface which sub-assemblies are reused — or reusable — across train variants, and where the data has inconsistencies that block safe reuse, in a reviewable way that engineers trust.

## Business Context

<!-- OPTIONAL — only for monetized or customer-facing projects. Delete this section otherwise. -->

- **Customer**: Alstom Valenciennes engineering team (pilot sponsor: Bruno Maréchal, Engineering Director; lead data engineer: Thomas Lindqvist)
- **Revenue model**: FDE pilot engagement (3-week pilot, PoC scope)
- **Success metric**: Engineering team can identify cross-variant reuse opportunities and data inconsistencies from the workbench without manually cross-referencing CSV exports
- **Strategy notes**: PoC → production evolution path documented in `docs/blueprint/docs/12_production_evolution.md`

## Requirements

### Validated

<!-- Shipped and confirmed valuable. -->

- ✓ **Pipeline architecture** — layered ingestion → normalization → reconciliation → canonical model → reuse analysis (existing codebase map confirms design)
- ✓ **Source data ingestion** — 6 CSV source files from PLM/ERP/engineering systems with provenance tracking (existing structure)
- ✓ **Normalization layer** — deterministic transformations: whitespace, casing, punctuation, UOM aliases, supplier aliases, reference aliases (architecture confirms)
- ✓ **Reconciliation model** — reviewable, provenance-bearing relationships (identity/alias, functional similarity, variant-specific specialization kept separate)
- ✓ **Cross-variant reuse analysis** — answers: already reused, reusable candidates, blockers, data-quality issues, explainability (scenario-driven)

### Active

<!-- Current scope. Building toward these. -->

- [ ] **INGEST-01**: Ingest all 6 source CSV files into source tables with file hash, row number, and raw column preservation
- [ ] **NORM-01**: Normalize PLM BOM lines: whitespace collapse, casing standardization, punctuation harmonization, UOM aliases
- [ ] **NORM-02**: Normalize ERP materials: supplier name aliases, UOM standardization
- [ ] **RECON-01**: Perform entity resolution: identity/alias detection (e.g. CTRL-AIR-01 vs CTRL-AIR01), confidence scoring, match method recording
- [ ] **RECON-02**: Detect functional similarity candidates (different entities, possibly interchangeable) without merging
- [ ] **RECON-03**: Detect variant-specific intentional differences (e.g. Nordic cold-rated parts) and exclude from generic reuse suggestions
- [ ] **REVIEW-01**: Human-in-the-loop review workflow: accept/reject/redirect reconciliation proposals with rationale
- [ ] **ANALYSIS-01**: Generate cross-variant reuse report: shared sub-assemblies, reusable candidates, blockers, data-quality issues
- [ ] **ANALYSIS-02**: Surface conflicting evidence without normalizing it away (scenario G)
- [ ] **ANALYSIS-03**: Handle multilingual evidence (FR/EN/DE technical notes) for reconciliation context (scenario H)
- [ ] **ANALYSIS-04**: Detect and report data-quality issues: inconsistent units, duplicate BOM lines, invalid quantities, lifecycle mismatches (scenarios I, J)

### Out of Scope

<!-- Explicit boundaries. Includes reasoning to prevent re-adding. -->

- **Production auth / user management** — PoC scope; production evolution path noted but not implemented
- **Distributed / graph database** — SQLite sufficient for PoC scale; PostgreSQL migration noted for production
- **Complex multi-agent framework** — single pipeline with human review, not autonomous agent swarm
- **Full deployment automation** — PoC is a working tool, not a deployed service
- **OCR / PDF extraction** — source data is CSV, no document extraction needed
- **General-purpose chatbot** — focused engineering workbench, not a conversational AI

## Context

- **Client**: Alstom x Cognyx FDE pilot at Valenciennes site (regional trains)
- **Pilot duration**: 3 weeks
- **Deliverable format**: 1 email + 1 in-person meeting (1h: 40min case + 20min Q&A)
- **Audience**: Bruno Maréchal (Engineering Director, pilot sponsor), Thomas Lindqvist (lead data engineer)
- **Email recipients**: deon@cognyx.io, francois@cognyx.io
- **Dataset**: Synthetic but intentionally messy — 5 train variants, 138 BOM lines, 45 assembly records, 44 ERP materials, 6 suppliers, multilingual technical notes
- **10 engineered scenarios** (A–J) covering: obvious reuse, hidden cross-source reuse, typos/aliases, similar-but-not-identical, variant-specific differences, potential reuse requiring review, conflicting evidence, multilingual evidence, data-quality issues, lifecycle mismatches
- **Tech stack**: Python, SQLite, CSV in / JSON out, planned React/TypeScript web UI (not yet built)
- **Repository**: https://github.com/leopold-lacroix/cognyx (private)

## Constraints

- **Timeline**: ~4 hours preparation timebox for the demo meeting — extract maximum value using AI-assisted coding tools
- **Data immutability**: `data/inputs/` is immutable test fixture — never edit
- **Ground truth secrecy**: `data/ground_truth/` exists for pipeline validation only — NOT client-facing
- **Output separation**: Normalized output goes to `data/processed/` — separate from source data
- **Scope discipline**: Prioritize working end-to-end ingestion path, clear canonical entity model, reviewable reconciliation, useful cross-variant reuse analysis, visible evidence/provenance, concise maintainable codebase, trace of AI-assisted development
- **Language**: Technical terms, code, file paths in English; user-facing output in English

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Layered pipeline with human-in-the-loop | AI proposes, humans decide — auditable, trust-building | — Pending |
| Three relationship types kept separate (identity/alias, functional similarity, variant-specific) | Prevents collapsing distinct concepts into single "match" | — Pending |
| Reconciliation as reviewable relationship, not silent overwrite | Provenance-bearing: source system, raw ID, canonical ID, status, match method, confidence, rationale, evidence | — Pending |
| SQLite for PoC | Simple, file-based, sufficient for dataset scale | — Pending |
| Python as sole implementation language | Matches existing codebase, broadens contributor pool | — Pending |

---

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

*Last updated: 2026-09-22 after initialization*
