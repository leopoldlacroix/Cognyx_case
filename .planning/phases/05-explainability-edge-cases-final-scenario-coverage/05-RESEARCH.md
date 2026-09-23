# Phase 5: Explainability, Edge Cases & Final Scenario Coverage - Research

**Researched:** 2026-09-24
**Domain:** Deterministic explainability, conflict display, multilingual evidence, and data-quality trails on the existing Python/SQLite pipeline
**Confidence:** HIGH

<research_summary>
## Summary

Phase 5 deepens analysis the pipeline already computes. It does not need a new matcher, a language model, a data-quality framework, or a web app. Phases 3 and 4 already store plain-language `explanation` strings, `technical_fact` rows with status `CONFLICTING`, and `source_file` plus `source_row` on blockers and data-quality issues. The blueprint's explainability rule is already the expert pattern for a rules pipeline: cite the stored records, and do not say "the AI thinks these are reusable" (`docs/blueprint/docs/06_canonicalization_and_analysis.md`, section 6.9).

The useful deepening is a structured trace beside the sentence. Each already-reused, candidate, blocker, and data-quality row should name the method, the records compared, what matched, what conflicted, and the evidence (file and row). The sentence is rendered from those fields, so the prose cannot drift from the data. `evidence.html` belongs in the existing static shell in `app/services/html_pages.py`, with `html.escape` on every note and value.

Checked against the immutable notes file on 2026-09-24: 71 notes, language column `en` 45 and `fr` 26, zero `de`. `detect_language()` agrees with that column on all 71. Notes that contain both 24 V and 48 V are `N-064` (`CTRL-AIR-01`), `N-067` (`PIS-DISPLAY-15`), and `N-015` (`BMU-027`). `N-011` mentions 750 V and 24 V and is a different fact. There is no German text to detect and no translation to display.

**Primary recommendation:** Stay on the standard library. Add a structured explanation object and `evidence.html`. Do not add Splink, Lingua, langdetect, Great Expectations, a translator, FTS5, or a PROV graph.
</research_summary>

<standard_stack>
## Standard Stack

The established tools for this phase are already in the repo. No `requirements.txt` dependencies exist. Runtime checked locally: CPython 3.14.4, SQLite 3.46.1.

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python `html` | 3.14 stdlib (`html.escape` since 3.2) | Escape note text and attribute values into static HTML | Official way to put untrusted text in HTML. Quote escaping is on by default, which covers attributes. https://docs.python.org/3/library/html.html |
| SQLite via `sqlite3` | 3.46.1 | Read notes, facts, quarantine, BOM keys | Already the canonical store. Explanations must be derived from these rows. |
| Existing services | current tree | `analysis.py`, `quality.py`, `html_pages.shell`, `report.py` | Phase 4 already writes the trail Phase 5 displays. |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Source `language` column | CSV values `en`, `fr` | Language flag for SCEN-H | The file already labels every note. Prefer this over a detector. |
| `language_normalized` | `EN` / `FR` / `DE` from `detect_language()` | Cross-check only | Matches the source label on all 71 notes today. Do not replace the source label with the heuristic. |
| `note_text` | raw | Original wording | `note_text_normalized` is whitespace cleanup, not a translation. |
| In-page script | same pattern as `compare.html` | Show one language section | No server. The compare page already switches sections in the static file. |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Sentence rendered from stored fields | Splink match-weight waterfall | Splink explains Fellegi-Sunter probabilities. This pipeline is deterministic rules. Splink's own guide says deterministic linkage is the cheap, high-precision choice, and Splink itself is primarily probabilistic. https://moj-analytical-services.github.io/splink/topic_guides/theory/probabilistic_vs_deterministic.html |
| Source `language` column | `lingua-language-detector` 2.2.0 (2026-03-09) | Accurate on short text, offline, Python >= 3.12. Full models are about 300 MB on disk. The heuristic already matches all 71 source labels, and the column is authoritative. https://github.com/pemistahl/lingua-py/releases/tag/v2.2.0 |
| Source `language` column | `langdetect` 1.0.6 | Official README: non-deterministic on short or ambiguous text unless `DetectorFactory.seed` is set, and the seed only makes runs repeatable. Port of a 2014 library. Poor fit for notes. https://github.com/Mimino666/langdetect/blob/master/README.md |
| SQL checks already in `quality.py` | Great Expectations | GX pays off when many datasets share expectation suites. For a few hundred rows and bespoke engineering rules, custom checks are the usual choice. https://bixtech.ai/great-expectations-vs-custom-data-validation-scripts-which-approach-actually-scales/ (secondary; consistent with the repo's zero-dependency constraint) |
| `LIKE` on `note_text` | SQLite FTS5 | FTS5 is the full-text engine for a large document collection. https://www.sqlite.org/fts5.html 71 notes do not need a virtual table, and trigram/unicode tokenizers can hide or strip the accents the demo needs to show. |
| `html.escape` + `shell()` | Jinja2 | A template engine helps when many people edit templates. One new page in the existing f-string shell does not. |
| Keep both fact rows | W3C PROV-O / PROV-DM graph | PROV's useful idea is already the model: an entity, an activity, and the entities it used. https://www.w3.org/TR/prov-dm/ Shipping RDF, bundles, and agents for a static HTML page adds a second store. |
| Show original wording | A translation library | SCEN-H is "language normalization without losing original wording." A translation would hide the evidence the engineer needs to read. |

**Installation:**

```bash
# No new packages.
# Pages are rewritten by the existing report command.
python -m app.backend.cli report
```
</standard_stack>

<architecture_patterns>
## Architecture Patterns

### Recommended Project Structure
```
app/services/
├── analysis.py          # already-reused and candidate rows; add structured trace
├── quality.py           # blockers and data-quality rows; reuse, do not re-parse
├── html_pages.py        # shell(), nav, evidence.html
└── report.py            # existing sentences stay; link to evidence anchors
data/processed/
└── evidence.html        # generated, same as compare.html and report.html
```

### Pattern 1: Explanation is a projection of a trace
**What:** Persist the inputs of the rule, then render one sentence from those inputs. W3C PROV calls the result an entity derived from the records the activity used (`wasDerivedFrom` / `used`). The blueprint states the same rule in demo language.
**When to use:** Every already-reused, candidate, blocker, and data-quality row.
**Example:**
```python
# Shape for planning. Sentence must be built only from these fields.
trace = {
    "method": "conflicting_evidence",
    "compared": ["N-064"],
    "matched": [],
    "conflicted": [
        {"attribute": "operating_voltage", "value": "24 V DC"},
        {"attribute": "operating_voltage", "value": "48 V DC"},
    ],
    "evidence": [
        {"source_file": "technical_notes.csv", "source_row": 64, "source_id": "N-064"},
    ],
}
# Blueprint 6.9, blocked case:
# "Reuse blocked because source records disagree on operating voltage (24 V DC vs 48 V DC)."
```

### Pattern 2: Contradiction is stored as two facts, not one winner
**What:** Bleiholder and Naumann (VLDB 2009 tutorial, "Data Fusion – Resolving Data Conflicts for Integration") separate deciding strategies, which pick a preferred value, from strategies that keep the contradiction. This PoC keeps the contradiction. `technical_fact.status` is already `OBSERVED | VALIDATED | CONFLICTING` (`docs/blueprint/docs/03_data_model.md`, section 3.8).
**When to use:** Two non-null values for the same attribute. Do not COALESCE, vote, or trust ERP over the note.
**Example:**
```text
# Same attribute, two rows, both CONFLICTING. No third row that says "the real voltage is …".
operating_voltage | 24 V DC | engineering_note | N-064 | CONFLICTING
operating_voltage | 48 V DC | engineering_note | N-064 | CONFLICTING
```

### Pattern 3: Static evidence page, same shell as Compare
**What:** `evidence.html` is another file in `PAGES`. Sections for conflicts, languages, data-quality issues, and lifecycle. Anchors use file, row, and source id. A few lines of script reveal one language, the way Compare reveals one variant pair. Nothing is fetched live.
**When to use:** The check page named in the roadmap for this phase.
**Example:**
```python
# Source: https://docs.python.org/3/library/html.html
import html
e = html.escape
badge = e(note["language"])          # "fr" or "en" from the CSV
body = e(note["note_text"])          # original wording, quotes and accents included
block = f'<article id="note-{e(note_id)}"><p class="badge">{badge}</p><p>{body}</p></article>'
```

### Anti-Patterns to Avoid
- **A second explanation written by hand next to the data:** The sentence and the trace diverge, and the demo shows a reason the query does not support.
- **Picking a voltage, a lifecycle, or a language and hiding the other:** That is the failure SCEN-G and SCEN-H exist to catch.
- **Re-parsing voltages or re-detecting language on the page:** `extract_voltage_facts` and the source `language` column are the evidence. A second algorithm will disagree with the report.
- **One card per soft warning:** Phase 3 already found that `missing_description` and `empty_supplier` fire because BOM description and supplier text were not mapped. Those stay a summary labeled mapping noise.
</architecture_patterns>

<dont_hand_roll>
## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HTML escaping of French notes and quoted CSV text | A replace of `<` only | `html.escape` (quotes on by default) | Attribute and body contexts both need `& < > " '`. https://docs.python.org/3/library/html.html |
| "Why this row" for a rules engine | An LLM blurb or a Splink waterfall | A trace rendered into the blueprint sentence | Splink waterfalls add match weights from a trained Fellegi-Sunter model. These results come from SQL rules and stored facts. https://moj-analytical-services.github.io/splink/topic_guides/theory/fellegi_sunter.html |
| Choosing the true voltage or lifecycle | A trust score, majority vote, or `COALESCE` | Two `CONFLICTING` facts and both values on the page | Deciding strategies hide the disagreement the engineer is there to see. http://www.vldb.org/pvldb/vol2/vldb09-tutorial1.pdf |
| Language of a note | Lingua 2.2.0 or langdetect 1.0.6 | The `language` column already ingested into `engineering_note.language` | 71/71 agreement with `detect_language()` on 2026-09-24. langdetect is non-deterministic on short text. Lingua's full model set is hundreds of megabytes. |
| Translation next to the original | deep-translator or an API | `note_text` plus the language flag | The roadmap phrase "normalized translation" does not match the data. Normalization here is whitespace. Translating would replace the evidence. |
| Search over 71 notes | FTS5 virtual table | `LIKE` on `note_text`, filter `language` | FTS5 is specified for large collections. https://www.sqlite.org/fts5.html Accents in the French notes are part of the demo. |
| Duplicate BOM keys, bad quantities, UOM aliases | A Great Expectations suite | `data_quality_issues()` | Rules are scenario-specific and already return records with file and row. |
| Provenance interchange | PROV-JSON or PROV-O | `source_file`, `source_row`, `source_id`, `status` | PROV-DM is the right vocabulary (entity, activity, used). It is the wrong artifact for this page. https://www.w3.org/TR/prov-dm/ |

**Key insight:** The hard part of this phase is keeping the sentence, the fact rows, and the HTML on the same records. New libraries each introduce a second opinion.
</dont_hand_roll>

<common_pitfalls>
## Common Pitfalls

### Pitfall 1: Treating the roadmap's HVAC story as an ERP-versus-note conflict
**What goes wrong:** The evidence page says ERP is 48 V and the note is 24 V, or the reverse, and marks one of them correct.
**Why it happens:** Phase 5 success criterion 2 in `.planning/ROADMAP.md` still says "ERP material record vs engineering note." The note itself says both. `N-064` text: "One legacy BOM extract lists 48V DC, but the current engineering specification and ERP material are 24V DC." Phase 3 context forbids attaching `MAT-10001` unless an accepted identity says so. `MAT-10001` is not an identity link.
**How to avoid:** One `conflicting_evidence` row for `CTRL-AIR-01`, values `24 V DC` and `48 V DC`, both from `technical_notes.csv` row of `N-064`, status `CONFLICTING`, no winner. The sentence may quote the note's claim about ERP. It may not invent an ERP fact row.
**Warning signs:** A source dict with `source_type` `erp_material` on the voltage blocker, or the word "winner" in the explanation.

### Pitfall 2: Treating every 24-and-48 note as the HVAC scenario
**What goes wrong:** The conflict list grows to include a different engineering point, and the demo calls it the same bug.
**Why it happens:** `extract_voltage_facts` keeps every integer before `V`. On 2026-09-24 the notes with both 24 and 48 are `N-064` (`CTRL-AIR-01`), `N-067` (`PIS-DISPLAY-15`), and `N-015` (`BMU-027`). `N-067` is the PIS Display case in `docs/scenarios.md`. `N-015` compares the 48 V export monitor with "the 24V unit"; the 24 V value is the other part. `N-011` is 750 V input and 24 V output and must stay out. `N-066` says `24 V` and `24V` are a format difference; the regex already collapses those to one value.
**How to avoid:** Keep the existing "both 24 V DC and 48 V DC" rule. On the page, show note id and object reference on every card so `N-064` and `N-067` are the scenario G stories and `N-015` is visibly a cross-part comparison. Do not add a second voltage parser.
**Warning signs:** `APC-750-24` listed as a voltage conflict, or `N-066` listed as a unit conflict.

### Pitfall 3: Inventing a German corpus or a translation
**What goes wrong:** The page has an empty DE section presented as a failure, or French notes are shown only in English.
**Why it happens:** SCEN-H and the roadmap say FR/EN/DE and "normalized translation." The CSV `language` column is `en` (45) and `fr` (26). There is no `de` row. `note_text_normalized` does not translate.
**How to avoid:** Flag each note with its source language. Search and filter on `language` (`fr`, `en`). Show `note_text` unchanged. A DE filter can exist and be empty. Do not edit `data/inputs/` to add German.
**Warning signs:** A translation column, or a test that requires a `de` note in the fixture.

### Pitfall 4: Rewriting lifecycle to match the roadmap's Active/Obsolete sentence
**What goes wrong:** The export counting module is described as ERP Active versus PLM Obsolete.
**Why it happens:** Phase 5 success criterion 5 says that. The assembly master does not. `PAX-COUNT-MOD-E` is `Prototype`. Peer counting assemblies are `Released`. ERP `OBSOLETE` materials (`MAT-20001`, `MAT-20002`, `MAT-20004`) are a separate `erp_lifecycle` issue and have no PLM twin in the current identity model.
**How to avoid:** Keep `lifecycle_mismatch` and `erp_lifecycle` as different issue types, each with its own file and row. Lifecycle does not block identity reconciliation and does not share a component id with a similarity.
**Warning signs:** The explanation contains "Obsolete" on `PAX-COUNT-MOD-E`, or a single issue type that mixes ERP status with PLM lifecycle.

### Pitfall 5: Promoting alias and mapping noise into conflicts
**What goes wrong:** `pcs` versus `EA`, or the 508 soft warnings, appear as blockers that prevent reuse.
**Why it happens:** SCEN-I says "unit inconsistencies." Phase 3 decided raw UOMs that normalize to the same unit are an informational `uom_aliased` issue. Most `missing_description` and `empty_supplier` warnings are ingestion-mapping noise.
**How to avoid:** Data-quality detection stays independent of identity reconciliation, and it stays classified. Quarantine (`BOM-0031`, quantity `one`), duplicate normalized BOM keys, and `uom_aliased` stay concrete records. Mapping noise stays a count by file.
**Warning signs:** A card per warning, or `pcs` → `EA` marked `CONFLICTING`.
</common_pitfalls>

<code_examples>
## Code Examples

Verified patterns from official sources and the blueprint. The trace dict is the planning shape; it is not copied from a library.

### Escape note text into the evidence page
```python
# Source: https://docs.python.org/3/library/html.html
import html

def note_card(note_id: str, language: str, note_text: str) -> str:
    e = html.escape
    return (
        f'<article id="note-{e(note_id)}">'
        f'<p class="badge">{e(language)}</p>'
        f'<p>{e(note_text)}</p>'
        f'</article>'
    )
```

### Blocked-result sentence from stored values
```python
# Source: docs/blueprint/docs/06_canonicalization_and_analysis.md section 6.9
# Do not display: "The AI thinks these are reusable."
def blocked_sentence(attribute: str, left: str, right: str) -> str:
    return (
        f"Reuse blocked because source records disagree on {attribute} "
        f"({left} vs {right})."
    )
```

### Keep both conflicting values
```python
# Source: technical_fact status in docs/blueprint/docs/03_data_model.md section 3.8
# and the current insert in app/services/quality.py
# Both rows use status CONFLICTING. There is no selected value.
facts = [
    {"attribute": "operating_voltage", "value": "24 V DC", "source_id": "N-064", "status": "CONFLICTING"},
    {"attribute": "operating_voltage", "value": "48 V DC", "source_id": "N-064", "status": "CONFLICTING"},
]
```
</code_examples>

<sota_updates>
## State of the Art (2025-2026)

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| langdetect as the default short-text detector | Lingua 2.x (Rust bindings, FST models, Python >= 3.12) when detection is actually required | Lingua 2.2.0, 2026-03-09 | Still the wrong dependency here: the CSV already has `language`, and the heuristic matches it |
| Probabilistic linkage UI (Splink waterfall) as "the" explanation | Cite the rule inputs for deterministic linkage | Splink docs, current topic guide | Waterfalls explain match weights. This phase explains SQL rules and fact rows |
| PROV-O as a triple store for every pipeline | Borrow entity / activity / used; store file, row, and status in SQLite | PROV-DM remains the W3C model (Recommendation) | Do not add an RDF library for one HTML page |
| Great Expectations Data Docs as the quality report | Domain queries that name the offending row | Still true for prototypes with bespoke rules | `evidence.html` is the report |

**New tools/patterns to consider:**
- **Structured trace next to the sentence:** Makes ANALYSIS-05 testable. Assert the ids and values in the trace, then assert the sentence contains those same strings.
- **Empty DE state:** Honest UI for a filter the scenario name mentions and the fixture does not contain.

**Deprecated/outdated:**
- **langdetect without a seed, and with a seed:** Repeatable is not accurate, and the project does not need it.
- **Roadmap sentences that disagree with the fixture:** ERP-versus-note voltage, PLM Obsolete, and a German/translation view. The fixture and Phase 3 context win.
</sota_updates>

<open_questions>
## Open Questions

1. **Should `N-015` (`BMU-027`) stay in `conflicting_evidence`?**
   - What we know: The current 24-and-48 rule includes it, because the note contains both voltages. The 24 V phrase refers to the other unit.
   - What's unclear: Whether the demo reads that card as a false conflict.
   - Recommendation: Keep the rule. Label the card with `N-015` and `BMU-027`. Do not special-case it away during planning unless a test already excludes it. Confirm against `tests/test_quality.py` before changing the rule.

2. **Where does the structured trace live?**
   - What we know: Phase 4 said Phase 3 `explanation` sentences stay. Compare and the quality report already have file and row.
   - What's unclear: A new JSON object on each row versus rendering the trace only in HTML.
   - Recommendation: Add the trace fields on the existing dicts and keep the current `explanation` string as the rendered sentence. Tests that assert the old sentences must keep passing.

3. **Context7 was not available in this session.**
   - What we know: Official pages were fetched directly for Python `html`, PROV-DM, Splink, SQLite FTS5, langdetect, and the Lingua 2.2.0 release notes.
   - What's unclear: Nothing that changes the recommendation. No library from Context7 would replace the source language column or the stored facts.
   - Recommendation: Plan against this file. Re-check only if someone proposes adding Lingua or Splink later.
</open_questions>

<sources>
## Sources

### Primary (HIGH confidence)
- https://docs.python.org/3/library/html.html — `html.escape` / `html.unescape`, Python 3.14 docs. Local runtime is CPython 3.14.4.
- https://www.w3.org/TR/prov-dm/ — PROV entity, activity, used, wasDerivedFrom. Used as vocabulary, not as a store.
- https://www.sqlite.org/fts5.html — FTS5 is for searching a large collection; trigram tokenizer constraints noted.
- https://moj-analytical-services.github.io/splink/topic_guides/theory/probabilistic_vs_deterministic.html — deterministic versus probabilistic linkage.
- https://moj-analytical-services.github.io/splink/topic_guides/theory/fellegi_sunter.html — match weights and the waterfall chart.
- https://github.com/Mimino666/langdetect/blob/master/README.md — non-determinism on short text; `DetectorFactory.seed`.
- https://github.com/pemistahl/lingua-py/releases/tag/v2.2.0 — Lingua 2.2.0, 2026-03-09; FST models; Python 3.10 and 3.11 dropped.
- `docs/blueprint/docs/06_canonicalization_and_analysis.md` section 6.9 — required explanation wording.
- `docs/blueprint/docs/03_data_model.md` section 3.8 — `technical_fact` status values.
- `data/inputs/engineering/technical_notes.csv` — 71 notes; `en` 45, `fr` 26, `de` 0; dual-voltage notes `N-015`, `N-064`, `N-067`. `detect_language()` mismatches: 0. Checked 2026-09-24.
- `.planning/phases/03-human-review-workflow-core-analysis/03-CONTEXT.md` — N-064 is one note; lifecycle is Prototype versus Released; mapping noise versus concrete SCEN-I issues.
- `.planning/phases/04-cross-variant-reuse-analysis-deep-reports/04-CONTEXT.md` — Phase 5 owns the plain-language pass, multilingual search, and `evidence.html`; Phase 3 sentences stay.

### Secondary (MEDIUM confidence)
- http://www.vldb.org/pvldb/vol2/vldb09-tutorial1.pdf — Bleiholder & Naumann, conflict-deciding versus conflict-keeping fusion. Tutorial classification, not a library API.
- https://bixtech.ai/great-expectations-vs-custom-data-validation-scripts-which-approach-actually-scales/ — custom checks for a small bespoke pipeline. A vendor blog; it agrees with the zero-dependency constraint and was not treated as a product requirement.

### Tertiary (LOW confidence - needs validation)
- None that the recommendation depends on. The Great Expectations blog is the only non-official web source, and it is not load-bearing.
</sources>

<metadata>
## Metadata

**Research scope:**
- Core technology: explanation traces on the existing Python 3.14 / SQLite 3.46 pipeline
- Ecosystem: Splink, Lingua, langdetect, Great Expectations, FTS5, PROV-O, Jinja2, translation libraries — all considered and rejected for this phase
- Patterns: trace-then-sentence, two CONFLICTING facts, static evidence page
- Pitfalls: stale roadmap wording versus `N-064`, `N-015`/`N-067`, missing German, Prototype versus Released, mapping noise

**Confidence breakdown:**
- Standard stack: HIGH — stdlib and the current services; rejected libraries checked against current docs
- Architecture: HIGH — blueprint section 6.9 plus Phase 3 and 4 context
- Pitfalls: HIGH — counted from `technical_notes.csv` and `detect_language()` on 2026-09-24
- Code examples: HIGH for `html.escape` and fact status; the trace dict is a planning shape derived from those sources

**Research date:** 2026-09-24
**Valid until:** 2026-10-24 for library versions. The fixture counts stay valid until `data/inputs/` changes, which the project forbids.

**Context7:** not installed in this session. Official docs were fetched directly.
</metadata>

---

*Phase: 05-explainability-edge-cases-final-scenario-coverage*
*Research completed: 2026-09-24*
*Ready for planning: yes*
