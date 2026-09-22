# 01 — Scope, Product Narrative and Engineering Principles

## 1.1 Product narrative

The PoC represents a small internal engineering tool for comparing BOMs across several train variants. The same physical or functional component may appear under different references because of:

- ERP material numbering;
- PLM reference variations;
- supplier naming differences;
- formatting inconsistencies;
- legacy identifiers;
- revision differences;
- incomplete descriptions;
- contradictory technical information.

The tool should make those inconsistencies visible rather than hiding them.

## 1.2 Three separate semantic questions

Every reconciliation or analysis operation must distinguish these questions:

### A. Identity / reconciliation
"Are these source records referring to the same entity?"

Example:

`CTRL-AIR01` ↔ `CTRL-AIR-01`

### B. Reuse / substitution
"Are these different entities nevertheless compatible or reusable for this engineering purpose?"

This is **not** the same as identity.

### C. Data quality / conflict
"Why do two source records disagree, and which evidence supports each value?"

This should be represented separately from identity.

## 1.3 In-scope

The first PoC should cover:

- multiple train variants;
- assemblies and components;
- source-specific references;
- suppliers;
- basic ERP material information;
- engineering notes;
- reference/UOM/text normalization;
- source-entity deduplication;
- AI-assisted candidate matching;
- evidence and rationale capture;
- human accept/reject workflow;
- canonical BOM relationships;
- a small technical-facts layer;
- cross-variant reuse analysis;
- basic inconsistency/blocker detection;
- an engineer-facing UI for inspecting and reviewing the data.

## 1.4 Explicit non-goals

Do not implement these unless needed to make the demo work:

- full PLM integration;
- full ERP integration;
- arbitrary-depth enterprise BOM modeling;
- real-time event streaming;
- enterprise identity/access management;
- multi-tenant security model;
- complex ontology editor;
- graph database deployment;
- vector database deployment;
- production-grade job scheduler;
- automated final engineering approval;
- autonomous mutation of source data;
- sophisticated optimization/solver algorithms;
- full change-management/version-control workflow.

## 1.5 PoC quality bar

The PoC should feel like something a strong FDE would prototype with a customer:

- small enough to understand in one sitting;
- technically coherent;
- traceable from source to decision;
- explicit about uncertainty;
- useful on messy data;
- easy to demo;
- easy to extend.

It should **not** feel like either:

- a toy CRUD application with an LLM bolted on; or
- an over-engineered enterprise platform built before proving the workflow.

## 1.6 Data ownership principle

Think in four layers:

1. **Source** — exactly what the customer gave us.
2. **Normalized source** — deterministic cleaning of source values.
3. **Canonical** — the application's reconciled representation.
4. **Derived analysis** — conclusions calculated from canonical data and sourced technical facts.

Never destroy the previous layer when creating the next one.

## 1.7 Human-in-the-loop principle

The reconciliation worker may create a proposal. It must not silently create an authoritative mapping.

Expected progression:

`PENDING → ASSESSED → ACCEPTED`

or

`PENDING → ASSESSED → REJECTED`

A later reassessment may create a new assessment/run while preserving the decision history needed by the demo.

## 1.8 Cost/control principle

Batch reconciliation can be resource intensive. Therefore:

- ingestion does not automatically call the LLM;
- batch reconciliation is explicitly launched from the UI or an operator command;
- a user can run reconciliation on a single source entity from its detail page;
- deterministic exact/normalized matching can be performed before any LLM call;
- only unresolved candidates need expensive semantic/LLM assessment.

## 1.9 Observability principle

Every consequential automated action should leave enough trace to answer:

- what input was processed?
- when?
- with which method?
- which candidates were considered?
- what confidence was assigned?
- what evidence supported it?
- was a human decision involved?

The PoC does not need enterprise observability tooling, but it does need persisted provenance.
