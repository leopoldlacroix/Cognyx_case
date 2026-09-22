---
last_mapped_commit: 92a308bb4f3975a737c94509b667c651a00285ba
last_mapped_at: 2026-09-22
---
# Structure — Cognyx BOM Reuse Explorer (PoC)

**Analysis Date:** 2026-09-22

> Directory layout, key locations, naming conventions, and file organization for the Cognyx Alstom FDE pilot.

<!-- refreshed: 2026-09-22 -->

---

## 1. Repository Root

```text
/home/leopold-lacroix/Desktop/Projects/Cognyx/
```

| Path | Purpose |
|------|---------|
| `README.md` | Case statement + project interpretation + implementation notes |
| `AGENTS.md` | AI coding instructions (working material for the FDE case) |
| `.gitignore` | Git ignore rules |
| `dataset_summary.json` | Dataset volume summary (variants, components, assemblies, row counts) |
| `data/` | All data directories |
| `docs/` | Project documentation |

---

## 2. Data Directory

```text
data/
├── README.md
├── inputs/
│   ├── plm/
│   │   ├── bom_export.csv
│   │   ├── assembly_master.csv
│   │   └── variant_configuration.csv
│   ├── erp/
│   │   ├── material_master.csv
│   │   └── supplier_master.csv
│   └── engineering/
│       └── technical_notes.csv
├── processed/
└── ground_truth/
    ├── canonical_components.csv
    ├── canonical_bom_structure.csv
    ├── variant_component_truth.csv
    ├── expected_reconciliations.csv
    └── expected_conflicts.csv
```

### 2.1 `data/inputs/` — Raw Client Exports (IMMUTABLE)

**Rule:** Do not edit files under `data/inputs/`. They represent what was supplied by the fictional client and are intentionally messy.

#### `data/inputs/plm/`

| File | Content | Row count |
|------|---------|-----------|
| `bom_export.csv` | Multi-variant BOM lines: parent/child relationships, quantities, units, descriptions, supplier text, line status | 138 data rows |
| `assembly_master.csv` | Variant-specific PLM assembly references + metadata (reference, description, category, variant, revision, lifecycle) | 45 data rows |
| `variant_configuration.csv` | 5 train variants + characteristics (variant_ref, variant_name, train_family, market, climate_class, capacity_class, voltage_system, notes) | 5 data rows |

**BOM export columns:** `plm_row_id`, `variant_ref`, `assembly_ref`, `assembly_description`, `component_ref`, `component_description`, `quantity`, `uom`, `supplier_name`, `line_status`

**Assembly master columns:** `plm_assembly_ref`, `assembly_description`, `assembly_category`, `variant_ref`, `revision`, `lifecycle`

**Variant configuration columns:** `variant_ref`, `variant_name`, `train_family`, `market`, `climate_class`, `capacity_class`, `voltage_system`, `notes`

#### `data/inputs/erp/`

| File | Content | Row count |
|------|---------|-----------|
| `material_master.csv` | Material IDs, descriptions, material type, base unit, supplier ID, category, status, standard cost (EUR) | 44 data rows |
| `supplier_master.csv` | Supplier master records: supplier ID, supplier name, country | 6 data rows |

**Material master columns:** `material_id`, `material_description`, `material_type`, `base_unit`, `supplier_id`, `category`, `status`, `standard_cost_eur`

**Supplier master columns:** `supplier_id`, `supplier_name`, `country`

**Suppliers in dataset:**

- `SUP-001` — Siemens Mobility GmbH (Germany)
- `SUP-002` — Faiveley Transport (France)
- `SUP-003` — Knorr-Bremse Rail Systems (Germany)
- `SUP-004` — Thales Ground Transportation Systems (France)
- `SUP-005` — Schaltbau GmbH (Germany)
- `SUP-006` — TE Connectivity (Switzerland)

#### `data/inputs/engineering/`

| File | Content | Row count |
|------|---------|-----------|
| `technical_notes.csv` | Free-text notes in French and English: equivalences, constraints, legacy references, qualification notes | 71 data rows |

**Technical notes columns:** `note_id`, `object_type`, `object_reference`, `language`, `author`, `date`, `note_text`

**Object types:** `component`, `assembly`

**Languages:** `en`, `fr`

### 2.2 `data/processed/` — Normalized/Canonical Output

**Purpose:** Write normalized output here, separate from source data.

**Status:** Empty in current repository. This directory is the target for pipeline output.

### 2.3 `data/ground_truth/` — Testing Only (NOT Client-Facing)

**Purpose:** Internal pipeline validation. Not intended to represent a real Alstom export. Not part of the client-facing ingestion path.

| File | Content |
|------|---------|
| `canonical_components.csv` | 40 canonical component records with id, name, category, supplier_id, voltage, interface, temp_min_c, temp_max_c, cost_eur, status |
| `canonical_bom_structure.csv` | Expected canonical BOM structure |
| `variant_component_truth.csv` | Expected variant-component mappings |
| `expected_reconciliations.csv` | 12 expected reconciliation records with resolution_id, entity_type, raw_value, canonical_id, expected_status, why |
| `expected_conflicts.csv` | Expected conflict records |

**Canonical components categories:** HVAC, DOOR, BRAKE, PIS, POWER, BATTERY, CAB, COUNTING, LIGHTING

---

## 3. Documentation Directory

```text
docs/
├── scenarios.md
└── blueprint/
    ├── README.md
    ├── MANIFEST.md
    ├── GSD_PLAN.md
    ├── config/
    │   └── normalization.example.json
    ├── checklists/
    │   ├── coder_checklist.md
    │   └── demo_checklist.md
    ├── examples/
    │   └── sample_entities.md
    └── docs/
        ├── 01_scope_and_principles.md
        ├── 02_architecture.md
        ├── 03_data_model.md
        ├── 04_ingestion_and_normalization.md
        ├── 05_reconciliation.md
        ├── 06_canonicalization_and_analysis.md
        ├── 07_ui_specification.md
        ├── 08_api_and_service_contracts.md
        ├── 09_synthetic_data_spec.md
        ├── 10_testing_and_validation.md
        ├── 11_execution_roadmap.md
        ├── 12_production_evolution.md
        └── 13_coding_agent_instructions.md
```

### 3.1 `docs/scenarios.md`

The 10 engineered scenarios (A–J) with where they appear and what the future product should demonstrate.

### 3.2 `docs/blueprint/` — Full Blueprint Package

**`docs/blueprint/README.md`** — Blueprint overview and navigation.

**`docs/blueprint/MANIFEST.md`** — Package manifest: what's included and explicitly excluded.

**`docs/blueprint/GSD_PLAN.md`** — GSD (Guided Software Development) plan integration.

### 3.3 `docs/blueprint/docs/` — 13 Specification Documents

| Document | Number | Purpose |
|----------|--------|---------|
| `01_scope_and_principles.md` | 01 | Scope, product narrative, engineering principles, data ownership, human-in-the-loop, cost/control, observability |
| `02_architecture.md` | 02 | Logical architecture: 6 components, responsibility boundaries, source of truth, storage choice, worker invocation, dependency rule |
| `03_data_model.md` | 03 | Complete ER specification: source tables, source entity tables, canonical tables, reconciliation tables, reconciliation_run, technical_fact, cardinality, canonicalization rule |
| `04_ingestion_and_normalization.md` | 04 | Pipeline stages, ingestion behavior, idempotency, validation levels, normalization principles, configuration boundary, source entity extraction, reconciliation eligibility, outputs, definition of done |
| `05_reconciliation.md` | 05 | Reconciliation engine: execution model, eligibility rule, candidate generation pipeline (Stage A–D), candidate object contract, LLM boundary, LLM rules, confidence semantics, persisting results, human decisions, reassessment, failure handling, performance expectation, definition of done |
| `06_canonicalization_and_analysis.md` | 06 | Canonicalization trigger/process, technical fact extraction, conflict detection, reuse categories, reuse logic, assembly-level analysis, example outcome, user-facing explanation, definition of done |
| `07_ui_specification.md` | 07 | UI philosophy, 7 screens (Overview, Data Explorer, Reconciliation Workbench, Reconciliation detail, Run detail, BOM Explorer, Reuse Analysis, Data Quality), empty/error states, UX constraints, definition of done |
| `08_api_and_service_contracts.md` | 08 | Service boundaries, ingestion endpoints, data explorer endpoints, reconciliation endpoints, canonical endpoints, analysis endpoints, response principles, concurrency assumptions, no business logic in frontend |
| `09_synthetic_data_spec.md` | 09 | Why synthetic data, target volume, variants, assemblies, required messy-data patterns, required engineering notes, required reconciliation cases, demo scenario |
| `10_testing_and_validation.md` | 10 | Testing layers, determinism requirements, important invariants, data-quality test cases, reconciliation test cases, UI acceptance criteria, demo validation script, performance expectations, acceptance gates |
| `11_execution_roadmap.md` | 11 | 12-phase implementation plan with goals, build items, validation, and definition of done for each phase. Priority order: must-have, should-have, nice-to-have, do-not-sacrifice |
| `12_production_evolution.md` | 12 | Production evolution: database, file ingestion, identity model, reconciliation, technical facts, UI, analysis, reliability, architectural message to communicate |
| `13_coding_agent_instructions.md` | 13 | Instructions for coding agent/developer handoff: working rules, implementation loop, before changing schema, before adding AI feature, reconciliation implementation guidance, UI implementation guidance, what to avoid, handoff expectations |

### 3.4 `docs/blueprint/config/`

**`normalization.example.json`** — Example normalization configuration with UOM aliases, supplier aliases, reference aliases, voltage aliases. This is the template for `config/normalization.json`.

### 3.5 `docs/blueprint/checklists/`

| File | Purpose |
|------|---------|
| `coder_checklist.md` | Implementation checklist: foundation, data, ingestion, normalization, reconciliation, human review, canonicalization, analysis, UI, demo |
| `demo_checklist.md` | Demo checklist: before demo preparation, demo sequence (16 steps), what the presenter should emphasize |

### 3.6 `docs/blueprint/examples/`

**`sample_entities.md`** — 5 sample reconciliation scenarios with source records, canonical candidates, evidence, and expected behavior.

---

## 4. Planned Source Code Structure (Not Yet Implemented)

The blueprint specifies the following structure for the implementation phase:

```text
app/
├── backend/
├── worker/
├── frontend/
├── domain/
├── services/
├── db/
└── tests/
config/
data/
├── raw/
docs/
```

### 4.1 Planned Module Boundaries

| Module | Responsibility |
|--------|----------------|
| `app/backend/` | Web API, HTTP handlers, request/response serialization |
| `app/worker/` | Reconciliation worker, batch processing, LLM adapter |
| `app/frontend/` | Web UI workbench (React/TypeScript or similar) |
| `app/domain/` | Domain models, entities, value objects |
| `app/services/` | `IngestionService`, `NormalizationService`, `SourceEntityService`, `ReconciliationService`, `CanonicalizationService`, `TechnicalFactService`, `ReuseAnalysisService`, `RunService` |
| `app/db/` | Database initialization, migrations, connection management, repositories |
| `app/tests/` | Unit tests, integration tests, end-to-end tests |
| `config/` | `normalization.json`, application configuration |

### 4.2 Planned Entry Points

| Entry point | Location |
|-------------|----------|
| Backend health endpoint | `app/backend/` |
| Worker entry point | `app/worker/` |
| Frontend shell | `app/frontend/` |
| Database init/migration | `app/db/` |

---

## 5. Naming Conventions

### 5.1 Files and Directories

| Convention | Example |
|------------|---------|
| Lowercase with underscores for data files | `bom_export.csv`, `technical_notes.csv` |
| Lowercase with hyphens for documentation | `02_architecture.md`, `coder_checklist.md` |
| Lowercase with underscores for config | `normalization.example.json` |
| Lowercase with underscores for code modules | `normalization_service.py`, `reconciliation_worker.py` (Python convention) |
| Singular for entity tables | `component`, `assembly`, `supplier`, `variant` |
| Plural for collection/containers | `components/`, `assembly_master.csv` |

### 5.2 Database Naming (from spec)

| Convention | Example |
|------------|---------|
| Snake_case for columns | `variant_ref_raw`, `component_ref_normalized`, `source_file_id` |
| `raw` suffix for immutable source values | `assembly_ref_raw`, `quantity_raw`, `description_raw` |
| `normalized` suffix for derived values | `assembly_ref_normalized`, `quantity_normalized`, `description_normalized` |
| `_id` suffix for foreign keys | `source_file_id`, `source_component_id`, `variant_id` |
| `_at` suffix for timestamps | `created_at`, `started_at`, `decided_at` |
| Status values are uppercase constants | `PENDING`, `ASSESSED`, `ACCEPTED`, `REJECTED`, `QUEUED`, `RUNNING`, `COMPLETED`, `FAILED`, `PARTIAL` |
| Method values are uppercase constants | `EXACT`, `NORMALIZED`, `STRUCTURED`, `SEMANTIC`, `LLM`, `MANUAL` |

### 5.3 Source Reference Naming

| Pattern | Example | Meaning |
|---------|---------|---------|
| PLM component references | `CTRL-AIR-01`, `CTRL-AIR01`, `CTRL-AIR-O1` | HVAC controller variants with formatting/alias differences |
| PLM assembly references | `HVAC-M01`, `HVAC-N01`, `DOOR-M02` | Assembly references prefixed by category |
| ERP material IDs | `MAT-10001`, `MAT-10002` | ERP material master identifiers |
| ERP supplier IDs | `SUP-001` through `SUP-006` | Supplier master identifiers |
| Engineering note IDs | `N-001` through `N-071` | Technical note identifiers |
| Canonical component IDs | `COMP-001` through `COMP-040` | Canonical component identifiers |
| Variant references | `REGIO-STD`, `REGIO-COMFORT`, `REGIO-NORDIC`, `REGIO-HC`, `REGIO-EXPORT` | Train variant identifiers |

### 5.4 Category Prefixes

| Category | Example references |
|----------|-------------------|
| HVAC | `CTRL-AIR-01`, `FAN-AIR01`, `CAPT-TEMP-01`, `FILTER-HVAC-01`, `HVAC-M01` |
| DOOR | `DCTRL-010`, `DCTRL-001`, `CTRL-DOOR-HD`, `PORTES-EXP02`, `DOOR-M02` |
| BRAKE | `BrakeCtrl01`, `BRAKE-CU-014`, `BRAKE-M03`, `FREIN-EXP03` |
| PIS | `PIS-CTRL-01`, `PAX-DISP-15`, `DISPLAY-15IN`, `PIS-M04`, `PAX-INFO-M01` |
| POWER | `APC-750-24`, `AUX-CONV-EXP`, `APC-M05`, `POWER-MOD-N` |
| BATTERY | `BAT-MON-UNIT`, `BMU-027`, `BAT-M06`, `BATT-MOD-EXP` |
| CAB | `DRIVER-CAB-CU`, `CAB-CU-NORDIC`, `CAB-M07`, `DRIVER-MOD-EXP` |
| COUNTING | `PASSCOUNT-CAMERA`, `PASSCOUNT-CPU`, `PCOUNT-M08`, `PAX-COUNT-MOD-E` |
| LIGHTING | `LED-DRV-01`, `LIGHT-DRIVER-01`, `LIGHT-M09`, `ECL-EXP09` |

---

## 6. Key Locations Summary

### 6.1 Source Data (Immutable)

- `data/inputs/plm/bom_export.csv` — 138 BOM rows
- `data/inputs/plm/assembly_master.csv` — 45 assembly records
- `data/inputs/plm/variant_configuration.csv` — 5 variants
- `data/inputs/erp/material_master.csv` — 44 material records
- `data/inputs/erp/supplier_master.csv` — 6 suppliers
- `data/inputs/engineering/technical_notes.csv` — 71 notes

### 6.2 Ground Truth (Testing Only)

- `data/ground_truth/canonical_components.csv` — 40 canonical components
- `data/ground_truth/expected_reconciliations.csv` — 12 expected reconciliations
- `data/ground_truth/canonical_bom_structure.csv` — expected BOM structure
- `data/ground_truth/variant_component_truth.csv` — expected variant-component mappings
- `data/ground_truth/expected_conflicts.csv` — expected conflicts

### 6.3 Blueprint Specification

- `docs/blueprint/docs/01_scope_and_principles.md` through `13_coding_agent_instructions.md` — 13 documents
- `docs/blueprint/config/normalization.example.json` — normalization config template
- `docs/blueprint/checklists/coder_checklist.md` — implementation checklist
- `docs/blueprint/checklists/demo_checklist.md` — demo checklist
- `docs/blueprint/examples/sample_entities.md` — sample scenarios

### 6.4 Project Context

- `README.md` — case statement + implementation notes
- `AGENTS.md` — AI coding instructions
- `dataset_summary.json` — dataset volume summary

### 6.5 Output Target

- `data/processed/` — normalized/canonical output (currently empty)
- `.planning/codebase/` — architecture and structure documentation (this directory)

---

## 7. Dataset Summary

| Metric | Count |
|--------|-------|
| Train variants | 5 |
| Canonical sub-assemblies | 9 |
| Canonical components | 40 |
| PLM BOM rows | 138 |
| PLM assembly records | 45 |
| ERP material records | 44 |
| Suppliers | 6 |
| Engineering notes | 71 |

**5 train variants:**

- `REGIO-STD` — Regional Standard (France, Temperate, 24 V DC auxiliary)
- `REGIO-COMFORT` — Regional Comfort (France, Temperate, 24 V DC auxiliary)
- `REGIO-NORDIC` — Regional Nordic (Nordics, Cold, 24 V DC auxiliary, -35°C envelope)
- `REGIO-HC` — Regional High Capacity (France, Temperate, 24 V DC auxiliary, High capacity)
- `REGIO-EXPORT` — Regional Export (International, Temperate, 48 V DC auxiliary, intentionally different)

---

## 8. Scenarios Covered by Dataset

| ID | Scenario | Data evidence |
|----|----------|---------------|
| A | Obvious reuse | HVAC Controller, Brake, PIS shared across variants |
| B | Hidden cross-source reuse | `CTRL-AIR-01` / `CTRL-AIR01` / `CTRL-HVAC-001` / `MAT-10001` |
| C | Typo/alias reconciliation | `CTRL-AIR-O1`, `LIGHT-DRIVER-01`, supplier aliases |
| D | Similar but not identical | Standard Door Controller vs Export Door Controller (24V vs 48V) |
| E | Variant-specific engineering difference | Nordic HVAC/Brake/Cab/Lighting cold-rated parts |
| F | Potential reuse | Passenger Counting Camera vs Rugged Camera |
| G | Conflicting source/specification | HVAC Controller (24V vs 48V legacy), PIS Display |
| H | Multilingual evidence | French/English/German labels and notes |
| I | Data-quality issue | Units, duplicate BOM lines, invalid quantity |
| J | Lifecycle mismatch | Export passenger counting module (Prototype status) |

---

*2026-09-22 analysis: Structure documentation generated from repository inventory and blueprint specifications.*
