---
last_mapped_commit: 92a308bb4f3975a737c94509b667c651a00285ba
last_mapped_at: 2026-09-22
---
# Cognyx — External Integrations

**Analysis Date:** 2026-09-22

<!-- refreshed: 2026-09-22 -->

## Overview

The Cognyx codebase is a **brownfield Python project in the blueprint/specification phase**. No integration code has been implemented yet. The documents below describe the **planned** integrations as specified in the blueprint, plus the **source data systems** that the tool ingests.

---

## Source Data Systems (Ingestion Inputs)

These are the external systems whose data exports form the input to the tool. They are represented as static CSV files in `data/inputs/`.

### PLM (Product Lifecycle Management)

**Files:**

- `data/inputs/plm/bom_export.csv` — Multi-variant BOM lines (parent/child, qty, units, descriptions, supplier text)
- `data/inputs/plm/assembly_master.csv` — Variant-specific PLM assembly references + metadata
- `data/inputs/plm/variant_configuration.csv` — 5 train variants + characteristics

**Fields captured:** variant references, assembly references, component references, quantities, units of measure, supplier names, lifecycle status, revisions.

**Planned integration (production):** `docs/blueprint/docs/12_production_evolution.md` §12.2 — "connectors to PLM/ERP systems, scheduled extraction, change detection and incremental ingestion."

### ERP (Enterprise Resource Planning)

**Files:**

- `data/inputs/erp/material_master.csv` — Material IDs, descriptions, supplier IDs, units, categories, lifecycle status, costs
- `data/inputs/erp/supplier_master.csv` — Supplier master records (ID, name, country)

**Fields captured:** material IDs, descriptions, material types, base units, supplier IDs, categories, status (ACTIVE/etc.), standard cost in EUR.

**Planned integration (production):** Same as PLM — direct system connectors, not CSV imports.

### Engineering Notes

**File:** `data/inputs/engineering/technical_notes.csv`

**Purpose:** Free-text notes (FR/EN) providing semantic evidence for reconciliation — equivalences, constraints, legacy references, qualification notes.

**Fields:** note ID, object type, object reference, language, author, date, note text.

**Planned integration (production):** Not specified as a live system; notes are treated as exported artifacts. The reconciliation engine uses them as evidence (`docs/blueprint/docs/05_reconciliation.md`).

---

## Database

### SQLite (PoC)

**Status:** Planned, not yet implemented.

**Scope:** Single-file local database for the PoC. Schema specified in `docs/blueprint/docs/03_data_model.md`.

**Rationale (from blueprint):**

- Small synthetic data volume
- Single local operator
- No high-concurrency requirement
- No need for distributed transactions

**Migration path:** PostgreSQL or enterprise data platform at production scale (`docs/blueprint/docs/12_production_evolution.md` §12.1).

### PostgreSQL (Production)

**Status:** Not implemented. Referenced as the likely production target.

---

## LLM / AI Provider

### Planned Abstraction

The blueprint (`docs/blueprint/README.md`, §"Suggested PoC technology boundary") specifies:

> "the LLM is called through one well-defined provider abstraction"

**Status:** Not implemented. No provider is chosen. No API keys, no adapter code.

**Design boundary:** The reconciliation worker may use an LLM for semantic explanation/judgment (`docs/blueprint/docs/02_architecture.md` §2.2). The blueprint explicitly says to build the deterministic pipeline first, then connect a "real LLM adapter" (`docs/blueprint/docs/11_execution_roadmap.md` §Phase 6).

**No vector database** is required for the first version. **No graph database** is required for the first version.

---

## Web UI / Frontend

### Planned

A small web UI for inspection and review (`docs/blueprint/docs/07_ui_specification.md`). The blueprint suggests React/TypeScript but does not mandate it.

**Status:** Not built. No frontend code exists.

**API contracts:** Defined in `docs/blueprint/docs/08_api_and_service_contracts.md` — REST-like endpoints for ingestion, data exploration, reconciliation, canonical data, and analysis.

---

## Auth / Identity Providers

**None.** The PoC assumes a single local operator with no authentication (`docs/blueprint/docs/08_api_and_service_contracts.md` §8.8). Production would require authentication/authorization (`docs/blueprint/docs/12_production_evolution.md` §12.8) but no specific provider is chosen.

---

## Webhooks / Event Subscriptions

**None.** The current design is synchronous request/response with batch worker invocation. No webhook subscriptions or event-driven integrations are specified.

---

## External APIs (in use or planned)

| API / System | Status | Details |
|---|---|---|
| PLM system (direct connector) | Not implemented | Planned for production (`docs/blueprint/docs/12_production_evolution.md`) |
| ERP system (direct connector) | Not implemented | Planned for production |
| LLM provider | Not implemented | One abstraction planned; no provider chosen |
| Any third-party REST API | None | No external API calls in the current codebase |
| OAuth / SSO | None | No auth in PoC scope |
| Email / SMTP | None | Not in scope |
| File storage (S3, etc.) | None | Local CSV files only |

---

## Summary

The codebase has **zero live external integrations**. It is a specification + synthetic data repository. The only "external" systems are the three CSV source feeds (PLM, ERP, Engineering notes) which are static files in the repository. All integration points (LLM provider, PLM/ERP connectors, web UI, auth) are documented as future work in the blueprint.
