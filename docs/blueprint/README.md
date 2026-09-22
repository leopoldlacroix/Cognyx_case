# Cognyx FDE PoC — BOM Reuse Explorer

## Purpose

This folder is the implementation blueprint for a small, credible Forward Deployed Engineer PoC inspired by an industrial PLM/ERP/BOM reconciliation problem.

The goal is **not** to build a production enterprise data platform. The goal is to demonstrate a disciplined workflow that:

1. ingests messy industrial source data;
2. preserves source truth and provenance;
3. deterministically normalizes what can be normalized;
4. reconciles source-side entities to canonical entities with AI-assisted suggestions;
5. keeps human approval as the authoritative decision;
6. produces a canonical BOM representation;
7. identifies cross-variant reuse and reuse blockers;
8. exposes the evidence and reasoning through a small engineer-oriented UI.

## Core product question

> Given several train variants with inconsistent PLM/ERP references, what is already reusable, what could be reusable, and what prevents reuse?

## Core principle

**AI proposes; deterministic logic validates; humans decide when the mapping is consequential.**

The PoC must not become an opaque "chat with your BOM" application.

---

# What this package contains

| File | Purpose |
|---|---|
| `docs/01_scope_and_principles.md` | Scope, non-goals, product narrative and engineering principles |
| `docs/02_architecture.md` | Logical architecture and end-to-end flow |
| `docs/03_data_model.md` | Complete ER-style schema specification |
| `docs/04_ingestion_and_normalization.md` | Raw ingestion, normalization and provenance pipeline |
| `docs/05_reconciliation.md` | Reconciliation engine, candidate workflow and human-in-the-loop behavior |
| `docs/06_canonicalization_and_analysis.md` | Accepted mappings, canonical BOM and reuse analysis |
| `docs/07_ui_specification.md` | Screens/windows and interactions |
| `docs/08_api_and_service_contracts.md` | Backend service/API contracts without implementation |
| `docs/09_synthetic_data_spec.md` | Synthetic industrial data set design and edge cases |
| `docs/10_testing_and_validation.md` | Test strategy, acceptance criteria and demo validation |
| `docs/11_execution_roadmap.md` | Ordered implementation roadmap and Definition of Done per phase |
| `docs/12_production_evolution.md` | What should change for production scale and what stays PoC-only |
| `checklists/coder_checklist.md` | Practical implementation checklist |
| `checklists/demo_checklist.md` | End-to-end demo checklist |
| `config/normalization.example.json` | Example shape of configurable normalization rules |
| `examples/sample_entities.md` | Example records and reconciliation scenarios |

---

# Recommended implementation order

1. Project skeleton and local runtime
2. Database schema + migrations
3. Synthetic source files
4. Raw ingestion
5. Deterministic normalization
6. Source-entity extraction / deduplication
7. Reconciliation engine
8. Reconciliation workbench
9. Human acceptance / rejection
10. Canonicalization
11. Technical facts and conflict handling
12. Reuse analysis
13. BOM / reuse UI
14. End-to-end polish and demo

Do not start by building the UI. Do not start by building the LLM agent. First establish traceable data foundations.

---

# Suggested PoC technology boundary

The exact stack is intentionally left open, but the specification assumes:

- Python backend and worker are acceptable;
- SQLite is sufficient for the PoC;
- CSV is the source-file format;
- a small web UI is used for inspection and review;
- the LLM is called through one well-defined provider abstraction;
- deterministic normalization and analysis logic remains normal application code;
- no vector database is required for the first version;
- no graph database is required for the first version;
- no generic enterprise workflow/orchestration product is required.

The implementer may choose equivalent technologies as long as the behavioral contracts in this package are preserved.
