"""One-page pilot snapshot for the client demo.

Reads the ingested database and writes a single HTML file. No web server.
Phase 3 analysis should fill the same sections; this page is the PoC surface.
"""
from __future__ import annotations

import html
import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

_VOLTAGE_RE = re.compile(r"(?i)(\d+)\s*V")
_RUGGED_RE = re.compile(r"(?i)\brugged\b")

REPO_ROOT = Path(__file__).resolve().parents[2]


def prepare_database(conn: sqlite3.Connection, inputs_dir: Path) -> None:
    """Ingest, normalize, extract, and reconcile. Safe to run again."""
    from app.services.extraction import run_source_extraction
    from app.services.ingestion import ingest_all_files
    from app.services.normalization import normalize_engineering_notes, normalize_erp_materials
    from app.services.reconciliation import run_full_reconciliation

    ingest_all_files(conn, inputs_dir)
    normalize_erp_materials(conn)
    normalize_engineering_notes(conn)
    run_source_extraction(conn)
    run_full_reconciliation(conn)


def build_snapshot(conn: sqlite3.Connection, limit: int = 8) -> Dict[str, Any]:
    """Client-facing sections from the current pipeline. Does not read ground truth."""
    variant_names = _variant_names(conn)
    reused = _section_already_reused(conn, variant_names)
    candidates = _section_candidates(conn)
    separate = _kept_separate(conn)
    blockers = _section_blockers(conn)
    issues = _section_data_issues(conn)

    bom_count = conn.execute("SELECT COUNT(*) AS n FROM plm_bom_line").fetchone()["n"]
    quarantine_count = conn.execute("SELECT COUNT(*) AS n FROM quarantine").fetchone()["n"]

    return {
        "title": "Which parts are reused across train variants?",
        "lede": (
            "Pilot snapshot for the Valenciennes regional-train BOMs. "
            "Same reference across variants is listed as already reused. "
            "Similar parts stay separate until someone reviews them. "
            "Conflicts and bad rows are shown, not cleaned away."
        ),
        "counts": {
            "variants": len(variant_names),
            "bom_lines": bom_count,
            "quarantined": quarantine_count,
            "already_reused": len(reused),
            "candidates": len(candidates),
            "kept_separate": len(separate),
        },
        "already_reused": reused[:limit],
        "already_reused_total": len(reused),
        "candidates": candidates[:limit],
        "candidates_total": len(candidates),
        "kept_separate": separate[:limit],
        "kept_separate_total": len(separate),
        "blockers": blockers,
        "data_issues": issues[:limit],
        "data_issues_total": len(issues),
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    }


def render_report_html(snapshot: Dict[str, Any]) -> str:
    """Render the snapshot as one self-contained HTML page."""
    e = html.escape
    counts = snapshot["counts"]
    sections = [
        _section(
            "Already reused",
            "reuse",
            "The same normalized part number shows up on more than one variant.",
            snapshot["already_reused"],
            snapshot["already_reused_total"],
            lambda item: (
                f"<strong>{e(item['ref'])}</strong>",
                e(item["explanation"]),
                e(", ".join(item["variants"])),
            ),
        ),
        _section(
            "Worth a look",
            "candidate",
            "These look close. They are not treated as the same part.",
            snapshot["candidates"],
            snapshot["candidates_total"],
            lambda item: (
                f"<strong>{e(item['left'])}</strong> and <strong>{e(item['right'])}</strong>",
                e(item["explanation"]),
                "",
            ),
        ),
        _section(
            "Intentional differences",
            "separate",
            "Nordic-only parts. They are a variant choice, not a duplicate.",
            snapshot["kept_separate"],
            snapshot["kept_separate_total"],
            lambda item: (
                f"<strong>{e(item['ref'])}</strong>",
                e(item["explanation"]),
                "",
            ),
        ),
        _section(
            "Blocked",
            "blocker",
            "Evidence disagrees, or lifecycle does not match. Nothing here was overwritten.",
            snapshot["blockers"],
            len(snapshot["blockers"]),
            lambda item: (
                f"<strong>{e(item['title'])}</strong>",
                e(item["explanation"]),
                "",
            ),
        ),
        _section(
            "Data issues",
            "issue",
            "Rows the pipeline refused or flagged. Separate from the question of identity.",
            snapshot["data_issues"],
            snapshot["data_issues_total"],
            lambda item: (
                f"<strong>{e(item['title'])}</strong>",
                e(item["explanation"]),
                "",
            ),
        ),
    ]

    body = "\n".join(sections)
    from app.services.html_pages import shell
    inner = f"""
  <h1>{e(snapshot["title"])}</h1>
  <p class="lede">{e(snapshot["lede"])}</p>
  <div class="counts">
    <span>{counts["variants"]} variants</span>
    <span>{counts["bom_lines"]} BOM lines</span>
    <span>{counts["quarantined"]} quarantined</span>
    <span>{counts["already_reused"]} shared parts</span>
    <span>{counts["candidates"]} candidates</span>
  </div>
  {body}
  <p class="meta">Generated {e(snapshot["generated_at"])}. This page is a preview from normalized references, not from an accepted canonical model. ERP material ids are not merged into PLM part numbers.</p>
"""
    return shell("Cognyx — reuse snapshot", "report.html", inner)


def write_report(conn: sqlite3.Connection, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_report_html(build_snapshot(conn)), encoding="utf-8")
    return output_path


def _section(title, css, intro, items, total, render_item) -> str:
    e = html.escape
    cards = []
    for item in items:
        heading, explanation, meta = render_item(item)
        meta_html = f'<p class="meta">{meta}</p>' if meta else ""
        cards.append(
            f'<article class="{css}"><p>{heading}</p><p>{explanation}</p>{meta_html}</article>'
        )
    if not cards:
        cards.append('<article><p>Nothing in this category.</p></article>')
    more = ""
    if total > len(items):
        more = f"<p class=\"meta\">Showing {len(items)} of {total}.</p>"
    return (
        f"<section><h2>{e(title)}</h2><p>{e(intro)}</p>"
        f"{''.join(cards)}{more}</section>"
    )


def _section_already_reused(
    conn: sqlite3.Connection, variant_names: Dict[str, str]
) -> List[Dict[str, Any]]:
    """Prefer analysis.already_reused; fall back to BOM preview if canonical empty."""
    try:
        from app.services.analysis import already_reused as analysis_reused

        rows = analysis_reused(conn)
    except Exception:
        rows = []
    if rows:
        items = []
        for row in rows:
            refs = row.get("variant_refs") or []
            labels = [variant_names.get(v, v) for v in refs]
            items.append(
                {
                    "ref": row.get("name") or str(row.get("canonical_id")),
                    "variants": labels,
                    "explanation": row.get("explanation") or "",
                }
            )
        return items
    return _already_reused(conn, variant_names)


def _section_candidates(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    try:
        from app.services.analysis import reusable_candidates

        rows = reusable_candidates(conn)
    except Exception:
        rows = []
    if rows:
        items = []
        for row in rows:
            left = row.get("left_ref") or row.get("left") or ""
            right = row.get("right_ref") or row.get("right") or ""
            items.append(
                {
                    "left": str(left),
                    "right": str(right),
                    "explanation": row.get("explanation") or "",
                }
            )
        items.sort(key=lambda item: (item["left"], item["right"]))
        return items
    return _candidates(conn)


def _section_blockers(conn: sqlite3.Connection) -> List[Dict[str, str]]:
    try:
        from app.services.quality import blockers as quality_blockers

        rows = quality_blockers(conn)
    except Exception:
        return _blockers(conn)
    items = []
    for row in rows:
        values = row.get("values") or []
        title = f"{row.get('entity_ref')}: {', '.join(values)}" if values else str(
            row.get("entity_ref")
        )
        items.append({"title": title, "explanation": row.get("explanation") or ""})
    return items


def _section_data_issues(conn: sqlite3.Connection) -> List[Dict[str, str]]:
    try:
        from app.services.quality import data_quality_issues

        payload = data_quality_issues(conn)
        rows = payload.get("issues") or []
    except Exception:
        return _data_issues(conn)
    items = []
    for row in rows:
        refs = row.get("refs") or []
        label = ", ".join(str(r) for r in refs[:3]) if refs else row.get("issue_type", "issue")
        items.append(
            {
                "title": f"{row.get('issue_type')}: {label}",
                "explanation": row.get("explanation") or "",
            }
        )
    return items


def _variant_names(conn: sqlite3.Connection) -> Dict[str, str]:
    names = {}
    for row in conn.execute(
        """
        SELECT variant_ref_normalized, variant_name_raw
        FROM plm_variant
        WHERE variant_ref_normalized IS NOT NULL
        """
    ):
        ref = row["variant_ref_normalized"]
        label = (row["variant_name_raw"] or "").strip()
        names[ref] = f"{label} ({ref})" if label else ref
    return names


def _already_reused(conn: sqlite3.Connection, variant_names: Dict[str, str]) -> List[Dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT variant_ref_normalized, component_ref_raw, component_ref_normalized
        FROM plm_bom_line
        WHERE component_ref_normalized IS NOT NULL
          AND component_ref_normalized != ''
        """
    ).fetchall()
    grouped: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        ref = row["component_ref_normalized"]
        bucket = grouped.setdefault(ref, {"variants": set(), "raws": set()})
        if row["variant_ref_normalized"]:
            bucket["variants"].add(row["variant_ref_normalized"])
        if row["component_ref_raw"]:
            bucket["raws"].add(row["component_ref_raw"])

    items = []
    for ref, bucket in grouped.items():
        if len(bucket["variants"]) < 2:
            continue
        labels = [variant_names.get(v, v) for v in sorted(bucket["variants"])]
        raws = sorted(bucket["raws"])
        explanation = f"Present on {len(labels)} variants."
        if len(raws) > 1:
            explanation += (
                " Normalization folded these raw references into one: "
                + ", ".join(raws)
                + "."
            )
        items.append({"ref": ref, "variants": labels, "explanation": explanation})
    items.sort(key=lambda item: (-len(item["variants"]), item["ref"]))
    return items


def _candidates(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    seen = set()
    items = []
    if _table_exists(conn, "component_reconciliation"):
        for row in conn.execute(
            "SELECT evidence_json, rationale FROM component_reconciliation WHERE evidence_json IS NOT NULL"
        ):
            try:
                evidence = json.loads(row["evidence_json"])
            except json.JSONDecodeError:
                continue
            if evidence.get("relationship") != "functional_similarity":
                continue
            # The suffix heuristic pairs unrelated sensors (BAT-TEMP-01 / CAPT-TEMP-01).
            # The client page only shows same-family prefixes, plus the camera pair below.
            if evidence.get("similarity_type") != "same_prefix_different_suffix":
                continue
            left = evidence.get("reference_a") or ""
            right = evidence.get("reference_b") or ""
            key = tuple(sorted((left, right)))
            if not left or not right or key in seen:
                continue
            seen.add(key)
            items.append(
                {
                    "left": left,
                    "right": right,
                    "explanation": (
                        f"{left} and {right} belong to the same reference family "
                        "but are different parts. Someone has to decide whether one "
                        "could stand in for the other."
                    ),
                }
            )

    camera = _rugged_camera_pair(conn)
    if camera is not None:
        key = tuple(sorted((camera["left"], camera["right"])))
        if key not in seen:
            items.append(camera)

    items.sort(key=lambda item: (item["left"], item["right"]))
    if camera is not None:
        items.sort(key=lambda item: (item["left"], item["right"]) != (camera["left"], camera["right"]))
    return items


def _rugged_camera_pair(conn: sqlite3.Connection) -> Optional[Dict[str, str]]:
    materials = conn.execute(
        """
        SELECT material_id_raw, description_raw, category_raw
        FROM erp_material
        WHERE description_raw IS NOT NULL
        """
    ).fetchall()
    by_key: Dict[tuple, List[sqlite3.Row]] = {}
    for row in materials:
        stripped = _RUGGED_RE.sub("", row["description_raw"])
        stripped = re.sub(r"\s+", " ", stripped).strip().lower()
        if not stripped:
            continue
        by_key.setdefault((row["category_raw"] or "", stripped), []).append(row)

    pair = None
    for group in by_key.values():
        if len(group) < 2:
            continue
        descriptions = {(row["description_raw"] or "").lower() for row in group}
        if not any("rugged" in text for text in descriptions):
            continue
        if not any("rugged" not in text for text in descriptions):
            continue
        ordered = sorted(group, key=lambda row: row["material_id_raw"])
        left, right = ordered[0], ordered[1]
        if "camera" not in (left["description_raw"] or "").lower() and "camera" not in (right["description_raw"] or "").lower():
            continue
        notes = conn.execute(
            """
            SELECT source_row, object_reference_raw
            FROM engineering_note
            WHERE object_reference_raw IN ('PASSCOUNT-CAMERA', 'PASSCOUNT-CAMERA-RUGGED')
            ORDER BY source_row
            """
        ).fetchall()
        note_label = " and ".join(n["object_reference_raw"] for n in notes)
        explanation = (
            f"{left['description_raw']} ({left['material_id_raw']}) and "
            f"{right['description_raw']} ({right['material_id_raw']}) share a function. "
            "Housing and temperature qualification differ, so they stay two parts."
        )
        if note_label:
            explanation += f" See engineering notes on {note_label}."
        pair = {"left": left["material_id_raw"], "right": right["material_id_raw"], "explanation": explanation}
        break
    return pair


def _kept_separate(conn: sqlite3.Connection) -> List[Dict[str, str]]:
    if not _table_exists(conn, "component_reconciliation"):
        return []
    seen = set()
    items = []
    for row in conn.execute(
        "SELECT evidence_json, rationale FROM component_reconciliation WHERE evidence_json IS NOT NULL"
    ):
        try:
            evidence = json.loads(row["evidence_json"])
        except json.JSONDecodeError:
            continue
        if evidence.get("relationship") != "variant_specific":
            continue
        ref = evidence.get("component_ref")
        if not ref or ref in seen:
            continue
        seen.add(ref)
        variant = evidence.get("variant_ref") or "the Nordic variant"
        items.append(
            {
                "ref": ref,
                "explanation": f"Used only on {variant}. Kept as its own part, not offered as a generic substitute.",
            }
        )
    items.sort(key=lambda item: item["ref"])
    return items


def _blockers(conn: sqlite3.Connection) -> List[Dict[str, str]]:
    items = []
    for row in conn.execute(
        """
        SELECT object_reference_raw, note_text, source_row
        FROM engineering_note
        WHERE note_text IS NOT NULL
        """
    ):
        volts = sorted({f"{int(n)} V DC" for n in _VOLTAGE_RE.findall(row["note_text"])})
        # 24 V and 48 V on the same note is the conflict. A converter note that
        # states 750 V in and 24 V out is one specification, not a disagreement.
        if "24 V DC" not in volts or "48 V DC" not in volts:
            continue
        items.append(
            {
                "title": f"{row['object_reference_raw']}: {' and '.join(volts)}",
                "explanation": (
                    f"An engineering note on {row['object_reference_raw']} states both "
                    "24 V DC and 48 V DC. Both values are kept. No voltage was chosen for you."
                ),
            }
        )

    odd_lifecycle = conn.execute(
        """
        SELECT assembly_ref_raw, variant_ref_raw, lifecycle_raw, assembly_description_raw
        FROM plm_assembly
        WHERE lifecycle_raw IS NOT NULL
          AND TRIM(lifecycle_raw) != ''
          AND LOWER(lifecycle_raw) != 'released'
        ORDER BY assembly_ref_raw
        """
    ).fetchall()
    released = conn.execute(
        """
        SELECT COUNT(*) AS n FROM plm_assembly
        WHERE LOWER(COALESCE(lifecycle_raw, '')) = 'released'
        """
    ).fetchone()["n"]
    for row in odd_lifecycle:
        items.append(
            {
                "title": f"{row['assembly_ref_raw']} is {row['lifecycle_raw']}",
                "explanation": (
                    f"{row['assembly_description_raw'] or 'This assembly'} on {row['variant_ref_raw']} "
                    f"is {row['lifecycle_raw']}. {released} other assemblies are Released. "
                    "This is a lifecycle mismatch, not an identity match."
                ),
            }
        )

    obsolete = conn.execute(
        """
        SELECT material_id_raw, description_raw
        FROM erp_material
        WHERE UPPER(COALESCE(status_raw, '')) = 'OBSOLETE'
        ORDER BY material_id_raw
        """
    ).fetchall()
    if obsolete:
        listed = ", ".join(f"{row['material_id_raw']} ({row['description_raw']})" for row in obsolete)
        items.append(
            {
                "title": "ERP materials marked obsolete",
                "explanation": (
                    f"{listed}. These statuses are reported on their own. "
                    "They are not paired with a PLM assembly."
                ),
            }
        )
    return items


def _data_issues(conn: sqlite3.Connection) -> List[Dict[str, str]]:
    items = []
    for row in conn.execute(
        """
        SELECT source_row, raw_data, rejection_reason
        FROM quarantine
        ORDER BY source_row
        """
    ):
        detail = row["rejection_reason"] or "Rejected during ingest."
        try:
            payload = json.loads(row["raw_data"])
        except (json.JSONDecodeError, TypeError):
            payload = {}
        qty = payload.get("quantity")
        ref = payload.get("component_ref") or payload.get("plm_row_id") or f"row {row['source_row']}"
        if qty:
            detail = f"Quantity is {qty!r}. {detail}"
        items.append(
            {
                "title": f"Quarantined {ref}",
                "explanation": detail,
            }
        )

    groups: Dict[tuple, List[str]] = {}
    for row in conn.execute(
        """
        SELECT source_row, variant_ref_normalized, assembly_ref_normalized,
               component_ref_normalized, component_ref_raw
        FROM plm_bom_line
        WHERE component_ref_normalized IS NOT NULL
        """
    ):
        key = (
            row["variant_ref_normalized"],
            row["assembly_ref_normalized"],
            row["component_ref_normalized"],
        )
        groups.setdefault(key, []).append(row["component_ref_raw"] or "")
    for key, raws in sorted(groups.items()):
        if len(raws) < 2:
            continue
        variant, assembly, component = key
        distinct = ", ".join(sorted(set(raws)))
        items.append(
            {
                "title": f"Duplicate BOM key {component}",
                "explanation": (
                    f"{variant} / {assembly} lists this part {len(raws)} times "
                    f"(raw references: {distinct})."
                ),
            }
        )
    return items


def _table_exists(conn: sqlite3.Connection, name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (name,),
    ).fetchone()
    return row is not None
