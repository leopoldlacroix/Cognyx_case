# Data

This directory contains the synthetic data used for the Alstom x Cognyx FDE case.

See the repository root `README.md` for:
- the full case statement;
- the project interpretation;
- source-system semantics;
- reconciliation/entity-resolution assumptions;
- synthetic dataset scenarios;
- intended demo story.

## Inputs

`data/inputs/` represents immutable fictional client exports:

- `plm/bom_export.csv`
- `plm/assembly_master.csv`
- `plm/variant_configuration.csv`
- `erp/material_master.csv`
- `erp/supplier_master.csv`
- `engineering/technical_notes.csv`

## Ground truth

`data/ground_truth/` is only for development/testing. It represents the hidden canonical model and expected cases used to validate the pipeline. It is not part of the client-facing ingestion path.
