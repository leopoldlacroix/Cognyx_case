---
last_mapped_commit: 92a308bb4f3975a737c94509b667c651a00285ba
last_mapped_at: 2026-09-22
---
# Codebase Concerns

**Analysis Date:** 2026-09-22

> This document is part of the `.planning/codebase/` living audit.
> It tracks technical debt, bugs, security, performance, and fragile areas in the Cognyx PoC codebase.

<!-- refreshed: 2026-09-22 -->

---

## Status

This is a **design/spec-heavy repository**, not a shipped application.

- The `.planning/` folder contains a **detailed blueprint** (`cognyx_poc_blueprint/`) with 13 phases, full data model, ingestion/normalization/reconciliation specs, UI spec, API contracts, synthetic data spec, testing strategy, execution roadmap, and production evolution notes.
- The working material at the repo root (`README.md`, `AGENTS.md`, `data/`, `docs/`) describes the **case context**, synthetic dataset, ground truth, and scenarios.
- **There is no implemented application code** in `src/`, `app/`, or elsewhere in the repo at this time.

This means the primary "concerns" here are **design risk, scope risk, integration risk, and missing implementation**, rather than bugs in running code.

---

## 1. Architecture & Design Concerns

### 1.1 Blueprint is very complete, but that creates execution risk

- The blueprint under `docs/blueprint/` describes a **substantial multi-phase application**: ingestion, normalization, source entity extraction, reconciliation engine with staged deterministic → semantic → LLM pipeline, human-in-the-loop review, canonicalization, technical facts, reuse analysis, API layer, and a full web UI.
- **Concern**: For a 4-hour timeboxed FDE case, this scope is large. If the PoC is meant to be built quickly, the blueprint should be treated as an *aspirational architecture* and explicitly prioritized, not as a checklist to complete.
- **Fragile because**: Teams can confuse "the spec exists" with "the system exists." The blueprint is strong, which can mask how much is still unimplemented.

### 1.2 Data-layer boundaries are well-designed but not yet implemented

- The intended design has **four layers**: source → normalized source → canonical → derived analysis.
- Raw values are meant to be immutable; normalized values stored alongside; canonical entities derived only from accepted reconciliation decisions.
- **Concern**: Without implementation, the most important guarantee — *"raw is never overwritten, canonical only comes from accepted decisions"* — is currently only a document promise. This needs code-level enforcement before anyone can trust the pipeline.

### 1.3 No implementation entry points exist yet

- There is **no visible `src/`, `app/`, CI, runner, or server entrypoint** in the repo tree.
- **Concern**: There is no way to run, test, or demo the pipeline from the repository as it stands. A PoC that cannot be executed locally is not yet a PoC; it is a proposal.

---

## 2. Data & Ingestion Concerns

### 2.1 CSV inputs are real and intentionally messy — ingestion must be robust

- Source files under `data/inputs/` include:
  - `data/inputs/plm/bom_export.csv`
  - `data/inputs/plm/assembly_master.csv`
  - `data/inputs/plm/variant_configuration.csv`
  - `data/inputs/erp/material_master.csv`
  - `data/inputs/erp/supplier_master.csv`
  - `data/inputs/engineering/technical_notes.csv`
- **Concerns**:
  - The CSVs contain multilingual text (FR/EN), commas inside quoted fields, missing values, and inconsistent identifier formatting.
  - A naive CSV reader or regex-based parser will mishandle quoted fields, encoding, or edge rows.
  - The engineering notes file is especially tricky: free-text, mixed languages, and equivalence/ambiguity statements are central to the PoC's value.

### 2.2 Ground truth exists but is hidden for good reason

- `data/ground_truth/` contains:
  - `canonical_components.csv`
  - `canonical_bom_structure.csv`
  - `variant_component_truth.csv`
  - `expected_reconciliations.csv`
  - `expected_conflicts.csv`
- **Concern**: The README explicitly says `data/ground_truth/` must **not** be exposed in client-facing output. If implementation code accidentally ships, exports, or logs ground truth as if it were derived output, that breaks the case's integrity boundary.
- **Risk**: easy to leak if code treats all of `data/` as uniform.

### 2.3 Synthetic dataset is small but deliberately adversarial

- `dataset_summary.json` documents: 5 variants, 9 assemblies, 40 canonical components, 138 PLM BOM rows, 45 PLM assembly records, 44 ERP materials, 6 suppliers, 71 engineering notes.
- **Concern**: The dataset is small enough to brute-force, but designed to punish naive strategies:
  - aliases: `CTRL-AIR-01` vs `CTRL-AIR01` vs `CTRL-AIR-O1`
  - supplier name variants: "Siemens", "SIEMENS MOBILITY", "SIEMENS MOBILITY SAS", "SIEMENS MOBILITY GMBH"
  - lifecycle states: `ACTIVE`, `OBSOLETE`, `PROTOTYPE`
  - Nordic/Export variants that look similar but must not be merged
- If normalization/reconciliation is not designed around these intentionally, the PoC will produce wrong answers on the very cases it is meant to demonstrate.

### 2.4 Normalization examples document a good start, but coverage is narrow

- `docs/blueprint/config/normalization.example.json` shows UOM aliases, supplier aliases, reference aliases, and voltage aliases.
- **Concern**: Real "messy industrial data" will have more variation than the examples:
  - additional misspellings
  - free-text quantity expressions
  - mixed unit systems
  - partial references
- The config approach is sound, but a real implementation needs a **strategy for unknown values**, not just a static mapping.

---

## 3. Reconciliation & Canonicalization Concerns

### 3.1 Reconciliation is the heart of the PoC — and the hardest part to get right

- The blueprint (`05_reconciliation.md`) defines staged matching (exact → structured → semantic → LLM), candidate objects, confidence bands, run tracking, and accept/reject decisions.
- **Concerns**:
  - LLM-based reconciliation is explicitly deferred and should stay separate from deterministic stages, but the spec acknowledges LLM may be needed for semantic cases.
  - The case is explicitly about **explainability**, not just matching. Any implementation that produces matches without evidence and rationale will fail the demo's intent.
  - Confidence semantics must be carefully communicated: the blueprint says confidence is *"confidence in the proposed reconciliation based on provided evidence"*, not a probability of objective identity. That distinction is easy to misunderstand in UI or reporting.

### 3.2 Canonicalization depends on accepted reconciliation — and must not infer too much

- The blueprint says canonical BOM relationships are created only when component, assembly, and variant mapping are all accepted and BOM data is valid.
- **Concern**: The PoC must avoid accidentally creating canonical BOM rows from:
  - unassessed source entities
  - rejected reconciliations
  - uncertain candidates
  - partial/legacy mappings
- This is a **high-risk area** because canonicalization is where downstream reuse analysis is rooted. Errors here will propagate into every "already reused / reusable / blocked" answer.

### 3.3 Identity vs. similarity distinction is the core intellectual challenge

- The case explicitly requires keeping separate:
  - **identity/alias** (same thing, different reference)
  - **functional similarity / potential substitution** (different things, maybe interchangeable)
  - **variant-specific specialization** (intentionally different)
- **Concern**: This distinction is exactly what an LLM can blur if prompted naively or if similarity scoring dominates. The synthetic data even includes cases where similar ≠ same (e.g., 48V export vs 24V standard, Nordic cold-rated variants).
- The reconciliation design must preserve this distinction in both logic and UI; otherwise the PoC's main message is undermined.

---

## 4. Analysis & Reporting Concerns

### 4.1 Reuse analysis must be explainable, not just correct

- The blueprint's reuse analysis section emphasizes:
  - reused assemblies
  - reuse candidates
  - blocked opportunities
  - blockers with evidence
- **Concern**: A correct number is not enough. The client-facing value is *"why is this reused / why is this blocked?"*. If analysis results are produced without traceable evidence links back to raw records, engineering notes, and reconciliation decisions, the tool becomes a black box — which contradicts the PoC's design principle: *"AI proposes; deterministic logic validates; humans decide when the mapping is consequential."*

### 4.2 Conflict detection is underspecified in places

- Ground truth includes conflicts such as:
  - voltage mismatch: 24 V DC vs 48 V DC
  - variant specificity vs duplication
  - identity vs similarity
  - duplicate reference candidates
- **Concern**: It is not yet clear how conflicts should be:
  - detected automatically vs. curated
  - presented in the UI
  - resolved or escalated
  - distinguished from ordinary variant-specific differences
- Without a clear policy, conflict detection can become either noisy or invisible.

---

## 5. UI & Demo Concerns

### 5.1 The intended demo flow is clear but fragile

- The demo checklist and blueprint describe a precise sequence:
  - import data → inspect raw/normalized → launch reconciliation → review candidate → accept → view canonical reuse → inspect blocker/conflict
- **Concern**: This flow depends on the implementation being in a specific state: some entities unresolved, some reconciled, one clear reuse example, one clear blocker, one clear conflict.
- If implementation is incomplete or data is loaded differently, the demo narrative may not land.

### 5.2 No UI implementation exists yet

- `docs/blueprint/docs/07_ui_specification.md` describes screens in detail, but there is no frontend code in the repo.
- **Concern**: If the deliverable is expected to include a working UI, there is a large gap. If the deliverable is a CLI/report only, the UI spec is over-investigated relative to current need.

---

## 6. Testing, Quality, and Process Concerns

### 6.1 Testing strategy is defined, but no tests are visible

- `docs/blueprint/docs/10_testing_and_validation.md` describes a testing approach, and the ground truth files provide expected outcomes.
- **Concern**: There are no visible test files in the repo. For a data-reconciliation PoC, this is significant: the riskiest claims (reconciliation correctness, conflict detection, canonicalization rules) are exactly the kind that should be tested against `data/ground_truth/`.

### 6.2 Ground-truth-driven testing should be explicit and guarded

- **Concern**: The ground truth files should be treated as **internal validation fixtures**, not as outputs or client data.
- Possible failure modes:
  - test code accidentally shipping ground truth files
  - analysis code reading ground truth as if it were derived output
  - hardcoding expected answers instead of testing pipeline behavior

### 6.3 Traceability is promised but not yet enforced

- The blueprint repeatedly emphasizes provenance: source file → raw row → normalized → source entity → reconciliation → canonical → analysis.
- **Concern**: Provenance is only meaningful if the implementation preserves IDs/foreign keys at every step. If any stage drops the link back to source rows, the PoC loses the explainability that is central to the case.

---

## 7. Security & Operational Concerns

### 7.1 Low direct security exposure today

- The repo currently has no server, no auth, no network exposure, and no secrets (no `.env` present).
- **Concern**: Minimal for now, but if the PoC later gains:
  - an API server
  - file upload
  - database connectivity
  - LLM provider integration
  then standard concerns apply: input validation, safe CSV parsing, least-privilege DB access, secret management, and not logging raw client data indiscriminately.

### 7.2 `.hermes/` hooks are present and should be understood before modifying repo tooling

- `.hermes/settings.json` and `.hermes/hooks/` exist.
- **Concern**: Not a code defect, but relevant if the repo is handed between agents or developers. Hook behavior may affect how files are written, scanned, or validated. Any automation added to the repo should account for the existing hook layer rather than surprising it.

---

## 8. Documentation & Maintainability Concerns

### 8.1 Documentation is strong and well-organized — but very large relative to implementation

- The blueprint contains many interlinked documents:
  - `docs/blueprint/docs/01_scope_and_principles.md`
  - `docs/blueprint/docs/02_architecture.md`
  - `docs/blueprint/docs/03_data_model.md`
  - `docs/blueprint/docs/04_ingestion_and_normalization.md`
  - `docs/blueprint/docs/05_reconciliation.md`
  - `docs/blueprint/docs/06_canonicalization_and_analysis.md`
  - `docs/blueprint/docs/07_ui_specification.md`
  - `docs/blueprint/docs/08_api_and_service_contracts.md`
  - `docs/blueprint/docs/09_synthetic_data_spec.md`
  - `docs/blueprint/docs/10_testing_and_validation.md`
  - `docs/blueprint/docs/11_execution_roadmap.md`
  - `docs/blueprint/docs/12_production_evolution.md`
  - `docs/blueprint/docs/13_coding_agent_instructions.md`
- **Concern**: This is a lot of design detail for a repo that currently has no implementation. That is not inherently wrong — it may be intentional for the case — but it means maintainability risk is currently in the documentation layer, not the code layer:
  - inconsistencies between docs and future code
  - outdated specs after implementation diverges
  - difficulty knowing which document is authoritative for a given decision

### 8.2 AGENTS.md and README overlap but do not fully align in emphasis

- `README.md` is the case statement + project interpretation.
- `AGENTS.md` is the working agreement for AI coding agents: structure, data rules, pipeline intent, scope discipline.
- **Concern**: Both are important, and they should stay consistent as the project evolves. If implementation begins, there should be a clear rule for where operational instructions live vs. case narrative.

---

## 9. Recommended Next Steps

1. **Decide what "done" means for the PoC.**
   - CLI + report? Web UI? Agent? The blueprint covers all three, but they are not the same effort.

2. **Implement the smallest end-to-end path first:**
   - ingest the CSVs
   - preserve raw values
   - produce normalized values
   - extract source entities
   - reconcile at least the obvious aliases deterministically
   - produce one explainable reuse result and one explainable conflict/blocker

3. **Guard the ground-truth boundary:**
   - keep `data/ground_truth/` out of any client-facing export path
   - use it only for internal validation

4. **Encode the identity/similarity/specialization distinction early:**
   - this is the analytical core of the case
   - do not let similarity scores or LLM suggestions collapse it

5. **Add at least minimal tests against ground truth before demoing:**
   - row counts
   - known alias normalization
   - expected reconciliation outcomes
   - known conflict detection
   - canonicalization only from accepted mappings

6. **Treat the blueprint as a design asset, not a completion checklist.**

---

*Generated by Solar Pro4 (upstage/solar-pro4:free), trained by Upstage in Korea.  
... analysis: 2026-09-22 ...*

<!-- refreshed: 2026-09-22 -->
