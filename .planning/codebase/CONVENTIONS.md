---
last_mapped_commit: 92a308bb4f3975a737c94509b667c651a00285ba
last_mapped_at: 2026-09-22
---
# Cognyx — Code Conventions

**Analysis Date:** 2026-09-22
**Scope:** full repository (Cognyx, Alstom x Cognyx FDE Case)
**Source of truth:** this document + `.planning/codebase/TESTING.md` + `docs/blueprint/docs/13_coding_agent_instructions.md` + `docs/blueprint/docs/10_testing_and_validation.md`.

---

The codebase is a small Python/CLI + web-UI PoC with an SQLite backend. There is no produced `src/` tree yet — the repository currently carries the blueprint, synthetic data, and project context rather than implemented application code. This document captures the conventions the implementation must follow, derived from the blueprint, so that future code in `src/`, `tests/`, and `ui/` is consistent regardless of who writes it.

---

## 1. Project model and layer boundaries

The system is six logical layers:

1. **Ingestion** — `src/ingestion/`
2. **Normalization** — `src/normalization/`
3. **Reconciliation worker** — `src/reconciliation/`
4. **Canonical / knowledge layer** — `src/canonical/` (or `src/knowledge/`)
5. **Analysis** — `src/analysis/`
6. **Web UI / API** — `src/ui/` and `src/api/`

Downstream layers may depend on upstream **persisted** outputs. The reconciliation worker must not reach backward and mutate raw source data. Canonical BOM relationships must only use accepted mappings. Source data lives in `data/inputs/` and is immutable; normalized output goes to `data/processed/`.

Business rules belong in backend/domain services. Keep the UI thin: it displays data and invokes behavior, and should not directly contain reconciliation or reuse logic.

## 2. Naming conventions

### General

- Use clear, domain-level names. Prefer `source_component`, `canonical_component`, `component_reconciliation` over generic names like `item`, `entity`, `rec`.
- Name by concept, not by storage shape. A reconciliation row is a reconciliation row, not a `match_record` or `pair`.

### Files and modules

- One module per bounded concept where practical: ingestion, normalization, reconciliation, canonicalization, analysis, UI/API.
- Keep modules small enough to understand in one sitting. A small service/module is preferred over an abstraction introduced only for future possibilities.

### Functions and methods

- Verbs for behavior: `normalize_reference`, `build_candidate`, `accept_mapping`, `compute_reuse`.
- Nouns for data containers/records: `Candidate`, `ReconciliationRow`, `SourceEntity`.
- Avoid hidden verbs in noun names (`Manager`, `Handler`) unless the type genuinely coordinates behavior.

### Tests

- Mirror source layout under `tests/` where practical: `tests/unit/ingestion/`, `tests/unit/normalization/`, `tests/integration/`, `tests/e2e/`.
- Test filenames should map to the behavior under test, e.g. `test_normalize_reference.py`, `test_component_reconciliation_eligibility.py`.

## 3. Source, normalized, canonical, derived layers

Think in four layers and never destroy the previous layer when creating the next one:

1. **Source** — exactly what the customer gave us.
2. **Normalized source** — deterministic cleaning of source values.
3. **Canonical** — the application's reconciled representation.
4. **Derived analysis** — conclusions calculated from canonical data and sourced technical facts.

Rules:

- Raw source values are immutable after ingestion. If a column holds raw data, treat it as read-only from the application's perspective.
- Normalized values may be recomputed; raw values are not overwritten by normalization.
- Canonical identity must not silently absorb source-system prefixes unless that is a deliberate domain decision.
- Reconciliation is a **reviewable, provenance-bearing relationship**, not a silent overwrite. Model the progression `PENDING → ASSESSED → ACCEPTED` or `PENDING → ASSESSED → REJECTED`.

## 4. Data handling conventions

### Preserve provenance

Whenever a transformation creates a new representation, retain a path back to its source. Every consequential automated action should leave enough trace to answer: what input was processed, when, with which method, which candidates were considered, what confidence was assigned, what evidence supported it, and whether a human decision was involved.

### Keep raw and normalized side by side

Store raw and normalized values alongside each other. Example:

- `component_ref_raw = CTRL-AIR01`
- `component_ref_normalized = CTRL-AIR-01`

Never replace the first with the second.

### Distinguish the three semantic questions

Every reconciliation or analysis operation must distinguish:

1. **Identity / reconciliation** — are these source records referring to the same entity?
2. **Reuse / substitution** — are these different entities nevertheless compatible or reusable?
3. **Data quality / conflict** — why do two source records disagree, and which evidence supports each value?

Do not collapse these into a single "match" concept.

### Unknown values

If a value cannot be safely normalized, do not guess:

- keep the raw value;
- leave the normalized value unchanged or null according to field semantics;
- emit a warning where appropriate.

### Evidence

JSON is acceptable for the PoC because the payload is inspected primarily as a unit. A production implementation could normalize it later. Evidence items should be inspectable as a list with explicit content, e.g. `same normalized reference`, `same 24 V DC supply`, `engineering note says equivalent`.

## 5. Reconciliation conventions

### Candidate generation order

Use a layered strategy from cheap/deterministic to expensive/semantic:

1. exact normalized match;
2. structured similarity (normalized name/description, category, supplier, identifiers, selected technical facts);
3. embedding/text similarity if useful (optional for the PoC);
4. LLM assessment for genuinely ambiguous cases.

Cheap deterministic matching should prevent unnecessary LLM calls.

### Candidate object contract

Each candidate should carry, conceptually:

- candidate canonical entity ID;
- match confidence 0–1;
- recommendation: `MATCH`, `NO_MATCH`, `UNCERTAIN`;
- method;
- rationale;
- evidence list;
- conflicts detected;
- fields compared.

### Status semantics

- `ASSESSED` does not mean accepted.
- Only an explicit human action (or an explicitly authorized deterministic auto-accept rule) changes authority state.
- For the demonstration, do not auto-accept LLM results.

### Failure handling

Worker failures should be recorded at run level and should not corrupt accepted mappings. Examples: LLM timeout, malformed LLM response, candidate lookup failure, invalid structured data. Mark the item/run as failed or partial and continue where practical. A failed reconciliation run must not invalidate previously accepted mappings.

## 6. LLM usage conventions

LLM output is evidence/proposal data that must pass application validation. Do not let an LLM determine:

- raw ingestion behavior;
- normalization rules;
- authoritative database state;
- canonical BOM creation after rejection;
- deterministic reuse calculations.

The LLM should receive only the information necessary to assess the candidate: source entity, candidate entities, relevant structured attributes, relevant engineering notes, an explicit task definition, and a required response schema. Do not send the entire database blindly.

The prompt must explicitly distinguish identity from interchangeability, evidence from inference, and missing information from contradiction. The model must be allowed to return `UNCERTAIN` when evidence is insufficient, and must not invent technical facts.

LLM calls do not need to be deterministic, but their outputs must be validated against a schema and should be recorded for traceability.

## 7. Error handling conventions

### Validation levels

- **Hard validation:** reject or quarantine rows when the required identifier is missing, the quantity is impossible to parse where required, or the source row is structurally malformed.
- **Soft validation:** keep the row but emit a warning when description is missing, UOM is unknown, supplier is absent, or a technical field is contradictory.

Industrial data is messy. Over-aggressive rejection hides the problem being demonstrated. Surface invalid rows rather than silently dropping them.

### Normalization failures

If a value cannot be safely normalized, leave it unchanged or null according to field semantics, emit a warning where appropriate, and do not guess.

### Explicit failures, not silent success

Operations that can fail should report outcome clearly: processed count, assessed count, review-required count, error count. Batch runs should be explicitly launchable and show queued/processing/completed status, items processed, items needing review, and errors.

### Reassessment and history

A future run may generate better candidates. Historical assessments should not simply disappear. Keep previous reconciliation rows and use the latest accepted decision as the effective mapping.

## 8. SQLite and schema conventions

SQLite is sufficient for the PoC because the volume is small, there is a single local operator, and there is no high-concurrency requirement. The schema should nevertheless use proper primary/foreign keys and indexes so that migrating to PostgreSQL later is straightforward.

- Primary keys: integer IDs are acceptable for the PoC.
- Foreign keys: explicit typed foreign keys are preferred.
- Timestamps: UTC storage recommended.
- Status fields: constrain to documented values.
- Recommended indexes: source entity FKs, status fields, canonical entity FKs, reconciliation run FKs, and lookup fields used by analysis such as normalized references.

## 9. Configuration conventions

Use a small configuration file such as `config/normalization.json` for explicit, reviewable mappings: UOM aliases, supplier aliases, reference aliases, textual replacements. Configuration is appropriate for explicit mappings. Do not build a database rule engine for the PoC.

## 10. UI conventions

Prioritize these flows:

- **Flow A — Inspect source data:** Overview → Data Explorer → row detail.
- **Flow B — Reconcile one entity:** Data Explorer → entity detail → Find matches → candidate detail → Accept/Reject.
- **Flow C — Reconcile a batch:** Reconciliation → choose entity type → launch → Run Detail → results.
- **Flow D — Demonstrate reuse:** BOM Explorer → select assembly → compare variants → inspect shared/blocking components.

UI acceptance criteria: a reviewer can see source records, normalized values, reconciliation status, launch a batch run, inspect run progress, open one source entity, run single-item assessment, inspect evidence, accept/reject, inspect canonical BOM, inspect reuse analysis, and trace results back to source.

## 11. What to avoid

Do not add, unless useful to explain evidence or make the demo work:

- chat interfaces just because they can be added;
- autonomous agents coordinating other agents;
- a graph database merely because the company talks about knowledge graphs;
- a vector database merely because semantic search is possible;
- complex queues/schedulers for a local PoC;
- a generalized workflow engine;
- elaborate authentication;
- speculative production infrastructure;
- full PLM/ERP integration, real-time event streaming, multi-tenant security, a sophisticated solver, or full change-management/version-control workflow.

---

<!-- refreshed: 2026-09-22 -->
*analysis: 2026-09-22 — Cognyx codebase conventions derived from blueprint docs 01–05 and 10–13; no implemented `src/` tree present yet.*
