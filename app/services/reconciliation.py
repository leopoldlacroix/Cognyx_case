"""
Entity resolution — identity / alias detection on source entities.

D-2.3: query source_component / source_supplier only (not raw PLM/ERP tables).
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.services.normalization import (
    apply_reference_aliases,
    apply_supplier_aliases,
    load_normalization_config,
    normalize_reference,
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _evidence_json(evidence: Dict[str, Any]) -> str:
    """Stable JSON serialization for evidence (sorted keys)."""
    return json.dumps(evidence, sort_keys=True, separators=(",", ":"))


def record_reconciliation(
    conn: sqlite3.Connection,
    entity_type: str,
    source_entity_id: int,
    canonical_id: Optional[int] = None,
    status: str = "PENDING",
    method: Optional[str] = None,
    confidence: Optional[float] = None,
    rationale: Optional[str] = None,
    evidence: Optional[Dict[str, Any]] = None,
    reconciliation_run_id: Optional[int] = None,
    decided_at: Optional[str] = None,
    decided_by: Optional[str] = None,
) -> Optional[int]:
    """Insert one row into the entity-specific reconciliation table.

    entity_type selects component_reconciliation / assembly_reconciliation /
    supplier_reconciliation. Pairwise identity evidence (two source entities)
    goes in evidence_json — the table models source→canonical, not source↔source.

    Idempotent for the same source entity + method + evidence pair.
    Returns inserted row id, or None if a duplicate already exists.
    canonical_* id columns stay NULL when canonical tables do not exist yet.
    """
    evidence_str = _evidence_json(evidence or {})
    now = _now()

    if entity_type == "component":
        table = "component_reconciliation"
        fk_col = "source_component_id"
        canonical_col = "component_id"
    elif entity_type == "assembly":
        table = "assembly_reconciliation"
        fk_col = "source_assembly_id"
        canonical_col = "assembly_id"
    elif entity_type == "supplier":
        table = "supplier_reconciliation"
        fk_col = "source_supplier_id"
        canonical_col = "supplier_id"
    else:
        raise ValueError(f"Unsupported entity_type: {entity_type!r}")

    existing = conn.execute(
        f"""
        SELECT id FROM {table}
        WHERE {fk_col} = ?
          AND method IS ?
          AND evidence_json = ?
        """,
        (source_entity_id, method, evidence_str),
    ).fetchone()
    if existing:
        return None

    cursor = conn.execute(
        f"""
        INSERT INTO {table} (
            {fk_col}, {canonical_col}, status, method, confidence, rationale,
            evidence_json, reconciliation_run_id, created_at, decided_at, decided_by
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            source_entity_id,
            canonical_id,
            status,
            method,
            confidence,
            rationale,
            evidence_str,
            reconciliation_run_id,
            now,
            decided_at,
            decided_by,
        ),
    )
    return cursor.lastrowid


def _component_method(members: List[sqlite3.Row], config: Dict) -> str:
    """EXACT if all source refs normalize identically without aliases; else NORMALIZED."""
    for m in members:
        base = normalize_reference(m["source_reference"])
        aliased = apply_reference_aliases(base, config)
        if aliased != base:
            return "NORMALIZED"
        if base != m["normalized_reference"]:
            return "NORMALIZED"
    # All members share the same post-normalization ref with no alias step
    norms = {normalize_reference(m["source_reference"]) for m in members}
    if len(norms) == 1:
        return "EXACT"
    return "NORMALIZED"


def detect_component_identities(
    conn: sqlite3.Connection,
    config: Optional[Dict] = None,
    reconciliation_run_id: Optional[int] = None,
) -> List[Dict]:
    """Detect identity/alias clusters among source_component rows.

    Group by normalized_reference. If a group has more than one member
    (distinct source_system/source_reference pairs), write a PENDING
    component_reconciliation row for each member. Queries source_component only.
    """
    if config is None:
        config = load_normalization_config()

    rows = conn.execute(
        """
        SELECT id, normalized_reference, source_reference, source_system
        FROM source_component
        WHERE normalized_reference IS NOT NULL
          AND normalized_reference != ''
        ORDER BY normalized_reference, id
        """
    ).fetchall()

    by_ref: Dict[str, List[sqlite3.Row]] = {}
    for row in rows:
        by_ref.setdefault(row["normalized_reference"], []).append(row)

    matches: List[Dict] = []
    for ref, members in sorted(by_ref.items()):
        if len(members) < 2:
            continue

        method = _component_method(members, config)
        member_summaries = [
            {
                "source_component_id": m["id"],
                "source_system": m["source_system"],
                "source_reference": m["source_reference"],
            }
            for m in members
        ]

        for member in members:
            others = [
                s
                for s in member_summaries
                if s["source_component_id"] != member["id"]
            ]
            evidence = {
                "canonical_ref": ref,
                "relationship": "identity",
                "source_component_id": member["id"],
                "source_system": member["source_system"],
                "source_reference": member["source_reference"],
                "cluster_members": others,
            }
            rationale = (
                f"Identity cluster on normalized_reference={ref}: "
                f"{len(members)} source components with distinct refs/systems"
            )
            record_reconciliation(
                conn,
                entity_type="component",
                source_entity_id=member["id"],
                status="PENDING",
                method=method,
                confidence=0.95,
                rationale=rationale,
                evidence=evidence,
                reconciliation_run_id=reconciliation_run_id,
            )
            matches.append(
                {
                    **evidence,
                    "confidence": 0.95,
                    "method": method,
                    "status": "PENDING",
                }
            )

    conn.commit()
    return matches


def _supplier_match_key(normalized_reference: Optional[str], config: Dict) -> Optional[str]:
    """Resolve supplier aliases so SIEMENS and SIEMENS MOBILITY share a key."""
    if not normalized_reference:
        return normalized_reference
    return apply_supplier_aliases(normalized_reference, config)


def _supplier_method(members: List[sqlite3.Row], config: Dict, match_key: str) -> str:
    """EXACT if all stored norms already equal the match key; else NORMALIZED."""
    for m in members:
        stored = m["normalized_reference"]
        resolved = _supplier_match_key(stored, config)
        if resolved != stored or stored != match_key:
            return "NORMALIZED"
    return "EXACT"


def detect_supplier_identities(
    conn: sqlite3.Connection,
    config: Optional[Dict] = None,
    reconciliation_run_id: Optional[int] = None,
) -> List[Dict]:
    """Detect identity relationships among source_supplier rows.

    Applies supplier_aliases to both sides before grouping. Queries
    source_supplier only (D-2.3).
    """
    if config is None:
        config = load_normalization_config()

    rows = conn.execute(
        """
        SELECT id, normalized_reference, source_reference, source_system
        FROM source_supplier
        WHERE normalized_reference IS NOT NULL
          AND normalized_reference != ''
        ORDER BY id
        """
    ).fetchall()

    by_key: Dict[str, List[sqlite3.Row]] = {}
    for row in rows:
        key = _supplier_match_key(row["normalized_reference"], config)
        if not key:
            continue
        by_key.setdefault(key, []).append(row)

    matches: List[Dict] = []
    for match_key, members in sorted(by_key.items()):
        if len(members) < 2:
            continue

        method = _supplier_method(members, config, match_key)
        member_summaries = [
            {
                "source_supplier_id": m["id"],
                "source_system": m["source_system"],
                "source_reference": m["source_reference"],
                "normalized_reference": m["normalized_reference"],
            }
            for m in members
        ]

        for member in members:
            others = [
                s
                for s in member_summaries
                if s["source_supplier_id"] != member["id"]
            ]
            evidence = {
                "canonical_ref": match_key,
                "relationship": "identity",
                "source_supplier_id": member["id"],
                "source_system": member["source_system"],
                "source_reference": member["source_reference"],
                "cluster_members": others,
            }
            rationale = (
                f"Identity cluster on supplier key={match_key}: "
                f"{len(members)} source suppliers"
            )
            record_reconciliation(
                conn,
                entity_type="supplier",
                source_entity_id=member["id"],
                status="PENDING",
                method=method,
                confidence=0.95,
                rationale=rationale,
                evidence=evidence,
                reconciliation_run_id=reconciliation_run_id,
            )
            matches.append(
                {
                    **evidence,
                    "confidence": 0.95,
                    "method": method,
                    "status": "PENDING",
                }
            )

    conn.commit()
    return matches


def _start_reconciliation_run(
    conn: sqlite3.Connection,
    entity_type: str,
) -> int:
    """Insert a reconciliation_run row and return its id."""
    cur = conn.execute(
        """
        INSERT INTO reconciliation_run (entity_type, started_at, status)
        VALUES (?, ?, 'RUNNING')
        """,
        (entity_type, _now()),
    )
    conn.commit()
    return cur.lastrowid


def _complete_reconciliation_run(
    conn: sqlite3.Connection,
    run_id: int,
    *,
    items_processed: int,
    items_assessed: int,
    items_needing_review: int,
) -> None:
    conn.execute(
        """
        UPDATE reconciliation_run
        SET completed_at = ?,
            status = 'COMPLETED',
            items_processed = ?,
            items_assessed = ?,
            items_needing_review = ?,
            error_count = 0
        WHERE id = ?
        """,
        (
            _now(),
            items_processed,
            items_assessed,
            items_needing_review,
            run_id,
        ),
    )
    conn.commit()


def _same_prefix_different_suffix(ref_a: str, ref_b: str) -> Optional[Dict[str, str]]:
    """Return similarity detail if refs share a family but differ in one segment.

    Primary (plan): first two hyphen parts equal, last part differs
    (e.g. CTRL-DOOR-01 vs CTRL-DOOR-EXP).

    Secondary (SCEN-D example): last two parts equal, first part differs
    (e.g. STANDARD-DOOR-CTRL vs EXPORT-DOOR-CTRL).
    """
    if ref_a == ref_b:
        return None

    parts_a = ref_a.split("-")
    parts_b = ref_b.split("-")

    if len(parts_a) >= 2 and len(parts_b) >= 2:
        prefix_a = "-".join(parts_a[:2])
        prefix_b = "-".join(parts_b[:2])
        if prefix_a == prefix_b and parts_a[-1] != parts_b[-1]:
            return {
                "similarity_type": "same_prefix_different_suffix",
                "similarity_detail": (
                    f"Prefix '{prefix_a}' matches, suffixes differ: "
                    f"'{parts_a[-1]}' vs '{parts_b[-1]}'"
                ),
            }

    if len(parts_a) >= 3 and len(parts_b) >= 3:
        suffix_a = "-".join(parts_a[-2:])
        suffix_b = "-".join(parts_b[-2:])
        if suffix_a == suffix_b and parts_a[0] != parts_b[0]:
            return {
                "similarity_type": "same_suffix_different_prefix",
                "similarity_detail": (
                    f"Suffix '{suffix_a}' matches, prefixes differ: "
                    f"'{parts_a[0]}' vs '{parts_b[0]}'"
                ),
            }

    return None


def _nordic_variant_refs(conn: sqlite3.Connection) -> set:
    """Nordic variant refs from plm_variant that also appear in source_assembly_variant."""
    nordic_variants = conn.execute(
        """
        SELECT variant_ref_normalized
        FROM plm_variant
        WHERE (
            LOWER(COALESCE(variant_name_raw, '')) LIKE '%nordic%'
            OR LOWER(COALESCE(variant_ref_normalized, '')) LIKE '%nordic%'
        )
          AND variant_ref_normalized IS NOT NULL
          AND variant_ref_normalized != ''
        """
    ).fetchall()
    nordic_from_plm = {v["variant_ref_normalized"] for v in nordic_variants}
    if not nordic_from_plm:
        return set()

    linked = conn.execute(
        """
        SELECT DISTINCT variant_ref_normalized
        FROM source_assembly_variant
        WHERE variant_ref_normalized IS NOT NULL
          AND variant_ref_normalized != ''
        """
    ).fetchall()
    linked_refs = {r["variant_ref_normalized"] for r in linked}
    return nordic_from_plm & linked_refs


def _nordic_only_component_refs(
    conn: sqlite3.Connection,
    nordic_refs: Optional[set] = None,
) -> set:
    """Component refs used only on Nordic variants (not on any other variant)."""
    if nordic_refs is None:
        nordic_refs = _nordic_variant_refs(conn)
    if not nordic_refs:
        return set()

    placeholders = ",".join("?" * len(nordic_refs))
    nordic_list = list(nordic_refs)

    rows = conn.execute(
        f"""
        SELECT DISTINCT component_ref_normalized
        FROM plm_bom_line
        WHERE component_ref_normalized IS NOT NULL
          AND component_ref_normalized != ''
          AND variant_ref_normalized IN ({placeholders})
          AND component_ref_normalized NOT IN (
              SELECT component_ref_normalized
              FROM plm_bom_line
              WHERE component_ref_normalized IS NOT NULL
                AND component_ref_normalized != ''
                AND (
                    variant_ref_normalized IS NULL
                    OR variant_ref_normalized NOT IN ({placeholders})
                )
          )
        """,
        nordic_list + nordic_list,
    ).fetchall()
    return {r["component_ref_normalized"] for r in rows}


def detect_variant_specific_differences(
    conn: sqlite3.Connection,
    reconciliation_run_id: Optional[int] = None,
) -> List[Dict]:
    """Detect components used only by Nordic climate variants.

    Intentional specialization — not merge/identity candidates.
    Uses source_assembly_variant to confirm Nordic variant linkage, then
    finds plm_bom_line components exclusive to those variants.
    """
    nordic_refs = _nordic_variant_refs(conn)
    if not nordic_refs:
        return []

    nordic_only = _nordic_only_component_refs(conn, nordic_refs)
    if not nordic_only:
        return []

    variant_ref = sorted(nordic_refs)[0]

    # Representative source_component id per normalized ref (if present)
    id_by_ref: Dict[str, int] = {}
    for row in conn.execute(
        """
        SELECT id, normalized_reference
        FROM source_component
        WHERE normalized_reference IS NOT NULL
          AND normalized_reference != ''
        ORDER BY id
        """
    ).fetchall():
        ref = row["normalized_reference"]
        if ref not in id_by_ref:
            id_by_ref[ref] = row["id"]

    records: List[Dict] = []
    rationale = (
        "Component used exclusively by Nordic climate variant — "
        "intentional specialization, not a merge candidate"
    )

    for comp_ref in sorted(nordic_only):
        source_id = id_by_ref.get(comp_ref)
        evidence = {
            "relationship": "variant_specific",
            "review_needed": False,
            "component_ref": comp_ref,
            "variant_ref": variant_ref,
            "nordic_variant_refs": sorted(nordic_refs),
        }
        if source_id is not None:
            record_reconciliation(
                conn,
                entity_type="component",
                source_entity_id=source_id,
                status="PENDING",
                method="STRUCTURED",
                confidence=0.95,
                rationale=rationale,
                evidence=evidence,
                reconciliation_run_id=reconciliation_run_id,
            )
        records.append(
            {
                "component_ref": comp_ref,
                "relationship": "variant_specific",
                "confidence": 0.95,
                "method": "STRUCTURED",
                "status": "PENDING",
                "variant_ref": variant_ref,
                "rationale": rationale,
                "review_needed": False,
                "source_component_id": source_id,
            }
        )

    conn.commit()
    return records


def detect_functional_similarity(
    conn: sqlite3.Connection,
    config: Optional[Dict] = None,
    reconciliation_run_id: Optional[int] = None,
    exclude_refs: Optional[set] = None,
) -> List[Dict]:
    """Detect functionally similar but non-identical components.

    Same-prefix / different-suffix heuristic on distinct normalized_reference
    values. Persists STRUCTURED / 0.50 / PENDING rows with
    relationship=functional_similarity and review_needed=true in evidence.
    These are NOT identity matches. Nordic-only (variant-specific) refs are
    excluded so intentional specialization is not proposed as interchangeable.
    """
    if config is None:
        config = load_normalization_config()
    _ = config  # reserved for future threshold/config knobs

    excluded = set(exclude_refs) if exclude_refs else set()
    excluded |= _nordic_only_component_refs(conn)

    refs = conn.execute(
        """
        SELECT DISTINCT normalized_reference
        FROM source_component
        WHERE normalized_reference IS NOT NULL
          AND normalized_reference != ''
        ORDER BY normalized_reference
        """
    ).fetchall()

    ref_list = [
        r["normalized_reference"]
        for r in refs
        if r["normalized_reference"] not in excluded
    ]

    # One representative source_component id per normalized_reference
    id_by_ref: Dict[str, int] = {}
    for row in conn.execute(
        """
        SELECT id, normalized_reference
        FROM source_component
        WHERE normalized_reference IS NOT NULL
          AND normalized_reference != ''
        ORDER BY id
        """
    ).fetchall():
        ref = row["normalized_reference"]
        if ref not in id_by_ref:
            id_by_ref[ref] = row["id"]

    candidates: List[Dict] = []

    for i, ref_a in enumerate(ref_list):
        for ref_b in ref_list[i + 1 :]:
            detail = _same_prefix_different_suffix(ref_a, ref_b)
            if detail is None:
                continue

            source_a = id_by_ref.get(ref_a)
            source_b = id_by_ref.get(ref_b)
            if source_a is None or source_b is None:
                continue

            rationale = (
                "Similar component family but different variants — "
                "requires human review to determine if interchangeable"
            )

            for source_id, self_ref, other_ref in (
                (source_a, ref_a, ref_b),
                (source_b, ref_b, ref_a),
            ):
                evidence = {
                    "relationship": "functional_similarity",
                    "review_needed": True,
                    "reference_a": ref_a,
                    "reference_b": ref_b,
                    "self_reference": self_ref,
                    "other_reference": other_ref,
                    "similarity_type": detail["similarity_type"],
                    "similarity_detail": detail["similarity_detail"],
                }
                record_reconciliation(
                    conn,
                    entity_type="component",
                    source_entity_id=source_id,
                    status="PENDING",
                    method="STRUCTURED",
                    confidence=0.50,
                    rationale=rationale,
                    evidence=evidence,
                    reconciliation_run_id=reconciliation_run_id,
                )

            candidate = {
                "reference_a": ref_a,
                "reference_b": ref_b,
                "similarity_type": detail["similarity_type"],
                "similarity_detail": detail["similarity_detail"],
                "relationship": "functional_similarity",
                "confidence": 0.50,
                "method": "STRUCTURED",
                "status": "PENDING",
                "rationale": rationale,
                "review_needed": True,
            }
            candidates.append(candidate)

    conn.commit()
    return candidates


def run_entity_resolution(
    conn: sqlite3.Connection,
    config: Optional[Dict] = None,
) -> Dict[str, Any]:
    """Run full entity resolution: components + suppliers.

    Creates reconciliation_run rows first, then runs both detectors.
    Returns a summary dict with match counts and run ids.
    """
    if config is None:
        config = load_normalization_config()

    component_run_id = _start_reconciliation_run(conn, "component")
    component_matches = detect_component_identities(
        conn, config=config, reconciliation_run_id=component_run_id
    )
    component_clusters = {m["canonical_ref"] for m in component_matches}
    _complete_reconciliation_run(
        conn,
        component_run_id,
        items_processed=len(component_matches),
        items_assessed=len(component_matches),
        items_needing_review=len(component_matches),
    )

    supplier_run_id = _start_reconciliation_run(conn, "supplier")
    supplier_matches = detect_supplier_identities(
        conn, config=config, reconciliation_run_id=supplier_run_id
    )
    supplier_clusters = {m["canonical_ref"] for m in supplier_matches}
    _complete_reconciliation_run(
        conn,
        supplier_run_id,
        items_processed=len(supplier_matches),
        items_assessed=len(supplier_matches),
        items_needing_review=len(supplier_matches),
    )

    total_records = (
        conn.execute(
            "SELECT COUNT(*) AS c FROM component_reconciliation"
        ).fetchone()["c"]
        + conn.execute(
            "SELECT COUNT(*) AS c FROM supplier_reconciliation"
        ).fetchone()["c"]
    )

    return {
        "components_matched": len(component_clusters),
        "suppliers_matched": len(supplier_clusters),
        "total_records": total_records,
        "component_run_id": component_run_id,
        "supplier_run_id": supplier_run_id,
    }


def main(argv: Optional[List[str]] = None) -> int:
    """Thin entry point: python -m app.services.reconciliation [--db PATH]."""
    import argparse

    from app.db.connection import get_connection, init_database

    parser = argparse.ArgumentParser(description="Run entity resolution")
    parser.add_argument("--db", default="cognyx.db", help="Database path")
    args = parser.parse_args(argv)

    init_database(args.db)
    conn = get_connection(args.db)
    summary = run_entity_resolution(conn)
    print(
        f"components_matched={summary['components_matched']} "
        f"suppliers_matched={summary['suppliers_matched']} "
        f"total_records={summary['total_records']}"
    )
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
