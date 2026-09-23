# Phase 3 Context — Impacts from Phases 1 and 2

**Date:** 2026-09-23
**Discovery:** Level 0. No new libraries. Work extends the existing Python, SQLite, pytest, and CLI pipeline.
**Interface:** CLI plus JSON under `data/processed/`. Web UI and HTTP endpoints stay out of scope (ROADMAP out-of-scope, STATE.md).

Roadmap success criteria that say "click Accept" or "open the reconciler" mean the same behaviors through CLI commands and persisted report rows.

## What Phase 3 must build

Human review of existing reconciliation rows, canonical tables (they do not exist yet), canonical BOM from accepted identity plus unambiguous singletons, and four core reports: already reused, reusable candidates, blockers, data-quality issues. Each report row carries a plain-language `explanation` built from persisted fields. Phase 5 deepens explainability; Phase 4 adds assembly overlap matrices and drill-down. Do not build those here.

## Constraints carried forward

1. **Do not edit `data/inputs/`.** Do not read or print `data/ground_truth/` in reports or CLI output.
2. **Three relationship types stay separate.** `evidence_json.relationship` is `identity`, `functional_similarity`, or `variant_specific`. There is no relationship column. A similarity score must never create a shared canonical id.
3. **Statuses in the database are `PENDING`, `ASSESSED`, `ACCEPTED`, `REJECTED`.** Phase 2 detectors write `PENDING`, not `ASSESSED`. Accept and reject must operate on `PENDING`. Do not require a pass through `ASSESSED`.
4. **Methods:** `EXACT`, `NORMALIZED`, `STRUCTURED`, `SEMANTIC`, `LLM`, `MANUAL`. Identity clusters are `EXACT` or `NORMALIZED` at confidence `0.95`. Functional similarity is `STRUCTURED` / `0.50` / `review_needed=true`. Variant-specific is `STRUCTURED` / `0.95` / `review_needed=false`.
5. **Canonical FKs were intentionally omitted.** `component_id`, `assembly_id`, and `supplier_id` are nullable integers with indexes and no foreign key, because the canonical tables did not exist. Create the canonical tables in this phase. Set those id columns on accept. Do not rebuild the reconciliation tables to add SQLite foreign keys.
6. **`record_reconciliation()` inserts only.** It is idempotent on `(source id, method, evidence_json)` and will not update a decision. Accept, reject, and redirect must `UPDATE` the existing row. Redirect then inserts a new `MANUAL` / `PENDING` row.
7. **Identity rows exist only for clusters of two or more `source_*` rows that share a normalized key.** A component used on many BOM lines under one reference is a single `source_component` and has no reconciliation row. Obvious reuse (SCEN-A) is mostly that case. Waiting for an accept on every singleton would leave the reuse report empty.
8. **`MAT-10001` is not an identity match for `CTRL-AIR-01`.** Reference aliases cover `CTRL-AIR01`, `CTRL-AIR-O1`, and `CTRL-HVAC-001`. They do not cover `MAT-10001`. Do not auto-link that ERP material in canonicalization or in the HVAC conflict.
9. **Assembly reconciliation is empty.** No detector writes `assembly_reconciliation`. Requiring an accepted assembly mapping before any canonical BOM row would make every line unresolved. Create canonical assemblies 1:1 from `source_assembly.normalized_reference`. Same rule for variants from `plm_variant`. Supplier canonical rows follow the component rule (accept identity clusters; singletons can be created) but BOM propagation does not depend on suppliers.
10. **Variant-specific Nordic parts stay their own canonical entities** and are excluded from generic reuse candidates. Accepting a `variant_specific` row must not merge it into the non-Nordic component.
11. **Functional similarity is a candidate, not a merge.** Accepting it records the human decision. It still must not assign one shared `component_id` to both sides.
12. **`normalize_erp_materials()` and `run_full_reconciliation()` are not called by `ingest`.** Tests and the CLI build on an already extracted and reconciled database, or call those functions explicitly. Do not hide a re-ingest inside analysis.
13. **BOM `component_description` and `line_status` were not mapped** in `ingest_all_files` (`app/services/ingestion.py` column_map). `plm_bom_line.description_raw` is empty for BOM rows. `line_status` is not a column. Lifecycle for SCEN-J is `plm_assembly.lifecycle_raw` (`PAX-COUNT-MOD-E` is `Prototype`; the other counting assemblies are `Released`) and `erp_material.status_raw` (`ACTIVE` / `OBSOLETE`). Do not look for an Obsolete status on the export counting module. The real mismatch is Prototype vs Released.
14. **Soft warnings over-fire.** `check_soft_validation` looks for `description` / `description_raw` and `supplier_name`. BOM rows store the text in columns that were never mapped, so almost every BOM row gets `missing_description`. The 508 warnings are not 508 engineering issues. The data-quality report must count them, label `missing_description` and `empty_supplier` as ingestion-mapping noise, and list the concrete SCEN-I issues separately: quarantined quantity `BOM-0031` (`one`), duplicate normalized BOM keys (for example `REGIO-STD` / `HVAC-M01` / `CTRL-AIR-01` from `BOM-0001` and `BOM-0301`), and raw UOM variation that aliases already collapse to `EA`.
15. **SCEN-G evidence is note text, not two structured voltage columns.** `N-064` on `CTRL-AIR-01` states both 48V DC and 24V DC. Surface both values as `CONFLICTING`. Do not pick a winner. Do not attach `MAT-10001`'s 24VDC description unless that material is accepted as the same canonical component.
16. **SCEN-F is not produced by the Phase 2 hyphen heuristic.** `PASSCOUNT-CAMERA` vs rugged camera does not share the prefix rule with `MAT-10034` (`Passenger Counting Camera Rugged`, no hyphen pair). `PASSCOUNT-CAMERA-RUGGED` exists on note `N-019` and is not a `source_component`. The candidates report needs an explicit description rule: same ERP `category_raw`, descriptions equal after removing the word `rugged`. That pairs `MAT-10033` with `MAT-10034`. Attach notes `N-018` and `N-019` as qualification evidence. Do not merge them.
17. **Supplier placement stays as stored.** Supplier on the ERP material and supplier text on the BOM line both remain. Do not redesign that in this phase.
18. **CLI ingest hardcodes an absolute `data/inputs` path.** New commands must take `--db` and write under the repo's `data/processed/`. Do not copy the absolute path.

## Canonical BOM rule for this phase

For each `plm_bom_line` that was not quarantined:

1. Resolve variant from `variant_ref_normalized` → canonical `variant` (always created).
2. Resolve assembly from `assembly_ref_normalized` → canonical `assembly` (always created from source assemblies).
3. Resolve component:
   - If the PLM `source_component` has a `PENDING` or `ASSESSED` row with `relationship=identity`, the BOM line stays **unresolved**. It must not appear as an authoritative `bom_relationship`.
   - If that identity row is `ACCEPTED`, use its `component_id`. When accepting, reuse `component_id` already set on an accepted cluster peer listed in `evidence_json` members; otherwise create one canonical `component`.
   - If that identity row is `REJECTED`, the line stays unresolved.
   - If there is no identity row, create or reuse one canonical component for that `source_component` (same normalized reference + source system). This is how HVAC, brake, and PIS lines that already share a reference become "already reused" without a human click.
4. Functional-similarity and variant-specific rows do not block step 3 and do not merge identities.
5. Keep `source_bom_line_id` on `bom_relationship`.
6. Unresolved lines remain queryable.

## Report rules

| Report | Include | Exclude |
|---|---|---|
| Already reused | Canonical component or assembly present on at least two variants via `bom_relationship` | Pending identity aliases, rejected mappings, unresolved lines |
| Reusable candidates | `functional_similarity` reconciliation rows, plus the rugged-description ERP pairs | `variant_specific` rows; anything already sharing a `component_id` |
| Blockers | `technical_fact` conflicts (`CONFLICTING`) for the same canonical or normalized component and attribute; lifecycle mismatches | Identity merges made to hide a conflict |
| Data quality | Quarantine, duplicate normalized BOM keys, UOM alias notes, warning summary that separates mapping noise from real gaps | `data/ground_truth`; the raw list of 508 warnings as if each were a defect |

Every row includes `explanation` citing the records compared, the relationship type, and the source ids.

## Out of this phase

Assembly overlap ratios, variant-vs-variant matrices, blocker click-through to the CSV byte offset, multilingual search UI, and a general note NLP matcher. Those are Phases 4 and 5.
