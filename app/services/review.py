"""
Human review decisions on reconciliation proposals.

Accept, reject, and redirect update existing PENDING rows via UPDATE.
Redirect additionally INSERTs a new MANUAL PENDING proposal.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


_ENTITY_CONFIG = {
    "component": {
        "table": "component_reconciliation",
        "source_fk": "source_component_id",
        "canonical_col": "component_id",
        "canonical_table": "component",
        "source_table": "source_component",
        "member_id_key": "source_component_id",
        "redirect_target_key": "target_source_component_id",
    },
    "assembly": {
        "table": "assembly_reconciliation",
        "source_fk": "source_assembly_id",
        "canonical_col": "assembly_id",
        "canonical_table": "assembly",
        "source_table": "source_assembly",
        "member_id_key": "source_assembly_id",
        "redirect_target_key": "target_source_assembly_id",
    },
    "supplier": {
        "table": "supplier_reconciliation",
        "source_fk": "source_supplier_id",
        "canonical_col": "supplier_id",
        "canonical_table": "supplier",
        "source_table": "source_supplier",
        "member_id_key": "source_supplier_id",
        "redirect_target_key": "target_source_supplier_id",
    },
}


def _parse_evidence(evidence_json: Optional[str]) -> Dict[str, Any]:
    if not evidence_json:
        return {}
    try:
        return json.loads(evidence_json)
    except json.JSONDecodeError:
        return {}


def _evidence_member_ids(evidence: Dict[str, Any], member_id_key: str) -> List[int]:
    """Collect peer source ids from identity evidence cluster_members."""
    ids: List[int] = []
    members = evidence.get("cluster_members") or []
    for m in members:
        if isinstance(m, dict) and member_id_key in m:
            ids.append(int(m[member_id_key]))
        elif isinstance(m, int):
            ids.append(m)
    # Also accept a flat "members" list of ids if present
    for m in evidence.get("members") or []:
        if isinstance(m, int):
            ids.append(m)
        elif isinstance(m, dict) and member_id_key in m:
            ids.append(int(m[member_id_key]))
    return ids


def _create_canonical(
    conn: sqlite3.Connection,
    cfg: Dict[str, str],
    source_entity_id: int,
) -> int:
    """Create a canonical row from the source entity's normalized_reference."""
    source = conn.execute(
        f"""
        SELECT normalized_reference, description
        FROM {cfg['source_table']}
        WHERE id = ?
        """,
        (source_entity_id,),
    ).fetchone()
    if source is None:
        raise ValueError(f"Source entity {source_entity_id} not found")

    ref = source["normalized_reference"] or ""
    name = ref
    now = _now()

    if cfg["canonical_table"] == "supplier":
        cur = conn.execute(
            """
            INSERT INTO supplier (name, country, normalized_reference, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (name, None, ref, now),
        )
    else:
        # component and assembly share name/category/normalized_reference
        cur = conn.execute(
            f"""
            INSERT INTO {cfg['canonical_table']}
                (name, category, normalized_reference, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (name, None, ref, now),
        )
    return cur.lastrowid


def _find_peer_canonical_id(
    conn: sqlite3.Connection,
    cfg: Dict[str, str],
    member_ids: List[int],
) -> Optional[int]:
    """Reuse canonical id from an ACCEPTED peer whose source id is in members."""
    if not member_ids:
        return None
    placeholders = ",".join("?" * len(member_ids))
    row = conn.execute(
        f"""
        SELECT {cfg['canonical_col']} AS canonical_id
        FROM {cfg['table']}
        WHERE status = 'ACCEPTED'
          AND {cfg['canonical_col']} IS NOT NULL
          AND {cfg['source_fk']} IN ({placeholders})
        ORDER BY id
        LIMIT 1
        """,
        member_ids,
    ).fetchone()
    if row is None:
        return None
    return row["canonical_id"]


def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    return {key: row[key] for key in row.keys()}


def decide_reconciliation(
    conn: sqlite3.Connection,
    entity_type: str,
    reconciliation_id: int,
    action: str,
    rationale: Optional[str] = None,
    redirect_source_id: Optional[int] = None,
    decided_by: str = "operator",
) -> Dict[str, Any]:
    """Accept, reject, or redirect a PENDING reconciliation row.

    Uses UPDATE for the decision. INSERT only for a new redirect proposal.
    Does not call record_reconciliation() to mutate the existing row.
    """
    if entity_type not in _ENTITY_CONFIG:
        raise ValueError(f"Unsupported entity_type: {entity_type!r}")
    if action not in ("accept", "reject", "redirect"):
        raise ValueError(f"Unsupported action: {action!r}")

    cfg = _ENTITY_CONFIG[entity_type]
    table = cfg["table"]
    canonical_col = cfg["canonical_col"]

    row = conn.execute(
        f"SELECT * FROM {table} WHERE id = ?",
        (reconciliation_id,),
    ).fetchone()
    if row is None:
        raise ValueError(f"Reconciliation row {reconciliation_id} not found")

    if row["status"] in ("ACCEPTED", "REJECTED"):
        raise ValueError(
            f"Cannot decide on row {reconciliation_id} with status {row['status']}"
        )

    evidence = _parse_evidence(row["evidence_json"])
    relationship = evidence.get("relationship", "identity")
    decided_at = _now()
    source_entity_id = row[cfg["source_fk"]]

    if action == "reject":
        if not rationale:
            raise ValueError("rationale is required for reject")
        conn.execute(
            f"""
            UPDATE {table}
            SET status = 'REJECTED',
                rationale = ?,
                decided_at = ?,
                decided_by = ?,
                {canonical_col} = NULL
            WHERE id = ?
            """,
            (rationale, decided_at, decided_by, reconciliation_id),
        )
        conn.commit()
        updated = conn.execute(
            f"SELECT * FROM {table} WHERE id = ?", (reconciliation_id,)
        ).fetchone()
        return _row_to_dict(updated)

    if action == "redirect":
        if redirect_source_id is None:
            raise ValueError("redirect_source_id is required for redirect")
        redirect_rationale = f"redirected: {rationale}" if rationale else "redirected:"
        conn.execute(
            f"""
            UPDATE {table}
            SET status = 'REJECTED',
                rationale = ?,
                decided_at = ?,
                decided_by = ?,
                {canonical_col} = NULL
            WHERE id = ?
            """,
            (redirect_rationale, decided_at, decided_by, reconciliation_id),
        )

        new_relationship = relationship or "identity"
        new_evidence = {
            "relationship": new_relationship,
            "redirect_from": reconciliation_id,
            cfg["redirect_target_key"]: redirect_source_id,
            "review_needed": True,
        }
        evidence_str = json.dumps(new_evidence, sort_keys=True, separators=(",", ":"))
        conn.execute(
            f"""
            INSERT INTO {table} (
                {cfg['source_fk']}, {canonical_col}, status, method, confidence,
                rationale, evidence_json, created_at
            ) VALUES (?, NULL, 'PENDING', 'MANUAL', NULL, ?, ?, ?)
            """,
            (
                source_entity_id,
                f"Redirected proposal toward source id {redirect_source_id}",
                evidence_str,
                _now(),
            ),
        )
        conn.commit()
        updated = conn.execute(
            f"SELECT * FROM {table} WHERE id = ?", (reconciliation_id,)
        ).fetchone()
        return _row_to_dict(updated)

    # action == "accept"
    canonical_id: Optional[int] = None

    if relationship == "functional_similarity":
        canonical_id = None
    elif relationship == "variant_specific":
        # Always create a new canonical for this source only — never reuse peers
        canonical_id = _create_canonical(conn, cfg, source_entity_id)
    else:
        # identity (default)
        member_ids = _evidence_member_ids(evidence, cfg["member_id_key"])
        peer_id = _find_peer_canonical_id(conn, cfg, member_ids)
        if peer_id is not None:
            canonical_id = peer_id
        else:
            canonical_id = _create_canonical(conn, cfg, source_entity_id)

    stored_rationale = rationale if rationale is not None else row["rationale"]
    conn.execute(
        f"""
        UPDATE {table}
        SET status = 'ACCEPTED',
            rationale = ?,
            decided_at = ?,
            decided_by = ?,
            {canonical_col} = ?
        WHERE id = ?
        """,
        (stored_rationale, decided_at, decided_by, canonical_id, reconciliation_id),
    )
    conn.commit()
    updated = conn.execute(
        f"SELECT * FROM {table} WHERE id = ?", (reconciliation_id,)
    ).fetchone()
    return _row_to_dict(updated)
