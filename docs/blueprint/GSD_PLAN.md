# Cognyx FDE PoC — GSD Implementation Plan

**Product**: BOM Reuse Explorer — a small Forward Deployed Engineer proof-of-concept  
**Core question**: Given several train variants with inconsistent PLM/ERP references, what is already reusable, what could be reusable, and what prevents reuse?  
**Core principle**: AI proposes; deterministic logic validates; humans decide when the mapping is consequential.

---

## Phase 0 — Project Foundation

**Goal**: Create a minimal, runnable repository with backend, worker, and UI boundaries.

**Steps**:
1. Initialize repository structure (app/backend, app/worker, app/frontend, app/domain, app/services, app/db, app/tests, config/, data/raw/, docs/)
2. Set up dependency management (Python backend + worker; SQLite; small web UI)
3. Create environment configuration and application configuration
4. Implement database initialization/migration mechanism
5. Build frontend shell (empty screens matching UI spec navigation)
6. Implement backend health endpoint
7. Create worker entry point
8. Write README with run instructions

**Deliverables**:
- Repository boots locally
- Configuration is centralized
- Database initializes from empty state
- Backend health check works
- Worker entry point exists
- UI shell works

**Do NOT build yet**: LLM integration, polished dashboards, vector search, graph DB

**Acceptance**: Repository starts locally and exposes backend/UI/worker entry points.

---

## Phase 1 — Database Schema

**Goal**: Implement exactly the entities defined in `docs/blueprint/docs/03_data_model.md`.

**Steps**:
1. Create all source/ingestion tables: `source_file`, `plm_variant`, `plm_assembly`, `plm_bom_line`, `erp_material`, `erp_supplier`, `engineering_note`
2. Create source entity tables: `source_component`, `source_assembly`, `source_supplier`
3. Create canonical tables: `component`, `assembly`, `supplier`, `variant`, `bom_relationship`
4. Create reconciliation tables: `component_reconciliation`, `assembly_reconciliation`, `supplier_reconciliation`, `reconciliation_run`
5. Create `technical_fact` table
6. Add foreign keys, constraints, indexes (source_system, normalized_reference, status, canonical entity FK, reconciliation run FK)
7. Create migration/init script
8. Add seed support for a few canonical entities

**Deliverables**:
- Schema created from empty database
- Integration tests can use it
- Coder can inspect relationships and run simple queries proving:
  - source files connect to raw rows
  - source entities connect to reconciliation records
  - accepted reconciliation can be linked to canonical entities
  - canonical BOM points to source BOM rows

**Acceptance**: Schema is created from an empty database and integration tests can use it.

---

## Phase 2 — Synthetic Data

**Goal**: Generate/load the intentionally messy railway-inspired dataset.

**Steps**:
1. Create six CSVs: `plm_bom.csv`, `plm_assemblies.csv`, `plm_variants.csv`, `erp_materials.csv`, `erp_suppliers.csv`, `engineering_notes.csv`
2. Write README describing the dataset
3. If generation is automated, make it deterministic
4. Ensure stable IDs/references sufficient for expected demo behavior

**Required data patterns** (from `docs/09_synthetic_data_spec.md`):
- 5 variants: REGIO-STD, REGIO-COMFORT, REGIO-NORDIC, REGIO-HIGH-CAPACITY, REGIO-EXPORT
- 8–10 assemblies: HVAC, Door Control, Brake Control, Traction Control, Passenger Information, CCTV, Auxiliary Power, Driver Cab, Battery System
- 40–60 canonical components
- ~150–300 BOM lines
- 10–20 suppliers
- 20–40 engineering notes

**Required messy-data patterns**:
- Reference aliases: CTRL-AIR-01, CTRL-AIR01, CTRL-HVAC-001, MAT-10001
- Supplier aliases: Siemens, SIEMENS MOBILITY, Siemens Mobility GmbH, SIEMENS MOBILITY SAS
- UOM variants: pcs, pc, piece, EA, units
- Voltage text variants: 24V, 24 V, 24 VDC, 24 volts DC
- Description variation: HVAC controller, HVAC CTRL unit, Air conditioning control module, Cabin HVAC controller
- Missing fields: missing supplier, missing description, missing revision, missing UOM

**Required engineering notes**:
- One note stating equivalence: CTRL-HVAC-001 is equivalent to CTRL-AIR-01 (same 24 V DC supply and CAN interface)
- One note with conflicting specification: Legacy record lists 48 V DC, current test sheet lists 24 V DC
- One ambiguous note: Compatible with northern-climate configuration; confirm enclosure rating before reuse

**Required reconciliation cases**:
1. Exact duplicate reference
2. Formatting-only alias
3. Semantic alias with strong evidence
4. Close but not identical component
5. Same description but conflicting electrical specification
6. Supplier alias
7. Component with no plausible match
8. Assembly reused across several variants
9. Assembly with one variant-specific component
10. Technically compatible-looking candidate blocked by one critical fact

**Deliverables**:
- All six CSV file types present
- Source-file provenance stored
- Fresh environment can load the same synthetic dataset and reproduce the demo scenario

**Acceptance**: A fresh environment can load the same synthetic dataset and reproduce the demo scenario.

---

## Phase 3 — Ingestion

**Goal**: Persist raw source data without semantic mutation.

**Steps**:
1. Implement source-file registration (compute file hash, create `source_file` record)
2. Implement CSV schema validation (required columns check)
3. Implement raw row ingestion (parse every row without semantic interpretation, preserve original strings, record source row number)
4. Implement duplicate-file protection (file hash identifies already imported file; identical hash = already ingested; changed file = new version)
5. Implement ingestion reporting (row count, validation errors)

**Validation levels**:
- **Hard validation** (reject/quarantine): required identifier missing, quantity impossible to parse, structurally malformed row
- **Soft validation** (keep row + warning): description missing, UOM unknown, supplier absent, contradictory technical field

**Deliverables**:
- All six synthetic file types can be loaded
- Raw values are preserved
- Re-importing the same file does not blindly duplicate it
- Invalid rows are surfaced rather than silently dropped
- Source entities are deduplicated
- Provenance from source entity to source record is inspectable

**Acceptance**: All source files appear in the data explorer with provenance.

---

## Phase 4 — Normalization

**Goal**: Produce normalized values beside the raw values.

**Steps**:
1. Implement normalization service
2. Implement config loader (read `config/normalization.json`)
3. Implement reference normalization (whitespace collapse, uppercase/lowercase standardization, punctuation harmonization, selected reference aliases)
4. Implement UOM normalization (pcs/pc/piece/EA/units → standard)
5. Implement supplier aliases (selected supplier-name formatting aliases)
6. Implement technical text normalization (numeric parsing, common voltage-expression normalization: 24V/24 V/24 VDC/24 volts DC → standard)
7. Ensure raw values remain untouched

**Normalization principles**:
- Deterministic and explainable
- Never replace the first value with the second — store normalized alongside raw
- If value cannot be safely normalized: keep raw, leave normalized null, emit warning, do not guess

**Configuration boundary**: Use small JSON config for explicit, reviewable mappings (UOM aliases, supplier aliases, reference aliases, textual replacements). Do not build a database rule engine.

**Deliverables**:
- Expected alias examples normalize correctly
- Raw values remain untouched

**Acceptance**: The expected alias examples in `docs/04_ingestion_and_normalization.md` normalize correctly and raw values remain untouched.

---

## Phase 5 — Source Entity Extraction

**Goal**: Create distinct source-level components, assemblies, and suppliers.

**Steps**:
1. Implement extraction service
2. Implement source entity upsert/deduplication
3. Implement mapping from raw records to source entities

**Deduplication rules**:
- Components: distinct by `(source_system, source_reference)`
- Assemblies: distinct by `(source_system, source_reference)`
- Suppliers: distinct by `(source_system, source_reference)` or equivalent stable source identity

**Key insight**: A source entity may be referenced by many BOM rows. Reconciliation happens at the entity level, not once per BOM line.

**Deliverables**:
- Same source component reference used on ten BOM lines appears once in `source_component`
- Can be traced back to those ten lines

**Acceptance**: The same source component reference used on ten BOM lines appears once in `source_component` and can be traced back to those ten lines.

---

## Phase 6 — Reconciliation Engine

**Goal**: Provide a layered candidate generation and assessment worker.

**Steps**:
1. Implement eligibility query (source entity has no authoritative accepted mapping and does not already have a current successful assessment)
2. Implement exact-match shortcut (Stage A: normalized source reference equals canonical reference/known alias → high-confidence candidate)
3. Implement structured candidate retrieval (Stage B: compare normalized name/description, category, supplier, relevant identifiers, selected technical facts)
4. Implement optional semantic retrieval (Stage C: embedding or text-similarity — optional for PoC)
5. Implement LLM assessment boundary (Stage D: LLM evaluates structured prompt, returns structured data — only when candidate set remains ambiguous or engineering notes provide semantic evidence)
6. Implement structured output validation (validate LLM response against schema)
7. Implement persistence to one of the three reconciliation tables (`component_reconciliation`, `assembly_reconciliation`, `supplier_reconciliation`)
8. Implement run tracking (`reconciliation_run` table: QUEUED → RUNNING → COMPLETED/FAILED/PARTIAL)
9. Implement error handling (LLM timeout, malformed LLM response, candidate lookup failure, invalid structured data → mark item/run as failed/partial, continue where practical)

**Layered strategy** (cheap → expensive):
- Stage A: Exact normalized match
- Stage B: Structured similarity
- Stage C: Semantic similarity (optional)
- Stage D: LLM assessment

**LLM boundary rules**:
- Send only: source entity, candidate entities, relevant structured attributes, relevant engineering notes, explicit task definition, required response schema
- Do NOT send entire database blindly
- Prompt must distinguish: identity from interchangeability, evidence from inference, missing information from contradiction
- Model must be allowed to say UNCERTAIN
- Model must NOT invent technical facts

**Candidate object contract**:
- candidate canonical entity ID
- match confidence 0–1
- recommendation: MATCH, NO_MATCH, UNCERTAIN
- method
- rationale
- evidence list
- conflicts detected
- fields compared

**Confidence bands** (UI thresholds only, not engineering certification):
- 0.90–1.00: strong evidence
- 0.75–0.89: likely match
- 0.50–0.74: uncertain
- <0.50: weak candidate

**Development strategy**: First implement deterministic candidate generation with mock assessment responses. Only after end-to-end persistence flow works, connect real LLM adapter.

**Two invocation modes**:
- **Batch mode**: explicitly launched for entity type (e.g., "Reconcile all unassessed components"). UI shows queued/processing/completed status, items processed, items requiring review, errors.
- **Single entity mode**: triggered from source-component/assembly/supplier detail screen.

**Human decisions**:
- Accept: selected candidate becomes authoritative
- Reject: selected candidate explicitly rejected
- No match: reviewer rejects candidates, source entity remains unresolved (preferable to forcing wrong mapping)

**Status progression**: PENDING → ASSESSED → ACCEPTED or PENDING → ASSESSED → REJECTED

**Deliverables**:
- Batch reconciliation is explicitly launchable
- Only eligible entities are processed
- Single-item reconciliation works
- Candidate results are persisted
- Evidence/rationale are inspectable
- LLM results are structured and validated
- Human acceptance/rejection changes authority state
- Source data is never mutated by reconciliation
- Failed items are visible

**Acceptance**: A component batch can be launched and produces persisted candidate assessments without modifying canonical BOMs.

---

## Phase 7 — Human Review Workflow

**Goal**: Turn suggestions into explicit engineering decisions.

**Steps**:
1. Implement reconciliation list UI (entity type selector, batch launch button, last run status, counts: pending/assessed/accepted/rejected)
2. Implement status filters
3. Implement candidate detail view (source entity left side, candidate matches right side)
4. Implement accept/reject actions
5. Implement run monitoring
6. Implement single-entity assessment (from entity detail page, "Find matches" button)

**Reconciliation detail view**:
- Left side: source entity (raw reference, normalized reference, description, source system, source record, linked BOM usage)
- Right side: candidate matches (canonical ID/name, confidence, rationale, evidence, conflicting fields, accept/reject controls)
- Action buttons: Find matches, Accept, Reject, Open canonical entity

**Deliverables**:
- Reviewer can accept a mapping in the UI
- Resulting authority state is visible immediately

**Acceptance**: A reviewer can accept a mapping in the UI, and the resulting authority state is visible immediately.

---

## Phase 8 — Canonicalization

**Goal**: Convert accepted mappings into usable canonical BOM relationships.

**Steps**:
1. Implement accepted-mapping resolver
2. Implement canonical BOM materialization
3. Implement unresolved-line reporting
4. Implement source-line traceability

**Canonicalization trigger**: Canonicalization is downstream of human-approved reconciliation. A source BOM line becomes a canonical BOM relationship only when its required identities are resolved.

**Process** (for each `plm_bom_line`):
1. Resolve source variant to canonical `variant`
2. Resolve source assembly through accepted assembly reconciliation
3. Resolve source component through accepted component reconciliation
4. Parse quantity/UOM from normalized values
5. Create/update `bom_relationship`
6. Preserve `source_bom_line_id`

**Canonicalization rule**: Do not infer canonical IDs merely because a candidate was suggested. Canonical BOM created only when:
1. Source component has accepted component mapping
2. Source assembly has accepted assembly mapping
3. Source variant has canonical variant mapping/creation rule
4. All required BOM data is valid

If any required identity is unresolved, the source BOM line remains visible as unresolved and must NOT be presented as an authoritative canonical BOM relationship.

**Deliverables**:
- Accepted HVAC example appears under one canonical component across the intended variants
- Unresolved lines remain visible
- Canonical BOM rows traceable to source BOM lines

**Acceptance**: The accepted HVAC example appears under one canonical component across the intended variants.

---

## Phase 9 — Technical Facts and Conflicts

**Goal**: Preserve small but meaningful engineering attributes with provenance.

**Steps**:
1. Implement fact extraction from source tables/notes
2. Implement fact persistence (`technical_fact` table)
3. Implement simple conflict detection
4. Implement issue list for conflicts

**Technical fact columns**: `id`, `entity_type` (COMPONENT/ASSEMBLY/VARIANT/SUPPLIER), `entity_id`, `attribute`, `value`, `unit`, `source_type` (ERP/PLM/ENGINEERING_NOTE/MANUAL), `source_id`, `confidence`, `status` (OBSERVED/VALIDATED/CONFLICTING), `created_at`

**Focus on small meaningful set** (do not create exhaustive ontology):
- Voltage
- Communication interface
- Temperature range
- Power rating
- Mounting type
- Enclosure/IP class

**Conflict detection**: A conflict exists when materially different values are associated with the same canonical entity/attribute and cannot be trivially normalized.

**Example conflict**:
```
Component: HVAC_CTRL_01
Attribute: operating_voltage
ERP: 48 V DC
Engineering note: 24 V DC
```
Analysis layer surfaces the conflict instead of arbitrarily selecting one.

**Deliverables**:
- Voltage conflict demo is visible and traceable to both source facts

**Acceptance**: The voltage conflict demo is visible and traceable to both source facts.

---

## Phase 10 — Reuse Analysis

**Goal**: Answer the business question using transparent deterministic logic.

**Steps**:
1. Implement assembly comparison
2. Implement component coverage
3. Implement reuse status calculation
4. Implement blocker calculation
5. Implement drill-down evidence

**Reuse categories** (must distinguish):
- **Reused**: Same canonical component/assembly appears across multiple variants
- **Reuse candidate**: Different source/canonical references appear potentially interchangeable, but evidence insufficient for authoritative reuse
- **Blocked reuse**: Candidate exists but material incompatibility or unresolved conflict prevents safe reuse
- **Unresolved**: Identity or technical evidence is insufficient

**Reuse logic** (transparent rules, configuration-driven or in one analysis module):
- Same canonical component across variants
- Compatible required technical attributes
- No unresolved critical conflicts
- Same or compatible voltage/interface/mounting constraints
- Supplier considerations where relevant
- Lifecycle/status where supplied

**Assembly-level analysis** (derived metrics):
- Component overlap ratio
- Exact common components
- Variant-specific components
- Unresolved components
- Conflicting facts
- Potential substitution opportunities

**User-facing explanation** (every reuse result explainable from stored data):
- NOT: "The AI thinks these are reusable."
- YES: "Potential reuse because the references reconcile to the same canonical component and the stored technical facts agree on supply voltage and interface."
- Blocked: "Reuse blocked because source records disagree on operating voltage (24 V DC vs 48 V DC)."

**Deliverables**:
- At least one assembly shown as reused
- At least one candidate blocked by a technical incompatibility

**Acceptance**: At least one assembly is shown as reused and at least one candidate is blocked by a technical incompatibility.

---

## Phase 11 — UI Completion

**Goal**: Connect the full workflow into a coherent engineering workbench.

**Steps**:
1. Implement Overview screen (cards: train variants, raw BOM lines, source components, canonical components, assemblies, accepted mappings, items requiring review, unresolved items, data-quality issues, reuse opportunities)
2. Implement Data Explorer (table selector, row count, search/filter, pagination, row detail, raw vs normalized values, source file provenance; tabs: Source files, PLM BOM lines, Components, Assemblies, Suppliers, Variants, Technical facts)
3. Implement Reconciliation Workbench (entity type selector, batch launch button, last run status, counts, table: source reference, normalized reference, description, status, candidate, confidence, method, last assessed, action)
4. Implement Run Detail (entity type, start/end time, status, total eligible, processed, assessed, review required, errors, optional method breakdown)
5. Implement BOM Explorer (select variant → select assembly → see source references vs canonical entities → inspect quantities and technical facts)
6. Implement Reuse Analysis (primary table: Variant/Assembly, Reuse status, Shared components, Blockers, Evidence; drill-down to component-level evidence)
7. Implement Data Quality (duplicate references, normalization warnings, missing supplier, missing description, conflicting technical facts, unresolved reconciliation, source-reference aliases; each issue links to underlying record)

**Empty/error states** (avoid misleading blank pages):
- No data ingested
- Ingestion failed
- No pending reconciliation
- Worker running
- Worker failed partially
- No canonical mapping yet
- No reuse candidates
- Insufficient evidence

**UX constraint**: Workflow must be obvious — Inspect → Assess → Review → Accept/Reject → Analyze. Do not hide reconciliation behind automatic background process.

**No business logic in frontend**: Do not duplicate reconciliation or reuse rules in React/TypeScript. Keep them server-side so same logic can be tested independently.

**Deliverables**:
- Entire demo can be performed through the UI
- Reviewer can perform entire PoC flow without using database console:
  1. Inspect imported data
  2. See what needs reconciliation
  3. Launch batch reconciliation
  4. Inspect a suggestion
  5. Accept/reject it
  6. Inspect the canonical result
  7. Inspect cross-variant reuse
  8. Trace the result back to source evidence

**Acceptance**: The entire demo can be performed through the UI.

---

## Phase 12 — Demo Polish and Hardening

**Goal**: Make the PoC easy to explain and robust enough for a live walkthrough.

**Steps**:
1. Implement useful loading states
2. Implement clear error states
3. Add seeded/demo account if needed
4. Ensure clean labels
5. Ensure consistent IDs and terminology
6. Implement one-click reset/reload for demo data
7. Write concise architecture README

**Deliverables**:
- Demo checklist can be completed from a fresh start without manual database edits

**Acceptance**: The demo checklist can be completed from a fresh start without manual database edits.

---

## Implementation Priority (when time is tight)

### Must-have
- Schema
- Ingestion
- Normalization
- Source entities
- Component reconciliation
- Accept/reject
- Canonical BOM
- One reuse analysis screen
- One high-quality demo scenario

### Should-have
- Assembly/supplier reconciliation
- Batch run dashboard
- Technical facts
- Data-quality screen

### Nice-to-have
- Semantic embeddings
- Sophisticated charts
- Broader ontology coverage
- Polished filtering

### Do NOT sacrifice
- Traceability
- Raw-data preservation
- Explicit human decisions
- Deterministic analysis layer

---

## API Endpoints (from `docs/08_api_and_service_contracts.md`)

### Ingestion
- `POST /ingestion/files` — register/upload/import one source file
- `GET /ingestion/files` — recent source files and ingestion status

### Data Explorer
- `GET /data/{entity_type}` — search, status filter, source-system filter, pagination
- `GET /data/{entity_type}/{id}` — source/entity fields, normalized fields, provenance, related rows, reconciliation state

### Reconciliation
- `POST /reconciliation/runs` — entity type, scope (UNASSESSED/ALL_REASSESS/explicit IDs), optional limits
- `GET /reconciliation/runs/{id}` — run progress and summary
- `GET /reconciliation/{entity_type}` — source entities with reconciliation state
- `POST /reconciliation/{entity_type}/{id}/assess` — single-entity reconciliation
- `POST /reconciliation/{entity_type}/{id}/decision` — candidate ID, decision (ACCEPT/REJECT), optional reviewer identity/comment

### Canonical
- `GET /canonical/components/{id}` — canonical entity and linked source references
- `GET /canonical/assemblies/{id}` — assembly, its components and variant usage
- `GET /canonical/bom` — filters: variant, assembly, component

### Analysis
- `GET /analysis/overview` — factual aggregate counts
- `GET /analysis/reuse` — filters: variant, assembly, status
- `GET /analysis/reuse/{assembly_id}` — detailed cross-variant comparison and evidence
- `GET /analysis/data-quality` — detected quality issues

---

## Demo Sequence (from `checklists/demo_checklist.md`)

**Before demo**:
- Reset database to known synthetic dataset
- Ingest all source files
- Confirm normalization complete
- Confirm some entities are intentionally unresolved
- Confirm no accepted mapping hides the key demo case

**Demo sequence**:
1. Open Overview
2. Show number of variants and BOM lines
3. Open Data Explorer
4. Show raw/normalized reference difference
5. Open Reconciliation Workbench
6. Launch a component batch
7. Show run progress/completion
8. Open the HVAC controller candidate
9. Show candidate canonical entity
10. Show engineering-note evidence
11. Accept the mapping
12. Open the HVAC BOM across two variants
13. Show canonical reuse
14. Open the blocked candidate
15. Show conflicting technical fact
16. End on Reuse Analysis

**What to emphasize**:
- Source data is deliberately messy
- Normalization is deterministic
- Reconciliation is explicit and traceable
- AI provides a proposal, not an invisible final decision
- Canonicalization is downstream of accepted decisions
- Reuse analysis is explainable from stored evidence
- PoC is intentionally smaller than a production deployment

---

## Invariants (must hold throughout)

1. Raw source values are never overwritten by normalization
2. Reconciliation never silently creates an accepted mapping
3. Rejected mappings cannot create canonical BOM relationships
4. Unresolved source rows remain visible
5. Canonical BOM rows must be traceable to source BOM lines
6. Analysis results must be derivable from persisted data
7. A failed reconciliation run must not invalidate previously accepted mappings

---

## Four Data Layers (never destroy previous layer when creating next)

1. **Source** — exactly what the customer gave us
2. **Normalized source** — deterministic cleaning of source values
3. **Canonical** — the application's reconciled representation
4. **Derived analysis** — conclusions calculated from canonical data and sourced technical facts

---

## Suggested Tech Boundary

- Python backend and worker
- SQLite (sufficient for PoC; proper PK/FK and indexes so PostgreSQL migration later is straightforward)
- CSV source-file format
- Small web UI for inspection and review
- LLM called through one well-defined provider abstraction
- Deterministic normalization and analysis logic remains normal application code
- No vector database required for first version
- No graph database required for first version
- No generic enterprise workflow/orchestration product required

---

## Documents in this Blueprint

| File | Purpose |
|---|---|
| `docs/01_scope_and_principles.md` | Scope, non-goals, product narrative, engineering principles |
| `docs/02_architecture.md` | Logical architecture and end-to-end flow |
| `docs/03_data_model.md` | Complete ER-style schema specification |
| `docs/04_ingestion_and_normalization.md` | Raw ingestion, normalization, provenance pipeline |
| `docs/05_reconciliation.md` | Reconciliation engine, candidate workflow, human-in-the-loop |
| `docs/06_canonicalization_and_analysis.md` | Accepted mappings, canonical BOM, reuse analysis |
| `docs/07_ui_specification.md` | Screens/windows and interactions |
| `docs/08_api_and_service_contracts.md` | Backend service/API contracts without implementation |
| `docs/09_synthetic_data_spec.md` | Synthetic data set design and edge cases |
| `docs/10_testing_and_validation.md` | Test strategy, acceptance criteria, demo validation |
| `docs/11_execution_roadmap.md` | Ordered implementation roadmap, Definition of Done per phase |
| `docs/12_production_evolution.md` | What changes for production scale, what stays PoC-only |
| `checklists/coder_checklist.md` | Practical implementation checklist |
| `checklists/demo_checklist.md` | End-to-end demo checklist |
| `config/normalization.example.json` | Example shape of configurable normalization rules |
| `examples/sample_entities.md` | Example records and reconciliation scenarios |
