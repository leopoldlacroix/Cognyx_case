# Roadmap: Cognyx BOM Reuse Explorer (PoC)

**Created:** 2026-09-22
**Mode:** MVP (vertical slices)
**Granularity:** Standard (5 phases, 3-5 plans each)
**Source:** `.planning/REQUIREMENTS.md` v1 requirements → derived phases

---

## Approach

Phases are **derived from requirements**, not imposed. Each requirement maps to exactly one phase. Each phase is a vertical slice: runnable end-to-end within its scope, building on the prior phase's persisted output. No phase leaves the pipeline non-functional.

## Phase Overview

| # | Phase | Requirements Covered | Success Criteria |
|---|-------|---------------------|------------------|
| 1 | Data Foundation: Ingest & Normalize | INGEST-01, INGEST-02, INGEST-03, NORM-01, NORM-02, NORM-03, NORM-04, SCEN-C | 6 criteria |
| 2 | Entity Resolution & Reconciliation Engine | NORM-05, NORM-06, RECON-01, RECON-02, RECON-03, RECON-04, SCEN-B, SCEN-D, SCEN-E, SCEN-H | 5 criteria |
| 3 | Human Review Workflow + Core Analysis | REVIEW-01, REVIEW-02, REVIEW-03, ANALYSIS-01, ANALYSIS-02, ANALYSIS-03, ANALYSIS-04, ANALYSIS-05, SCEN-A, SCEN-F, SCEN-G, SCEN-J | 6 criteria |
| 4 | Cross-Variant Reuse Analysis | *Analysis layer fully realized* (Phase 3 covers ANALYSIS-01–05; Phase 4 deepens report generation, variant-level drill-down, and assembly overlap metrics) | 4 criteria |
| 5 | Explainability, Edge Cases & Data Quality | SCEN-G (deepen), SCEN-H (deepen), SCEN-I (deepen), SCEN-J (deepen), ANALYSIS-05 (deepen) | 4 criteria |

> **Note on Phases 3–5:** ANALYSIS requirements and SCEN-A through SCEN-J are deliberately split across Phases 3–5 because the analysis layer depends on the canonical model (Phase 3 review output), and explainability/edge-case handling (Phase 5) requires the full pipeline to be in place. No requirement is duplicated; each owns exactly one phase.

---

## Phase 1: Data Foundation — Ingest & Normalize

**Goal:** All 6 source CSV files are ingested into source tables with full provenance, structurally sound rows are preserved, malformed rows are quarantined, and deterministic normalization (whitespace, casing, punctuation, UOM/supplier/reference aliases) produces clean normalized values alongside raw values.

**Scope:** Source ingestion layer + normalization layer (architectural layers 3.1 and 3.2).

### Plans

| # | Plan | Requirements |
|----|------|-------------|
| 1.1 | **Ingest all 6 CSV source files** — `plm/bom_export.csv`, `plm/assembly_master.csv`, `plm/variant_configuration.csv`, `erp/material_master.csv`, `erp/supplier_master.csv`, `engineering/technical_notes.csv` — into source tables with `source_file` registration, file hash, and `source_row` preservation | INGEST-01 |
| 1.2 | **Hard validation quarantine** — structurally malformed rows (wrong column count, unparseable numbers) are rejected into a quarantine table with reason; pipeline continues for valid rows | INGEST-02 |
| 1.3 | **Soft validation warnings** — rows kept but warnings emitted for missing description, unknown UOM, empty supplier; warnings visible in data explorer | INGEST-03 |
| 1.4 | **Normalize PLM BOM lines** — whitespace collapse, casing standardization for identifiers, punctuation harmonization; raw values preserved, normalized values stored alongside | NORM-01 |
| 1.5 | **Apply UOM, supplier, and reference aliases** — UOM aliases (`pcs` → `EA`, `units` → `EA`), supplier name aliases (`SIEMENS` → `SIEMENS MOBILITY`), reference aliases (`CTRL-AIR01` → `CTRL-AIR-01`); config-driven, reviewable mappings | NORM-02, NORM-03, NORM-04, SCEN-C |

### Success Criteria (observable user behaviors)

1. **All 6 source files visible in data explorer** with file name, source system, file hash, ingestion timestamp, and row count — user can confirm nothing was lost.
2. **Raw values never replaced** — navigating to any source row shows both `component_ref_raw` and `component_ref_normalized` side by side; raw is identical to the CSV.
3. **Malformed rows are quarantined, not silently dropped** — user sees a quarantine count and can inspect each quarantined row with the rejection reason.
4. **Soft warnings are visible per row** — missing descriptions, unknown UOMs, and empty suppliers are flagged with warnings, not errors; the row is still usable.
5. **Typo/alias references resolve** — searching for `CTRL-AIR01` (the typo) returns the normalized `CTRL-AIR-01` record, demonstrating alias application (SCEN-C).
6. **UOM and supplier aliases are applied consistently** — `pcs`, `units` display as `EA`; `SIEMENS` displays as `SIEMENS MOBILITY` in normalized views.

### Requirements Coverage

| Requirement | Phase | Status |
|-------------|-------|--------|
| INGEST-01 | Phase 1 | Pending |
| INGEST-02 | Phase 1 | Pending |
| INGEST-03 | Phase 1 | Pending |
| NORM-01 | Phase 1 | Pending |
| NORM-02 | Phase 1 | Pending |
| NORM-03 | Phase 1 | Pending |
| NORM-04 | Phase 1 | Pending |
| SCEN-C | Phase 1 | Pending |

---

## Phase 2: Entity Resolution & Reconciliation Engine

**Status:** Complete (2026-09-23). Plans 02-01 through 02-05 executed. 110 tests passing.

**Goal:** Source entities are extracted and deduplicated. The reconciliation engine proposes candidate mappings — identity/alias matches, functional similarity candidates, and variant-specific exclusions — each with confidence scores, match methods, rationale, and evidence. Multilingual engineering notes are ingested and available as reconciliation context (SCEN-H). No silent merges; all proposals are reviewable.

**Scope:** Source entity extraction layer + reconciliation worker (architectural layers 3.3 and 3.4). Note: ERP material normalization (NORM-05) and engineering note normalization (NORM-06) are included here because they are prerequisites for entity extraction and reconciliation context respectively — they produce the normalized ERP/note data that the reconciliation engine consumes.

### Plans

| # | Plan | Requirements |
|----|------|-------------|
| 2.1 | **Normalize ERP materials** — supplier ID mapping to canonical supplier references, UOM standardization for ERP material records; normalized values stored alongside raw | NORM-05 |
| 2.2 | **Normalize engineering notes** — language detection (FR/EN/DE), text extraction for evidence use; original wording preserved; notes indexed for search as reconciliation context | NORM-06, SCEN-H |
| 2.3 | **Entity resolution: identity/alias detection** — detect same-entity-different-ID relationships (e.g. `CTRL-AIR-01` vs `CTRL-AIR01`, PLM vs ERP vs note identifiers for the same component); confidence scoring; match method recorded (exact normalized match, alias table lookup); proposals stored as `ASSESSED` status | RECON-01, SCEN-B |
| 2.4 | **Functional similarity detection** — detect different entities that may be interchangeable (e.g. similar controllers with different ratings); surface as `UNCERTAIN` proposals without merging; structured similarity comparison of name/description/category/supplier/technical facts | RECON-02, SCEN-D, SCEN-F |
| 2.5 | **Variant-specific difference detection** — detect intentional variant-specific component choices (e.g. Nordic cold-rated HVAC/Brake/Cab/Lighting); flag as variant-specific specialization; exclude from generic reuse suggestions; record as separate canonical entities | RECON-03, SCEN-E |
| 2.6 | **Complete reconciliation record schema** — every reconciliation row includes: source system, raw ID, canonical ID (nullable), status (pending/assessed/rejected), match method, confidence (0–1), rationale text, evidence list (JSON); persistence in `component_reconciliation`, `assembly_reconciliation`, `supplier_reconciliation` tables | RECON-04 |

### Success Criteria (observable user behaviors)

1. **Same entity, different IDs — detected and linked** — user opens the reconciler for `CTRL-AIR-01` (PLM) and sees a candidate linking to the ERP material `MAT-10001` and the engineering note reference, all proposing the same canonical entity with high confidence (SCEN-B).
2. **Similar-but-not-identical — NOT merged** — user inspects "Standard Door Controller" vs "Export Door Controller"; the system proposes them as functional similarity candidates with `UNCERTAIN` status and visible justification, not as an identity match (SCEN-D).
3. **Nordic variant parts — excluded from generic reuse** — user reviews the Nordic HVAC variant; cold-rated parts appear as variant-specific specializations, not as duplicates or generic reuse candidates (SCEN-E).
4. **Engineering notes are searchable reconciliation context** — user assessing a candidate sees relevant FR/EN/DE notes surfaced alongside structured attributes; original wording is preserved (SCEN-H).
5. **Every reconciliation proposal carries full provenance** — each row displays source system, raw ID, canonical ID, status, method, confidence, rationale, and evidence; nothing is opaque (RECON-04).

### Requirements Coverage

| Requirement | Phase | Status |
|-------------|-------|--------|
| NORM-05 | Phase 2 | Complete |
| NORM-06 | Phase 2 | Complete |
| RECON-01 | Phase 2 | Complete |
| RECON-02 | Phase 2 | Complete |
| RECON-03 | Phase 2 | Complete |
| RECON-04 | Phase 2 | Complete |
| SCEN-B | Phase 2 | Complete |
| SCEN-D | Phase 2 | Complete |
| SCEN-E | Phase 2 | Complete |
| SCEN-H | Phase 2 | Complete |

---

## Phase 3: Human Review Workflow + Core Analysis

**Status:** Complete (2026-09-23). Plans 03-01 through 03-05 executed. 180 tests passing. CLI review and analyze commands write JSON under `data/processed/`. Canonical BOM is built from accepted identity plus singletons. `MAT-10001` is not an identity link.

**Goal:** Human operators can review reconciliation proposals (accept/reject/redirect with rationale), filtered and navigable by confidence, match method, and source system. Accepted reconciliations propagate to the canonical model; rejected ones are recorded. Core analysis reports — already reused, reusable candidates, blockers, data-quality issues — are generated from the canonical model with explainability. Obvious reuse scenarios (A), potential reuse requiring review (F), conflicting evidence (G), data-quality issues (I), and lifecycle mismatches (J) are surfaced.

**Scope:** Review workflow (layer 3.5 trigger) + canonicalization layer + analysis layer initial outputs (architectural layers 3.5, 3.6). This is the first phase where the full pipeline — ingest → normalize → reconcile → human decide → canonical → analyze — is operational end-to-end.

### Plans

| # | Plan | Requirements |
|----|------|-------------|
| 3.1 | **Review decisions** — `decide_reconciliation`: accept / reject / redirect on PENDING rows; identity accept sets a canonical id; similarity accept does not merge; create canonical tables without retrofitting SQLite FKs | REVIEW-01 |
| 3.2 | **Filterable queue** — list by entity type, status, confidence band, method, source system, and `evidence_json.relationship` | REVIEW-02 |
| 3.3 | **Canonical BOM** — accepted identity clusters share one component; singletons with no identity row propagate (otherwise SCEN-A is empty); pending/rejected identity stays unresolved; assemblies and variants are created without waiting for empty assembly reconciliation | REVIEW-03 |
| 3.4 | **Reuse reports** — already reused from `bom_relationship`; candidates from functional-similarity rows plus the rugged-description rule (SCEN-F cameras are not in the Phase 2 hyphen detector) | ANALYSIS-01, ANALYSIS-02, ANALYSIS-05, SCEN-A, SCEN-F |
| 3.5 | **Conflicts, data quality, CLI** — N-064 voltages both kept; export counting lifecycle is Prototype vs Released; quarantine + duplicate BOM keys; CLI `review` and `analyze` write JSON under `data/processed/` | ANALYSIS-03, ANALYSIS-04, ANALYSIS-05, SCEN-G, SCEN-I, SCEN-J |

### Success Criteria (observable user behaviors)

1. **Operator can review and decide** — user opens a pending reconciliation, sees the candidate with confidence, method, rationale, and evidence; clicks "Accept" with optional rationale; the mapping propagates to the canonical model and the BOM explorer shows the resolved component (REVIEW-01).
2. **Pending items are findable and filterable** — user filters pending components by confidence band (e.g. "uncertain 0.50–0.74") and source system (e.g. "PLM only"); the filtered list matches expectations; counts update correctly (REVIEW-02).
3. **Accepted mappings are reflected in analysis; rejected mappings are not** — after accepting a reconciliation, the reuse analysis report shows the component as shared across variants; after rejecting, it does not appear; rejected items show the rejection reason in the reconciler history (REVIEW-03).
4. **Obvious reuse is surfaced correctly** — HVAC Controller, Brake, and PIS components that appear in multiple variant BOMs are listed in the "already reused" report with variant count and evidence (SCEN-A).
5. **Potential reuse candidates are surfaced with evidence** — Passenger Counting Camera vs Rugged Camera appears as a reuse candidate with functional similarity justification and qualification blockers visible; user can see why it requires review (SCEN-F).
6. **Conflicts and lifecycle issues are visible, not hidden** — HVAC Controller conflict (ERP 48V vs note 24V) appears in the blockers report with both values shown and `CONFLICTING` status; Export passenger counting module lifecycle mismatch appears as a separate data-quality issue (SCEN-G, SCEN-J).

### Requirements Coverage

| Requirement | Phase | Status |
|-------------|-------|--------|
| REVIEW-01 | Phase 3 | Complete |
| REVIEW-02 | Phase 3 | Complete |
| REVIEW-03 | Phase 3 | Complete |
| ANALYSIS-01 | Phase 3 | Complete |
| ANALYSIS-02 | Phase 3 | Complete |
| ANALYSIS-03 | Phase 3 | Complete |
| ANALYSIS-04 | Phase 3 | Complete |
| ANALYSIS-05 | Phase 3 | Complete |
| SCEN-A | Phase 3 | Complete |
| SCEN-F | Phase 3 | Complete |
| SCEN-G | Phase 3 | Complete |
| SCEN-I | Phase 3 | Complete |
| SCEN-J | Phase 3 | Complete |

---

## Phase 4: Cross-Variant Reuse Analysis — Deep Reports

**Status:** Complete (2026-09-23). Plans 04-01 through 04-04 executed. 201 tests passing. `compare.html` opens on REGIO-STD vs REGIO-NORDIC. `analyze compare` writes `compare.json`.

**Goal:** Analysis layer outputs are enriched with assembly-level overlap metrics, variant-vs-variant comparison drill-downs, component coverage matrices, and structured reuse category assignments (reused / reuse candidate / blocked / unresolved). This phase deepens the analysis from Phase 3's report generation into a usable cross-variant comparison workbench. All analysis is derived from the accepted canonical model + sourced technical facts.

**Scope:** Analysis layer deep outputs (architectural layer 3.6 full scope). This phase does not add new requirements — it realizes the full depth of ANALYSIS-01 through ANALYSIS-05 that Phase 3 established, plus the assembly-level metrics defined in the architecture. The check page for this phase is `data/processed/compare.html`: pick two variants, see shared assemblies and parts. Same static HTML shell as the earlier pages, no web framework.

### Plans

| # | Plan | Requirements |
|----|------|-------------|
| 4.1 | **Assembly-level overlap metrics** — for each assembly, compute component overlap ratio, exact common components across variants, variant-specific components, unresolved components, conflicting facts count, potential substitution opportunities; display as assembly comparison matrix | ANALYSIS-01 (deepen) |
| 4.2 | **Variant-vs-variant comparison drill-down** — select two variants, see side-by-side assembly list with shared components highlighted, variant-specific components marked, unresolved items flagged; drill from assembly to component-level evidence | ANALYSIS-02 (deepen) |
| 4.3 | **Blockers detail with evidence trail** — each blocker in the blockers report links to the specific technical fact or reconciliation conflict that causes it; user can trace from blocker → conflicting facts → source records → original CSV row | ANALYSIS-03 (deepen) |
| 4.4 | **Data-quality report enrichment** — duplicate reference detection across source systems, normalization warning summary by type, missing supplier/description counts by source, conflicting technical facts list, unresolved reconciliation count, source-reference alias summary; each issue links to underlying record | ANALYSIS-04 (deepen) |

### Success Criteria (observable user behaviors)

1. **Assembly comparison matrix is readable** — user views the assembly comparison view; each assembly row shows component overlap ratio, shared component count, variant-specific count, unresolved count, and conflict count; rows with high overlap are visually distinct.
2. **Variant-to-variant drill-down works** — user selects "Variant A vs Variant B"; the side-by-side view shows assemblies present in both, assemblies unique to each, and shared components highlighted; clicking a shared component shows its source references from both variants.
3. **Blocker evidence trail is complete** — user clicks a blocker in the report; the detail view shows the conflicting technical facts with source type, source ID, original value, and a link back to the source CSV row; user can see exactly why this blocks reuse.
4. **Data-quality report is actionable** — user opens the data-quality report; duplicate references are grouped with the source rows that share them; normalization warnings are summarized by type with counts; each issue row links to the record that triggered it.

### Requirements Coverage

| Requirement | Phase | Status |
|-------------|-------|--------|
| ANALYSIS-01 | Phase 4 | Complete (deepen) |
| ANALYSIS-02 | Phase 4 | Complete (deepen) |
| ANALYSIS-03 | Phase 4 | Complete (deepen) |
| ANALYSIS-04 | Phase 4 | Complete (deepen) |

> **Note:** ANALYSIS-01 through ANALYSIS-04 are initially covered in Phase 3 (report generation exists). Phase 4 deepens them to full assembly-level metrics and drill-down. The traceability reflects Phase 4 as the phase where the full depth is realized.

---

## Phase 5: Explainability, Edge Cases & Final Scenario Coverage

**Goal:** Every analysis result carries explainability. Conflicting evidence (SCEN-G), multilingual evidence (SCEN-H), data-quality issues (SCEN-I), and lifecycle mismatches (SCEN-J) are fully realized with complete evidence trails and edge-case handling. This phase finalizes the scenario coverage and ensures the demo can show all 10 scenarios A–J.

**Scope:** Analysis explainability + edge-case hardening (architectural layer 3.6 final scope). This phase completes what Phase 3 established and Phase 4 deepened. The check page is `data/processed/evidence.html`: each conflict, language, data-quality issue, and lifecycle mismatch shows both values and the source row. Same static HTML shell. An interactive workbench stays a later version.

### Plans

| # | Plan | Requirements |
|----|------|-------------|
| 5.1 | **Explainability for all analysis results** — every "already reused", "reusable candidate", "blocker", and "data-quality issue" row includes a plain-language explanation: which records were compared, what attributes matched or conflicted, what evidence was used, what method produced the result; explainability is derived from persisted data, not generated ad hoc | ANALYSIS-05 (deepen) |
| 5.2 | **Conflicting evidence — full surfacing** — SCEN-G: conflicting technical facts for the same canonical entity/attribute are displayed with both values, both source records, both source types, and a conflict status; the system does not select one winner; user sees the conflict and can decide | SCEN-G (deepen) |
| 5.3 | **Multilingual evidence — complete context** — SCEN-H: FR/EN/DE notes are displayed in original language alongside any normalized translation; language is flagged per note; notes are searchable by language; reconciliation candidates include relevant notes as evidence regardless of language | SCEN-H (deepen) |
| 5.4 | **Data-quality issues — complete detection** — SCEN-I: duplicate BOM lines detected and reported, invalid quantities flagged, unit inconsistencies across sources reported, missing supplier references reported; each issue is independent of identity reconciliation; data-quality report is comprehensive | SCEN-I (deepen) |
| 5.5 | **Lifecycle mismatch — complete handling** — SCEN-J: ERP and PLM lifecycle state differences for the same component are detected, compared, and reported as a distinct issue type; the mismatch does not block identity reconciliation but is visible in the data-quality and blockers reports | SCEN-J (deepen) |

### Success Criteria (observable user behaviors)

1. **Every analysis row has an explanation** — user hovers or expands any row in the reuse/blockers/data-quality reports; a plain-language explanation appears stating what was compared, what matched, what conflicted, and what evidence was used; the explanation is consistent with the persisted data.
2. **Conflicting evidence shows both sides** — for the HVAC Controller 24V vs 48V conflict, the blockers report shows both values with source provenance (ERP material record vs engineering note), both marked as `CONFLICTING`; no value is silently selected; user understands the conflict (SCEN-G).
3. **Multilingual notes retain original wording and are searchable** — user searches for a French note term; the note appears with its original FR text, language flag, and any relevant reconciliation candidates; switching to EN view shows the same note with language metadata intact (SCEN-H).
4. **Data-quality issues are comprehensive and independent** — the data-quality report shows duplicate BOM lines (same variant/assembly/component appearing twice), invalid quantities (negative or non-numeric), unit inconsistencies (same component referenced with different UOMs across sources), and missing suppliers; none of these require reconciliation to be detected (SCEN-I).
5. **Lifecycle mismatches are reported distinctly** — the Export passenger counting module shows ERP status "Active" and PLM status "Obsolete" (or similar mismatch); this appears as a lifecycle mismatch issue in the data-quality report, separate from any identity or similarity issue; the mismatch is clearly attributed to the two source records (SCEN-J).

### Requirements Coverage

| Requirement | Phase | Status |
|-------------|-------|--------|
| SCEN-G | Phase 5 | Pending (deepen) |
| SCEN-H | Phase 5 | Pending (deepen) |
| SCEN-I | Phase 5 | Pending (deepen) |
| SCEN-J | Phase 5 | Pending (deepen) |
| ANALYSIS-05 | Phase 5 | Pending (deepen) |

---

## Coverage Validation

### v1 Requirements: 32 total

| Category | Count | Phases |
|----------|-------|--------|
| Ingestion (INGEST-01–03) | 3 | Phase 1 |
| Normalization (NORM-01–06) | 6 | Phase 1 (NORM-01–04), Phase 2 (NORM-05–06) |
| Reconciliation (RECON-01–04) | 4 | Phase 2 |
| Review Workflow (REVIEW-01–03) | 3 | Phase 3 |
| Cross-Variant Reuse Analysis (ANALYSIS-01–05) | 5 | Phase 3 (initial), Phase 4 (deepen), Phase 5 (deepen) |
| Scenario Coverage (SCEN-A–J) | 10 | Phase 1 (SCEN-C), Phase 2 (SCEN-B, D, E, H), Phase 3 (SCEN-A, F, G, J), Phase 5 (SCEN-G, H, I, J deepen) |

### Phase → Requirement Map (every requirement appears exactly once)

| Requirement | Phase |
|-------------|-------|
| INGEST-01 | Phase 1 |
| INGEST-02 | Phase 1 |
| INGEST-03 | Phase 1 |
| NORM-01 | Phase 1 |
| NORM-02 | Phase 1 |
| NORM-03 | Phase 1 |
| NORM-04 | Phase 1 |
| NORM-05 | Phase 2 |
| NORM-06 | Phase 2 |
| RECON-01 | Phase 2 |
| RECON-02 | Phase 2 |
| RECON-03 | Phase 2 |
| RECON-04 | Phase 2 |
| REVIEW-01 | Phase 3 |
| REVIEW-02 | Phase 3 |
| REVIEW-03 | Phase 3 |
| ANALYSIS-01 | Phase 3 |
| ANALYSIS-02 | Phase 3 |
| ANALYSIS-03 | Phase 3 |
| ANALYSIS-04 | Phase 3 |
| ANALYSIS-05 | Phase 3 |
| SCEN-A | Phase 3 |
| SCEN-B | Phase 2 |
| SCEN-C | Phase 1 |
| SCEN-D | Phase 2 |
| SCEN-E | Phase 2 |
| SCEN-F | Phase 3 |
| SCEN-G | Phase 3 |
| SCEN-H | Phase 2 |
| SCEN-I | Phase 3 |
| SCEN-J | Phase 3 |

**Total: 31 requirements → 31 mappings. Unmapped: 0. Duplicates: 0.**

### Phase → Success Criteria Summary

| Phase | Success Criteria Count |
|-------|----------------------|
| Phase 1 | 6 |
| Phase 2 | 5 |
| Phase 3 | 6 |
| Phase 4 | 4 |
| Phase 5 | 5 |
| **Total** | **26** |

---

## MVP Mode Notes

- **Vertical slices:** Each phase is independently runnable. Phase 1 ingests and normalizes. Phase 2 adds reconciliation on top of normalized data. Phase 3 adds human review + canonical model + analysis. Phase 4 deepens analysis. Phase 5 completes edge cases.
- **No phase is a "foundation-only" layer:** Even Phase 1 produces a usable data explorer with normalized values. Even Phase 2 produces visible reconciliation proposals.
- **Demo ordering:** For the 1-hour demo, the natural walk-through is Phase 1 (load data) → Phase 2 (show reconciliation proposals) → Phase 3 (accept/reject + see analysis update) → Phase 4/5 (deep dive into specific scenarios A–J).

---

## Out of Scope ( reaffirmed )

- Production auth / user management
- Distributed / graph database (SQLite for PoC)
- Complex multi-agent framework
- Full deployment automation
- OCR / PDF extraction
- General-purpose chatbot
- Client-facing ground truth exposure
- Web UI (React/TS) — planned per blueprint, not in PoC scope; CLI + report output for demo

---

*Roadmap created: 2026-09-22*
*Last updated: 2026-09-22*
