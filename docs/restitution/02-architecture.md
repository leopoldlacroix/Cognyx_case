# Architecture and what each step does

The pilot is one Python package, one SQLite file, and six generated HTML pages. There is no web framework. `python -m app.backend.cli serve` is a small local server so the Proposals buttons can write a decision and regenerate the pages.

Raw spreadsheets in `data/inputs/` are never edited. Output goes to `data/processed/` (`cognyx.db` and the HTML). `data/ground_truth/` is for tests only and is not rendered.

## How the pieces connect

```text
data/inputs/*.csv
        │
        ▼
ingestion + validation          app/services/ingestion.py
        │                       app/services/validation.py
        ▼
normalization                   app/services/normalization.py
        │                       config/normalization.json
        ▼
source extraction               app/services/extraction.py
        │
        ▼
reconciliation (proposals)      app/services/reconciliation.py
        │
        ▼
human decision                  app/services/review.py
        │                       app/backend/serve.py  (buttons)
        ▼
canonical model                 app/services/canonicalization.py
        │
        ├─► reuse, candidates, compare     app/services/analysis.py
        ├─► blockers, data quality         app/services/quality.py
        └─► HTML pages                     app/services/html_pages.py
                                           app/services/report.py
```

`prepare_database` in `app/services/report.py` runs ingest, ERP and note normalization, extraction, and reconciliation. `write_site` then rebuilds the canonical model and writes the six HTML files. `cli report` does both. `cli serve` rewrites the pages and, on each Accept / Reject / Redirect, calls `decide_reconciliation` and `write_site` again. It does not re-ingest, so a decision is not wiped by the next click.

SQLite tables, in the order they fill:

| Table | What lands there |
|---|---|
| `source_file` | One row per spreadsheet: system, file name, hash, time |
| `plm_bom_line`, `plm_assembly`, `plm_variant`, `erp_material`, `erp_supplier`, `engineering_note` | Valid source rows. Raw columns and normalized columns side by side |
| `quarantine` | Rows refused by hard validation, with the original payload and the reason |
| `warnings` | Soft problems. The row is still in the source table |
| `source_component`, `source_assembly`, `source_supplier`, `source_assembly_variant` | One entity per source system + source reference |
| `component_reconciliation`, `assembly_reconciliation`, `supplier_reconciliation` | Proposals: status, method, confidence, rationale, evidence JSON |
| `component`, `assembly`, `variant`, `supplier` | Official entities |
| `bom_relationship` | Official parts-list lines the reports may trust |
| `technical_fact` | Voltages and lifecycle values, including conflicts |

## 1. Ingestion

`ingest_all_files` reads the six CSVs under `data/inputs/` (`plm/`, `erp/`, `engineering/`).

For each file:

1. Hash the file and register it in `source_file`.
2. If that file was already loaded into the target table, stop. The load is idempotent.
3. Read the CSV with the header as row 1. The first data row is source row 2.
4. Hard-validate the row. On failure, insert the raw dict into `quarantine` with `source_file_id`, `source_row`, and the reason, then continue with the next row.
5. Soft-check the row. Each warning goes to `warnings`. The row continues.
6. Normalize the fields (next section) and insert the row. Raw values and normalized values are both stored.

Hard rules in `validate_hard`:

- A BOM line with an empty component reference, an assembly with an empty assembly reference, a variant, material, supplier, or note with an empty identifier is refused.
- A BOM quantity that is present and not a number is refused. The word “one” on `bom_export.csv` row 32 is this case. The reason stored is `Unparseable quantity: 'one'`.

Soft rules in `check_soft_validation` keep the row and record a warning:

- empty description → `missing_description`
- unit text outside a known set (`EA`, `PCS`, `UNITS`, …) → `unknown_uom`
- empty supplier → `empty_supplier`
- a numeric quantity that is zero or negative → a quantity warning

There is no path that edits a quarantined row and inserts it back into `plm_bom_line`.

## 2. Normalization

Generic cleanup and the alias file `config/normalization.json` run before the insert. The raw column is untouched.

For a part reference (`normalize_reference`, then `apply_reference_aliases`):

1. Collapse whitespace and trim.
2. Uppercase.
3. Turn spaces around dashes or underscores into a single dash, collapse repeated dashes, strip leading and trailing dashes and dots.
4. If that string is a key in `reference_aliases`, replace it. `CTRL-AIR01` and `CTRL-AIR-O1` and `CTRL-HVAC-001` become `CTRL-AIR-01`.

For a unit: trim, uppercase, then `uom_aliases`. `PCS` and `UNITS` become `EA`.

For a supplier name: trim, then alias lookup. The lookup compares a punctuation-normalized form of the name with the config keys, exact match first, then prefix match, so `Siemens` and `Siemens Mobility GmbH` both become `SIEMENS MOBILITY`.

Descriptions are trimmed. Their letter case is kept.

Engineering notes, in `normalize_engineering_notes`:

- `detect_language` scores the text. French accents or at least two French function words → `FR`. At least two German function words and a higher German score than French → `DE`. Otherwise `EN`.
- A cleaned copy of the text is stored. `note_text` stays the original sentence.

ERP materials, in `normalize_erp_materials`, get the same unit and supplier treatment on the material master.

## 3. Source extraction

`run_source_extraction` builds one row per real source identifier. Duplicates are ignored on `(source_system, source_reference)`.

- `source_component` comes from PLM BOM component references and from ERP material ids. PLM rows keep the normalized reference already computed. ERP rows are a second source system, so `MAT-10001` is not automatically the same entity as `CTRL-AIR-01`.
- `source_assembly` comes from PLM assemblies and from the assembly column on BOM lines.
- `source_supplier` comes from the supplier master and from supplier text on materials.
- `source_assembly_variant` records which assembly reference is used on which variant. Nordic detection uses this link later.

## 4. Reconciliation

`run_full_reconciliation` writes proposals. It does not overwrite source rows. Every proposal is a row in `component_reconciliation` (or the assembly or supplier table) with `status = PENDING`, a method, a confidence, a rationale sentence, and `evidence_json`.

### Identity

`detect_component_identities` groups `source_component` by `normalized_reference`. A group of one is skipped. A group of two or more gets one PENDING proposal per member.

Evidence for each member contains `relationship: identity`, `canonical_ref` (the shared normalized string), and `cluster_members` (the other members’ source ids and raw references). Confidence is 0.95. Method is `EXACT` when every raw reference already normalizes to that string with no alias, and `NORMALIZED` when an alias was required.

On this dataset the only component identity cluster is `CTRL-AIR-01`, four PLM spellings, four proposals. `MAT-10001` does not share that normalized string, so it is not in the cluster.

Supplier identities use the supplier alias key the same way, in `detect_supplier_identities`.

### Similarity

`detect_functional_similarity` compares every pair of distinct normalized references. Nordic-only references are removed first so a cold-weather part is not proposed as a substitute.

`_same_prefix_different_suffix` returns a hit in two cases:

- The first two hyphen segments match and the last segment differs (`BATT-MON-01` vs `BATT-MON-EXP`). Type `same_prefix_different_suffix`.
- Or, for names with at least three segments, the last two segments match and the first differs. Type `same_suffix_different_prefix`.

Each hit writes two PENDING rows, one on each side, method `STRUCTURED`, confidence 0.50. Evidence holds `relationship: functional_similarity`, both references, `self_reference`, `other_reference`, and `review_needed: true`. The pages’ waiting table prints the relationship and not `other_reference`. The pair is visible in the “Similar, not merged” section and in `reusable_candidates`.

### Nordic-only

`detect_variant_specific_differences` finds component references that appear on a Nordic variant and on no other variant. Nordic variants are those whose name or reference contains “nordic” and that also appear in `source_assembly_variant`. Each such part gets a PENDING proposal with `relationship: variant_specific`. These parts are excluded from the similarity pass.

## 5. Human decision

`decide_reconciliation` updates one PENDING row. Allowed actions are `accept`, `reject`, and `redirect`. A row already `ACCEPTED` or `REJECTED` cannot be decided again. Reject requires a rationale. Redirect requires a source id.

**Reject.** Set status `REJECTED`, store the rationale, `decided_at`, `decided_by`, and clear the canonical id.

**Redirect.** Reject the current row with a rationale that starts with `redirected:`. Insert a new PENDING row, method `MANUAL`, whose evidence keeps the same relationship, points at `redirect_from`, and records the target source id. The new row is still waiting. Nothing is merged by the redirect itself.

**Accept, identity.** Look through `cluster_members` for a source id that already has an `ACCEPTED` proposal with a canonical id. If one exists, reuse that id. If none exists, insert one `component` row whose name and `normalized_reference` come from the source entity, and store that id on the proposal. Status becomes `ACCEPTED`. The other spellings stay pending until their own rows are accepted. When they are, they reuse the same canonical id because each evidence list names the siblings.

**Accept, similarity.** Status becomes `ACCEPTED` and the canonical id stays null. The two parts are not mapped onto each other.

**Accept, variant-specific.** Create a new canonical component for that source only. Peers are not reused.

`build_canonical_model` is what makes the accept visible on the official list. Until it runs, the decision is only on the proposal row. `write_site` and the serve handler both call it after a decision.

## 6. Canonical model

`build_canonical_model` deletes and refills `bom_relationship`, `component`, `assembly`, and `variant`, then rebuilds them.

1. Accepted identity proposals become official components. Members of one cluster share one component id via `_rebuild_accepted_identity_components`.
2. Every distinct variant reference and assembly reference becomes an official variant or assembly.
3. Each PLM BOM line is considered:
   - No identity proposal for that source component → singleton. One official component for that normalized reference, shared by every line with the same reference. This is why most of the 85 official parts exist before any click.
   - Identity status `PENDING` or `ASSESSED` → the line is skipped and counted `identity_pending`. It is not inserted into `bom_relationship`.
   - Identity status `REJECTED` → skipped, reason `identity_rejected`.
   - Identity status `ACCEPTED` → the line is inserted on the cluster’s component id.

Similarity and Nordic-only proposals do not block this and do not merge ids. A Nordic-only part that has no identity proposal is still a singleton under its own reference.

## 7. Analysis

### Already reused

`already_reused` reads `bom_relationship`. An official assembly or component used on more than one variant is “already reused”, with the variant list and a sentence built from those ids. Lines still pending identity are absent here, because they never entered `bom_relationship`.

### Worth a look

`reusable_candidates` unions two sources:

- Every `functional_similarity` proposal, paired on `reference_a` / `reference_b`. Status is not filtered, so a pending pair is already listed, and a reject does not remove it.
- A description rule for the rugged camera: a part whose description contains “rugged” paired with the passenger-counting camera when that pair was not already produced by the hyphen rule.

Each pair stays two components. The result is the “Worth a look” section.

### Compare

`all_variant_pairs` lists every unordered pair of variant references, left name before right name in alphabetical order.

`compare_variants(left, right)` compares one assembly reference at a time. Assemblies that only sound alike are separate rows.

For each assembly reference that appears on at least one of the two variants:

- Official BOM lines (`bom_relationship`) for that assembly and those variants contribute canonical component ids.
- Shared count = ids present on both sides. Left-only and right-only are the rest.
- Overlap = shared / (shared + left-only + right-only). Zero union → 0.0. `high_overlap` is true at 0.5 or above.
- BOM lines on those two variants and that assembly whose ids are not on `bom_relationship` are `unresolved` and stay out of the ratio.
- A component whose proposal evidence says `variant_specific` is labeled `variant_specific`. That count is a subset of the one-sided counts, not an extra term in the ratio.
- A pair already returned by `reusable_candidates` is labeled `reuse_candidate` on both components. `candidate_count` is the number of pairs, not the number of rows.
- If `blockers` names that component reference or that assembly reference, the label is `blocked`. If the same canonical id is on both trains, it still counts as shared. Both blocker values stay on the blocker record.

Label priority, one label per row: unresolved, then blocked, then variant-specific, then reuse candidate, then reused (on both sides), then left-only, then right-only.

The Standard vs Nordic section calls `compare_variants` with Standard on the left even though alphabetical order would differ. Other pairs keep alphabetical left and right. All pairs are written into `compare.html`. A few lines of script show one section and hide the others.

### Blockers

`blockers` writes `technical_fact` rows and returns three issue types. Both values are kept.

- **conflicting_evidence.** Scan `engineering_note.note_text` with `(?i)(\d+)\s*V`, normalize to `"{n} V DC"`. If both `24 V DC` and `48 V DC` are in the same note, store both as `operating_voltage` with status `CONFLICTING`. One voltage does not become a conflict.
- **lifecycle_mismatch.** Among PLM assemblies, a counting module whose lifecycle is `Prototype` while a peer counting assembly is `Released` (the export module versus `PCOUNT-M08`).
- **erp_lifecycle.** An ERP material whose raw status is `OBSOLETE`, reported alone. No PLM twin is invented.

Each source object includes `source_file` (the file name) and `source_row`.

### Data quality

`data_quality_issues` returns concrete issues plus a warning summary.

Existing concrete issues, each with a `records` list of `{source_table, source_id, source_file, source_row}` when the source table has them:

- `invalid_quantity` from `quarantine`
- `duplicate_bom_key` when two BOM lines share the same normalized variant, assembly, and component
- `uom_aliased` when one component’s raw units differ and all normalize to the same unit. `records` may be empty. `refs` still names the raw units

`missing_description` and `empty_supplier` stay inside `ingestion_warning_summary` with `mapping_noise: true` and a `by_source_file` count. They are not one issue card per warning.

Further issue types, appended after those three:

- `duplicate_reference` — the same `normalized_reference` on two `source_component` rows with different `source_system`. `CTRL-AIR-01` and `MAT-10001` appear together only if a fixture forces the same normalized string.
- `conflicting_facts` — groups of `technical_fact` rows already marked `CONFLICTING` for the same entity and attribute. This pass does not parse voltages again.
- `unresolved_reconciliation` — count of `component_reconciliation` rows that are `PENDING` or `REJECTED` and whose evidence relationship is `identity`. Accepted identity is not counted. The same number is returned as `unresolved_reconciliation_count`.
- `alias_summary` — one informational issue whose text contains `CTRL-AIR01 → CTRL-AIR-01`, read from `config/normalization.json` through `load_normalization_config`.

## 8. Pages

`write_site` calls `build_canonical_model`, then writes:

| File | Renderer | Role |
|---|---|---|
| `workflow.html` | `render_workflow` | Step list from live counts |
| `normalize.html` | `render_normalize` | Raw versus cleaned, quarantine, note excerpts |
| `proposals.html` | `render_proposals` | Every pending proposal, plus identity, similarity, and Nordic summaries |
| `canonical.html` | `render_canonical` | Accepted identity clusters and unresolved identity lines |
| `compare.html` | `render_compare` | All variant pairs, one visible |
| `report.html` | `render_report_html` | Already reused, worth a look, Nordic-only, blocked, data issues |

The proposals form posts to `/review/decide` on the local server. Opened as a file, the form has nowhere to send the decision.

## What is deliberately absent

- No editor that repairs a quarantined quantity and reinserts the row.
- No screen to create an identity link the matcher did not propose.
- Similarity accept/reject is stored and does not drive the Worth a look list.
- No score used by a design assistant. Similarity is a hyphen-family rule plus the rugged-camera description rule.
- No login, no API framework, and no live workbench beyond the three buttons. Phase 5, not built here, is the plain-language explanation page `evidence.html`.
