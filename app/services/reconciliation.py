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
    status: str,
    method: str,
    confidence: float,
    rationale: str,
    evidence: Dict[str, Any],
    reconciliation_run_id: Optional[int] = None,
) -> Optional[int]:
    """Insert a component or supplier reconciliation row.

    Idempotent for the same source entity + method + evidence pair.
    Returns inserted row id, or None if a duplicate already exists.
    component_id / supplier_id stay NULL (canonical tables do not exist yet).
    """
    evidence_str = _evidence_json(evidence)
    now = _now()

    if entity_type == "component":
        table = "component_reconciliation"
        fk_col = "source_component_id"
    elif entity_type == "supplier":
        table = "supplier_reconciliation"
        fk_col = "source_supplier_id"
    else:
        raise ValueError(f"Unsupported entity_type: {entity_type!r}")

    existing = conn.execute(
        f"""
        SELECT id FROM {table}
        WHERE {fk_col} = ?
          AND method = ?
          AND evidence_json = ?
        """,
        (source_entity_id, method, evidence_str),
    ).fetchone()
    if existing:
        return None

    cursor = conn.execute(
        f"""
        INSERT INTO {table} (
            {fk_col}, status, method, confidence, rationale,
            evidence_json, reconciliation_run_id, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            source_entity_id,
            status,
            method,
            confidence,
            rationale,
            evidence_str,
            reconciliation_run_id,
            now,
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
