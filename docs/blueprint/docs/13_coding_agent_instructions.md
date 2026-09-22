# 13 — Instructions for the Coding Agent / Developer Handoff

## Mission

Implement the Cognyx-inspired BOM Reuse Explorer PoC strictly from this blueprint.

The objective is to produce a **small, coherent, demonstrable vertical slice**, not to invent a larger product.

## Working rules

### 1. Follow the dependency order

Implement phases in the order defined in `11_execution_roadmap.md`.

Do not implement downstream features against imagined schemas or in-memory shortcuts.

### 2. Read the relevant specification first

Before implementing a phase, read:

- the corresponding phase in `11_execution_roadmap.md`;
- the relevant detailed specification document;
- the data-model document for any tables involved.

### 3. Do not invent hidden state

Prefer deriving state from persisted records.

For example, reconciliation eligibility should be based on reconciliation history/status rather than a second unrelated `processed=true` flag.

### 4. Preserve provenance

Whenever a transformation creates a new representation, retain a path back to its source.

### 5. Keep AI at explicit boundaries

Do not let an LLM determine:

- raw ingestion behavior;
- normalization rules;
- authoritative database state;
- canonical BOM creation after rejection;
- deterministic reuse calculations.

LLM output is evidence/proposal data that must pass application validation.

### 6. Never silently accept a semantic mapping

For the PoC, LLM/semantic recommendations remain `ASSESSED` until an explicit human action changes them to `ACCEPTED`.

### 7. Prefer simple code over abstractions without demonstrated value

A small service/module is better than a generic framework introduced only for future possibilities.

### 8. Keep the UI thin

The UI displays and invokes backend behavior. Business rules belong in backend/domain services.

### 9. Write tests with the business invariants

At minimum, test the invariants in `10_testing_and_validation.md`.

### 10. Make the demo reproducible

A fresh environment should be able to:

1. initialize the DB;
2. load synthetic data;
3. run the pipeline;
4. launch reconciliation;
5. review/accept mappings;
6. view the canonical BOM;
7. view reuse analysis.

## Suggested implementation loop per phase

```text
Read phase specification
        ↓
Identify inputs/outputs
        ↓
Implement smallest coherent version
        ↓
Add unit/integration tests
        ↓
Run tests
        ↓
Verify Definition of Done
        ↓
Only then proceed to next phase
```

## Before changing the schema

Ask whether the requirement can be handled by:

- an existing field;
- existing source/canonical relationships;
- a derived query;
- a small config entry.

Only introduce a new table when there is a durable domain concept that needs independent persistence.

## Before adding an AI feature

Ask:

1. Can deterministic logic solve this reliably?
2. Is there enough evidence in the available data?
3. Does an LLM materially improve semantic interpretation?
4. Can its output be validated?
5. Can a human inspect the evidence?

If deterministic logic is sufficient, use it.

## Reconciliation implementation guidance

Build reconciliation in this order:

1. retrieve eligible source entities;
2. find exact normalized candidates;
3. retrieve structured candidates;
4. return candidate objects;
5. persist candidate evidence;
6. add LLM assessment for genuinely ambiguous cases;
7. add batch runs;
8. add UI acceptance/rejection.

This creates a useful system even if the LLM integration is unavailable during early development.

## UI implementation guidance

Prioritize these flows:

### Flow A — Inspect source data

Overview → Data Explorer → row detail

### Flow B — Reconcile one entity

Data Explorer → entity detail → Find matches → candidate detail → Accept/Reject

### Flow C — Reconcile a batch

Reconciliation → choose entity type → launch → Run Detail → results

### Flow D — Demonstrate reuse

BOM Explorer → select assembly → compare variants → inspect shared/blocking components

## What to avoid

Do not add:

- chat interfaces unless useful to explain evidence;
- autonomous agents coordinating other agents;
- a graph database merely because the company talks about knowledge graphs;
- a vector database merely because semantic search is possible;
- complex queues/schedulers for a local PoC;
- a generalized workflow engine;
- elaborate authentication;
- speculative production infrastructure.

## Handoff expectations

At the end of implementation, the repository should contain:

- source code;
- tests;
- synthetic data;
- configuration;
- run instructions;
- a concise architecture README;
- a documented demo path.

The documentation in this folder is the specification. Implementation decisions that deviate materially from it should be documented with the reason for the deviation.
