# Phase 02: Entity Resolution & Reconciliation Engine - Context

**Gathered:** 2026-09-23  
**Status:** Ready for execution

<domain>
## Phase Boundary

**Pre-Phase 2 Step (Plan 02-03):** Schema refinement + source entity extraction. The source entity tables (`source_component`, `source_assembly`, `source_supplier`) exist in `schema.py` but are **not populated**. Before entity resolution can work per D-2.3, a schema refinement + extraction step must: add missing normalized columns to `erp_supplier` and `engineering_note`, create the `source_assembly_variant` junction table (HIGH priority per data model discussion), create reconciliation tables, and populate source entity tables from raw data.

Normalize ERP materials (supplier ID → supplier name mapping, UOM standardization) and engineering notes (language detection FR/EN/DE, text normalization). Then run entity resolution: detect identity/alias relationships across source entities with confidence scoring, detect functional similarity candidates (surface, don't merge), detect variant-specific intentional differences (exclude from reuse), and populate complete reconciliation records.

**Starts with:** Phase 1 output — all 6 CSV files ingested, normalized, raw tables populated with normalized columns.

**Stops at:** Reconciliation records in `component_reconciliation`/`supplier_reconciliation` tables for all detected relationships. No human review interface, no canonical model, no analysis reports. Those are Phase 3+.

**Blueprint mapping:** Combines Blueprint execution Phases 6 (entity resolution), 7 (reconciliation records), and parts of Phase 9 (technical fact extraction prep). Source entity extraction is a prerequisite step unique to this PoC implementation.</domain>
</domain>

<decisions>
## Implementation Decisions

### Entity Resolution Approach
- **D-2.1:** Entity resolution is deterministic rule-based in Phase 2. No LLM calls. Matching is by normalized reference equality (identity) or prefix similarity (functional similarity). — **Reversibility:** reversible — LLM integration can be added in Phase 5+ without affecting Phase 2 code.

### Reconciliation Record Design
- **D-2.2:** Reconciliation records use canonical status workflow per blueprint §3.6: `PENDING → ASSESSED → ACCEPTED/REJECTED`. Identity matches start as `PENDING` with confidence 0.95 (HIGH), functional similarity as `PENDING` with `review_needed=True` and confidence 0.50 (MEDIUM), variant-specific as `PENDING` with `review_needed=False` and high confidence (not excluded — reviewed but not flagged as reuse candidates). Confidence is REAL (0–1), not TEXT. `method` field records detection method (EXACT, NORMALIZED, STRUCTURED, SEMANTIC, LLM, MANUAL). — **Reversibility:** costly — status workflow affects Phase 3 review interface design.

### Source Assembly Variant Junction Table
- **D-2.7:** `source_assembly_variant` junction table created to separate assembly identity from variant usage. `plm_assembly` has `variant_ref_raw` inline (conflating identity + usage); the junction table preserves this relationship at the source entity layer. Canonical `bom_relationship` (Phase 3) handles variant→assembly→component natively. LOW priority junction tables (`note_entity_reference`, `material_supplier`) are NOT created. — **Reversibility:** reversible — junction table can be dropped if not needed.

### Source Entity Extraction Prerequisite
- **D-2.8:** Source entity tables (`source_component`, `source_assembly`, `source_supplier`) exist in schema.py but are not populated by Phase 1 ingestion. Plan 02-03 extracts them from normalized raw tables before entity resolution runs. D-2.3 (reconciliation queries source entities) depends on this. — **Reversibility:** reversible — extraction can be modified without affecting core logic.

### Source Entity to Reconciliation Bridge
- **D-2.3:** Reconciliation queries source entities (source_component, source_assembly, source_supplier) by normalized reference, not raw source tables directly. This ensures we reconcile the deduplicated, normalized view. — **Reversibility:** costly — changes to source entity extraction affect reconciliation queries.

### Engineering Note Language Detection
- **D-2.4:** Language detection is heuristic-based (accented characters, common words per language), not LLM-based. Suitable for FR/EN/DE triad in this dataset. — **Reversibility:** reversible — can be upgraded to LLM-based detection later.

### Variant-Specific Detection
- **D-2.5:** Variant-specific detection is based on exclusive usage: components that appear only in Nordic variant BOMs and nowhere else are flagged as variant-specific. This is a conservative heuristic that may miss some variant-specific parts but won't falsely flag standard parts. — **Reversibility:** reversible — detection heuristics can be refined.

### Reconciliation Record Uniqueness
- **D-2.6:** Reconciliation records are unique by (source_system_a, source_table_a, raw_id_a, source_system_b, source_table_b, raw_id_b). Duplicate detection proposals are rejected. — **Reversibility:** costly — uniqueness constraint affects how proposals are curated.

</decisions>

<canonical_refs>
## Canonical References

### Data Model & Schema
- `docs/blueprint/docs/03_data_model.md` — Reconciliation table definition, source_component table, canonical entity tables
- `docs/blueprint/docs/02_architecture.md` — 6-layer architecture, reconciliation layer responsibility

### Pipeline & Normalization
- `docs/blueprint/docs/04_ingestion_and_normalization.md` — NORM-05, NORM-06 specifications
- `docs/blueprint/docs/06_canonicalization_and_analysis.md` — Entity resolution principles, functional similarity vs identity distinction

### Principles & Constraints
- `docs/blueprint/docs/01_scope_and_principles.md` — Three relationship types must stay separate
- `docs/blueprint/docs/13_coding_agent_instructions.md` — Reconciliation build order, what to avoid

### Testing & Validation
- `docs/blueprint/docs/10_testing_and_validation.md` — Reconciliation test cases, invariants

### Data & Scenarios
- `docs/scenarios.md` — SCEN-B, SCEN-D, SCEN-E, SCEN-H specifications
- `docs/blueprint/docs/09_synthetic_data_spec.md` — Required reconciliation cases in synthetic data

### Project Context
- `.planning/STATE.md` — Current state, Phase 1 complete
- `.planning/ROADMAP.md` — Phase 2 requirements and success criteria
- `.planning/REQUIREMENTS.md` — RECON-01 through RECON-04, NORM-05, NORM-06
- `app/services/normalization.py` — Existing normalization functions from Phase 1
- `app/services/ingestion.py` — Existing ingestion functions
- `app/db/schema.py` — Database schema (source entity tables defined but NOT populated; missing `supplier_id_normalized` on `erp_supplier`; missing `language_normalized`/`note_text_normalized` on `engineering_note`; reconciliation tables not yet created)
- `.planning/data-model-discussion-2026-09-23.md` — Data model discussion: source_assembly_variant junction table (HIGH priority), supplier placement question
- `config/normalization.json` — Alias configuration
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets from Phase 1
- **normalization.py**: `normalize_reference()`, `normalize_description()`, `normalize_uom()`, `normalize_supplier()`, `detect_language()` (if created), `load_normalization_config()`, alias functions, `normalize_erp_materials()` (partial — queries non-existent `erp_supplier.supplier_id_normalized` column)
- **ingestion.py**: `ingest_csv_file()`, `ingest_all_files()`, `get_quarantine_report()`, `get_warnings()`, `add_warning()`
- **validation.py**: `validate_hard()`, `check_soft_validation()`, `check_row_structure()`
- **schema.py**: Full database schema including source_component, source_assembly, source_supplier tables (defined but NOT populated); missing `supplier_id_normalized` on `erp_supplier`, `language_normalized`/`note_text_normalized` on `engineering_note`; reconciliation tables not yet created
- **config/normalization.json**: UOM aliases, supplier aliases, reference aliases

### Established Patterns
- Four-layer data model: source → normalized source → canonical → derived analysis
- Three separate relationship types: identity/alias, functional similarity, variant-specific
- Config-driven normalization via JSON
- Provenance-bearing records with timestamps and method tracking
- Deterministic processing — no LLM calls in Phase 2

### Integration Points
- Entity resolution queries source_component, source_assembly, source_supplier tables
- Reconciliation records link back to source entities via raw_id + source_system
- Language detection uses existing normalize_whitespace() for text cleanup
- Supplier matching uses config/normalization.json supplier_aliases
</code_context>

<specifics>
## Specific Ideas

- SCEN-B requires CTRL-AIR-01 (PLM BOM) to match CTRL-AIR-01 (ERP material) — same normalized reference in source_component
- SCEN-D requires STANDARD-DOOR-CTRL vs EXPORT-DOOR-CTRL to be flagged as similar but NOT merged (canonical status: PENDING, confidence 0.50, review_needed=True)
- SCEN-E requires Nordic-specific components to be detected via source_assembly_variant junction table and excluded (not merged)
- SCEN-H requires engineering notes in FR/EN/DE to have language detected (language_normalized column to be added in Plan 02-03)
- The reconciliation table must support all three match types with canonical schema (blueprint §3.6): component_reconciliation, assembly_reconciliation, supplier_reconciliation
- `source_assembly_variant` junction table (HIGH priority per data model discussion) is created in Plan 02-03 to preserve variant-assembly relationship lost during source_assembly extraction
- Plan 02-03 (Schema Refinement + Source Entity Extraction) is a **new prerequisite step** — raw tables exist and are normalized, but source entity tables are empty and key columns/tables are missing
- Plan 02-04/02-05 query source_entity tables (per D-2.3) — alignment with data model discussion and blueprint §3.4
</specifics>

<deferred>
## Deferred Ideas

### Out of Phase Scope
- Human review interface (accept/reject UI) — Phase 3
- Canonical entity creation from accepted reconciliations — Phase 3
- Cross-variant reuse analysis reports — Phase 3+
- LLM-assisted reconciliation proposals — Phase 5+
- Automated confidence calibration — Phase 5+
</deferred>

---

*Phase: 02-Entity Resolution & Reconciliation Engine*
*Context gathered: 2026-09-23*
