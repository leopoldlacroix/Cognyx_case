# 10 — Testing and Validation Strategy

## 10.1 Testing layers

### Unit tests

Cover deterministic logic:

- reference normalization;
- UOM normalization;
- numeric parsing;
- candidate scoring helpers;
- status transitions;
- reuse rules;
- conflict detection.

### Integration tests

Cover:

- file → source tables;
- source entity extraction;
- reconciliation persistence;
- accept/reject transitions;
- canonicalization;
- analysis queries.

### End-to-end test

Run the complete synthetic scenario from source files to reuse analysis.

## 10.2 Determinism requirements

Deterministic transformations must produce the same result for the same input/configuration.

LLM calls do not need to be deterministic, but their outputs must be validated against a schema and should be recorded for traceability.

## 10.3 Important invariants

1. Raw source values are never overwritten by normalization.
2. Reconciliation never silently creates an accepted mapping.
3. Rejected mappings cannot create canonical BOM relationships.
4. Unresolved source rows remain visible.
5. Canonical BOM rows must be traceable to source BOM lines.
6. Analysis results must be derivable from persisted data.
7. A failed reconciliation run must not invalidate previously accepted mappings.

## 10.4 Data-quality test cases

Verify that:

- duplicate references become one source entity;
- raw aliases remain inspectable;
- unknown UOMs do not crash processing;
- missing descriptions are retained;
- conflicting technical facts are surfaced.

## 10.5 Reconciliation test cases

Verify:

- exact match shortcut avoids unnecessary LLM usage;
- ambiguous candidate returns `UNCERTAIN` where evidence is insufficient;
- malformed LLM result is rejected/retried rather than persisted as trusted data;
- accepted candidate becomes authoritative;
- rejected candidate remains traceable.

## 10.6 UI acceptance criteria

A reviewer can:

- see source records;
- see normalized values;
- see reconciliation status;
- launch a batch run;
- inspect run progress;
- open one source entity;
- run single-item assessment;
- inspect evidence;
- accept/reject;
- inspect canonical BOM;
- inspect reuse analysis;
- trace results back to source.

## 10.7 Demo validation script

The end-to-end demo should take the following path:

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

## 10.8 Performance expectations

The PoC is not judged on massive throughput.

It should, however, avoid obviously wasteful behavior such as sending every row independently to an LLM when exact normalized matching can resolve it.

## 10.9 Acceptance gates

Do not polish UI before:

- ingestion works;
- normalization works;
- source entities work;
- reconciliation persistence works;
- accepted mapping can create canonical BOM;
- at least one reuse result works end-to-end.
