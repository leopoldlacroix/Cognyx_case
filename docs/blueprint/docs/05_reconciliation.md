# 05 — Reconciliation Engine Specification

## 5.1 Objective

For each source entity, identify likely canonical matches without silently deciding on behalf of the engineer.

The engine should work for:

- components;
- assemblies;
- suppliers.

The implementation is intentionally split into three persistence tables:

- `component_reconciliation`
- `assembly_reconciliation`
- `supplier_reconciliation`

## 5.2 Execution model

### Explicit batch launch

A user starts a batch run from a reconciliation screen.

Example actions:

- Reconcile all unassessed components
- Reconcile all unassessed assemblies
- Reconcile all unassessed suppliers

The worker should process only eligible records.

### Single-entity launch

A user opens one entity and clicks `Find matches`.

This is useful when investigating a specific issue.

## 5.3 Eligibility rule

A source entity is eligible for batch processing when it has no authoritative accepted mapping and does not already have a current successful assessment that the product considers complete.

Do not use a simple permanent `processed=true` boolean unless the product needs it. The reconciliation records and run history already provide richer state.

## 5.4 Candidate generation pipeline

Use a layered strategy from cheap/deterministic to expensive/semantic:

### Stage A — Exact normalized match

If normalized source reference equals a canonical reference/known alias, generate a high-confidence candidate.

### Stage B — Structured similarity

Compare fields such as:

- normalized name/description;
- category;
- supplier;
- relevant identifiers;
- selected technical facts.

### Stage C — Semantic similarity

Use embedding or text-similarity only if useful. It is optional for the PoC.

### Stage D — LLM assessment

Use the LLM when the candidate set remains ambiguous or when engineering notes provide semantic evidence.

The LLM should evaluate a structured prompt and return structured data, not free-form prose only.

## 5.5 Candidate object contract

Each candidate should contain conceptually:

- candidate canonical entity ID;
- match confidence 0–1;
- recommendation: `MATCH`, `NO_MATCH`, `UNCERTAIN`;
- method;
- rationale;
- evidence list;
- conflicts detected;
- fields compared.

Example evidence items:

```text
- same normalized reference
- same 24 V DC supply
- same CAN interface
- engineering note says equivalent
```

## 5.6 LLM boundary

The LLM receives only the information necessary to assess the candidate.

Recommended input structure:

```text
Source entity
Candidate entities
Relevant structured attributes
Relevant engineering notes
Explicit task definition
Required response schema
```

Do not send the entire database blindly.

## 5.7 LLM rules

Prompt must explicitly distinguish:

- identity from interchangeability;
- evidence from inference;
- missing information from contradiction.

The model must be allowed to say:

`UNCERTAIN`

when evidence is insufficient.

The model must not invent technical facts.

## 5.8 Confidence semantics

Confidence is not a probability that the entity is objectively identical. It is the engine's confidence in the proposed reconciliation based on the provided evidence.

Recommended presentation bands for UI only:

- `0.90–1.00`: strong evidence
- `0.75–0.89`: likely match
- `0.50–0.74`: uncertain
- `<0.50`: weak candidate

These are interface thresholds, not engineering certification thresholds.

## 5.9 Persisting results

For each assessed source entity:

1. create reconciliation candidate/assessment record(s);
2. persist method and confidence;
3. persist rationale;
4. persist evidence JSON;
5. reference the current `reconciliation_run` when running in batch mode;
6. leave status at `ASSESSED` until a human decision or deterministic auto-accept rule is explicitly authorized.

For the demonstration, do not auto-accept LLM results.

## 5.10 Human decisions

### Accept

The selected candidate becomes authoritative for that source entity.

### Reject

The selected candidate is explicitly rejected.

### No match

A reviewer can reject candidates and leave the source entity unresolved. This is preferable to forcing a wrong canonical mapping.

## 5.11 Reassessment

A future run may generate better candidates. Historical assessments should not simply disappear.

For a PoC, keep previous reconciliation rows and use the latest accepted decision as the effective mapping.

## 5.12 Failure handling

Worker failures should be recorded at run level and should not corrupt accepted mappings.

Examples:

- LLM timeout;
- malformed LLM response;
- candidate lookup failure;
- invalid structured data.

The worker should mark the item/run as failed or partial and continue where practical.

## 5.13 Performance expectation

The objective is not benchmark performance. The PoC should demonstrate that cheap deterministic matching prevents unnecessary LLM calls.

The run summary should therefore optionally display:

- total entities;
- exact matches resolved without LLM;
- semantic/LLM assessments;
- review-required count;
- error count.

## 5.14 Definition of Done

A coder is done when:

- batch reconciliation is explicitly launchable;
- only eligible entities are processed;
- single-item reconciliation works;
- candidate results are persisted;
- evidence/rationale are inspectable;
- LLM results are structured and validated;
- human acceptance/rejection changes authority state;
- source data is never mutated by reconciliation;
- failed items are visible.
