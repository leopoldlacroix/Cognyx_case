# Phase 01: Data Foundation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-09-22
**Phase:** 01-Data Foundation: Ingest & Normalize
**Areas discussed:** Source table design, alias configuration format, soft warning persistence, file hash strategy, normalized column storage, validation approach, source entity extraction timing, engineering notes scope, quantity handling, variant reference normalization, technology choices

---

## Discussion Approach

User requested clarification-first approach rather than interactive questioning. I read the full blueprint specification (docs/blueprint/docs/01–13), the synthetic data spec, scenarios, actual CSV data, and project context files (.planning/PROJECT.md, REQUIREMENTS.md, ROADMAP.md, STATE.md, codebase maps) before surfacing 5 clarification questions.

User resolved all 5 questions directly and confirmed the blueprint is internally consistent and complete. No gray areas required deep-dive discussion — the blueprint already locks all implementation decisions for Phase 1.

---

## Key Decisions Confirmed

### Source table design
- **Option chosen:** Separate tables per source system (`plm_bom_line`, `plm_assembly`, `plm_variant`, `erp_material`, `erp_supplier`, `engineering_note`)
- **Rationale:** Blueprint 03_data_model.md specifies this; cleaner schemas per source system; matches the data model that all downstream phases reference.

### Alias configuration format
- **Option chosen:** JSON config file (`config/normalization.json`), example at `docs/blueprint/config/normalization.example.json`
- **Rationale:** Blueprint 04.6 specifies config file for explicit, reviewable mappings. Non-devs can review alias changes.

### Soft warning persistence
- **Option chosen:** Separate `warnings` table linked to source rows (queryable, filterable, countable)
- **Rationale:** Enables filtering/aggregation for data quality reports in later phases. Blob approach would break this.

### File hash strategy
- **Option chosen:** Content hash (SHA-256), NOT NULL, unique per `(source_system, file_hash)`
- **Rationale:** Bulletproof idempotency. Blueprint 04.3 recommends file hash for duplicate detection.

### Normalized column storage
- **Option chosen:** `_normalized` suffix columns side-by-side with `_raw` columns in each source table
- **Rationale:** Simplest to query; raw and normalized values visible together. Blueprint 03 and 04 both show this pattern.

### Validation approach
- **Hard validation:** Quarantine table for malformed rows, missing required IDs, unparseable quantities. Row excluded from main source tables.
- **Soft validation:** Separate `warnings` table. Row kept in main table with warning record.
- **Quantity handling:** BOM line quantity is required. Unparseable → hard-invalid → quarantined. `quantity_normalized` is REAL, valid numeric for all accepted rows.

### Source entity extraction timing
- **Option chosen:** (b) — populate `source_component`, `source_assembly`, `source_supplier` in Phase 1
- **Rationale:** Deterministic deduplication is cheap and is part of the normalization pipeline. Phase 1 stops before reconciliation proposals.

### Engineering notes scope
- **Option chosen:** Phase 1 = raw ingestion only. No language detection, no text normalization.
- **Rationale:** NORM-06 assigned to Phase 2. Preserve original `note_text` verbatim in Phase 1.

### Variant reference normalization
- **Option chosen:** Generic deterministic rules only (whitespace, casing, punctuation). No semantic aliasing unless configured.
- **Rationale:** No variant aliases in current config. `REGIO-STD` stays `REGIO-STD`.

### Technology choices
- SQLite (PoC scope, PostgreSQL migration path noted)
- Python (sole implementation language)
- No LLM calls in Phase 1 (all deterministic)

---

## Claude's Discretion

Areas left for planner to decide:
- Python web framework / API approach for data explorer (if any in Phase 1)
- ORM vs raw SQLite for schema management
- Exact `src/` directory layout
- Migration approach (single init script vs versioned migrations)
- Database file location

---

## Deferred Ideas

None — discussion stayed within Phase 1 scope. All Phase 2+ capabilities (reconciliation, review workflow, analysis, LLM integration, language detection, ERP normalization) are deferred by design.
