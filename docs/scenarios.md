# Alstom x Cognyx — Synthetic Pilot Dataset Scenarios

This dataset is intentionally synthetic and contains controlled inconsistencies representative of industrial PLM/ERP exports.

## Core scenarios

| ID | Scenario | Where it appears | What the future product should demonstrate |
|---|---|---|---|
| A | Obvious reuse | HVAC Controller, Brake, PIS | Same canonical component/assembly appears across several variants |
| B | Hidden cross-source reuse | CTRL-AIR-01 / CTRL-AIR01 / CTRL-HVAC-001 / MAT-10001 | Several identifiers from PLM, ERP and notes refer to the same entity |
| C | Typo/alias reconciliation | CTRL-AIR-O1, LIGHT-DRIVER-01, supplier aliases | Candidate identity match with visible provenance |
| D | Similar but not identical | Standard Door Controller vs Export Door Controller | Functional similarity must not be mistaken for identity |
| E | Variant-specific engineering difference | Nordic HVAC/Brake/Cab/Lighting | Intentional differences must not be flagged as duplicate data |
| F | Potential reuse | Passenger Counting Camera vs Rugged Camera | Similar architecture, but qualification differences create a reviewable candidate |
| G | Conflicting source/specification | HVAC Controller, PIS Display | Conflicting evidence must be surfaced, not silently normalized |
| H | Multilingual evidence | French/English/German labels and notes | Language normalization without losing original wording |
| I | Data-quality issue | units, duplicate BOM lines, invalid quantity | Validation panel should catch issues independently of identity matching |
| J | Lifecycle mismatch | Export passenger counting module | ERP/PLM status should be visible and treated as a separate issue |

## Important modeling distinction

The dataset contains three conceptually different relationships:

1. **Identity / alias**: two source identifiers refer to the same canonical entity.
2. **Functional similarity / potential substitution**: two different entities may be interchangeable in some context.
3. **Variant-specific specialization**: a variant intentionally uses a specialized component.

These must not be collapsed into a single "match" concept.

## Intended demo narrative

1. Load the five train variants and their BOMs.
2. Show that raw references are inconsistent across PLM, ERP and engineering notes.
3. Propose candidate entity resolutions with evidence and confidence.
4. Allow a human to accept/reject/redirect the reconciliation.
5. Recompute cross-variant reuse from the accepted canonical model.
6. Surface technical conflicts and variant-specific exceptions.
