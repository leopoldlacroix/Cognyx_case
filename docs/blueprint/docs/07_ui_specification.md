# 07 — UI / Screen Specification

## 7.1 UI philosophy

The UI is an engineering workbench, not a marketing dashboard.

Every aggregate number should lead to inspectable underlying records.

Recommended navigation:

```text
Overview
Data Explorer
Reconciliation
BOM Explorer
Reuse Analysis
Data Quality
```

## 7.2 Screen 1 — Overview

Purpose: quickly communicate whether the imported data is understood and where work remains.

Display cards such as:

- train variants;
- raw BOM lines;
- source components;
- canonical components;
- assemblies;
- accepted mappings;
- items requiring review;
- unresolved items;
- data-quality issues;
- reuse opportunities.

Important: these are factual counters, not scores.

## 7.3 Screen 2 — Data Explorer

Purpose: inspect tables and underlying rows.

Features:

- table selector;
- row count;
- search/filter;
- pagination or small-table scrolling;
- row detail;
- raw vs normalized values where relevant;
- source file provenance.

Suggested tabs:

- Source files
- PLM BOM lines
- Components
- Assemblies
- Suppliers
- Variants
- Technical facts

## 7.4 Screen 3 — Reconciliation Workbench

Purpose: monitor reconciliation and review suggestions.

Top area:

- entity type selector: component / assembly / supplier;
- batch launch button;
- last run status;
- counts: pending / assessed / accepted / rejected.

Table columns:

- source reference;
- normalized reference;
- description;
- status;
- candidate;
- confidence;
- method;
- last assessed;
- action.

## 7.5 Reconciliation detail drawer/page

When a row is selected, display:

### Left side
Source entity:

- raw reference;
- normalized reference;
- description;
- source system;
- source record;
- linked BOM usage.

### Right side
Candidate matches:

- canonical ID/name;
- confidence;
- rationale;
- evidence;
- conflicting fields;
- accept/reject controls.

Action buttons:

- `Find matches`
- `Accept`
- `Reject`
- `Open canonical entity`

## 7.6 Screen 4 — Reconciliation run detail

Display:

- entity type;
- start/end time;
- status;
- total eligible;
- processed;
- assessed;
- review required;
- errors;
- optional method breakdown.

The screen is especially valuable during a live demo because it makes the expensive worker explicit.

## 7.7 Screen 5 — BOM Explorer

Purpose: inspect one train variant or assembly.

Recommended interaction:

```text
Select variant
  ↓
Select assembly
  ↓
See source references vs canonical entities
  ↓
Inspect quantities and technical facts
```

For the PoC, a table is enough. Do not build a sophisticated graph visualization unless there is time.

## 7.8 Screen 6 — Reuse Analysis

Primary table:

| Variant/Assembly | Reuse status | Shared components | Blockers | Evidence |
|---|---|---:|---|---|

Drill-down should show the exact component-level evidence.

## 7.9 Screen 7 — Data Quality

Show issues such as:

- duplicate references;
- normalization warnings;
- missing supplier;
- missing description;
- conflicting technical facts;
- unresolved reconciliation;
- source-reference aliases.

Each issue should link to its underlying record.

## 7.10 Empty/error states

Important states:

- no data ingested;
- ingestion failed;
- no pending reconciliation;
- worker running;
- worker failed partially;
- no canonical mapping yet;
- no reuse candidates;
- insufficient evidence.

Avoid misleading blank pages.

## 7.11 UX constraints

The UI should make the workflow obvious:

`Inspect → Assess → Review → Accept/Reject → Analyze`

Do not hide reconciliation behind an automatic background process.

## 7.12 Definition of Done

A reviewer should be able to perform the entire PoC flow without using a database console:

1. inspect imported data;
2. see what needs reconciliation;
3. launch batch reconciliation;
4. inspect a suggestion;
5. accept/reject it;
6. inspect the canonical result;
7. inspect cross-variant reuse;
8. trace the result back to source evidence.
