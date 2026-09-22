# 12 — Production Evolution / Intentional PoC Boundaries

The PoC should make clear what would be different at production scale.

## 12.1 Database

PoC: SQLite.

Production: likely PostgreSQL or an enterprise data platform depending on customer architecture.

## 12.2 File ingestion

PoC: CSV upload/import.

Production: connectors to PLM/ERP systems, scheduled extraction, change detection and incremental ingestion.

## 12.3 Identity model

PoC: simple relational canonical entities.

Production: potentially a richer engineering ontology/knowledge graph if relationship complexity justifies it.

## 12.4 Reconciliation

PoC: explicit worker and one LLM/provider adapter.

Production:

- scalable workers;
- caching;
- model routing;
- versioned prompts;
- evaluation datasets;
- cost tracking;
- confidence calibration;
- human-review queues;
- audit history;
- tenant/customer isolation.

## 12.5 Technical facts

PoC: simple fact table.

Production: potentially typed ontology properties, source lineage, versioned assertions and richer conflict semantics.

## 12.6 UI

PoC: one operator.

Production: role-based workflows, permissions, collaborative review, saved views, notification systems, richer audit trails.

## 12.7 Analysis

PoC: deterministic rules.

Production: domain-specific compatibility rules, optimization, constraints, scenario simulation and potentially advanced graph/solver components.

## 12.8 Reliability

Production would require:

- authentication/authorization;
- secrets management;
- monitoring;
- structured logs;
- retry policies;
- dead-letter/error handling;
- backup/restore;
- migrations;
- data retention;
- security reviews;
- evaluation and regression suites.

## 12.9 Architectural message to communicate

The important design choice is not that the PoC has every production component. It is that the boundaries are already correct:

`source → normalize → reconcile → human decision → canonical model → analysis`

Those boundaries allow the system to scale in sophistication without changing its conceptual workflow.
