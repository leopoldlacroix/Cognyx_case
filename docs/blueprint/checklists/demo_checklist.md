# Demo Checklist

## Before demo

- [ ] Reset database to known synthetic dataset
- [ ] Ingest all source files
- [ ] Confirm normalization complete
- [ ] Confirm some entities are intentionally unresolved
- [ ] Confirm no accepted mapping hides the key demo case

## Demo sequence

1. Open Overview.
2. Show number of variants and BOM lines.
3. Open Data Explorer.
4. Show raw/normalized reference difference.
5. Open Reconciliation Workbench.
6. Launch a component batch.
7. Show run progress/completion.
8. Open the HVAC controller candidate.
9. Show candidate canonical entity.
10. Show engineering-note evidence.
11. Accept the mapping.
12. Open the HVAC BOM across two variants.
13. Show canonical reuse.
14. Open the blocked candidate.
15. Show conflicting technical fact.
16. End on Reuse Analysis.

## What the presenter should emphasize

- The source data is deliberately messy.
- Normalization is deterministic.
- Reconciliation is explicit and traceable.
- AI provides a proposal, not an invisible final decision.
- Canonicalization is downstream of accepted decisions.
- Reuse analysis is explainable from stored evidence.
- The PoC is intentionally smaller than a production deployment.
