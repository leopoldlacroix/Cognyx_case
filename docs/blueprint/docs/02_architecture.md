# 02 — Logical Architecture

## 2.1 High-level components

The PoC consists of six logical areas:

1. **Source ingestion layer**
2. **Normalization / preparation layer**
3. **Reconciliation worker**
4. **Canonical / knowledge layer**
5. **Analysis layer**
6. **Web UI / API**

Conceptually:

```text
                 ┌───────────────────────────┐
                 │ PLM / ERP / Engineering    │
                 │ CSV files                  │
                 └─────────────┬─────────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ Ingestion           │
                    │ preserve source     │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ Source + normalized │
                    │ records             │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ Source entities     │
                    │ component/supplier/ │
                    │ assembly/variant    │
                    └──────────┬──────────┘
                               │
                    explicit   │ reconciliation run
                    launch     ▼
                    ┌─────────────────────┐
                    │ Reconciliation      │
                    │ candidate engine    │
                    └──────────┬──────────┘
                               │ proposals
                               ▼
                    ┌─────────────────────┐
                    │ Human review        │
                    │ accept/reject       │
                    └──────────┬──────────┘
                               │ accepted
                               ▼
                    ┌─────────────────────┐
                    │ Canonical model     │
                    │ + canonical BOM     │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ Technical facts +   │
                    │ reuse analysis      │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ Web UI              │
                    │ explorer/workbench  │
                    └─────────────────────┘
```

## 2.2 Responsibility boundaries

### Ingestion
Responsible for getting source files into source tables and preserving provenance.

It must not perform semantic reconciliation.

### Normalization
Responsible for deterministic transformations that reduce superficial variation.

Examples: whitespace, casing, UOM aliases, selected reference aliases.

It must not claim two entities are semantically identical merely because their strings look similar.

### Reconciliation worker
Responsible for proposing candidate mappings between source entities and canonical entities.

It may use:

- exact normalized equality;
- token similarity;
- structured attribute comparison;
- note retrieval;
- an LLM for semantic explanation/judgment.

It must persist the method, confidence, rationale and evidence.

### Canonicalization
Responsible for turning accepted reconciliation decisions into canonical relationships that downstream analysis can safely use.

### Analysis
Responsible for deterministic engineering/business rules such as:

- reused assembly detection;
- component coverage across variants;
- reuse candidates;
- blockers;
- conflicting technical facts.

### UI
Responsible for inspection, explicit actions and visualization.

The UI should not directly contain reconciliation logic.

## 2.3 Source of truth

For the PoC, source tables are append-oriented and treated as the customer's supplied evidence. Normalized fields may be updated/recomputed, but raw fields must remain intact.

Canonical entities are application-managed.

Reconciliation tables are the decision/audit layer between the two.

## 2.4 Storage choice

SQLite is sufficient because the PoC has:

- a small synthetic data volume;
- a single local operator;
- no high-concurrency requirement;
- no need for distributed transactions.

The schema should nevertheless use proper primary/foreign keys and indexes so that migrating to PostgreSQL later is straightforward.

## 2.5 Worker invocation model

Two modes are required:

### Batch mode
Explicitly launched for an entity type, e.g. "Reconcile all unassessed components."

The UI should show:

- queued/processing/completed status;
- items processed;
- items requiring review;
- errors.

### Single entity mode
Triggered from a source-component/assembly/supplier detail screen.

This is useful for demos and manual investigation.

## 2.6 Dependency rule

Downstream layers can depend on upstream persisted outputs, but the worker should not reach backward and alter raw source data.

A canonical BOM should only use accepted mappings.
