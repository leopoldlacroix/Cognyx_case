# 06 — Canonicalization, Technical Facts and Reuse Analysis

## 6.1 Canonicalization trigger

Canonicalization is downstream of human-approved reconciliation.

A source BOM line becomes a canonical BOM relationship only when its required identities are resolved.

## 6.2 Canonicalization process

For each `plm_bom_line`:

1. resolve source variant to canonical `variant`;
2. resolve source assembly through accepted assembly reconciliation;
3. resolve source component through accepted component reconciliation;
4. parse quantity/UOM from normalized values;
5. create/update `bom_relationship`;
6. preserve `source_bom_line_id`.

Unresolved lines remain visible as unresolved source data.

## 6.3 Technical fact extraction

Technical facts may come from:

- ERP fields;
- PLM attributes;
- engineering notes;
- manually entered review information.

Facts should capture provenance.

The PoC should focus on a small meaningful set of attributes, for example:

- voltage;
- communication interface;
- temperature range;
- power rating;
- mounting type;
- enclosure/IP class.

Do not create an exhaustive ontology.

## 6.4 Conflict detection

A conflict exists when materially different values are associated with the same canonical entity/attribute and cannot be trivially normalized.

Example:

```text
Component: HVAC_CTRL_01
Attribute: operating_voltage

ERP: 48 V DC
Engineering note: 24 V DC
```

The analysis layer should surface the conflict instead of arbitrarily selecting one.

## 6.5 Reuse categories

The analysis should distinguish at least:

### Reused
Same canonical component/assembly appears across multiple variants.

### Reuse candidate
Different source/canonical references appear potentially interchangeable or compatible, but the evidence is not yet sufficient for authoritative reuse.

### Blocked reuse
A candidate exists but a material incompatibility or unresolved conflict prevents safe reuse.

### Unresolved
Identity or technical evidence is insufficient.

## 6.6 Reuse logic

The first PoC should use transparent rules.

Possible signals:

- same canonical component across variants;
- compatible required technical attributes;
- no unresolved critical conflicts;
- same or compatible voltage/interface/mounting constraints;
- supplier considerations where relevant;
- lifecycle/status where supplied.

The precise thresholds should be configuration-driven or kept in one analysis module so they can be changed without rewriting UI logic.

## 6.7 Assembly-level analysis

For an assembly, compare the component set across variants.

Suggested derived metrics:

- component overlap ratio;
- exact common components;
- variant-specific components;
- unresolved components;
- conflicting facts;
- potential substitution opportunities.

## 6.8 Example outcome

For `HVAC_CTRL`:

```text
REGIO-STD       CTRL-AIR-01
REGIO-COMFORT   CTRL-HVAC-001
REGIO-NORDIC    CTRL-AIR-01
```

After reconciliation:

```text
CTRL-AIR-01     ─┐
CTRL-HVAC-001   ─┼→ COMPONENT-042
CTRL-AIR-01     ─┘
```

The system can then say the component is reused across these variants because the canonical identity is shared.

A different situation:

```text
CTRL-24V
CTRL-48V
```

may remain a reuse candidate but be blocked because of a voltage conflict.

## 6.9 User-facing explanation

Every reuse result should be explainable in terms of stored data.

Do not display:

> "The AI thinks these are reusable."

Prefer:

> "Potential reuse because the references reconcile to the same canonical component and the stored technical facts agree on supply voltage and interface."

For a blocked case:

> "Reuse blocked because source records disagree on operating voltage (24 V DC vs 48 V DC)."

## 6.10 Definition of Done

- accepted mappings create canonical relationships;
- unresolved lines remain visible;
- technical facts have provenance;
- conflicts can be surfaced;
- reuse results are deterministic and explainable;
- a user can drill from an analysis result back to the source and reconciliation evidence.
