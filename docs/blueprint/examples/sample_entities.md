# Sample Records / Expected Reconciliation Scenarios

## Example 1 — Formatting-only component alias

Source:

```text
source_component
source_reference: CTRL-AIR01
normalized_reference: CTRL-AIR-01
description: HVAC controller
```

Canonical candidate:

```text
component
id: 42
name: HVAC Controller
```

Expected behavior:

- exact normalized match should be generated;
- high confidence;
- evidence includes normalized-reference equality;
- still remains `ASSESSED` until accepted.

## Example 2 — Semantic component alias

Source:

```text
source_reference: CTRL-HVAC-001
description: Air conditioning control module
```

Candidate:

```text
component 42 — HVAC Controller
```

Evidence:

- engineering note says equivalent;
- same 24 V DC supply;
- same CAN interface.

Expected behavior:

- candidate proposed;
- rationale and evidence shown;
- human acceptance required.

## Example 3 — Blocked reuse candidate

Source A:

```text
component: CTRL-24V
operating_voltage: 24 V DC
```

Source B:

```text
component: CTRL-48V
operating_voltage: 48 V DC
```

Expected behavior:

- do not equate identity solely on similar descriptions;
- may surface as a reuse candidate;
- reuse analysis marks a voltage mismatch/blocker;
- UI can point to both facts.

## Example 4 — Supplier alias

```text
SIEMENS
Siemens Mobility GmbH
SIEMENS MOBILITY
```

Expected behavior:

- deterministic supplier-name normalization;
- supplier reconciliation can propose a canonical supplier;
- legal/vendor distinctions should remain configurable in production.

## Example 5 — Ambiguous candidate

```text
Source: HVAC controller, 24 V DC, CAN
Candidate A: HVAC controller, 24 V DC, CAN
Candidate B: Door controller, 24 V DC, CAN
```

Expected behavior:

- Candidate A should have stronger structured evidence;
- candidate B can remain as a lower-ranked candidate;
- no automatic acceptance.
