---
last_mapped_commit: 92a308bb4f3975a737c94509b667c651a00285ba
last_mapped_at: 2026-09-22
---
# Architecture — Cognyx BOM Reuse Explorer (PoC)

**Analysis Date:** 2026-09-22

> Architecture decisions, layers, data flow, abstractions, and entry points for the Cognyx Alstom FDE pilot.

<!-- refreshed: 2026-09-22 -->

---

## 1. Purpose

The Cognyx BOM Reuse Explorer is a small internal engineering workbench for comparing Bills of Materials across multiple train variants. It ingests messy multi-source PLM/ERP/engineering exports, normalizes them, proposes candidate entity reconciliations, lets a human accept or reject those proposals, and then derives cross-variant reuse analysis from the accepted canonical model.

The system is explicitly **not** an autonomous answer engine. It is an auditable, provenance-bearing pipeline where AI proposes and humans decide.

---

## 2. Architectural Pattern

**Layered pipeline with explicit human-in-the-loop reconciliation.**

```text
Raw PLM / ERP / Engineering data
        ↓
Validation + normalization
        ↓
Source entity extraction
        ↓
Reconciliation (candidate proposals)
        ↓
Human review (accept / reject / redirect)
        ↓
Canonical model + canonical BOM
        ↓
Technical facts + conflict detection
        ↓
Cross-variant reuse analysis
        ↓
Web UI workbench
```

The architecture separates concerns into six logical areas, each with a clear responsibility boundary and no backward mutation of upstream layers.

---

## 3. Layers

### 3.1 Source Ingestion Layer

**Responsibility:** Get source files into source tables and preserve provenance. Must not perform semantic reconciliation.

**Inputs:**

- `data/inputs/plm/bom_export.csv` — multi-variant BOM lines
- `data/inputs/plm/assembly_master.csv` — variant-specific PLM assembly references
- `data/inputs/plm/variant_configuration.csv` — 5 train variants
- `data/inputs/erp/material_master.csv` — material master records
- `data/inputs/erp/supplier_master.csv` — supplier master records
- `data/inputs/engineering/technical_notes.csv` — free-text notes (FR/EN)

**Tables (source/ingestion):**

- `source_file` — every ingested file, its source system, file hash, ingestion timestamp
- `plm_bom_line` — raw BOM rows with both raw and normalized columns
- `plm_assembly` — source-side assembly records
- `plm_variant` — source-side variant metadata
- `erp_material` — ERP material master
- `erp_supplier` — ERP supplier records
- `engineering_note` — technical notes with object reference, type, language, author, date, text

**Key behaviors:**

- File hash enables idempotent re-ingestion
- Raw columns are immutable after ingestion
- Normalized columns may be recomputed
- `source_row` tracks the original file row number (not a domain identity)
- Hard validation rejects/quarantines structurally malformed rows
- Soft validation keeps rows but emits warnings (missing description, unknown UOM, etc.)

**Entry point:** `POST /ingestion/files` — register/upload/import one source file.

---

### 3.2 Normalization / Preparation Layer

**Responsibility:** Deterministic transformations that reduce superficial variation without claiming semantic identity.

**What it normalizes:**

- Whitespace collapse
- Casing standardization for identifiers
- Punctuation harmonization
- UOM aliases (e.g. `pcs` → `EA`, `units` → `EA`)
- Supplier name aliases (e.g. `SIEMENS` → `SIEMENS MOBILITY`)
- Reference aliases (e.g. `CTRL-AIR01` → `CTRL-AIR-01`)
- Voltage expression normalization (e.g. `24V` → `24 V DC`)

**Configuration:** `docs/blueprint/config/normalization.example.json` — explicit, reviewable mappings for UOM, supplier, reference, and voltage aliases.

**Key principle:** Raw values are never replaced. Normalized values are stored alongside raw values for transparency.

```text
component_ref_raw        = CTRL-AIR01
component_ref_normalized = CTRL-AIR-01
```

**Entry point:** `NormalizationService` — called during ingestion and re-runnable.

---

### 3.3 Source Entity Extraction Layer

**Responsibility:** Create distinct source-side entities from normalized raw records.

**Entity types:**

- `source_component` — distinct by `(source_system, source_reference)`
- `source_assembly` — distinct by `(source_system, source_reference)`
- `source_supplier` — distinct by `(source_system, source_reference)` or equivalent stable source identity

**Key behavior:** A source entity may be referenced by many BOM rows. Reconciliation happens at the entity level, not once per BOM line.

**Derived state:** Every source entity exposes eligibility state derived from reconciliation rows:

- never assessed
- assessed but unresolved
- accepted
- rejected/no-match
- needs reassessment

**Entry point:** `SourceEntityService` — extraction, upsert/deduplication, mapping from raw records to source entities.

---

### 3.4 Reconciliation Worker

**Responsibility:** Propose candidate mappings between source entities and canonical entities without silently deciding.

**Execution modes:**

- **Batch mode:** Explicitly launched for an entity type (e.g. "Reconcile all unassessed components"). Shows queued/processing/completed status, items processed, items requiring review, errors.
- **Single entity mode:** Triggered from a source entity detail screen. Useful for demos and manual investigation.

**Candidate generation pipeline (layered, cheap → expensive):**

| Stage | Method | When used |
|-------|--------|-----------|
| A | Exact normalized match | Normalized source reference equals a canonical reference/known alias |
| B | Structured similarity | Compare name/description, category, supplier, identifiers, technical facts |
| C | Semantic similarity | Embedding or text-similarity (optional for PoC) |
| D | LLM assessment | When candidate set remains ambiguous or engineering notes provide semantic evidence |

**Candidate object contract:**

- candidate canonical entity ID
- match confidence 0–1
- recommendation: `MATCH`, `NO_MATCH`, `UNCERTAIN`
- method
- rationale
- evidence list
- conflicts detected
- fields compared

**Confidence bands (UI thresholds only, not engineering certification):**

- 0.90–1.00: strong evidence
- 0.75–0.89: likely match
- 0.50–0.74: uncertain
- <0.50: weak candidate

**LLM boundary:**

- LLM receives only necessary information: source entity, candidate entities, structured attributes, relevant engineering notes, explicit task, required response schema
- Prompt must distinguish identity from interchangeability, evidence from inference, missing information from contradiction
- LLM must be allowed to say `UNCERTAIN`
- LLM must not invent technical facts
- LLM results are `ASSESSED` until human action changes them to `ACCEPTED` or `REJECTED`

**Persistence:** `component_reconciliation`, `assembly_reconciliation`, `supplier_reconciliation` — each with source entity FK, canonical entity FK (nullable), status, method, confidence, rationale, evidence JSON, reconciliation run FK, timestamps.

**Status flow:** `PENDING → ASSESSED → ACCEPTED` or `PENDING → ASSESSED → REJECTED`

**Entry points:**

- `POST /reconciliation/runs` — launch batch run
- `GET /reconciliation/runs/{id}` — run progress/summary
- `GET /reconciliation/{entity_type}` — source entities with reconciliation state
- `POST /reconciliation/{entity_type}/{id}/assess` — single-entity reconciliation
- `POST /reconciliation/{entity_type}/{id}/decision` — accept/reject decision

---

### 3.5 Canonicalization Layer

**Responsibility:** Turn accepted reconciliation decisions into canonical relationships that downstream analysis can safely use.

**Trigger:** Downstream of human-approved reconciliation. A source BOM line becomes a canonical BOM relationship only when its required identities are resolved.

**Process for each `plm_bom_line`:**

1. Resolve source variant to canonical `variant`
2. Resolve source assembly through accepted assembly reconciliation
3. Resolve source component through accepted component reconciliation
4. Parse quantity/UOM from normalized values
5. Create/update `bom_relationship`
6. Preserve `source_bom_line_id`

**Unresolved lines:** Remain visible as unresolved source data. Must not be presented as authoritative canonical BOM relationships.

**Canonical tables:**

- `component` — internal canonical component identity (id, name, category, created_at)
- `assembly` — canonical assembly (id, name, category, created_at)
- `supplier` — canonical supplier (id, name, country, created_at)
- `variant` — canonical train variant (id, name, train_family, market, climate_class, capacity_class, voltage_system, created_at)
- `bom_relationship` — canonical BOM (variant_id, assembly_id, component_id, quantity, unit, source_bom_line_id, created_at)

**Recommended unique constraint on `bom_relationship`:** `(variant_id, assembly_id, component_id, source_bom_line_id)`

**PoC simplification:** Model hierarchy as `Variant → Assembly → Component`. Document that production can support arbitrary BOM depth.

**Entry points:**

- `GET /canonical/components/{id}` — canonical entity + linked source references
- `GET /canonical/assemblies/{id}` — assembly, components, variant usage
- `GET /canonical/bom` — filtered by variant/assembly/component

---

### 3.6 Analysis Layer

**Responsibility:** Deterministic engineering/business rules: reused assembly detection, component coverage across variants, reuse candidates, blockers, conflicting technical facts.

**Technical fact extraction (`technical_fact` table):**

| Column | Purpose |
|--------|---------|
| entity_type | `COMPONENT`, `ASSEMBLY`, `VARIANT`, optionally `SUPPLIER` |
| entity_id | canonical entity |
| attribute | e.g. `operating_voltage`, `interface`, `temperature_range`, `power_rating`, `mounting_type`, `enclosure_ip_class` |
| value | the fact value |
| unit | nullable |
| source_type | `ERP`, `PLM`, `ENGINEERING_NOTE`, `MANUAL` |
| source_id | source record identifier |
| confidence | nullable 0–1 |
| status | `OBSERVED`, `VALIDATED`, `CONFLICTING` |
| created_at | timestamp |

**Conflict detection:** A conflict exists when materially different values are associated with the same canonical entity/attribute and cannot be trivially normalized. Example: ERP says 48 V DC, engineering note says 24 V DC for the same component. The analysis layer surfaces the conflict instead of arbitrarily selecting one.

**Reuse categories:**

- **Reused** — same canonical component/assembly appears across multiple variants
- **Reuse candidate** — different references appear potentially interchangeable, but evidence insufficient for authoritative reuse
- **Blocked reuse** — candidate exists but material incompatibility or unresolved conflict prevents safe reuse
- **Unresolved** — identity or technical evidence insufficient

**Assembly-level analysis metrics:**

- component overlap ratio
- exact common components
- variant-specific components
- unresolved components
- conflicting facts
- potential substitution opportunities

**Reuse logic signals:**

- same canonical component across variants
- compatible required technical attributes
- no unresolved critical conflicts
- same or compatible voltage/interface/mounting constraints
- supplier considerations where relevant
- lifecycle/status where supplied

**Entry points:**

- `GET /analysis/overview` — factual aggregate counts
- `GET /analysis/reuse` — filtered by variant/assembly/status
- `GET /analysis/reuse/{assembly_id}` — detailed cross-variant comparison + evidence
- `GET /analysis/data-quality` — detected quality issues

---

### 3.7 Web UI / API Layer

**Philosophy:** Engineering workbench, not marketing dashboard. Every aggregate number leads to inspectable underlying records.

**Recommended navigation:**

1. Overview
2. Data Explorer
3. Reconciliation
4. BOM Explorer
5. Reuse Analysis
6. Data Quality

**Screen summary:**

| Screen | Purpose |
|--------|---------|
| Overview | factual counters: variants, BOM lines, source components, canonical components, accepted mappings, items requiring review, unresolved items, data-quality issues, reuse opportunities |
| Data Explorer | table selector, search/filter, pagination, row detail, raw vs normalized values, source file provenance. Tabs: Source files, PLM BOM lines, Components, Assemblies, Suppliers, Variants, Technical facts |
| Reconciliation Workbench | entity type selector, batch launch, last run status, counts (pending/assessed/accepted/rejected), source reference, normalized reference, description, status, candidate, confidence, method, last assessed, action |
| Reconciliation detail | left side: source entity (raw ref, normalized ref, description, source system, source record, linked BOM usage). right side: candidate matches (canonical ID/name, confidence, rationale, evidence, conflicting fields, accept/reject controls) |
| Reconciliation run detail | entity type, start/end time, status, total eligible, processed, assessed, review required, errors, optional method breakdown |
| BOM Explorer | select variant → select assembly → see source references vs canonical entities → inspect quantities and technical facts |
| Reuse Analysis | primary table: Variant/Assembly × Reuse status × Shared components × Blockers × Evidence. Drill-down to component-level evidence |
| Data Quality | duplicate references, normalization warnings, missing supplier, missing description, conflicting technical facts, unresolved reconciliation, source-reference aliases. Each issue links to underlying record |

**Action flow:** `Inspect → Assess → Review → Accept/Reject → Analyze`

**Service boundaries (backend modules):**

- `IngestionService`
- `NormalizationService`
- `SourceEntityService`
- `ReconciliationService`
- `CanonicalizationService`
- `TechnicalFactService`
- `ReuseAnalysisService`
- `RunService`

**Response principles:** API exposes IDs and provenance needed by UI to navigate backward. Errors are structured enough for UI to display useful messages.

**Concurrency assumption:** PoC assumes one active operator. Mutation endpoints validate current status before changing it.

**No business logic in frontend:** Reconciliation and reuse rules stay server-side so the same logic can be tested independently.

---

## 4. Data Flow

```text

1. File discovery
2. Source-file registration (source_file record, file hash)
3. Schema validation (required columns, hard/soft validation)
4. Raw row ingestion (preserve original strings, record source_row)
5. Normalization (deterministic transformations, config-driven aliases)
6. Source-entity extraction (deduplicate by source_system + source_reference)
7. Reconciliation eligibility calculation (derived from reconciliation rows)
   ↓ [explicit launch]
8. Reconciliation candidate generation (Stage A → B → C → D)
9. LLM assessment (optional, structured output, validated)
10. Persistence of candidate assessments (status = ASSESSED)
   ↓ [human action]
11. Accept/reject decision (status → ACCEPTED/REJECTED)
12. Canonicalization (only accepted mappings create canonical BOM)
13. Technical fact extraction + conflict detection
14. Reuse analysis (deterministic rules from canonical model)
15. UI presentation (all results traceable back to source evidence)

```

---

## 5. Key Abstractions

### 5.1 Four Data Layers (Data Ownership Principle)

| Layer | Description | Mutability |
|-------|-------------|------------|
| **Source** | Exactly what the customer gave us | Immutable |
| **Normalized source** | Deterministic cleaning of source values | Recomputable |
| **Canonical** | Application's reconciled representation | Application-managed |
| **Derived analysis** | Conclusions from canonical data + sourced technical facts | Recomputable |

Never destroy the previous layer when creating the next one.

### 5.2 Three Separate Relationship Types (Never Collapse)

1. **Identity/alias** — two source IDs refer to the same canonical entity (e.g. `CTRL-AIR-01` vs `CTRL-AIR01`)
2. **Functional similarity/potential substitution** — different entities, possibly interchangeable in context
3. **Variant-specific specialization** — intentional variant-specific component choice (e.g. Nordic cold-rated parts)

A similarity score must not automatically turn these into one canonical entity.

### 5.3 Reconciliation as Reviewable Relationship

```text
raw source record → candidate canonical entity → pending/accepted/rejected
```

Each reconciliation records: source system, raw ID, canonical ID, status, match method, confidence, rationale, evidence.

A mapping table is preferable to a simple grouped-name JSON object.

### 5.4 Reconciliation Run (Batch Traceability)

| Column | Purpose |
|--------|---------|
| id | PK |
| entity_type | `COMPONENT`, `ASSEMBLY`, `SUPPLIER` |
| started_at | NOT NULL |
| completed_at | nullable |
| status | `QUEUED`, `RUNNING`, `COMPLETED`, `FAILED`, `PARTIAL` |
| items_processed | default 0 |
| items_assessed | default 0 |
| items_needing_review | default 0 |
| error_count | default 0 |
| created_by | nullable |

A run must be created before processing starts and updated as progress changes.

### 5.5 Polymorphic Technical Fact

`technical_fact` uses `(entity_type, entity_id)` as a polymorphic reference for the PoC. Production may replace it with typed fact tables or graph-native properties if querying needs justify it.

Example:

```text
COMPONENT 42 | operating_voltage | 24 | V DC | ENGINEERING_NOTE | 7
COMPONENT 42 | interface          | CAN | null | PLM             | 91
COMPONENT 42 | operating_voltage | 48 | V DC | ERP             | 204
```

Those facts can coexist so that conflict detection is possible.

### 5.6 Dependency Rule

Downstream layers can depend on upstream persisted outputs, but the worker should not reach backward and alter raw source data. A canonical BOM should only use accepted mappings.

---

## 6. Storage

**SQLite** is sufficient for the PoC because:

- Small synthetic data volume
- Single local operator
- No high-concurrency requirement
- No need for distributed transactions

The schema uses proper primary/foreign keys and indexes so that migrating to PostgreSQL later is straightforward.

---

## 7. Entry Points

### 7.1 API Endpoints

**Ingestion:**

- `POST /ingestion/files` — register/upload/import one source file
- `GET /ingestion/files` — recent source files and ingestion status

**Data Explorer:**

- `GET /data/{entity_type}` — with search, status filter, source-system filter, pagination
- `GET /data/{entity_type}/{id}` — source/entity fields, normalized fields, provenance, related rows, reconciliation state

**Reconciliation:**

- `POST /reconciliation/runs` — launch batch run (entity type, scope, optional limits)
- `GET /reconciliation/runs/{id}` — run progress and summary
- `GET /reconciliation/{entity_type}` — source entities with reconciliation state
- `POST /reconciliation/{entity_type}/{id}/assess` — single-entity reconciliation
- `POST /reconciliation/{entity_type}/{id}/decision` — accept/reject decision

**Canonical:**

- `GET /canonical/components/{id}` — canonical entity + linked source references
- `GET /canonical/assemblies/{id}` — assembly, components, variant usage
- `GET /canonical/bom` — filtered by variant/assembly/component

**Analysis:**

- `GET /analysis/overview` — factual aggregate counts
- `GET /analysis/reuse` — filtered by variant/assembly/status
- `GET /analysis/reuse/{assembly_id}` — detailed cross-variant comparison + evidence
- `GET /analysis/data-quality` — detected quality issues

### 7.2 Worker Entry Points

- Batch reconciliation launch (from UI or operator command)
- Single-entity reconciliation (from entity detail page)
- Deterministic exact/normalized matching before any LLM call

### 7.3 UI Entry Points

- Overview screen (entry point for demo)
- Data Explorer (inspect imported data)
- Reconciliation Workbench (launch batch, review candidates)
- BOM Explorer (inspect one variant/assembly)
- Reuse Analysis (cross-variant comparison)
- Data Quality (issues list)

---

## 8. Non-Goals (PoC Scope Discipline)

Do not implement unless needed to make the demo work:

- Full PLM/ERP integration
- Arbitrary-depth enterprise BOM modeling
- Real-time event streaming
- Enterprise identity/access management
- Multi-tenant security model
- Complex ontology editor
- Graph database deployment
- Vector database deployment
- Production-grade job scheduler
- Automated final engineering approval
- Autonomous mutation of source data
- Sophisticated optimization/solver algorithms
- Full change-management/version-control workflow
- OCR/PDF extraction
- General-purpose chatbot

---

## 9. Key Scenarios the Architecture Must Support

| ID | Scenario | Architectural implication |
|----|----------|--------------------------|
| A | Obvious cross-variant reuse | Canonical BOM must show same component across variants |
| B | Hidden cross-source reuse | Reconciliation must link PLM/ERP/note IDs to one canonical entity |
| C | Typo/alias reconciliation | Normalization + exact-match stage must handle `CTRL-AIR01` / `CTRL-AIR-O1` |
| D | Similar-but-not-identical | Structured similarity must not auto-merge 24V and 48V controllers |
| E | Variant-specific intentional differences | Nordic cold-rated parts must remain distinct canonical entities |
| F | Potential reuse requiring review | Reuse analysis must surface candidates with blockers, not silent merges |
| G | Conflicting evidence — surface, don't normalize | `technical_fact` must allow coexisting conflicting values with `CONFLICTING` status |
| H | Multilingual evidence | Engineering notes in FR/EN must be ingested and searchable without losing original wording |
| I | Data-quality issues | Validation panel must catch units, duplicate BOM lines, invalid quantities independently of identity matching |
| J | Lifecycle mismatch | ERP/PLM status differences visible as separate issue |

---

## 10. Production Evolution Notes

| Concern | PoC | Production |
|---------|-----|------------|
| Database | SQLite | PostgreSQL or enterprise data platform |
| File ingestion | CSV upload/import | Connectors to PLM/ERP, scheduled extraction, incremental ingestion |
| Identity model | Simple relational canonical entities | Potentially richer engineering ontology/knowledge graph |
| Reconciliation | Explicit worker + one LLM adapter | Scalable workers, caching, model routing, versioned prompts, evaluation datasets, cost tracking, confidence calibration, human-review queues, audit history, tenant isolation |
| Technical facts | Simple fact table | Typed ontology properties, source lineage, versioned assertions, richer conflict semantics |
| UI | One operator | Role-based workflows, permissions, collaborative review, saved views, notifications, richer audit trails |
| Analysis | Deterministic rules | Domain-specific compatibility rules, optimization, constraints, scenario simulation, potentially advanced graph/solver components |
| Reliability | — | Auth/authz, secrets management, monitoring, structured logs, retry policies, dead-letter/error handling, backup/restore, migrations, data retention, security reviews, evaluation and regression suites |

The important design choice is not that the PoC has every production component. It is that the boundaries are already correct:

```text
source → normalize → reconcile → human decision → canonical model → analysis
```

Those boundaries allow the system to scale in sophistication without changing its conceptual workflow.

---

## 11. Invariants

1. Raw source values are never overwritten by normalization.
2. Reconciliation never silently creates an accepted mapping.
3. Rejected mappings cannot create canonical BOM relationships.
4. Unresolved source rows remain visible.
5. Canonical BOM rows must be traceable to source BOM lines.
6. Analysis results must be derivable from persisted data.
7. A failed reconciliation run must not invalidate previously accepted mappings.
8. Deterministic transformations must produce the same result for the same input/configuration.
9. LLM output is evidence/proposal data that must pass application validation.
10. The UI should not directly contain reconciliation logic.

---

## 12. Related Documents

- `docs/blueprint/docs/01_scope_and_principles.md` — scope, product narrative, engineering principles
- `docs/blueprint/docs/03_data_model.md` — complete ER specification
- `docs/blueprint/docs/04_ingestion_and_normalization.md` — pipeline specification
- `docs/blueprint/docs/05_reconciliation.md` — reconciliation engine specification
- `docs/blueprint/docs/06_canonicalization_and_analysis.md` — canonicalization, technical facts, reuse analysis
- `docs/blueprint/docs/07_ui_specification.md` — UI/screen specification
- `docs/blueprint/docs/08_api_and_service_contracts.md` — API and service contracts
- `docs/blueprint/docs/09_synthetic_data_spec.md` — synthetic data design
- `docs/blueprint/docs/10_testing_and_validation.md` — testing strategy
- `docs/blueprint/docs/11_execution_roadmap.md` — phased implementation plan
- `docs/blueprint/docs/12_production_evolution.md` — production evolution notes
- `docs/blueprint/docs/13_coding_agent_instructions.md` — coding agent/developer handoff
- `docs/scenarios.md` — 10 engineered scenarios (A–J)
- `docs/blueprint/config/normalization.example.json` — normalization configuration example
- `docs/blueprint/examples/sample_entities.md` — sample reconciliation scenarios

*2026-09-22 analysis: Architecture documentation generated from blueprint specifications and synthetic dataset.*
