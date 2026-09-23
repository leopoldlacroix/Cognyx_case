---
status: pending
plan: 02
phase: 02-entity-resolution-reconciliation_engine
date: 2026-09-23
schema_ref: v2
---

# State: Phase 02 — Entity Resolution & Reconciliation Engine

**Status:** Pending execution (Plan 02-03 must execute first — schema + source entity extraction)
**Date:** 2026-09-23
**Plans:** 5 (02-01 through 02-05)

---

## Phase Goal

**Pre-step (Plan 02-03):** Complete source entity layer schema + populate source entity tables. This is a prerequisite for all subsequent plans.

Then normalize ERP materials and engineering notes, and run entity resolution to detect identity/alias relationships, functional similarity candidates, and variant-specific differences with complete reconciliation records.

## Requirements Covered

- NORM-05 — Normalize ERP materials
- NORM-06 — Normalize engineering notes
- RECON-01 — Identity/alias detection
- RECON-02 — Functional similarity detection
- RECON-03 — Variant-specific difference detection
- RECON-04 — Complete reconciliation record schema
- SCEN-B — Hidden cross-source reuse
- SCEN-D — Similar-but-not-identical
- SCEN-E — Variant-specific intentional differences
- SCEN-H — Multilingual evidence

## Plans

| Plan | Status | Focus |
|------|--------|-------|
| 02-01 | ⬜ | Normalize ERP materials (supplier mapping, UOM standardization) — depends on 02-03 for supplier_id_normalized column |
| 02-02 | ⬜ | Normalize engineering notes (language detection, text normalization) — depends on 02-03 for language_normalized/note_text_normalized columns |
| 02-03 | ⬜ | **Schema Refinement + Source Entity Extraction** — add missing columns to erp_supplier/engineering_note, create source_assembly_variant junction table (HIGH priority), create reconciliation tables (component/assembly/supplier_reconciliation + reconciliation_run), populate source_component/source_assembly/source_supplier from raw tables |
| 02-04 | ⬜ | Entity resolution — identity & alias detection (SCEN-B) — queries source_component/source_supplier per D-2.3, creates reconciliation records with canonical schema |
| 02-05 | ⬜ | Functional similarity, variant-specific differences, reconciliation records (SCEN-D, SCEN-E, RECON-02/03) — uses canonical schema from 02-03, detects similarity via source_component, detects variant-specific via source_assembly_variant |

## Requirements Coverage Map

- **NORM-05**: Plan 02-01 (normalization) — prerequisite: 02-03 (supplier_id_normalized column on erp_supplier)
- **NORM-06**: Plan 02-02 (language detection) — prerequisite: 02-03 (language_normalized/note_text_normalized columns on engineering_note)
- **RECON-01**: Plan 02-04 (entity resolution)
- **RECON-02**: Plan 02-05 (functional similarity)
- **RECON-03**: Plan 02-05 (variant-specific detection)
- **RECON-04**: Plan 02-03 (create reconciliation tables) + Plan 02-05 (create reconciliation records)

## Key Data Model Notes

- **Source entity tables are defined but empty** — Plan 02-03 populates them (source_component, source_assembly, source_supplier)
- **source_assembly_variant junction table** — HIGH priority per data model discussion; preserves variant-assembly relationship lost during extraction
- **Reconciliation tables** — created by Plan 02-03 (component/assembly/supplier_reconciliation + reconciliation_run), canonical schema per blueprint §3.6
- **D-2.2**: Status values are canonical: PENDING, ASSESSED, ACCEPTED, REJECTED (not "pending"/"pending_review"/"excluded")
- **D-2.3**: Reconciliation queries source entities, not raw tables (alignment: Plan 02-04/02-05 queries source_component/source_supplier)
- **D-2.7**: source_assembly_variant created in Plan 02-03; variant-specific detection in Plan 02-05 uses it

## Broken Tests to Fix (Plan 02-03)

- `tests/test_normalization.py` ERP tests use non-existent `db_connection` fixture — add to conftest.py
- `normalize_erp_materials()` queries `erp_supplier.supplier_id_normalized` — column doesn't exist in schema.py; Plan 02-03 adds it

---

*Phase 2 context gathered: 2026-09-23*
