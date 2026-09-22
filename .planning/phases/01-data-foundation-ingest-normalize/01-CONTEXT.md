# Phase 01: Data Foundation - Context

**Gathered:** 2026-09-22
**Status:** Ready for planning

<domain>
## Phase Boundary

Ingest all 6 source CSV files from PLM/ERP/engineering systems into source tables with full provenance (file hash, source row, raw column preservation). Apply hard validation (quarantine malformed rows) and soft validation (warnings for missing description, unknown UOM, empty supplier). Apply deterministic normalization — whitespace collapse, casing standardization, punctuation harmonization, and config-driven UOM/supplier/reference/voltage aliases — storing normalized values alongside raw values. Populate source entity tables (`source_component`, `source_assembly`, `source_supplier`) via deterministic deduplication by `(source_system, source_reference)`.

**Stops at:** Populated source entities with reconciliation eligibility derivable. No reconciliation proposals, no canonical entities, no analysis. Those are Phase 2+.

**Blueprint mapping:** Combines Blueprint execution Phases 1 (schema), 3 (ingestion), 4 (normalization), and 5 (source entity extraction). Synthetic data (Blueprint Phase 2) is already present in `data/inputs/`.
</domain>

<decisions>
## Implementation Decisions

### Source tables — separate per source system
- **D-01:** Create separate raw source tables per source system: `plm_bom_line`, `plm_assembly`, `plm_variant`, `erp_material`, `erp_supplier`, `engineering_note`. Each has `source_file_id` FK, `source_row`, raw columns (immutable), and normalized columns stored alongside. — **Reversibility:** costly — changing to a unified table would require rewriting all ingestion, normalization, and downstream query paths.
- **D-02:** `source_file.file_hash` is NOT NULL and unique per `(source_system, file_hash)`. Ingestion always computes the hash for reliable idempotency. — **Reversibility:** costly — idempotency semantics depend on this; relaxing would allow duplicate file imports.

### Normalization — config-driven, deterministic
- **D-03:** Normalization config lives in `config/normalization.json`. Aliases: UOM (`pcs/pc/piece/units → EA`), supplier (`SIEMENS* → SIEMENS MOBILITY`), reference (`CTRL-AIR01 → CTRL-AIR-01`, `CTRL-HVAC-001 → CTRL-AIR-01`), voltage (`24V/24VDC/24 VOLTS DC → 24 V DC`). Generic rules: whitespace collapse, casing standardization for identifiers, punctuation harmonization. — **Reversibility:** reversible — config file change only; no code change needed for new aliases.
- **D-04:** Raw values are never overwritten. Each normalized column has a `_raw` counterpart. Unknown values: keep raw, leave normalized null/unchanged, emit warning, do not guess. — **Reversibility:** one-way — this is a foundational data-ownership principle; violating it would corrupt the provenance model that all downstream phases depend on.

### Validation — hard quarantine + soft warnings
- **D-05:** Hard validation quarantines structurally malformed rows (wrong column count, unparseable numbers) and rows with missing required identifiers or unparseable quantities. Quarantined rows go to a separate `quarantine` table with rejection reason; they are NOT in the main source tables. — **Reversibility:** costly — quarantine table design affects how unresolved data is surfaced in later phases.
- **D-06:** Soft validation keeps rows but emits warnings for missing description, unknown UOM, empty supplier, contradictory technical fields. Warnings stored in a separate `warnings` table linked to source rows (queryable, filterable, countable) — not a JSON blob column. — **Reversibility:** costly — switching to blob storage would break filtering/aggregation used by data quality reports in later phases.
- **D-07:** For BOM lines, `quantity` is required. Unparseable quantity → hard-invalid → quarantined. `quantity_normalized` is REAL and contains a valid numeric for all accepted BOM rows. — **Reversibility:** costly — quantity parsing semantics affect canonical BOM creation in Phase 3.

### Source entity extraction — Phase 1, deterministic
- **D-08:** Populate `source_component`, `source_assembly`, `source_supplier` in Phase 1. Deterministic deduplication by `(source_system, source_reference)`. This is NOT reconciliation — it is deduplication of normalized source records. Reconciliation proposals (linking source entities to canonical entities) are Phase 2. — **Reversibility:** costly — source entity tables are the bridge between raw source data and the reconciliation engine; changing extraction logic affects all downstream phases.
- **D-09:** Reconciliation eligibility is derived from reconciliation rows (not a redundant `processed` flag). Since no reconciliation records exist yet in Phase 1, all source entities start as "never assessed". — **Reversibility:** reversible — derived state computation can be adjusted without schema changes.

### Engineering notes — raw ingestion only
- **D-10:** Engineering notes are ingested raw in Phase 1. No language detection, no text normalization, no semantic processing of `note_text`. Original text preserved verbatim. NORM-06 (language detection) and any note normalization belong to Phase 2. — **Reversibility:** reversible — adding normalization later is additive; no raw data is affected.

### Variant reference normalization
- **D-11:** Variant references use only generic deterministic rules (trim/collapse whitespace, casing, punctuation harmonization). No semantic aliasing (e.g., `VT-100 → VT100`) unless explicitly configured in `config/normalization.json`. Since no variant aliases are configured, `REGIO-STD` stays `REGIO-STD`. — **Reversibility:** reversible — config-driven; adding variant aliases is a config change.

### Technology choices
- **D-12:** SQLite for storage (PoC scope, sufficient for dataset scale, migration path to PostgreSQL noted for production). — **Reversibility:** costly — schema is designed for SQLite but with proper FKs/indexes for PostgreSQL migration; changing database would require schema adaptation.
- **D-13:** Python as sole implementation language. — **Reversibility:** costly — all code, tests, and tooling are Python; switching languages would be a full rewrite.
- **D-14:** No LLM calls in Phase 1. All normalization and extraction is deterministic. — **Reversibility:** reversible — LLM integration is added in Phase 2+ without affecting Phase 1 code.

### Claude's Discretion
- Python web framework / API approach for the data explorer (if any in Phase 1) — blueprint specifies API endpoints but Phase 1 deliverable may be CLI + SQLite + report output. Planner should decide based on time budget.
- Whether to use an ORM (e.g., SQLAlchemy) or raw SQLite for schema management and queries.
- Exact `src/` directory layout — blueprint suggests `app/` structure with `backend/`, `worker/`, `domain/`, `services/`, `db/`, `tests/` subdirectories.
- Migration approach — single init script vs. versioned migrations.

### Folded Todos
None — no cross-referenced todos matched this phase.
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Data Model & Schema
- `docs/blueprint/docs/03_data_model.md` — Complete ER specification: all source tables, source entity tables, canonical tables, reconciliation tables, technical_fact table, cardinalities, constraints, indexes. This is the schema authority.
- `docs/blueprint/docs/02_architecture.md` — Logical architecture: 6 layers, responsibility boundaries, storage choice (SQLite), dependency rule, worker invocation model.

### Pipeline & Normalization
- `docs/blueprint/docs/04_ingestion_and_normalization.md` — Pipeline stages, ingestion behavior, idempotency rules, validation levels (hard/soft), normalization principles, configuration boundary, unknown value handling, source entity extraction, reconciliation eligibility derivation, definition of done.
- `docs/blueprint/config/normalization.example.json` — Example normalization config: UOM aliases, supplier aliases, reference aliases, voltage aliases. Live config should be created at `config/normalization.json`.

### Principles & Constraints
- `docs/blueprint/docs/01_scope_and_principles.md` — Product narrative, three separate semantic questions (identity/reuse/conflict), in-scope, explicit non-goals, PoC quality bar, four data layers (ownership principle), human-in-the-loop principle, cost/control principle, observability principle.
- `docs/blueprint/docs/13_coding_agent_instructions.md` — Working rules: follow dependency order, read spec first, don't invent hidden state, preserve provenance, keep AI at explicit boundaries, never silently accept semantic mapping, prefer simple code, write tests against invariants, make demo reproducible. Reconciliation build order. What to avoid. Handoff expectations.

### Testing & Validation
- `docs/blueprint/docs/10_testing_and_validation.md` — Testing layers (unit/integration/e2e), determinism requirements, important invariants (raw never overwritten, no silent accepted mappings, rejected → no canonical BOM, unresolved rows visible, canonical BOM traceable, analysis derivable, failed run doesn't invalidate accepted), data-quality test cases, reconciliation test cases, UI acceptance criteria, demo validation script, acceptance gates.

### Data & Scenarios
- `docs/blueprint/docs/09_synthetic_data_spec.md` — Synthetic data design: target volume, variants, assemblies, required messy-data patterns (reference aliases, supplier aliases, UOM variants, voltage text variants, description variation, missing fields), required engineering notes (equivalence, conflict, ambiguity), required reconciliation cases, demo scenario narrative.
- `docs/scenarios.md` — 10 engineered scenarios A–J with where each appears and what the product should demonstrate. Core modeling distinction: identity/alias vs. functional similarity vs. variant-specific specialization.

### Execution Roadmap (Blueprint)
- `docs/blueprint/docs/11_execution_roadmap.md` — Blueprint's own phased implementation plan (Phases 0–12). GSD Phase 1 corresponds to Blueprint Phases 1+3+4+5. Implementation priority when time tight: schema → ingestion → normalization → source entities → component reconciliation → accept/reject → canonical BOM → one reuse screen → one demo scenario.

### Project Context
- `.planning/PROJECT.md` — Project definition: value, business context, requirements summary, key decisions, constraints.
- `.planning/REQUIREMENTS.md` — 32 v1 requirements with traceability to phases. Phase 1 covers: INGEST-01–03, NORM-01–04, SCEN-C.
- `.planning/ROADMAP.md` — 5-phase roadmap derived from requirements. Phase 1 goal, 5 plans, 6 success criteria.
- `.planning/codebase/ARCHITECTURE.md` — Codebase architecture analysis: 6 layers, data flow, key abstractions, invariants, API endpoints, UI screens.
- `.planning/codebase/STACK.md` — Technology stack analysis: Python CPython 3.x, SQLite, no existing dependency manifest, no runnable code yet.
- `.planning/codebase/CONVENTIONS.md` — Code conventions: layer boundaries, naming conventions, four-layer model, provenance preservation, reconciliation conventions, LLM usage conventions, error handling, SQLite conventions, configuration conventions, UI conventions, what to avoid.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **None yet.** The repository currently contains specification documents and synthetic test data only. No `src/` tree exists. The first code written in this phase establishes the foundation all later phases build on.

### Established Patterns
- **Four-layer data model** (source → normalized source → canonical → derived analysis) from blueprint 01 and 03 — this is the architectural pattern all code must follow.
- **Three separate relationship types** (identity/alias, functional similarity, variant-specific specialization) — never collapse into a single "match" concept.
- **Config-driven normalization** — explicit, reviewable mappings in JSON, not hardcoded in code.
- **Provenance-bearing records** — every consequential action leaves trace: input, timestamp, method, confidence, evidence, human decision.

### Integration Points
- **Schema → Ingestion → Normalization → Source Entity Extraction** is the Phase 1 pipeline. Each stage's output is the next stage's input.
- **Normalization config** (`config/normalization.json`) is consumed by the normalization service and must be loadable at runtime.
- **SQLite database file** — location TBD by planner; blueprint implies it lives in the app/db/ directory or project root.
- **Synthetic data in `data/inputs/`** — immutable; ingestion reads from here, writes to database.
- **Normalized output** — per AGENTS.md, goes to `data/processed/` (or equivalent), separate from source data.

</code_context>

<specifics>
## Specific Ideas

- The demo narrative (blueprint 09.8) should be kept in mind: show two variants with apparently different HVAC controller references → reconcile → show shared canonical component. Phase 1 enables this by getting clean data into the system.
- The dataset is deliberately messy with specific patterns (reference aliases, supplier aliases, UOM variants, voltage variants, missing fields) — normalization must handle all of these correctly.
- SCEN-C (typo/alias reconciliation) is the only scenario assigned to Phase 1 — specifically, `CTRL-AIR01` normalizing to `CTRL-AIR-01` must work end-to-end.
- Blueprint 11_execution_roadmap.md lists "Must-have" priority: schema, ingestion, normalization, source entities. These are exactly Phase 1.
</specifics>

<deferred>
## Deferred Ideas

### Reviewed Todos (not folded)
None.

### Out of Phase Scope
- **LLM-assisted reconciliation** — Phase 2 (RECON-01 through RECON-04)
- **Human review workflow (accept/reject UI)** — Phase 3 (REVIEW-01 through REVIEW-03)
- **Cross-variant reuse analysis reports** — Phase 3+ (ANALYSIS-01 through ANALYSIS-05)
- **ERP material normalization (supplier ID mapping, UOM standardization)** — Phase 2 (NORM-05)
- **Engineering note normalization (language detection, text extraction)** — Phase 2 (NORM-06)
- **Technical fact extraction and conflict detection** — Phase 3+ (blueprint Phase 9)
- **Canonical BOM materialization** — Phase 3 (blueprint Phase 8)
- **Web UI (React/TypeScript)** — out of PoC scope; CLI + report output for demo
</deferred>

---

*Phase: 01-Data Foundation: Ingest & Normalize*
*Context gathered: 2026-09-22*
