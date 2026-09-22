# 11 — Execution Roadmap / Coder Plan

This is the ordered implementation plan. Each phase has a goal, files/modules to create, expected behavior, tests and a Definition of Done.

## Phase 0 — Project foundation

### Goal
Create a minimal, runnable repository with backend, worker and UI boundaries.

### Build

- repository structure;
- dependency management;
- environment configuration;
- application configuration;
- database initialization/migration mechanism;
- frontend shell;
- backend health endpoint;
- worker entry point;
- README with run instructions.

### Suggested structure

```text
app/
  backend/
  worker/
  frontend/
  domain/
  services/
  db/
  tests/
config/
data/
  raw/
docs/
```

Keep the structure clean but not excessively layered.

### Do not build yet

- LLM integration;
- polished dashboards;
- vector search;
- graph DB.

### Definition of Done

The repository starts locally and exposes backend/UI/worker entry points.

---

## Phase 1 — Database schema

### Goal
Implement exactly the entities defined in `03_data_model.md`.

### Build

- tables;
- foreign keys;
- constraints;
- indexes;
- migration/init script;
- seed support for a few canonical entities.

### Validation

The coder should be able to inspect relationships and run simple queries proving:

- source files connect to raw rows;
- source entities connect to reconciliation records;
- accepted reconciliation can be linked to canonical entities;
- canonical BOM points to source BOM rows.

### Definition of Done

Schema is created from an empty database and integration tests can use it.

---

## Phase 2 — Synthetic data

### Goal
Generate/load the intentionally messy railway-inspired dataset.

### Build

- six CSVs;
- README describing the dataset;
- deterministic generation if generation is automated;
- stable IDs/references sufficient for expected demo behavior.

### Definition of Done

A fresh environment can load the same synthetic dataset and reproduce the demo scenario.

---

## Phase 3 — Ingestion

### Goal
Persist raw source data without semantic mutation.

### Build

- source-file registration;
- CSV validation;
- raw table insertion;
- duplicate-file protection;
- ingestion reporting.

### Tests

- row counts;
- duplicate file re-import;
- malformed row handling;
- missing values.

### Definition of Done

All source files appear in the data explorer with provenance.

---

## Phase 4 — Normalization

### Goal
Produce normalized values beside the raw values.

### Build

- normalization service;
- config loader;
- reference normalization;
- UOM normalization;
- selected supplier aliases;
- selected technical text normalization.

### Definition of Done

The expected alias examples in `04_ingestion_and_normalization.md` normalize correctly and raw values remain untouched.

---

## Phase 5 — Source entity extraction

### Goal
Create distinct source-level components, assemblies and suppliers.

### Build

- extraction service;
- source entity upsert/deduplication;
- mapping from raw records to source entities.

### Definition of Done

The same source component reference used on ten BOM lines appears once in `source_component` and can be traced back to those ten lines.

---

## Phase 6 — Reconciliation engine

### Goal
Provide a layered candidate generation and assessment worker.

### Build

1. eligibility query;
2. exact-match shortcut;
3. structured candidate retrieval;
4. optional semantic retrieval;
5. LLM assessment boundary;
6. structured output validation;
7. persistence to one of the three reconciliation tables;
8. run tracking;
9. error handling.

### Suggested development strategy

First implement deterministic candidate generation with mock assessment responses.

Only after the end-to-end persistence flow works should the real LLM adapter be connected.

### Definition of Done

A component batch can be launched and produces persisted candidate assessments without modifying canonical BOMs.

---

## Phase 7 — Human review workflow

### Goal
Turn suggestions into explicit engineering decisions.

### Build

- reconciliation list;
- status filters;
- candidate detail;
- accept/reject actions;
- run monitoring;
- single-entity assessment.

### Definition of Done

A reviewer can accept a mapping in the UI, and the resulting authority state is visible immediately.

---

## Phase 8 — Canonicalization

### Goal
Convert accepted mappings into usable canonical BOM relationships.

### Build

- accepted-mapping resolver;
- canonical BOM materialization;
- unresolved-line reporting;
- source-line traceability.

### Definition of Done

The accepted HVAC example appears under one canonical component across the intended variants.

---

## Phase 9 — Technical facts and conflicts

### Goal
Preserve small but meaningful engineering attributes with provenance.

### Build

- fact extraction from source tables/notes;
- fact persistence;
- simple conflict detection;
- issue list for conflicts.

### Definition of Done

The voltage conflict demo is visible and traceable to both source facts.

---

## Phase 10 — Reuse analysis

### Goal
Answer the business question using transparent deterministic logic.

### Build

- assembly comparison;
- component coverage;
- reuse status calculation;
- blocker calculation;
- drill-down evidence.

### Definition of Done

At least one assembly is shown as reused and at least one candidate is blocked by a technical incompatibility.

---

## Phase 11 — UI completion

### Goal
Connect the full workflow into a coherent engineering workbench.

### Build

- Overview;
- Data Explorer;
- Reconciliation Workbench;
- Run Detail;
- BOM Explorer;
- Reuse Analysis;
- Data Quality.

### Definition of Done

The entire demo can be performed through the UI.

---

## Phase 12 — Demo polish and hardening

### Goal
Make the PoC easy to explain and robust enough for a live walkthrough.

### Build

- useful loading states;
- clear error states;
- seeded/demo account if needed;
- clean labels;
- consistent IDs and terminology;
- one-click reset/reload for demo data;
- concise architecture README.

### Definition of Done

The demo checklist can be completed from a fresh start without manual database edits.

---

# Implementation priority inside a constrained time budget

When time is tight, implement in this order:

### Must-have

- schema;
- ingestion;
- normalization;
- source entities;
- component reconciliation;
- accept/reject;
- canonical BOM;
- one reuse analysis screen;
- one high-quality demo scenario.

### Should-have

- assembly/supplier reconciliation;
- batch run dashboard;
- technical facts;
- data-quality screen.

### Nice-to-have

- semantic embeddings;
- sophisticated charts;
- broader ontology coverage;
- polished filtering.

### Do not sacrifice

Traceability, raw-data preservation, explicit human decisions, and a deterministic analysis layer.
