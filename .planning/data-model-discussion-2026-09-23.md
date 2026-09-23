# Data Model Design Discussion (2026-09-23)

## Context

Discussion with user about the data model structure, junction tables, and implications for Phase 2 planning.

**Participants:** User (Leopold), AI assistant  
**Date:** 2026-09-23  
**Related:** Phase 1 completion, Phase 2 planning

---

## Key User Insights

### 1. `plm_assembly` Conflates Two Concerns

The raw `plm_assembly` table has `variant_ref_raw` as an inline column, which mixes:
- **Assembly identity** (what is this assembly?)
- **Variant usage** (which variant uses it?)

The user identified this as confusing and proposed a junction table to separate these concerns.

### 2. CRITICAL PRINCIPLE: Raw Tables Are Immutable

> "All this data modeling stuff should be something to expect from the target tables, not the raw tables that the client (Forvia) communicates us."

**Confirmed understanding:**
- **Raw tables** (`plm_assembly`, `plm_bom_line`, etc.): Preserve client export format exactly — immutable. This is "what Forvia sent us."
- **Source entity tables** (`source_assembly`, `source_component`, etc.): Deduplication layer. This is where junction tables COULD be added for clarity.
- **Canonical tables** (`assembly`, `component`, `variant`, etc.): Clean domain model. This is where proper relationships belong.

### 3. Supplier Placement Question (Open)

User raised: should supplier be on the **component** (master data — "who makes this part") or on the **BOM line** (sourcing decision — "who are we buying from for this build")?

Both patterns exist in the data:
- `erp_material.supplier_id` — supplier as component property
- `plm_bom_line.supplier_name` — supplier as BOM line attribute

Needs business context to decide. For PoC, keep as-is but flag as design question.

---

## Junction Table Opportunities

Discussed potential junction tables to clarify table responsibilities. All are for **source entity or canonical layers**, NOT raw tables.

| Junction Table Idea | Priority | Layer | Rationale |
|---------------------|----------|-------|-----------|
| `source_assembly_variant` | HIGH | Source entity | Separates assembly identity from variant usage. Resolves confusion about `variant_ref` being inline in `plm_assembly`. Raw table keeps `variant_ref_raw` as-is. |
| `note_entity_reference` | LOW | Source entity | Polymorphic association cleanup for `engineering_note`. Currently uses `object_reference_raw` + `object_type`, but explicit junction clarifies entity linking. |
| Supplier placement (component vs BOM line) | QUESTION | Discussion | Open question — needs business context. See note above. |
| `material_supplier` junction | VERY LOW | Future | Only if multi-supplier support needed. Not in current dataset. |

---

## Phase 2 Impact Assessment

### What Stays Unchanged
- **Raw tables**: NO CHANGE. These are immutable client exports. Preserve exactly as received.

### Where Junction Tables Could Be Added (Optional)
- **Source entity tables**: Could add `source_assembly_variant` if queries need it. But NOT blocking for Phase 2.
- **Canonical tables**: Already well-designed. `bom_relationship` is a proper junction table (variant → assembly → component).

### Phase 2 Focus (Priority Order)
1. Entity resolution (linking source entities to canonical entities)
2. Reconciliation records (pending/accepted/rejected mappings)
3. Canonical model construction
4. Junction table refinements (optional enhancements, not prerequisites)

### Recommendation
Don't let junction table redesign block Phase 2. The current source entity design (deduplication by `source_system + source_reference`) is sufficient to start. Add junction tables when the query need becomes clear.

---

## Notes for Phase 2 Planner

When planning Phase 2, reference these points:

1. **User understands the raw-vs-target distinction clearly** — raw tables preserve client format, normalization happens downstream
2. **`source_assembly_variant` is a HIGH priority refinement** but not a Phase 2 blocker
3. **Supplier placement is an open design question** — flag for business context decision
4. **Don't force schema changes onto raw tables** — they are immutable client exports
5. **Canonical layer is already well-designed** — focus Phase 2 on reconciliation and entity resolution

---

## Related Files

- `docs/blueprint/docs/03_data_model.md` — Complete data model specification
- `.planning/phases/01-data-foundation-ingest-normalize/01-CONTEXT.md` — Phase 1 design decisions
- `.planning/REQUIREMENTS.md` — Normalization requirements (NORM-01 through NORM-06)
