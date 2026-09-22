# Coder Implementation Checklist

## Foundation

- [ ] Repository boots locally
- [ ] Configuration is centralized
- [ ] Database initializes from empty state
- [ ] Backend health check works
- [ ] Worker entry point exists
- [ ] UI shell works

## Data

- [ ] All schema tables exist
- [ ] PK/FK constraints work
- [ ] Required indexes exist
- [ ] Synthetic files are present
- [ ] Source-file provenance is stored

## Ingestion

- [ ] CSV schema validation works
- [ ] Raw values are preserved
- [ ] Duplicate-file import is handled
- [ ] Invalid rows are surfaced
- [ ] Source entities are deduplicated

## Normalization

- [ ] Reference normalization works
- [ ] UOM normalization works
- [ ] Supplier aliases work
- [ ] Raw values remain visible
- [ ] Unknown values are not guessed

## Reconciliation

- [ ] Batch runs are explicit
- [ ] Single-item run works
- [ ] Eligibility is queryable
- [ ] Exact matches avoid LLM calls where possible
- [ ] Candidate records include rationale
- [ ] Candidate records include evidence
- [ ] Confidence is validated
- [ ] Worker failures are visible
- [ ] Three reconciliation tables are used

## Human review

- [ ] Accept works
- [ ] Reject works
- [ ] Accepted mapping becomes authoritative
- [ ] Rejected mappings do not become canonical
- [ ] History remains traceable

## Canonicalization

- [ ] Accepted component mappings can be resolved
- [ ] Accepted assembly mappings can be resolved
- [ ] Canonical BOM is traceable to source BOM lines
- [ ] Unresolved lines stay visible

## Analysis

- [ ] Technical facts store provenance
- [ ] Conflicting facts are detectable
- [ ] Reused assemblies are detectable
- [ ] Reuse candidates are detectable
- [ ] Blockers are explainable

## UI

- [ ] Overview works
- [ ] Data Explorer works
- [ ] Reconciliation Workbench works
- [ ] Run Detail works
- [ ] BOM Explorer works
- [ ] Reuse Analysis works
- [ ] Data Quality works
- [ ] All major actions are possible without DB console access

## Demo

- [ ] Demo dataset loads from fresh state
- [ ] HVAC alias scenario works
- [ ] Human acceptance changes canonical BOM
- [ ] Cross-variant reuse is visible
- [ ] Conflict/blocker scenario is visible
- [ ] Source evidence is one or two clicks away
