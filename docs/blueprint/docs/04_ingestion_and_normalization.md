# 04 — Ingestion and Normalization Pipeline Specification

## 4.1 Pipeline stages

```text
File discovery
  ↓
Source-file registration
  ↓
Schema validation
  ↓
Raw row ingestion
  ↓
Normalization
  ↓
Source-entity extraction
  ↓
Reconciliation eligibility calculation
```

Reconciliation is **not** part of ingestion.

## 4.2 Source files for the PoC

Minimum set:

1. `plm_bom.csv`
2. `plm_assemblies.csv`
3. `plm_variants.csv`
4. `erp_materials.csv`
5. `erp_suppliers.csv`
6. `engineering_notes.csv`

The synthetic-data specification defines the exact columns and required inconsistencies.

## 4.3 Ingestion behavior

For every file:

1. compute a stable file hash if feasible;
2. create `source_file` record;
3. validate required columns;
4. parse every row without semantic interpretation;
5. preserve original strings;
6. record the original source row number;
7. write to the corresponding raw/source table;
8. report row count and validation errors.

### Idempotency

Re-ingesting the exact same file should not unexpectedly duplicate the data.

Recommended PoC rule:

- file hash identifies an already imported file;
- identical file hash may be treated as already ingested;
- a changed file is a new source-file version.

## 4.4 Validation levels

### Hard validation
Reject or quarantine rows when:

- required identifier is missing;
- quantity is impossible to parse where required;
- source row is structurally malformed.

### Soft validation
Keep the row but emit a warning when:

- description is missing;
- UOM is unknown;
- supplier is absent;
- technical field is contradictory.

Industrial data is messy; over-aggressive rejection would hide the problem being demonstrated.

## 4.5 Normalization principles

Normalization is deterministic and explainable.

Examples:

- whitespace collapse;
- uppercase/lowercase standardization for identifiers;
- punctuation harmonization;
- UOM aliases;
- selected reference aliases;
- obvious supplier-name formatting aliases;
- numeric parsing;
- common voltage-expression normalization.

### Preserve raw values

Example:

```text
component_ref_raw        = CTRL-AIR01
component_ref_normalized = CTRL-AIR-01
```

Never replace the first value with the second.

## 4.6 Configuration boundary

Use a small configuration file such as:

`config/normalization.json`

Configuration is appropriate for explicit, reviewable mappings such as:

- UOM aliases;
- supplier aliases;
- reference aliases;
- textual replacements.

Do not build a database rule engine for the PoC.

## 4.7 Unknown normalization values

If a value cannot be safely normalized:

- keep the raw value;
- leave normalized value unchanged or null according to field semantics;
- emit a warning where appropriate;
- do not guess.

## 4.8 Source entity extraction

After normalization, create distinct source entities.

### Components
Distinct by `(source_system, source_reference)`.

### Assemblies
Distinct by `(source_system, source_reference)`.

### Suppliers
Distinct by `(source_system, source_reference)` or equivalent stable source identity.

A source entity may be referenced by many BOM rows.

This separation is important because reconciliation happens at the entity level, not once per BOM line.

## 4.9 Reconciliation eligibility

Every source entity should expose a derived state to the application:

- never assessed;
- assessed but unresolved;
- accepted;
- rejected/no-match;
- needs reassessment.

The PoC may derive this from reconciliation rows rather than adding a redundant boolean field.

Prefer deriving state from the authoritative reconciliation table to avoid contradictory flags.

## 4.10 Outputs

At the end of ingestion/normalization, the system should be able to answer:

- how many files were loaded?
- how many rows per file?
- how many source components/assemblies/suppliers exist?
- how many have never been assessed?
- how many normalization warnings exist?
- which raw rows refer to which source entities?

## 4.11 Definition of Done

- all six synthetic file types can be loaded;
- raw values are preserved;
- normalized values are reproducible;
- re-importing the same file does not blindly duplicate it;
- invalid rows are surfaced rather than silently dropped;
- source entities are deduplicated;
- provenance from source entity to source record is inspectable.
