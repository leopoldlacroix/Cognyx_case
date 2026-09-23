# Phase 4: Cross-Variant Reuse Analysis — Deep Reports - Context

**Gathered:** 2026-09-23
**Status:** Ready for planning

<vision>
## How This Should Work

Opening the site, Compare sits with the pages that already exist. Someone picks two of the five trains — Standard, Comfort, Nordic, High Capacity, Export — and reads each assembly as one row: how much of the part list is shared, which parts are on both trains, which exist on only one, which are still unresolved, and which are blocked.

A shared part is one already reused. A part that is only close stays a candidate, still two parts. A Nordic cold-rated part is marked as an intentional choice for that train. A conflict, such as the two voltages on the HVAC controller, stays on the row with both values visible. Following that row leads to the facts, the source records, and the original CSV row. The data-quality section on the existing reuse preview gets the same kind of trail: each issue names the record that caused it.

The page is still a generated HTML file. All ten pairs are already in it. Choosing a pair only reveals that section. Choosing a part or a blocker jumps to evidence already written on the page. Nothing is loaded live.

</vision>

<essential>
## What Must Be Nailed

- **Same assembly reference is the comparison.** Overlap is the canonical components on one assembly reference, on the two chosen variants. Assemblies that only sound alike are not grouped together.
- **Counts you can check.** Each assembly row shows shared, only on the left, only on the right, unresolved, conflicts, and substitution candidates. The overlap ratio is shared divided by the union of those canonical components. A row at 0.5 or above looks different from the rest.
- **Labels stay separate.** Reused means the same canonical component is on both variants. A reuse candidate is a similarity, not a merge. Blocked means a conflict or a lifecycle mismatch is in the way. Unresolved means an identity decision is still pending or was rejected. Nordic variant-specific parts are marked intentional: not unresolved, and not candidates.
- **The trail is the record.** A blocker names both values, the attribute, the source type, the source id, the file, and the row. A data-quality issue names the record that triggered it. Both sides of a conflict stay. No value is chosen as the winner.
- **All four deepenings ship together.** Assembly overlap, the pairwise drill-down, the blocker trail, and the richer data-quality report. `compare.html` is the new page. The quality section on `report.html` is enriched. JSON is written beside the HTML.

</essential>

<boundaries>
## What's Out of Scope

- A web framework, an API, accounts, or a live workbench. The architecture's `GET /analysis/...` routes are not this phase.
- New matchers, and any merge of a similarity into one canonical component.
- Grouping assemblies by guessed function when their references differ.
- A byte offset into the CSV. The trail is source file plus row id.
- Plain-language explainability as a new pass, multilingual search, and `evidence.html`. Phase 5 owns those, and can reuse the ids and rows this phase stores.
- Reading `data/ground_truth/` into any page or JSON. Editing `data/inputs/`.
- Redesigning where supplier text lives.

</boundaries>

<specifics>
## Specific Ideas

- The same command that rewrites the other pages also writes `compare.html` and adds it to the nav.
- The page opens on Regional Standard vs Regional Nordic, so shared baseline parts and intentional cold-rated differences are the first thing visible. Standard vs Export is the pair that shows the 48 V architecture and the export counting-module lifecycle issue.
- All ten pairs are rendered. One is visible. A few lines of script in the static file switch the pair. There is no server.
- A click is an anchor to a section already on the page: source system, source id, file, and row, plus both values when they conflict.
- Data-quality enrichment keeps the Phase 3 split. Mapping noise (`missing_description`, `empty_supplier`) stays labeled as mapping noise. Concrete issues stay listed on their own: quarantined quantity, duplicate BOM keys, UOM aliases, duplicate references across sources, conflicting facts, unresolved reconciliations, and the alias summary.
- `MAT-10001` is still not an identity link for `CTRL-AIR-01`. The voltage conflict stays the note text on `N-064`, both values kept.

</specifics>

<notes>
## Additional Context

The roadmap already listed four plans. The choice was to keep all four, including the blocker trail and the data-quality enrichment, even though Phase 5 also has an evidence page. The remaining choices were settled so planning can start:

- Five variants: `REGIO-STD`, `REGIO-COMFORT`, `REGIO-NORDIC`, `REGIO-HC`, `REGIO-EXPORT`.
- Canonical assemblies stay one per normalized assembly reference, as Phase 3 built them.
- Overlap uses canonical component ids already on `bom_relationship`. Pending or rejected identity lines stay unresolved and out of the shared count.
- Phase 3 `explanation` text stays. This phase adds the structured trail. It does not replace those sentences.
- High overlap means a ratio of at least 0.5. The counts are always shown next to the ratio.

</notes>

---

*Phase: 04-cross-variant-reuse-analysis-deep-reports*
*Context gathered: 2026-09-23*
