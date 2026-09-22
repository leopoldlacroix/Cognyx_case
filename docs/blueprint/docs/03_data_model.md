# 03 — Complete Data Model / ER Specification

## 3.1 Modeling conventions

- Primary keys: integer IDs are acceptable for the PoC.
- Foreign keys: explicit typed foreign keys are preferred.
- Timestamps: UTC storage recommended.
- Raw source values: preserve original strings exactly where practical.
- Normalized values: stored alongside raw values for transparency.
- Status fields: constrain to documented values.
- Evidence: JSON is acceptable for the PoC because the payload is inspected primarily as a unit; a production implementation could normalize it.

## 3.2 Entity relationship overview

```text
source_file
  │
  ├──< plm_variant
  ├──< plm_assembly
  ├──< plm_bom_line
  ├──< erp_material
  ├──< erp_supplier
  └──< engineering_note

plm_bom_line >── source_component
plm_assembly >── source_assembly
erp_supplier  >── source_supplier

source_component ──< component_reconciliation >── component
source_assembly  ──< assembly_reconciliation  >── assembly
source_supplier  ──< supplier_reconciliation  >── supplier

variant ──< bom_relationship >── assembly
component ──< bom_relationship

canonical entities ──< technical_fact
reconciliation_run ──< reconciliation rows
```

## 3.3 SOURCE / INGESTION TABLES

### `source_file`

**Purpose:** identifies every ingested file and its origin.

| Column | Type | Null | Key | Notes |
|---|---|---:|---|---|
| id | INTEGER | No | PK | Internal source-file identifier |
| source_system | TEXT | No | IDX | `PLM`, `ERP`, `ENGINEERING` |
| file_name | TEXT | No | — | Original file name |
| file_hash | TEXT | Yes | IDX | Recommended for idempotency |
| ingested_at | DATETIME | No | — | Ingestion timestamp |

Relationships: `source_file 1:N` to every raw-source table below.

### `plm_bom_line`

**Purpose:** stores each BOM row supplied by the PLM export.

| Column | Type | Null | Key |
|---|---|---:|---|
| id | INTEGER | No | PK |
| source_file_id | INTEGER | No | FK |
| source_row | INTEGER | No | — |
| variant_ref_raw | TEXT | No | — |
| assembly_ref_raw | TEXT | No | — |
| component_ref_raw | TEXT | No | — |
| description_raw | TEXT | Yes | — |
| quantity_raw | TEXT | Yes | — |
| uom_raw | TEXT | Yes | — |
| supplier_raw | TEXT | Yes | — |
| variant_ref_normalized | TEXT | Yes | IDX |
| assembly_ref_normalized | TEXT | Yes | IDX |
| component_ref_normalized | TEXT | Yes | IDX |
| description_normalized | TEXT | Yes | — |
| quantity_normalized | REAL | Yes | — |
| uom_normalized | TEXT | Yes | — |
| supplier_normalized | TEXT | Yes | IDX |

Rules:

- raw columns are immutable after ingestion;
- normalized values may be recomputed;
- one row represents one source BOM relationship;
- `source_row` is the source-file row number, not a domain identity.

### `plm_assembly`

**Purpose:** source-side assembly records extracted from PLM export data.

Core columns:

- `id` PK
- `source_file_id` FK
- `source_row`
- `assembly_ref_raw`
- `assembly_description_raw`
- `variant_ref_raw`
- `revision_raw`
- `lifecycle_raw`
- normalized equivalents for reference, description and variant

Indexes: `(assembly_ref_normalized)`, `(variant_ref_raw)`, `(source_file_id)`.

### `plm_variant`

**Purpose:** source-side train variant metadata.

Core columns:

- `id` PK
- `source_file_id` FK
- `source_row`
- `variant_ref_raw`
- `variant_name_raw`
- `train_family_raw`
- `market_raw`
- `climate_class_raw`
- `capacity_class_raw`
- `voltage_system_raw`
- `notes_raw`

Normalized fields should be present for values used by analysis.

### `erp_material`

**Purpose:** ERP material master data.

Core columns:

- `id` PK
- `source_file_id` FK
- `source_row`
- `material_id_raw`
- `description_raw`
- `material_type_raw`
- `base_unit_raw`
- `supplier_id_raw`
- `category_raw`
- `status_raw`
- normalized equivalents where useful
- `cost_raw` as numeric value if supplied

### `erp_supplier`

**Purpose:** ERP supplier records.

Core columns:

- `id` PK
- `source_file_id` FK
- `source_row`
- `supplier_id_raw`
- `supplier_name_raw`
- `country_raw`
- normalized supplier-name fields

### `engineering_note`

**Purpose:** source technical notes that may provide semantic evidence.

Core columns:

- `id` PK
- `source_file_id` FK
- `source_row`
- `object_reference_raw`
- `object_type` (`COMPONENT`, `ASSEMBLY`, `VARIANT`, `SUPPLIER`)
- `language`
- `author`
- `date`
- `note_text`

Index: `(object_reference_raw, object_type)`.

---

## 3.4 SOURCE ENTITY TABLES

These tables deliberately represent **distinct source-side entities**, not every BOM row.

### `source_component`

**Purpose:** one record per distinct source-side component reference.

| Column | Type | Null | Key |
|---|---|---:|---|
| id | INTEGER | No | PK |
| source_system | TEXT | No | IDX |
| source_reference | TEXT | No | UNIQUE within source system |
| normalized_reference | TEXT | Yes | IDX |
| description | TEXT | Yes | — |
| source_record_type | TEXT | No | — |
| source_record_id | INTEGER | No | — |
| created_at | DATETIME | No | — |

Constraint: `(source_system, source_reference)` should be unique.

### `source_assembly`

Same pattern as `source_component`, with an assembly-specific identity.

### `source_supplier`

Same pattern as `source_component`, with supplier-specific naming/reference semantics.

---

## 3.5 CANONICAL TABLES

### `component`

**Purpose:** internal canonical component identity.

Columns:

- `id` PK
- `name` NOT NULL
- `category` nullable
- `created_at` NOT NULL

Canonical identity must not contain source-system prefixes unless that is the domain model decision.

### `assembly`

Columns:

- `id` PK
- `name` NOT NULL
- `category` nullable
- `created_at` NOT NULL

### `supplier`

Columns:

- `id` PK
- `name` NOT NULL
- `country` nullable
- `created_at` NOT NULL

### `variant`

Columns:

- `id` PK
- `name` NOT NULL
- `train_family` nullable
- `market` nullable
- `climate_class` nullable
- `capacity_class` nullable
- `voltage_system` nullable
- `created_at` NOT NULL

### `bom_relationship`

**Purpose:** canonical BOM relationship used by analysis.

Columns:

- `id` PK
- `variant_id` FK → `variant.id`
- `assembly_id` FK → `assembly.id`
- `component_id` FK → `component.id`
- `quantity` REAL NOT NULL
- `unit` TEXT NOT NULL
- `source_bom_line_id` FK → `plm_bom_line.id`
- `created_at` DATETIME NOT NULL

Recommended unique constraint:

`(variant_id, assembly_id, component_id, source_bom_line_id)`

PoC simplification: model hierarchy as `Variant → Assembly → Component`. Explicitly document that production can support arbitrary BOM depth.

---

## 3.6 RECONCILIATION TABLES

The reconciliation tables are intentionally split by entity type.

### `component_reconciliation`

Columns:

- `id` PK
- `source_component_id` FK → `source_component.id`
- `component_id` FK → `component.id`, nullable while no candidate is selected
- `status` NOT NULL: `PENDING | ASSESSED | ACCEPTED | REJECTED`
- `method` nullable: `EXACT | NORMALIZED | STRUCTURED | SEMANTIC | LLM | MANUAL`
- `confidence` nullable, numeric 0–1
- `rationale` nullable
- `evidence_json` nullable
- `reconciliation_run_id` FK, nullable
- `created_at` NOT NULL
- `decided_at` nullable
- `decided_by` nullable

Rules:

- a source component can have multiple historical candidate assessments;
- at most one current `ACCEPTED` mapping should exist for a source component in the PoC;
- `ACCEPTED` means authoritative mapping for downstream canonicalization;
- `ASSESSED` does not mean accepted.

### `assembly_reconciliation`

Same pattern with:

- `source_assembly_id`
- `assembly_id`

### `supplier_reconciliation`

Same pattern with:

- `source_supplier_id`
- `supplier_id`

Recommended indexes for all three:

- source entity FK
- status
- canonical entity FK
- reconciliation run FK

---

## 3.7 `reconciliation_run`

**Purpose:** batch-execution traceability.

Columns:

- `id` PK
- `entity_type` NOT NULL (`COMPONENT`, `ASSEMBLY`, `SUPPLIER`)
- `started_at` NOT NULL
- `completed_at` nullable
- `status` NOT NULL: `QUEUED | RUNNING | COMPLETED | FAILED | PARTIAL`
- `items_processed` NOT NULL default 0
- `items_assessed` NOT NULL default 0
- `items_needing_review` NOT NULL default 0
- `error_count` NOT NULL default 0
- `created_by` nullable

A run must be created before processing starts and updated as progress changes.

---

## 3.8 `technical_fact`

**Purpose:** store a technical property with provenance rather than flattening all evidence into the canonical entity.

PoC columns:

- `id` PK
- `entity_type` NOT NULL (`COMPONENT`, `ASSEMBLY`, `VARIANT`, optionally `SUPPLIER`)
- `entity_id` NOT NULL
- `attribute` NOT NULL
- `value` NOT NULL
- `unit` nullable
- `source_type` NOT NULL (`ERP`, `PLM`, `ENGINEERING_NOTE`, `MANUAL`)
- `source_id` NOT NULL
- `confidence` nullable 0–1
- `status` NOT NULL: `OBSERVED | VALIDATED | CONFLICTING`
- `created_at` NOT NULL

The `entity_type/entity_id` pair is intentionally polymorphic for this small PoC. Production may replace it with typed fact tables or graph-native properties if querying needs justify it.

Example facts:

```text
COMPONENT 42 | operating_voltage | 24 | V DC | ENGINEERING_NOTE | 7
COMPONENT 42 | interface          | CAN | null | PLM             | 91
COMPONENT 42 | operating_voltage | 48 | V DC | ERP             | 204
```

Those facts can coexist so that conflict detection is possible.

---

## 3.9 Cardinality summary

| Relationship | Cardinality |
|---|---|
| source_file → raw source rows | 1:N |
| source_component → plm_bom_line | 1:N |
| source_assembly → plm_bom_line | 1:N |
| source_component → component_reconciliation | 1:N historical assessments |
| component → component_reconciliation | 1:N candidate mappings |
| source_assembly → assembly_reconciliation | 1:N |
| assembly → assembly_reconciliation | 1:N |
| source_supplier → supplier_reconciliation | 1:N |
| supplier → supplier_reconciliation | 1:N |
| reconciliation_run → reconciliation rows | 1:N |
| variant → bom_relationship | 1:N |
| assembly → bom_relationship | 1:N |
| component → bom_relationship | 1:N |
| plm_bom_line → bom_relationship | 1:0..1 for the PoC |
| canonical entity → technical_fact | 1:N |

---

## 3.10 Canonicalization rule

Do not infer canonical IDs merely because a candidate was suggested.

The canonical BOM relationship is created only when:

1. the source component has an accepted component mapping;
2. the source assembly has an accepted assembly mapping;
3. the source variant has a canonical variant mapping/creation rule;
4. all required BOM data is valid.

If any required identity is unresolved, the source BOM line remains visible as unresolved and must not be presented as an authoritative canonical BOM relationship.
