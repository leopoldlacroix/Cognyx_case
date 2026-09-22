---
last_mapped_commit: 92a308bb4f3975a737c94509b667c651a00285ba
last_mapped_at: 2026-09-22
---
# Cognyx — Testing Conventions

**Analysis Date:** 2026-09-22
**Scope:** full repository (Cognyx, Alstom x Cognyx FDE Case)
**Source of truth:** this document + `.planning/codebase/CONVENTIONS.md` + `docs/blueprint/docs/10_testing_and_validation.md` + `docs/blueprint/docs/13_coding_agent_instructions.md`.

---

Like `CONVENTIONS.md`, this document is written against the blueprint rather than an existing test suite. There is no `tests/` tree yet. The conventions below define the testing shape the implementation must adopt so that future tests are consistent, business-driven, and traceable.

---

## 1. Testing philosophy

Test the business invariants from `docs/blueprint/docs/10_testing_and_validation.md`, not just internal helper functions. At minimum, tests must cover the invariants listed there, plus the layered behaviors described in the blueprint.

Write tests with the business invariants. A fresh environment should be able to:

1. initialize the DB;
2. load synthetic data;
3. run the pipeline;
4. launch reconciliation;
5. review/accept mappings;
6. view the canonical BOM;
7. view reuse analysis.

A small service/module is better than a generic framework introduced only for future possibilities. Apply the same principle to the test suite: keep it small, coherent, and demonstrable rather than over-engineered.

## 2. Test layers

### Unit tests

Cover deterministic logic:

- reference normalization;
- UOM normalization;
- numeric parsing;
- candidate scoring helpers;
- status transitions;
- reuse rules;
- conflict detection.

Unit tests should be deterministic and fast. They should not depend on LLM availability.

### Integration tests

Cover:

- file → source tables;
- source entity extraction;
- reconciliation persistence;
- accept/reject transitions;
- canonicalization;
- analysis queries.

### End-to-end test

Run the complete synthetic scenario from source files to reuse analysis. The demo validation script in section 10.7 of the blueprint is the shape to validate: start from Overview, inspect messy references and normalized values, launch component batch reconciliation, explain evidence and confidence for a concrete HVAC candidate, accept the mapping, show the shared canonical component across two variants, show a blocked reuse candidate with the conflicting technical fact, and finish on the Reuse Analysis page.

## 3. Determinism requirements

Deterministic transformations must produce the same result for the same input/configuration.

LLM calls do not need to be deterministic, but their outputs must be validated against a schema and should be recorded for traceability.

Normalize tests around this split:

- pure/normalized/reference/UOM/numeric/status/reuse/conflict logic → strict determinism tests;
- reconciliation/LLM-assisted assessment → schema + provenance + outcome tests, not exact-output snapshot tests on free-form prose.

## 4. Test data and fixtures

### Synthetic data is the fixture

The synthetic dataset in `data/inputs/` is the test fixture. Use it for integration and end-to-end tests. The ground truth in `data/ground_truth/` exists for pipeline validation only and is **not** client-facing.

Do not edit `data/inputs/`. Do not expose `data/ground_truth/` in client/demo output.

### Fixture expectations

Tests should be able to answer, at the end of ingestion/normalization:

- how many files were loaded?
- how many rows per file?
- how many source components/assemblies/suppliers exist?
- how many have never been assessed?
- how many normalization warnings exist?
- which raw rows refer to which source entities?

### Idempotency

Re-ingesting the exact same file should not unexpectedly duplicate the data. Tests should verify that identical file hash may be treated as already ingested, and that a changed file is a new source-file version.

## 5. What tests must cover

### Data-quality test cases

Verify that:

- duplicate references become one source entity;
- raw aliases remain inspectable;
- unknown UOMs do not crash processing;
- missing descriptions are retained;
- conflicting technical facts are surfaced.

### Reconciliation test cases

Verify that:

- exact match shortcut avoids unnecessary LLM usage;
- ambiguous candidate returns `UNCERTAIN` where evidence is insufficient;
- malformed LLM result is rejected/retried rather than persisted as trusted data;
- accepted candidate becomes authoritative;
- rejected candidate remains traceable.

### Important invariants to assert

1. Raw source values are never overwritten by normalization.
2. Reconciliation never silently creates an accepted mapping.
3. Rejected mappings cannot create canonical BOM relationships.
4. Unresolved source rows remain visible.
5. Canonical BOM rows must be traceable to source BOM lines.
7. A failed reconciliation run must not invalidate previously accepted mappings.

Rule 6 from the blueprint is implicit: analysis results must be derivable from persisted data.

## 6. Mocking and external boundaries

### Where mocking is appropriate

- LLM calls: mock or replace with a deterministic test harness for unit/integration tests, but also keep at least one path that validates the real structured-output contract.
- File I/O for unit tests on normalization: use small inline strings rather than real CSV files when testing pure normalization logic.
- Dates/timestamps: control them in tests rather than depending on wall clock, especially for ordering and run-state assertions.

### Where mocking is not appropriate

- Ingestion of synthetic CSVs in integration/e2e tests: use the real fixture files.
- Canonicalization from accepted mappings: test against persisted state, not mocked domain objects.
- Reuse/conflict analysis: test against persisted canonical data and sourced technical facts.

### LLM boundary in tests

The LLM receives only the information necessary to assess the candidate. Tests should reflect the same boundary: do not test by sending the entire database blindly. Structured output should be validated against a schema; malformed results should be rejected/retried rather than persisted as trusted data.

## 7. Coverage expectations

Coverage is not the primary goal; invariant coverage is. That said, the test suite should meaningfully cover:

- ingestion and normalization of all six synthetic file types;
- source-entity deduplication;
- reconciliation eligibility and persistence;
- accept/reject state transitions;
- canonical BOM creation only from accepted mappings;
- analysis queries for reuse, blockers, and conflicting technical facts;
- at least one end-to-end synthetic scenario.

Acceptance gates from the blueprint: do not polish UI before ingestion works, normalization works, source entities work, reconciliation persistence works, accepted mapping can create canonical BOM, and at least one reuse result works end-to-end. The test suite should be able to gate those same concerns.

## 8. Test organization and boundaries

### Org

- Unit tests under `tests/unit/` by layer where practical.
- Integration tests under `tests/integration/`.
- End-to-end tests under `tests/e2e/`.

### Scope discipline for tests

Do not test UI styling before the backend behaviors above are covered. Do not test speculative production infrastructure. Keep the demo path reproducible and testable.

### Definition of Done per phase

For each implementation phase, the loop is:

- read phase specification, inputs/outputs;
- implement smallest coherent version;
- add unit/integration tests;
- run tests;
- verify Definition of Done;
- only then proceed to the next phase.

## 9. Acceptance test script (demo path)

A reviewer should be able to run or walk the following and have it pass:

1. Start from Overview.
2. Open Data Explorer and select components.
3. Show messy references and normalized values.
4. Open Reconciliation Workbench.
5. Launch component batch reconciliation.
6. Open a concrete HVAC candidate.
7. Explain evidence and confidence.
8. Accept the mapping.
9. Open BOM Explorer for two variants.
10. Show the shared canonical component.
11. Open a blocked reuse candidate.
12. Show the conflicting technical fact.
13. Finish on the Reuse Analysis page.

Tests should validate that this path is reproducible and that trace exists from result back to source.

## 10. Suggested test naming and structure

- Name tests after the business behavior or invariant, e.g. `test_normalization_preserves_raw_value`, `test_rejected_mapping_cannot_create_canonical_bom`, `test_ambiguous_candidate_is_uncertain`, `test_end_to_end_reuse_across_two_variants`.
- Group assertions by layer: ingestion, normalization, source entities, reconciliation, canonicalization, analysis.
- Keep test data explicit and small enough to read in one sitting.

---

<!-- refreshed: 2026-09-22 -->
*analysis: 2026-09-22 — Cognyx testing conventions derived from blueprint docs 10 and 13; no implemented `tests/` tree present yet.*
