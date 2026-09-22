# 09 — Synthetic Industrial Data Specification

## 9.1 Why synthetic data

The PoC should not depend on proprietary Alstom or other customer data. Synthetic railway-inspired data is enough to demonstrate the workflow.

The data should be deliberately messy in **plausible industrial ways**, not random noise.

## 9.2 Target volume

Recommended initial dataset:

- 5 train variants;
- 8–10 assemblies;
- 40–60 canonical components;
- roughly 150–300 BOM lines;
- 10–20 suppliers;
- 20–40 engineering notes.

Exact counts are less important than having the required edge cases.

## 9.3 Variants

Suggested:

- `REGIO-STD`
- `REGIO-COMFORT`
- `REGIO-NORDIC`
- `REGIO-HIGH-CAPACITY`
- `REGIO-EXPORT`

Include meaningful differences in:

- climate class;
- passenger capacity;
- market;
- voltage system.

## 9.4 Suggested assemblies

- HVAC
- Door Control
- Brake Control
- Traction Control
- Passenger Information
- CCTV
- Auxiliary Power
- Driver Cab
- Battery System

## 9.5 Required messy-data patterns

### Reference aliases

Examples:

```text
CTRL-AIR-01
CTRL-AIR01
CTRL-HVAC-001
MAT-10001
```

At least some of these should resolve to known canonical entities; some should remain ambiguous.

### Supplier aliases

Examples:

```text
Siemens
SIEMENS MOBILITY
Siemens Mobility GmbH
SIEMENS MOBILITY SAS
```

Some variations are formatting-only; others should remain distinct when the legal/vendor identity matters.

### UOM variants

```text
pcs
pc
piece
EA
units
```

### Voltage text variants

```text
24V
24 V
24 VDC
24 volts DC
```

### Description variation

```text
HVAC controller
HVAC CTRL unit
Air conditioning control module
Cabin HVAC controller
```

### Missing fields

Include rows with:

- missing supplier;
- missing description;
- missing revision;
- missing UOM.

## 9.6 Required engineering notes

At least one note should explicitly state an equivalence.

Example meaning:

> `CTRL-HVAC-001` is equivalent to `CTRL-AIR-01`. Same 24 V DC supply and CAN interface.

At least one note should contain a conflicting specification.

Example meaning:

> Legacy record lists 48 V DC, but the current engineering test sheet lists 24 V DC.

At least one note should be deliberately ambiguous.

Example meaning:

> Compatible with the northern-climate configuration; confirm enclosure rating before reuse.

## 9.7 Required reconciliation cases

The dataset should include:

1. exact duplicate reference;
2. formatting-only alias;
3. semantic alias with strong evidence;
4. close but not identical component;
5. same description but conflicting electrical specification;
6. supplier alias;
7. component with no plausible match;
8. assembly reused across several variants;
9. assembly with one variant-specific component;
10. technically compatible-looking candidate blocked by one critical fact.

## 9.8 Demo scenario

The dataset must support at least one compelling narrative:

### Step 1
Show that two variants contain apparently different HVAC controller references.

### Step 2
Open reconciliation and show the candidate mapping.

### Step 3
Show the evidence from engineering notes and structured attributes.

### Step 4
Accept the mapping.

### Step 5
Open the HVAC assembly and show that the canonical component is now shared.

### Step 6
Show a second candidate where reuse is blocked by conflicting voltage or another technical attribute.

This demonstrates both successful automation and disciplined refusal to overreach.
