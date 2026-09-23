"""Static HTML pages for checking the pipeline and explaining what is left.

No web framework. `python -m app.backend.cli report` rewrites every page.
"""
from __future__ import annotations

import html
import json
import sqlite3
from pathlib import Path
from typing import Dict, List

PAGES = (
    ("workflow.html", "Workflow"),
    ("normalize.html", "1 · Normalize"),
    ("proposals.html", "2 · Proposals"),
    ("canonical.html", "3 · Canonical"),
    ("compare.html", "4 · Compare"),
    ("report.html", "Preview · Reuse"),
)

_STD_NORDIC = ("REGIO-STD", "REGIO-NORDIC")


def shell(
    title: str,
    active: str,
    body: str,
    *,
    body_class: str = "",
    extra_css: str = "",
) -> str:
    e = html.escape
    links = []
    for filename, label in PAGES:
        cls = ' class="active"' if filename == active else ""
        links.append(f'<a href="{filename}"{cls}>{e(label)}</a>')
    nav = "".join(links)
    body_attr = f' class="{e(body_class)}"' if body_class else ""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{e(title)}</title>
  <style>
    body {{
      font-family: "Segoe UI", Helvetica, Arial, sans-serif;
      max-width: 820px;
      margin: 1.5rem auto 4rem;
      padding: 0 1.25rem;
      color: #1c1917;
      background: #f7f6f3;
      line-height: 1.45;
    }}
    h1 {{ font-size: 1.7rem; font-weight: 650; margin: 0.6rem 0 0.4rem; }}
    h2 {{ font-size: 1.05rem; margin: 0; }}
    p {{ margin: 0.3rem 0; }}
    a {{ color: #1e3a8a; }}
    nav {{
      display: flex; flex-wrap: wrap; gap: 0.4rem;
      margin-bottom: 0.5rem;
    }}
    nav a {{
      text-decoration: none; color: #44403c;
      background: #fff; border: 1px solid #e7e5e4;
      border-radius: 999px; padding: 0.25rem 0.75rem; font-size: 0.9rem;
    }}
    nav a.active {{ background: #1c1917; color: #fff; border-color: #1c1917; }}
    .lede {{ color: #44403c; margin-bottom: 1rem; }}
    .counts {{ display: flex; flex-wrap: wrap; gap: 0.5rem; margin: 1rem 0; font-size: 0.9rem; }}
    .counts span, .badge {{
      background: #fff; border: 1px solid #e7e5e4;
      border-radius: 999px; padding: 0.15rem 0.7rem; font-size: 0.8rem;
    }}
    .badge.done {{ background: #ecfccb; border-color: #65a30d; color: #3f6212; }}
    .badge.preview {{ background: #fef9c3; border-color: #ca8a04; color: #854d0e; }}
    .badge.missing {{ background: #fee2e2; border-color: #dc2626; color: #991b1b; }}
    .badge.later {{ background: #e0e7ff; border-color: #6366f1; color: #3730a3; }}
    ol.flow {{ list-style: none; padding: 0; margin: 1rem 0; }}
    ol.flow li {{
      background: #fff; border: 1px solid #e7e5e4; border-radius: 10px;
      padding: 0.8rem 1rem; margin: 0;
    }}
    ol.flow li + li {{ margin-top: 0.45rem; }}
    ol.flow .step-head {{ display: flex; justify-content: space-between; gap: 1rem; align-items: center; }}
    ol.flow p {{ color: #44403c; font-size: 0.95rem; }}
    table {{
      width: 100%; border-collapse: collapse; background: #fff;
      border: 1px solid #e7e5e4; border-radius: 8px; overflow: hidden;
      margin-top: 0.5rem; font-size: 0.92rem;
    }}
    th, td {{ text-align: left; padding: 0.45rem 0.6rem; border-bottom: 1px solid #f5f5f4; vertical-align: top; }}
    th {{ background: #fafaf9; font-weight: 600; }}
    section {{ margin-top: 1.6rem; }}
    .note {{
      background: #fff; border: 1px solid #e7e5e4; border-radius: 8px;
      padding: 0.75rem 1rem; margin-top: 0.8rem;
    }}
    footer {{ margin-top: 2.5rem; color: #78716c; font-size: 0.85rem; }}
    code {{ font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 0.92em; }}
    article {{
      background: #fff; border: 1px solid #e7e5e4;
      border-left: 4px solid #44403c;
      border-radius: 8px; padding: 0.75rem 1rem; margin-top: 0.6rem;
    }}
    article.reuse {{ border-left-color: #3f6212; }}
    article.candidate {{ border-left-color: #a16207; }}
    article.separate {{ border-left-color: #1e40af; }}
    article.blocker {{ border-left-color: #b91c1c; }}
    article.issue {{ border-left-color: #9a3412; }}
    .meta {{ color: #57534e; font-size: 0.85rem; margin-top: 0.25rem; }}
    {extra_css}
  </style>
</head>
<body{body_attr}>
  <nav>{nav}</nav>
  {body}
  <footer>
    <p>Regenerate every page with <code>python -m app.backend.cli report</code>.</p>
  </footer>
</body>
</html>
"""


def write_site(conn: sqlite3.Connection, directory: Path) -> List[Path]:
    """Write the workflow, the check pages, canonical BOM, compare, and the reuse preview."""
    from app.services.canonicalization import build_canonical_model
    from app.services.report import build_snapshot, render_report_html

    # Report CLI prepares the DB first; refill canonical before pages that need BOM.
    build_canonical_model(conn)

    directory.mkdir(parents=True, exist_ok=True)
    written = [
        directory / "workflow.html",
        directory / "normalize.html",
        directory / "proposals.html",
        directory / "canonical.html",
        directory / "compare.html",
        directory / "report.html",
    ]
    written[0].write_text(render_workflow(conn), encoding="utf-8")
    written[1].write_text(render_normalize(conn), encoding="utf-8")
    written[2].write_text(render_proposals(conn), encoding="utf-8")
    written[3].write_text(render_canonical(conn), encoding="utf-8")
    written[4].write_text(render_compare(conn), encoding="utf-8")
    written[5].write_text(render_report_html(build_snapshot(conn)), encoding="utf-8")
    return written


def render_compare(conn: sqlite3.Connection) -> str:
    """Static variant-pair comparison. All pairs in one file; script toggles visibility."""
    from app.services.analysis import all_variant_pairs, compare_variants
    from app.services.quality import blockers as quality_blockers

    e = html.escape
    pairs = all_variant_pairs(conn)
    variant_refs = {left for left, right in pairs} | {right for left, right in pairs}

    if "REGIO-STD" in variant_refs and "REGIO-NORDIC" in variant_refs:
        default_left, default_right = _STD_NORDIC
    elif pairs:
        default_left, default_right = pairs[0]
    else:
        default_left, default_right = None, None

    blocker_by_ref: Dict[str, Dict] = {}
    for row in quality_blockers(conn):
        ref = row.get("entity_ref")
        if ref:
            blocker_by_ref[ref] = row

    select_options = []
    sections = []
    for lex_left, lex_right in pairs:
        if {lex_left, lex_right} == set(_STD_NORDIC):
            left_ref, right_ref = _STD_NORDIC
        else:
            left_ref, right_ref = lex_left, lex_right
        comparison = compare_variants(conn, left_ref, right_ref)
        section_id = f"pair-{left_ref}-{right_ref}"
        is_default = left_ref == default_left and right_ref == default_right
        hidden_cls = "" if is_default else " hidden"
        selected = " selected" if is_default else ""
        label = f"{left_ref} vs {right_ref}"
        select_options.append(
            f'<option value="{e(section_id)}"{selected}>{e(label)}</option>'
        )

        assembly_blocks = []
        for asm in comparison["assemblies"]:
            ratio = asm["overlap_ratio"]
            high_cls = " high-overlap" if asm.get("high_overlap") else ""
            counts = (
                f"shared {asm['shared_count']}, "
                f"left-only {asm['left_only_count']}, "
                f"right-only {asm['right_only_count']}, "
                f"unresolved {asm['unresolved_count']}, "
                f"conflicts {asm['conflict_count']}, "
                f"candidates {asm['candidate_count']}"
            )
            component_html = []
            for comp in asm["components"]:
                anchor = comp["anchor"]
                blocker = blocker_by_ref.get(comp["ref"]) or blocker_by_ref.get(
                    asm["assembly_ref"]
                )
                record_bits = []
                for rec in comp.get("records") or []:
                    record_bits.append(
                        f"{e(str(rec.get('source_file') or ''))} "
                        f"row {e(str(rec.get('source_row')))}"
                    )
                records_text = "; ".join(record_bits) if record_bits else "no source rows"
                values_html = ""
                if comp["label"] == "blocked" and blocker:
                    vals = blocker.get("values") or []
                    if vals:
                        values_html = (
                            f'<p class="meta">Both values: '
                            f"{e(' and '.join(str(v) for v in vals))}</p>"
                        )
                    for src in blocker.get("sources") or []:
                        values_html += (
                            f'<p class="meta">{e(str(src.get("value") or ""))} — '
                            f'{e(str(src.get("source_file") or ""))} '
                            f'row {e(str(src.get("source_row")))}</p>'
                        )
                component_html.append(
                    f'<div class="component" id="{e(anchor)}">'
                    f'<p><a href="#{e(anchor)}"><strong>{e(comp["ref"])}</strong></a> '
                    f'<span class="badge">{e(comp["label"])}</span></p>'
                    f'<p class="meta">{records_text}</p>'
                    f"{values_html}</div>"
                )
            assembly_blocks.append(
                f'<article class="assembly{high_cls}">'
                f'<p><strong>{e(asm["assembly_ref"])}</strong> '
                f'overlap {e(str(ratio))} — {e(counts)}</p>'
                f'{"".join(component_html)}</article>'
            )

        sections.append(
            f'<section class="pair-section{hidden_cls}" id="{e(section_id)}" '
            f'data-left="{e(left_ref)}" data-right="{e(right_ref)}">'
            f"<h2>{e(label)}</h2>"
            f'{"".join(assembly_blocks) if assembly_blocks else "<p>No assemblies.</p>"}'
            f"</section>"
        )

    control = (
        '<label for="pair-select">Variant pair </label>'
        f'<select id="pair-select">{"".join(select_options)}</select>'
        if select_options
        else "<p>No variants to compare.</p>"
    )
    script = """
<script>
(function () {
  var sel = document.getElementById("pair-select");
  if (!sel) return;
  function showPair(id) {
    document.querySelectorAll(".pair-section").forEach(function (el) {
      el.classList.add("hidden");
    });
    var target = document.getElementById(id);
    if (target) target.classList.remove("hidden");
  }
  sel.addEventListener("change", function () { showPair(sel.value); });
})();
</script>
"""
    extra_css = """
    body.compare-page { max-width: 1100px; }
    .hidden { display: none; }
    article.assembly.high-overlap {
      background: #f7fee7;
      border-left-color: #65a30d;
    }
    .component {
      border-top: 1px solid #f5f5f4;
      margin-top: 0.45rem;
      padding-top: 0.35rem;
    }
    #pair-select { margin: 0.5rem 0 1rem; padding: 0.25rem 0.5rem; }
"""
    body = f"""
  <h1>Compare variants</h1>
  <p class="lede">Assembly overlap between two trains. Shared parts, one-sided parts, unresolved identity, blockers, and substitution candidates stay labeled separately. Pick a pair — the page already contains every combination.</p>
  {control}
  {"".join(sections)}
  {script}
"""
    return shell(
        "Cognyx — compare",
        "compare.html",
        body,
        body_class="compare-page",
        extra_css=extra_css,
    )


def render_workflow(conn: sqlite3.Connection) -> str:
    counts = _pipeline_counts(conn)
    canonical_ready = counts["canonical_rows"] > 0
    steps = [
        ("done", "Done", "1. Ingest",
         f"{counts['files']} source files, {counts['bom_lines']} BOM lines, raw values kept."),
        ("done", "Done", "2. Validate",
         f"{counts['quarantined']} row quarantined. Soft warnings exist, many of them from column-name noise."),
        ("done", "Done", "3. Normalize",
         "Aliases, units, and supplier names are cleaned beside the raw value. See the Normalize page."),
        ("done", "Done", "4. Source entities",
         f"{counts['source_components']} components, {counts['source_assemblies']} assemblies, {counts['source_suppliers']} suppliers."),
        ("done", "Done", "5. Reconciliation proposals",
         f"{counts['proposals']} component proposals. {counts['pending']} are still pending. No one has accepted or rejected them. See the Proposals page."),
        ("missing", "Not yet", "6. Human decision",
         "Accept, reject, or redirect a proposal. This is Phase 3. The decision is stored. It does not overwrite the source row."),
        ("missing", "Not yet", "7. Canonical model",
         "One component, assembly, and variant the rest of the analysis is allowed to trust, plus a canonical BOM. These tables do not exist yet. This is the missing piece."),
        ("preview", "Preview", "8. Reuse snapshot",
         "The Reuse page is a preview from normalized references and notes. It is not yet computed from an accepted canonical BOM."),
        ("later", "Later", "9. Compare and explain",
         "Phase 4 adds variant-versus-variant and assembly overlap. Phase 5 puts a plain explanation on every row and finishes the edge cases."),
        ("later", "Later version", "10. Interactive workbench",
         "Filters, clicking a row, and deciding on screen. Not part of this PoC. It needs the canonical model first."),
    ]
    if canonical_ready:
        steps[6] = ("done", "Done", "7. Canonical model",
                    f"{counts['canonical_rows']} canonical component rows exist.")
    items = []
    for kind, badge, title, text in steps:
        items.append(
            "<li><div class=\"step-head\">"
            f"<h2>{html.escape(title)}</h2>"
            f"<span class=\"badge {kind}\">{html.escape(badge)}</span></div>"
            f"<p>{html.escape(text)}</p></li>"
        )
    body = f"""
  <h1>How the pipeline fits together</h1>
  <p class="lede">What is already in the database, what this preview report is doing, and what a later version still needs. Use this page while you talk. Open Normalize and Proposals to check the rows.</p>
  <ol class="flow">{''.join(items)}</ol>
  <section>
    <h2>What to say</h2>
    <div class="note">
      <p><strong>Accomplished.</strong> Messy PLM, ERP, and engineering notes are ingested, cleaned, and turned into reviewable proposals. Identity, similarity, and Nordic-only parts stay separate.</p>
      <p><strong>Missing.</strong> A canonical model, and a human decision that fills it. Until then, “already reused” means “same normalized reference,” not “an engineer accepted the match.”</p>
      <p><strong>Later.</strong> Comparison across variants, fuller explanations, then a screen where someone can filter and decide. Not required to show the pilot story.</p>
    </div>
  </section>
"""
    return shell("Cognyx — workflow", "workflow.html", body)


def render_normalize(conn: sqlite3.Connection) -> str:
    aliases = conn.execute(
        """
        SELECT component_ref_raw, component_ref_normalized, uom_raw, uom_normalized,
               supplier_raw, supplier_normalized, variant_ref_normalized
        FROM plm_bom_line
        WHERE component_ref_raw IS NOT NULL
          AND component_ref_normalized IS NOT NULL
          AND component_ref_raw != component_ref_normalized
        ORDER BY component_ref_normalized, variant_ref_normalized
        LIMIT 12
        """
    ).fetchall()
    units = conn.execute(
        """
        SELECT DISTINCT uom_raw, uom_normalized
        FROM plm_bom_line
        WHERE uom_raw IS NOT NULL AND uom_normalized IS NOT NULL
          AND UPPER(uom_raw) != UPPER(uom_normalized)
        ORDER BY uom_raw
        LIMIT 8
        """
    ).fetchall()
    suppliers = conn.execute(
        """
        SELECT DISTINCT supplier_raw, supplier_normalized
        FROM plm_bom_line
        WHERE supplier_raw IS NOT NULL AND supplier_normalized IS NOT NULL
          AND UPPER(supplier_raw) != UPPER(supplier_normalized)
        ORDER BY supplier_normalized
        LIMIT 8
        """
    ).fetchall()
    quarantine = conn.execute(
        "SELECT source_row, rejection_reason, raw_data FROM quarantine ORDER BY source_row LIMIT 5"
    ).fetchall()
    notes = conn.execute(
        """
        SELECT language, language_normalized, object_reference_raw, substr(note_text, 1, 140) AS excerpt
        FROM engineering_note
        WHERE language IS NOT NULL
        ORDER BY language, source_row
        LIMIT 6
        """
    ).fetchall()

    body = f"""
  <h1>Check normalization</h1>
  <p class="lede">Raw value on the left, cleaned value on the right. The source row is not overwritten.</p>
  <section>
    <h2>Reference aliases</h2>
    <p>These BOM lines did not use the canonical spelling. Normalization folded them.</p>
    {_table(["Variant", "Raw reference", "Normalized"], [
        [row["variant_ref_normalized"], row["component_ref_raw"], row["component_ref_normalized"]]
        for row in aliases
    ])}
  </section>
  <section>
    <h2>Units</h2>
    {_table(["Raw unit", "Normalized unit"], [[row["uom_raw"], row["uom_normalized"]] for row in units])}
  </section>
  <section>
    <h2>Supplier names</h2>
    {_table(["Raw supplier", "Normalized supplier"], [[row["supplier_raw"], row["supplier_normalized"]] for row in suppliers])}
  </section>
  <section>
    <h2>Quarantine</h2>
    <p>Structurally bad rows stay out of the BOM.</p>
    {_table(["Source row", "Reason"], [_quarantine_cells(row) for row in quarantine])}
  </section>
  <section>
    <h2>Note languages</h2>
    <p>Original wording is kept. Language is a label, not a translation.</p>
    {_table(["Language", "Reference", "Excerpt"], [
        [row["language_normalized"] or row["language"], row["object_reference_raw"], row["excerpt"]]
        for row in notes
    ])}
  </section>
"""
    return shell("Cognyx — normalization", "normalize.html", body)


def render_proposals(conn: sqlite3.Connection) -> str:
    rows = []
    if _table_exists(conn, "component_reconciliation"):
        rows = conn.execute(
            """
            SELECT r.status, r.method, r.confidence, r.component_id, r.evidence_json, r.rationale,
                   s.source_reference, s.normalized_reference, s.source_system
            FROM component_reconciliation r
            JOIN source_component s ON s.id = r.source_component_id
            """
        ).fetchall()
    identity = {}
    similarity = []
    nordic = []
    seen_pairs = set()
    for row in rows:
        try:
            evidence = json.loads(row["evidence_json"] or "{}")
        except json.JSONDecodeError:
            evidence = {}
        kind = evidence.get("relationship")
        if kind == "identity":
            key = evidence.get("canonical_ref") or row["normalized_reference"]
            bucket = identity.setdefault(key, {"refs": set(), "status": row["status"], "canonical_id": row["component_id"]})
            bucket["refs"].add(row["source_reference"])
            for member in evidence.get("cluster_members") or []:
                if member.get("source_reference"):
                    bucket["refs"].add(member["source_reference"])
        elif kind == "functional_similarity" and evidence.get("similarity_type") == "same_prefix_different_suffix":
            pair = tuple(sorted((evidence.get("reference_a") or "", evidence.get("reference_b") or "")))
            if pair[0] and pair not in seen_pairs:
                seen_pairs.add(pair)
                similarity.append(pair)
        elif kind == "variant_specific" and evidence.get("component_ref"):
            nordic.append(evidence["component_ref"])
    nordic = sorted(set(nordic))
    assembly_n = 0
    if _table_exists(conn, "assembly_reconciliation"):
        assembly_n = conn.execute("SELECT COUNT(*) AS n FROM assembly_reconciliation").fetchone()["n"]
    canonical_exists = _table_exists(conn, "component")

    identity_rows = [
        [ref, ", ".join(sorted(info["refs"])), info["status"], "—" if info["canonical_id"] is None else str(info["canonical_id"])]
        for ref, info in sorted(identity.items())
    ][:8]
    body = f"""
  <h1>Check reconciliation proposals</h1>
  <p class="lede">Proposals only. Nothing here has been accepted into a canonical component. Canonical id stays empty on purpose.</p>
  <div class="counts">
    <span>{len(rows)} component proposals</span>
    <span>{len(identity)} identity clusters</span>
    <span>{len(similarity)} similarity pairs</span>
    <span>{len(nordic)} Nordic-only parts</span>
    <span>{assembly_n} assembly proposals</span>
    <span>{"canonical table exists" if canonical_exists else "no canonical table"}</span>
  </div>
  <section>
    <h2>Same part, different ids</h2>
    <p>These raw references share one normalized key. They are waiting for a person to accept the link.</p>
    {_table(["Normalized", "Raw references in the cluster", "Status", "Canonical id"], identity_rows)}
  </section>
  <section>
    <h2>Similar, not merged</h2>
    {_table(["Left", "Right"], [[a, b] for a, b in similarity[:8]])}
  </section>
  <section>
    <h2>Nordic-only</h2>
    <p>Intentional for the cold-rated variant. Not offered as a generic duplicate.</p>
    {_table(["Reference"], [[ref] for ref in nordic[:8]])}
  </section>
"""
    return shell("Cognyx — proposals", "proposals.html", body)


def render_canonical(conn: sqlite3.Connection) -> str:
    """Accepted identity clusters with canonical id, plus unresolved identity lines."""
    accepted_rows = []
    if _table_exists(conn, "component_reconciliation"):
        accepted_rows = conn.execute(
            """
            SELECT r.component_id, r.status, r.evidence_json,
                   s.source_reference, s.normalized_reference
            FROM component_reconciliation r
            JOIN source_component s ON s.id = r.source_component_id
            WHERE r.status = 'ACCEPTED'
            ORDER BY r.component_id, s.source_reference
            """
        ).fetchall()

    clusters: Dict[object, Dict[str, object]] = {}
    for row in accepted_rows:
        try:
            evidence = json.loads(row["evidence_json"] or "{}")
        except json.JSONDecodeError:
            evidence = {}
        if evidence.get("relationship", "identity") != "identity":
            continue
        key = row["component_id"]
        bucket = clusters.setdefault(
            key,
            {"canonical_id": key, "normalized": row["normalized_reference"], "refs": set()},
        )
        bucket["refs"].add(row["source_reference"])
        if row["normalized_reference"]:
            bucket["normalized"] = row["normalized_reference"]

    cluster_table = [
        [
            str(info["canonical_id"]) if info["canonical_id"] is not None else "—",
            info["normalized"] or "—",
            ", ".join(sorted(info["refs"])),
        ]
        for _, info in sorted(
            clusters.items(),
            key=lambda item: (item[0] is None, item[0] or 0),
        )
    ]

    unique_unresolved: List[List[object]] = []
    if _table_exists(conn, "plm_bom_line") and _table_exists(conn, "component_reconciliation"):
        pending_or_rejected = conn.execute(
            """
            SELECT b.id AS bom_line_id, b.variant_ref_normalized, b.component_ref_raw,
                   r.status, r.evidence_json
            FROM plm_bom_line b
            JOIN source_component s
              ON s.source_system = 'PLM' AND s.source_reference = b.component_ref_raw
            JOIN component_reconciliation r ON r.source_component_id = s.id
            WHERE r.status IN ('PENDING', 'ASSESSED', 'REJECTED')
            ORDER BY b.id, r.id
            """
        ).fetchall()
        seen = set()
        for row in pending_or_rejected:
            if row["bom_line_id"] in seen:
                continue
            try:
                evidence = json.loads(row["evidence_json"] or "{}")
            except json.JSONDecodeError:
                evidence = {}
            if evidence.get("relationship", "identity") != "identity":
                continue
            seen.add(row["bom_line_id"])
            reason = (
                "identity_rejected"
                if row["status"] == "REJECTED"
                else "identity_pending"
            )
            unique_unresolved.append(
                [
                    row["bom_line_id"],
                    row["variant_ref_normalized"],
                    row["component_ref_raw"],
                    reason,
                ]
            )

    bom_n = 0
    if _table_exists(conn, "bom_relationship"):
        bom_n = conn.execute("SELECT COUNT(*) AS n FROM bom_relationship").fetchone()["n"]

    body = f"""
  <h1>Canonical BOM</h1>
  <p class="lede">Accepted identity clusters share one canonical id. BOM lines whose identity is still pending or was rejected stay unresolved and are not in the authoritative BOM.</p>
  <div class="counts">
    <span>{len(clusters)} accepted identity clusters</span>
    <span>{bom_n} canonical BOM rows</span>
    <span>{len(unique_unresolved)} unresolved identity lines</span>
  </div>
  <section>
    <h2>Accepted identity clusters</h2>
    <p>These source references share a canonical component after a human accept.</p>
    {_table(["Canonical id", "Normalized reference", "Source references"], cluster_table)}
  </section>
  <section>
    <h2>Unresolved because of identity</h2>
    <p>Pending or rejected identity keeps these source BOM lines out of <code>bom_relationship</code>.</p>
    {_table(["BOM line id", "Variant", "Component ref", "Reason"], unique_unresolved)}
  </section>
"""
    return shell("Cognyx — canonical", "canonical.html", body)


def _pipeline_counts(conn: sqlite3.Connection) -> Dict[str, int]:
    def n(sql: str) -> int:
        try:
            return conn.execute(sql).fetchone()[0]
        except sqlite3.OperationalError:
            return 0

    return {
        "files": n("SELECT COUNT(*) FROM source_file"),
        "bom_lines": n("SELECT COUNT(*) FROM plm_bom_line"),
        "quarantined": n("SELECT COUNT(*) FROM quarantine"),
        "source_components": n("SELECT COUNT(*) FROM source_component"),
        "source_assemblies": n("SELECT COUNT(*) FROM source_assembly"),
        "source_suppliers": n("SELECT COUNT(*) FROM source_supplier"),
        "proposals": n("SELECT COUNT(*) FROM component_reconciliation"),
        "pending": n("SELECT COUNT(*) FROM component_reconciliation WHERE status = 'PENDING'"),
        "canonical_rows": n("SELECT COUNT(*) FROM component") if _table_exists(conn, "component") else 0,
    }


def _table(headers: List[str], rows: List[List[object]]) -> str:
    head = "".join(f"<th>{html.escape(str(h))}</th>" for h in headers)
    if not rows:
        body = f'<tr><td colspan="{len(headers)}">Nothing to show.</td></tr>'
    else:
        body = "".join(
            "<tr>" + "".join(f"<td>{html.escape('' if cell is None else str(cell))}</td>" for cell in row) + "</tr>"
            for row in rows
        )
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def _quarantine_cells(row) -> List[str]:
    reason = row["rejection_reason"] or ""
    try:
        payload = json.loads(row["raw_data"])
    except (json.JSONDecodeError, TypeError):
        payload = {}
    qty = payload.get("quantity")
    if qty:
        reason = f"{reason} (quantity {qty})"
    return [str(row["source_row"]), reason]


def _table_exists(conn: sqlite3.Connection, name: str) -> bool:
    found = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (name,),
    ).fetchone()
    return found is not None
