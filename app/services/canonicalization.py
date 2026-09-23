"""
Build canonical entities and BOM from accepted identity + unambiguous singletons.

Clears and refills variant, assembly, component, and bom_relationship on each
run so rebuilds stay idempotent. Does not clear reconciliation or raw tables.
Accepted identity rows keep a shared component_id (recreated and written back
onto the reconciliation rows when the component table is refilled).
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_evidence(evidence_json: Optional[str]) -> Dict[str, Any]:
    if not evidence_json:
        return {}
    try:
        return json.loads(evidence_json)
    except json.JSONDecodeError:
        return {}


def _is_identity(evidence: Dict[str, Any]) -> bool:
    return evidence.get("relationship", "identity") == "identity"


def _insert_component(conn: sqlite3.Connection, ref: str) -> int:
    cur = conn.execute(
        """
        INSERT INTO component (name, category, normalized_reference, created_at)
        VALUES (?, ?, ?, ?)
        """,
        (ref, None, ref, _now()),
    )
    return cur.lastrowid


def _rebuild_accepted_identity_components(conn: sqlite3.Connection) -> Dict[int, int]:
    """Recreate canonical components for ACCEPTED identity rows.

    Peers that previously shared a component_id keep sharing one after rebuild.
    Returns map source_component_id → canonical component_id.
    """
    rows = conn.execute(
        """
        SELECT id, source_component_id, component_id, evidence_json
        FROM component_reconciliation
        WHERE status = 'ACCEPTED'
        ORDER BY id
        """
    ).fetchall()

    # Group ACCEPTED identity rows by their old component_id (or by row id if null)
    groups: Dict[Any, List[sqlite3.Row]] = {}
    for row in rows:
        evidence = _parse_evidence(row["evidence_json"])
        if not _is_identity(evidence):
            continue
        key = row["component_id"] if row["component_id"] is not None else ("row", row["id"])
        groups.setdefault(key, []).append(row)

    source_to_canonical: Dict[int, int] = {}
    for group_rows in groups.values():
        # Name from first member's source normalized_reference
        first_source = conn.execute(
            "SELECT normalized_reference, source_reference FROM source_component WHERE id = ?",
            (group_rows[0]["source_component_id"],),
        ).fetchone()
        ref = (
            (first_source["normalized_reference"] or first_source["source_reference"])
            if first_source
            else "UNKNOWN"
        )
        new_id = _insert_component(conn, ref)
        for row in group_rows:
            conn.execute(
                """
                UPDATE component_reconciliation
                SET component_id = ?
                WHERE id = ?
                """,
                (new_id, row["id"]),
            )
            source_to_canonical[row["source_component_id"]] = new_id

    conn.commit()
    return source_to_canonical


def _create_variants(conn: sqlite3.Connection) -> Dict[str, int]:
    mapping: Dict[str, int] = {}
    now = _now()
    rows = conn.execute(
        """
        SELECT DISTINCT variant_ref_normalized, variant_name_normalized,
               train_family_raw, market_raw, climate_class_raw,
               capacity_class_raw, voltage_system_raw
        FROM plm_variant
        WHERE variant_ref_normalized IS NOT NULL
          AND TRIM(variant_ref_normalized) != ''
        ORDER BY variant_ref_normalized
        """
    ).fetchall()
    for row in rows:
        ref = row["variant_ref_normalized"]
        if ref in mapping:
            continue
        name = row["variant_name_normalized"] or ref
        cur = conn.execute(
            """
            INSERT INTO variant (
                name, train_family, market, climate_class,
                capacity_class, voltage_system, normalized_reference, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                name,
                row["train_family_raw"],
                row["market_raw"],
                row["climate_class_raw"],
                row["capacity_class_raw"],
                row["voltage_system_raw"],
                ref,
                now,
            ),
        )
        mapping[ref] = cur.lastrowid
    conn.commit()
    return mapping


def _create_assemblies(conn: sqlite3.Connection) -> Dict[str, int]:
    mapping: Dict[str, int] = {}
    now = _now()
    rows = conn.execute(
        """
        SELECT id, normalized_reference
        FROM source_assembly
        WHERE normalized_reference IS NOT NULL
          AND TRIM(normalized_reference) != ''
        ORDER BY id
        """
    ).fetchall()
    for row in rows:
        ref = row["normalized_reference"]
        if ref in mapping:
            continue
        cur = conn.execute(
            """
            INSERT INTO assembly (name, category, normalized_reference, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (ref, None, ref, now),
        )
        mapping[ref] = cur.lastrowid
    conn.commit()
    return mapping


def _identity_row_for_source(
    conn: sqlite3.Connection,
    source_component_id: int,
) -> Optional[sqlite3.Row]:
    """Return the identity reconciliation row for this source, if any."""
    rows = conn.execute(
        """
        SELECT id, status, component_id, evidence_json
        FROM component_reconciliation
        WHERE source_component_id = ?
        ORDER BY id
        """,
        (source_component_id,),
    ).fetchall()
    for row in rows:
        if _is_identity(_parse_evidence(row["evidence_json"])):
            return row
    return None


def _get_or_create_singleton(
    conn: sqlite3.Connection,
    source: sqlite3.Row,
    by_source: Dict[int, int],
    by_key: Dict[Tuple[str, str], int],
) -> int:
    sc_id = source["id"]
    if sc_id in by_source:
        return by_source[sc_id]

    ref = source["normalized_reference"] or source["source_reference"]
    key = (source["source_system"], ref)
    if key in by_key:
        by_source[sc_id] = by_key[key]
        return by_key[key]

    canon_id = _insert_component(conn, ref)
    by_source[sc_id] = canon_id
    by_key[key] = canon_id
    return canon_id


def build_canonical_model(conn: sqlite3.Connection) -> Dict[str, Any]:
    """Clear and refill canonical variant/assembly/component/BOM from source data.

    Singletons (no identity reconciliation row) get a canonical component.
    PENDING/ASSESSED identity → unresolved identity_pending.
    REJECTED identity → unresolved identity_rejected.
    ACCEPTED identity → shared component_id for the cluster.
    Functional similarity and variant_specific neither block nor merge.
    """
    conn.execute("DELETE FROM bom_relationship")
    conn.execute("DELETE FROM component")
    conn.execute("DELETE FROM assembly")
    conn.execute("DELETE FROM variant")
    conn.commit()

    accepted_map = _rebuild_accepted_identity_components(conn)
    variant_map = _create_variants(conn)
    assembly_map = _create_assemblies(conn)

    by_source: Dict[int, int] = dict(accepted_map)
    by_key: Dict[Tuple[str, str], int] = {}
    for sc_id, canon_id in accepted_map.items():
        source = conn.execute(
            "SELECT source_system, normalized_reference, source_reference "
            "FROM source_component WHERE id = ?",
            (sc_id,),
        ).fetchone()
        if source:
            ref = source["normalized_reference"] or source["source_reference"]
            by_key[(source["source_system"], ref)] = canon_id

    unresolved: List[Dict[str, Any]] = []
    bom_count = 0
    now = _now()

    lines = conn.execute(
        """
        SELECT id, variant_ref_normalized, assembly_ref_normalized,
               component_ref_raw, quantity_normalized, uom_normalized
        FROM plm_bom_line
        ORDER BY id
        """
    ).fetchall()

    for line in lines:
        line_id = line["id"]
        variant_ref = line["variant_ref_normalized"]
        assembly_ref = line["assembly_ref_normalized"]
        component_ref_raw = line["component_ref_raw"]

        if not variant_ref or variant_ref not in variant_map:
            unresolved.append(
                {"source_bom_line_id": line_id, "reason": "missing_variant"}
            )
            continue

        if assembly_ref and assembly_ref not in assembly_map:
            cur = conn.execute(
                """
                INSERT INTO assembly (name, category, normalized_reference, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (assembly_ref, None, assembly_ref, now),
            )
            assembly_map[assembly_ref] = cur.lastrowid

        if not assembly_ref or assembly_ref not in assembly_map:
            unresolved.append(
                {"source_bom_line_id": line_id, "reason": "missing_assembly"}
            )
            continue

        source = conn.execute(
            """
            SELECT id, source_system, source_reference, normalized_reference
            FROM source_component
            WHERE source_system = 'PLM' AND source_reference = ?
            """,
            (component_ref_raw,),
        ).fetchone()

        if source is None:
            unresolved.append(
                {"source_bom_line_id": line_id, "reason": "missing_source_component"}
            )
            continue

        identity = _identity_row_for_source(conn, source["id"])
        component_id: Optional[int] = None

        if identity is None:
            component_id = _get_or_create_singleton(conn, source, by_source, by_key)
        else:
            status = identity["status"]
            if status in ("PENDING", "ASSESSED"):
                unresolved.append(
                    {"source_bom_line_id": line_id, "reason": "identity_pending"}
                )
                continue
            if status == "REJECTED":
                unresolved.append(
                    {"source_bom_line_id": line_id, "reason": "identity_rejected"}
                )
                continue
            if status == "ACCEPTED":
                # Prefer map rebuilt above; fall back to row value
                component_id = by_source.get(source["id"]) or identity["component_id"]
                if component_id is None:
                    unresolved.append(
                        {
                            "source_bom_line_id": line_id,
                            "reason": "identity_accepted_without_canonical",
                        }
                    )
                    continue
            else:
                unresolved.append(
                    {
                        "source_bom_line_id": line_id,
                        "reason": f"identity_status_{status}",
                    }
                )
                continue

        conn.execute(
            """
            INSERT INTO bom_relationship (
                variant_id, assembly_id, component_id,
                quantity, unit, source_bom_line_id, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                variant_map[variant_ref],
                assembly_map[assembly_ref],
                component_id,
                line["quantity_normalized"],
                line["uom_normalized"],
                line_id,
                now,
            ),
        )
        bom_count += 1

    conn.commit()

    return {
        "variants": conn.execute("SELECT COUNT(*) AS n FROM variant").fetchone()["n"],
        "assemblies": conn.execute("SELECT COUNT(*) AS n FROM assembly").fetchone()["n"],
        "components": conn.execute("SELECT COUNT(*) AS n FROM component").fetchone()["n"],
        "bom_relationships": bom_count,
        "unresolved": unresolved,
    }
