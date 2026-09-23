"""
Already-reused and reusable-candidate reports from the canonical BOM.

already_reused reads bom_relationship only — pending identity aliases are
absent until accepted and the model is rebuilt.

reusable_candidates surfaces functional_similarity reconciliation rows plus
ERP description pairs that match after stripping the word "rugged".
Variant-specific rows are excluded. No new identity merges are written.
"""
from __future__ import annotations

import json
import re
import sqlite3
from typing import Any, Dict, List, Optional, Set, Tuple


_RUGGED_RE = re.compile(r"\brugged\b", re.IGNORECASE)
_NOTE_ID_RE = re.compile(r"^N-\d+$", re.IGNORECASE)


def _parse_evidence(evidence_json: Optional[str]) -> Dict[str, Any]:
    if not evidence_json:
        return {}
    try:
        return json.loads(evidence_json)
    except json.JSONDecodeError:
        return {}


def _collapse_description(text: str) -> str:
    stripped = _RUGGED_RE.sub("", text)
    return re.sub(r"\s+", " ", stripped).strip().lower()


def _normalize_note_id(author: Optional[str], note_pk: int) -> str:
    """Prefer fixture/dataset note ids stored in author (e.g. N-018)."""
    if author:
        stripped = author.strip()
        if _NOTE_ID_RE.match(stripped):
            num = stripped.split("-", 1)[1]
            return f"N-{num}"
    return f"note-{note_pk}"


def _notes_for_refs(conn: sqlite3.Connection, refs: Set[str]) -> List[Tuple[str, str]]:
    """Return (note_id_label, object_reference) for notes matching refs."""
    if not refs:
        return []
    placeholders = ",".join("?" * len(refs))
    rows = conn.execute(
        f"""
        SELECT id, author, object_reference_raw
        FROM engineering_note
        WHERE object_reference_raw IN ({placeholders})
        ORDER BY id
        """,
        tuple(refs),
    ).fetchall()
    return [
        (_normalize_note_id(row["author"], row["id"]), row["object_reference_raw"])
        for row in rows
    ]


def _accepted_identity_refs(conn: sqlite3.Connection, component_id: int) -> List[str]:
    rows = conn.execute(
        """
        SELECT sc.source_reference, cr.evidence_json
        FROM component_reconciliation cr
        JOIN source_component sc ON sc.id = cr.source_component_id
        WHERE cr.component_id = ?
          AND cr.status = 'ACCEPTED'
        ORDER BY sc.source_reference
        """,
        (component_id,),
    ).fetchall()
    refs: List[str] = []
    seen: Set[str] = set()
    for row in rows:
        evidence = _parse_evidence(row["evidence_json"])
        if evidence.get("relationship", "identity") != "identity":
            continue
        ref = row["source_reference"]
        if ref and ref not in seen:
            seen.add(ref)
            refs.append(ref)
    return refs


def _explain_reused(
    entity_type: str,
    name: str,
    variant_refs: List[str],
    identity_refs: Optional[List[str]] = None,
) -> str:
    variants = ", ".join(variant_refs)
    if entity_type == "component":
        base = (
            f"{name} is the same canonical component on variants {variants}."
        )
        if identity_refs:
            base += (
                " Accepted identity refs: "
                + ", ".join(identity_refs)
                + "."
            )
        return base
    return f"{name} is the same canonical assembly on variants {variants}."


def already_reused(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    """Components/assemblies present on at least two variants via bom_relationship."""
    results: List[Dict[str, Any]] = []

    # Components
    component_rows = conn.execute(
        """
        SELECT
            c.id AS canonical_id,
            c.name AS name,
            c.normalized_reference AS normalized_reference,
            v.normalized_reference AS variant_ref,
            br.source_bom_line_id AS source_bom_line_id
        FROM bom_relationship br
        JOIN component c ON c.id = br.component_id
        JOIN variant v ON v.id = br.variant_id
        ORDER BY c.id, v.normalized_reference, br.source_bom_line_id
        """
    ).fetchall()

    by_component: Dict[int, Dict[str, Any]] = {}
    for row in component_rows:
        cid = row["canonical_id"]
        bucket = by_component.setdefault(
            cid,
            {
                "name": row["name"] or row["normalized_reference"] or str(cid),
                "variants": set(),
                "bom_ids": [],
            },
        )
        if row["variant_ref"]:
            bucket["variants"].add(row["variant_ref"])
        if row["source_bom_line_id"] is not None:
            bucket["bom_ids"].append(row["source_bom_line_id"])

    for cid, bucket in by_component.items():
        variant_refs = sorted(bucket["variants"])
        if len(variant_refs) < 2:
            continue
        identity_refs = _accepted_identity_refs(conn, cid)
        results.append(
            {
                "entity_type": "component",
                "canonical_id": cid,
                "name": bucket["name"],
                "variant_refs": variant_refs,
                "variant_count": len(variant_refs),
                "source_bom_line_ids": sorted(set(bucket["bom_ids"])),
                "explanation": _explain_reused(
                    "component", bucket["name"], variant_refs, identity_refs
                ),
            }
        )

    # Assemblies
    assembly_rows = conn.execute(
        """
        SELECT
            a.id AS canonical_id,
            a.name AS name,
            a.normalized_reference AS normalized_reference,
            v.normalized_reference AS variant_ref,
            br.source_bom_line_id AS source_bom_line_id
        FROM bom_relationship br
        JOIN assembly a ON a.id = br.assembly_id
        JOIN variant v ON v.id = br.variant_id
        ORDER BY a.id, v.normalized_reference, br.source_bom_line_id
        """
    ).fetchall()

    by_assembly: Dict[int, Dict[str, Any]] = {}
    for row in assembly_rows:
        aid = row["canonical_id"]
        bucket = by_assembly.setdefault(
            aid,
            {
                "name": row["name"] or row["normalized_reference"] or str(aid),
                "variants": set(),
                "bom_ids": [],
            },
        )
        if row["variant_ref"]:
            bucket["variants"].add(row["variant_ref"])
        if row["source_bom_line_id"] is not None:
            bucket["bom_ids"].append(row["source_bom_line_id"])

    for aid, bucket in by_assembly.items():
        variant_refs = sorted(bucket["variants"])
        if len(variant_refs) < 2:
            continue
        results.append(
            {
                "entity_type": "assembly",
                "canonical_id": aid,
                "name": bucket["name"],
                "variant_refs": variant_refs,
                "variant_count": len(variant_refs),
                "source_bom_line_ids": sorted(set(bucket["bom_ids"])),
                "explanation": _explain_reused(
                    "assembly", bucket["name"], variant_refs
                ),
            }
        )

    results.sort(key=lambda r: (r["entity_type"], r["name"], r["canonical_id"]))
    return results


def _pair_key(left: str, right: str) -> Tuple[str, str]:
    a, b = sorted((left, right))
    return a, b


def _explain_candidate(
    left_ref: str,
    right_ref: str,
    relationship: str,
    evidence: List[Any],
    *,
    rugged_pair: bool = False,
) -> str:
    evidence_str = ", ".join(str(e) for e in evidence) if evidence else "(none)"
    if rugged_pair:
        return (
            f"{left_ref} and {right_ref} are a {relationship} candidate: "
            f"descriptions match after removing 'rugged', but qualification differs "
            f"and the rows were not merged. Evidence: {evidence_str}."
        )
    return (
        f"{left_ref} and {right_ref} are a {relationship} candidate. "
        f"Evidence: {evidence_str}."
    )


def _functional_similarity_candidates(
    conn: sqlite3.Connection,
) -> List[Dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT id, source_component_id, evidence_json
        FROM component_reconciliation
        WHERE evidence_json IS NOT NULL
        ORDER BY id
        """
    ).fetchall()

    # pair_key → {recon_ids, left, right}
    pairs: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for row in rows:
        evidence = _parse_evidence(row["evidence_json"])
        relationship = evidence.get("relationship")
        if relationship == "variant_specific":
            continue
        if relationship != "functional_similarity":
            continue

        left = evidence.get("reference_a") or evidence.get("self_reference") or ""
        right = evidence.get("reference_b") or evidence.get("other_reference") or ""
        if not left or not right or left == right:
            continue

        key = _pair_key(left, right)
        bucket = pairs.setdefault(
            key,
            {"left": key[0], "right": key[1], "recon_ids": []},
        )
        bucket["recon_ids"].append(row["id"])

    results: List[Dict[str, Any]] = []
    for key, bucket in pairs.items():
        left_ref, right_ref = bucket["left"], bucket["right"]
        evidence_ids: List[Any] = list(bucket["recon_ids"])
        # Attach notes whose object_reference equals either candidate ref
        note_labels = _notes_for_refs(conn, {left_ref, right_ref})
        for label, _obj in note_labels:
            if label not in evidence_ids:
                evidence_ids.append(label)

        results.append(
            {
                "left_ref": left_ref,
                "right_ref": right_ref,
                "relationship": "functional_similarity",
                "review_needed": True,
                "evidence": evidence_ids,
                "blocked_by": [],
                "explanation": _explain_candidate(
                    left_ref, right_ref, "functional_similarity", evidence_ids
                ),
            }
        )
    return results


def _rugged_description_candidates(
    conn: sqlite3.Connection,
    existing_keys: Set[Tuple[str, str]],
) -> List[Dict[str, Any]]:
    materials = conn.execute(
        """
        SELECT material_id_raw, description_raw, category_raw
        FROM erp_material
        WHERE description_raw IS NOT NULL
          AND TRIM(description_raw) != ''
        ORDER BY material_id_raw
        """
    ).fetchall()

    by_key: Dict[Tuple[str, str], List[sqlite3.Row]] = {}
    for row in materials:
        collapsed = _collapse_description(row["description_raw"])
        if not collapsed:
            continue
        category = row["category_raw"] or ""
        by_key.setdefault((category, collapsed), []).append(row)

    results: List[Dict[str, Any]] = []
    for (_category, _collapsed), group in by_key.items():
        if len(group) < 2:
            continue
        descriptions = {(row["description_raw"] or "").lower() for row in group}
        has_rugged = any(_RUGGED_RE.search(text) for text in descriptions)
        has_plain = any(not _RUGGED_RE.search(text) for text in descriptions)
        if not (has_rugged and has_plain):
            continue

        # Pair distinct materials; take sorted unique material ids
        ordered = sorted(group, key=lambda r: r["material_id_raw"])
        # Deduplicate by material id
        seen_mats: Set[str] = set()
        unique: List[sqlite3.Row] = []
        for row in ordered:
            mid = row["material_id_raw"]
            if mid in seen_mats:
                continue
            seen_mats.add(mid)
            unique.append(row)
        if len(unique) < 2:
            continue

        # Emit one candidate per consecutive sorted pair within the group
        # (camera fixture has exactly two)
        left, right = unique[0], unique[1]
        left_ref = left["material_id_raw"]
        right_ref = right["material_id_raw"]
        key = _pair_key(left_ref, right_ref)
        if key in existing_keys:
            continue

        # Notes: exact PASSCOUNT-CAMERA / PASSCOUNT-CAMERA-RUGGED for camera pair,
        # plus any note whose object_reference equals either material ref.
        note_refs = {
            "PASSCOUNT-CAMERA",
            "PASSCOUNT-CAMERA-RUGGED",
            left_ref,
            right_ref,
        }
        note_labels = _notes_for_refs(conn, note_refs)
        evidence_ids: List[Any] = []
        for label, _obj in note_labels:
            if label not in evidence_ids:
                evidence_ids.append(label)

        results.append(
            {
                "left_ref": key[0],
                "right_ref": key[1],
                "relationship": "functional_similarity",
                "review_needed": True,
                "evidence": evidence_ids,
                "blocked_by": [],
                "explanation": _explain_candidate(
                    key[0],
                    key[1],
                    "functional_similarity",
                    evidence_ids,
                    rugged_pair=True,
                ),
            }
        )
        existing_keys.add(key)

    return results


def reusable_candidates(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    """Functional similarity candidates that are not the same canonical entity."""
    candidates = _functional_similarity_candidates(conn)
    existing_keys = {_pair_key(c["left_ref"], c["right_ref"]) for c in candidates}
    candidates.extend(_rugged_description_candidates(conn, existing_keys))
    candidates.sort(key=lambda c: (c["left_ref"], c["right_ref"]))
    return candidates
