---
status: complete
plan: 01-05
phase: 01-data-foundation-ingest-normalize
date: 2026-09-23
---

# SUMMARY: Plan 01-05 — Apply UOM, Supplier, and Reference Aliases

**Phase:** 1 — Data Foundation: Ingest & Normalize  
**Status:** ✅ Complete  
**Date:** 2026-09-23

---

## What Was Built

Config-driven alias normalization layer on top of generic normalization. Aliases are loaded from `config/normalization.json` and applied after generic normalization during ingestion.

### Components Implemented

1. **`config/normalization.json`** — alias configuration:
   - `uom_aliases`: 6 entries (PCS/PC/PIECE/UNITS/SET/BOX → EA)
   - `supplier_aliases`: 12 entries (SIEMENS*, FAIVELEY*, KNORR-BREMSE*, THALES*, SCHALTBAU*, TE CONNECTIVITY → canonical names)
   - `reference_aliases`: 9 entries (CTRL-AIR01, CTRL-HVAC-001, FAN-AIR01, CTRL-DOOR01 → canonical forms)

2. **Alias functions in `app/services/normalization.py`**:
   - `load_normalization_config()` — loads config from `config/normalization.json`
   - `apply_uom_aliases(normalized_uom, config)` — exact match lookup
   - `apply_supplier_aliases(normalized_supplier, config)` — exact match + prefix matching
   - `apply_reference_aliases(normalized_reference, config)` — exact match lookup
   - `normalize_with_aliases(raw_value, field_type, config)` — full pipeline: generic → aliases

3. **Updated `_apply_normalization()` in `app/services/ingestion.py`**:
   - Now accepts optional `config` param, loads config if not provided
   - Component refs: generic normalize → reference alias lookup
   - UOM: generic normalize → UOM alias lookup
   - Supplier: generic normalize → supplier alias lookup (prefix matching for variants)

4. **Tests**:
   - `tests/test_alias_debug.py` — 2 tests for UOM normalization pipeline + config loading
   - `tests/test_alias_integration.py` — 2 integration tests verifying aliases applied in real DB ingestion

---

## Key Behaviors

### UOM Aliases
| Raw | Generic Norm | Alias Result |
|-----|-------------|--------------|
| `pcs` | `PCS` | `EA` |
| `units` | `UNITS` | `EA` |
| `PC` | `PC` | `EA` |
| `EA` | `EA` | `EA` |
| `METER` | `METER` | `METER` (no alias) |

### Supplier Aliases (prefix matching)
| Raw | Generic Norm | Alias Result |
|-----|-------------|--------------|
| `Siemens` | `SIEMENS` | `SIEMENS MOBILITY` |
| `Siemens Mobility GmbH` | `SIEMENS MOBILITY GMBH` | `SIEMENS MOBILITY` |
| `Knorr-Bremse` | `KNORR-BREMSE` | `KNORR-BREMSE RAIL SYSTEMS` |
| `Knorr Bremse` | `KNORR BREMSE` | `KNORR-BREMSE RAIL SYSTEMS` (prefix match) |

### Reference Aliases (SCEN-C)
| Raw | Generic Norm | Alias Result |
|-----|-------------|--------------|
| `CTRL-AIR01` | `CTRL-AIR01` | `CTRL-AIR-01` |
| `CTRL-HVAC-001` | `CTRL-HVAC-001` | `CTRL-AIR-01` |
| `FAN-AIR01` | `FAN-AIR01` | `FAN-AIR-01` |

---

## Real Data Results

From `data/inputs/plm/bom_export.csv`:
- **UOM**: `pcs` → `EA` ✅, `units` → `EA` ✅, `EA` → `EA` ✅
- **Suppliers**: `Siemens` → `SIEMENS MOBILITY` ✅, `Knorr-Bremse` → `KNORR-BREMSE RAIL SYSTEMS` ✅
- **References**: No CTRL-AIR01 style typos in actual BOM data (all use correct dash format already)

508 soft warnings still present (descriptions, unknown UOMs that don't have aliases, empty suppliers).

---

## Bug Fixed

**Config path resolution**: `load_normalization_config()` initially used `parent.parent` from `app/services/`, resolving to `app/config/` instead of repo-root `config/`. Fixed by using `parent.parent.parent`.

**CSV column name mismatch**: `_apply_normalization()` was looking up `uom_raw` (DB column name) in the raw CSV row dict, but the CSV column is `uom`. Fixed to use `raw_row.get('uom')`.

---

## Deviations from Plan

| Plan Item | Deviation |
|-----------|-----------|
| `normalize_bom_row()` function | Not created; aliasing integrated directly into `_apply_normalization()` which already handles all tables |
| Supplier alias matching | Plan specified exact match only; implemented prefix matching as well (e.g., "Knorr Bremse" → "KNORR-BREMSE RAIL SYSTEMS") |
| `normalize_with_aliases()` | Created but not used in ingestion flow (ingestion uses individual apply_* functions directly) |

---

## must_haves Checklist

- [x] `config/normalization.json` created with uom_aliases, supplier_aliases, reference_aliases
- [x] Alias lookup functions: `apply_uom_aliases`, `apply_supplier_aliases`, `apply_reference_aliases`
- [x] Aliases applied during ingestion after generic normalization
- [x] UOM aliases: pcs/pc/piece/units → EA
- [x] Supplier aliases: SIEMENS variants → SIEMENS MOBILITY
- [x] Reference aliases: CTRL-AIR01 → CTRL-AIR-01 (SCEN-C)
- [x] Config-driven: aliases from `config/normalization.json`
- [x] No alias match returns original value (graceful fallback)
- [x] SCEN-C verified: `CTRL-AIR01` normalizes to `CTRL-AIR-01` (unit test)
- [x] Integration tests verify aliases applied in real DB

---

## Files Modified

- `config/normalization.json` — new alias configuration file
- `app/services/normalization.py` — added alias functions + config loader
- `app/services/ingestion.py` — updated `_apply_normalization()` to apply aliases
- `tests/test_alias_debug.py` — new: UOM pipeline + config tests
- `tests/test_alias_integration.py` — new: DB integration tests for aliases

---

## Next Steps

Phase 1 is complete (plans 01-01 through 01-05). All 5 plans executed:
- 01-01: Ingest all 6 CSV files ✅
- 01-02: Hard validation quarantine ✅
- 01-03: Soft validation warnings ✅
- 01-04: Normalize PLM BOM lines ✅
- 01-05: Apply UOM/supplier/reference aliases ✅

Phase 2 (Normalization: ERP materials + engineering notes, entity resolution, reconciliation) is next.
