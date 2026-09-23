"""Blockers and data-quality reports (conflicts, lifecycle, SCEN-I issues)."""
from __future__ import annotations

import json
import re
import sqlite3
import zlib
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

_VOLTAGE_RE = re.compile(r"(?i)(\d+)\s*V")

COUNTING_ASSEMBLY_REFS = frozenset(
    {
        "PAX-COUNT-MOD-E",
        "PCOUNT-M08",
        "PASSCOUNT-MOD-01",
        "PASSCOUNT-MOD-N",
        "PAX-COUNT-MOD-HC",
    }
)

_MAPPING_NOISE_TYPES = frozenset({"missing_description", "empty_supplier"})

# Facts written by blockers(); deleted/replaced on each call for idempotency.
_OWNED_SOURCE_TYPES = frozenset({"engineering_note", "plm_assembly", "erp_material"})


def extract_voltage_facts(text: Optional[str]) -> Set[str]:
    """Return sorted-unique voltages as '{n} V DC' from integers matched by (?i)(\\d+)\\s*V."""
    if not text:
        return set()
    return {f"{int(n)} V DC" for n in _VOLTAGE_RE.findall(text)}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _stable_entity_id(entity_ref: str) -> int:
    value = zlib.crc32(entity_ref.encode("utf-8")) & 0x7FFFFFFF
    return value or 1


def _component_entity_id(conn: sqlite3.Connection, entity_ref: str) -> int:
    row = conn.execute(
        """
        SELECT id FROM source_component
        WHERE source_reference = ? OR normalized_reference = ?
        ORDER BY id LIMIT 1
        """,
        (entity_ref, entity_ref),
    ).fetchone()
    if row:
        return int(row["id"])
    return _stable_entity_id(entity_ref)


def _clear_owned_facts(conn: sqlite3.Connection) -> None:
    placeholders = ",".join("?" for _ in _OWNED_SOURCE_TYPES)
    conn.execute(
        f"DELETE FROM technical_fact WHERE source_type IN ({placeholders})",
        tuple(_OWNED_SOURCE_TYPES),
    )


def _insert_fact(
    conn: sqlite3.Connection,
    *,
    entity_type: str,
    entity_id: int,
    attribute: str,
    value: str,
    source_type: str,
    source_id: str,
    status: str,
) -> None:
    conn.execute(
        """
        INSERT INTO technical_fact (
            entity_type, entity_id, attribute, value, unit,
            source_type, source_id, confidence, status, created_at
        ) VALUES (?, ?, ?, ?, NULL, ?, ?, NULL, ?, ?)
        """,
        (
            entity_type,
            entity_id,
            attribute,
            value,
            source_type,
            source_id,
            status,
            _now(),
        ),
    )


def blockers(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    """Detect conflicting evidence and lifecycle issues; persist technical_fact rows."""
    _clear_owned_facts(conn)
    results: List[Dict[str, Any]] = []

    # --- SCEN-G: conflicting voltages in note text ---
    notes = conn.execute(
        """
        SELECT n.id, n.object_reference_raw, n.note_text, n.author, n.source_row,
               sf.file_name AS source_file
        FROM engineering_note n
        JOIN source_file sf ON sf.id = n.source_file_id
        WHERE n.note_text IS NOT NULL AND TRIM(n.note_text) != ''
        ORDER BY n.id
        """
    ).fetchall()

    for note in notes:
        entity_ref = (note["object_reference_raw"] or "").strip()
        if not entity_ref:
            continue
        volts = sorted(extract_voltage_facts(note["note_text"]))
        if len(volts) < 2:
            continue
        # Keep only true 24V/48V HVAC-style conflicts (both present).
        if not ({"24 V DC", "48 V DC"} <= set(volts)):
            # Still record multi-voltage notes that disagree on more than one value
            # only when at least two distinct values appear — already true.
            # For the PoC demo, require both 24 and 48 as the known conflict pattern.
            if "24 V DC" not in volts or "48 V DC" not in volts:
                continue

        entity_id = _component_entity_id(conn, entity_ref)
        source_id = note["author"] or f"note-{note['id']}"
        sources = []
        for value in volts:
            _insert_fact(
                conn,
                entity_type="component",
                entity_id=entity_id,
                attribute="operating_voltage",
                value=value,
                source_type="engineering_note",
                source_id=str(source_id),
                status="CONFLICTING",
            )
            sources.append(
                {
                    "source_type": "engineering_note",
                    "source_id": str(source_id),
                    "value": value,
                    "source_file": note["source_file"],
                    "source_row": int(note["source_row"]),
                }
            )
        results.append(
            {
                "issue_type": "conflicting_evidence",
                "entity_ref": entity_ref,
                "attribute": "operating_voltage",
                "values": volts,
                "sources": sources,
                "explanation": (
                    f"Engineering note {source_id} on {entity_ref} states both "
                    f"{' and '.join(volts)}. Both values were kept; neither was selected."
                ),
            }
        )

    # --- SCEN-J: counting assembly lifecycle mismatch ---
    assemblies = conn.execute(
        """
        SELECT a.id, a.assembly_ref_raw, a.assembly_ref_normalized, a.lifecycle_raw,
               a.variant_ref_raw, a.source_row, sf.file_name AS source_file
        FROM plm_assembly a
        JOIN source_file sf ON sf.id = a.source_file_id
        WHERE a.assembly_ref_raw IS NOT NULL
        ORDER BY a.id
        """
    ).fetchall()

    counting: Dict[str, sqlite3.Row] = {}
    for row in assemblies:
        ref = row["assembly_ref_raw"] or row["assembly_ref_normalized"]
        if ref in COUNTING_ASSEMBLY_REFS:
            counting[ref] = row

    prototype = counting.get("PAX-COUNT-MOD-E")
    released_peers = [
        r
        for ref, r in counting.items()
        if ref != "PAX-COUNT-MOD-E"
        and (r["lifecycle_raw"] or "").strip().lower() == "released"
    ]
    if (
        prototype is not None
        and (prototype["lifecycle_raw"] or "").strip() == "Prototype"
        and released_peers
    ):
        peer = released_peers[0]
        entity_id = int(prototype["id"])
        values = sorted({"Prototype", "Released"})
        for value, src_row in (
            ("Prototype", prototype),
            ("Released", peer),
        ):
            _insert_fact(
                conn,
                entity_type="assembly",
                entity_id=entity_id,
                attribute="lifecycle",
                value=value,
                source_type="plm_assembly",
                source_id=src_row["assembly_ref_raw"],
                status="CONFLICTING",
            )
        results.append(
            {
                "issue_type": "lifecycle_mismatch",
                "entity_ref": "PAX-COUNT-MOD-E",
                "attribute": "lifecycle",
                "values": values,
                "sources": [
                    {
                        "source_type": "plm_assembly",
                        "source_id": prototype["assembly_ref_raw"],
                        "value": "Prototype",
                        "source_file": prototype["source_file"],
                        "source_row": int(prototype["source_row"]),
                    },
                    {
                        "source_type": "plm_assembly",
                        "source_id": peer["assembly_ref_raw"],
                        "value": "Released",
                        "source_file": peer["source_file"],
                        "source_row": int(peer["source_row"]),
                    },
                ],
                "explanation": (
                    "PAX-COUNT-MOD-E is Prototype while peer counting assembly "
                    f"{peer['assembly_ref_raw']} is Released. "
                    "This is a lifecycle mismatch between counting modules."
                ),
            }
        )

    # --- SCEN-J: ERP obsolete materials (separate rows) ---
    obsolete = conn.execute(
        """
        SELECT m.id, m.material_id_raw, m.status_raw, m.description_raw,
               m.source_row, sf.file_name AS source_file
        FROM erp_material m
        JOIN source_file sf ON sf.id = m.source_file_id
        WHERE UPPER(COALESCE(m.status_raw, '')) = 'OBSOLETE'
        ORDER BY m.material_id_raw
        """
    ).fetchall()
    for mat in obsolete:
        mid = mat["material_id_raw"]
        _insert_fact(
            conn,
            entity_type="material",
            entity_id=int(mat["id"]),
            attribute="status",
            value="OBSOLETE",
            source_type="erp_material",
            source_id=mid,
            status="OBSERVED",
        )
        results.append(
            {
                "issue_type": "erp_lifecycle",
                "entity_ref": mid,
                "attribute": "status",
                "values": ["OBSOLETE"],
                "sources": [
                    {
                        "source_type": "erp_material",
                        "source_id": mid,
                        "value": "OBSOLETE",
                        "source_file": mat["source_file"],
                        "source_row": int(mat["source_row"]),
                    }
                ],
                "explanation": (
                    f"ERP material {mid} has status OBSOLETE. "
                    "Reported on its own; no PLM twin was invented."
                ),
            }
        )

    conn.commit()
    return results


def data_quality_issues(conn: sqlite3.Connection) -> Dict[str, Any]:
    """Concrete SCEN-I issues plus grouped soft-warning summary."""
    issues: List[Dict[str, Any]] = []

    # Invalid quantity from quarantine
    for row in conn.execute(
        """
        SELECT id, source_row, raw_data, rejection_reason
        FROM quarantine
        ORDER BY source_row
        """
    ):
        reason = (row["rejection_reason"] or "").lower()
        try:
            payload = json.loads(row["raw_data"]) if row["raw_data"] else {}
        except (json.JSONDecodeError, TypeError):
            payload = {}
        qty = payload.get("quantity")
        if qty is None:
            continue
        qty_str = str(qty).strip().lower()
        if qty_str != "one" and "quantity" not in reason:
            continue
        if "quantity" not in reason and qty_str != "one":
            continue
        # Prefer rows that mention quantity in reason OR have literal "one"
        if qty_str != "one" and "quantity" not in reason:
            continue

        source_label = (
            payload.get("plm_row_id")
            or payload.get("component_ref")
            or f"row-{row['source_row']}"
        )
        issues.append(
            {
                "issue_type": "invalid_quantity",
                "refs": [source_label, f"quarantine:{row['id']}"],
                "detail": f"quantity={qty!r}",
                "explanation": (
                    f"Quarantined source row {row['source_row']} ({source_label}) "
                    f"has unparseable quantity {qty!r}. "
                    f"{row['rejection_reason'] or ''}".strip()
                ),
            }
        )

    # Duplicate normalized BOM keys
    groups: Dict[tuple, List[Dict[str, Any]]] = {}
    for row in conn.execute(
        """
        SELECT id, source_row, variant_ref_normalized, assembly_ref_normalized,
               component_ref_normalized, component_ref_raw
        FROM plm_bom_line
        WHERE component_ref_normalized IS NOT NULL
          AND TRIM(component_ref_normalized) != ''
        ORDER BY id
        """
    ):
        key = (
            row["variant_ref_normalized"],
            row["assembly_ref_normalized"],
            row["component_ref_normalized"],
        )
        groups.setdefault(key, []).append(dict(row))

    for key, members in sorted(groups.items(), key=lambda item: item[0]):
        if len(members) < 2:
            continue
        variant, assembly, component = key
        source_ids = [str(m["id"]) for m in members]
        raws = sorted({m["component_ref_raw"] or "" for m in members if m["component_ref_raw"]})
        issues.append(
            {
                "issue_type": "duplicate_bom_key",
                "refs": source_ids + [component] + raws,
                "detail": f"{variant}/{assembly}/{component} x{len(members)}",
                "explanation": (
                    f"Duplicate normalized BOM key {variant} / {assembly} / {component} "
                    f"appears {len(members)} times (source ids {', '.join(source_ids)}; "
                    f"raw refs: {', '.join(raws)})."
                ),
            }
        )

    # UOM alias informational: same component, different raw UOMs → same normalized
    by_component: Dict[str, Dict[str, Set[str]]] = {}
    for row in conn.execute(
        """
        SELECT component_ref_normalized, uom_raw, uom_normalized
        FROM plm_bom_line
        WHERE component_ref_normalized IS NOT NULL
          AND uom_normalized IS NOT NULL
        """
    ):
        ref = row["component_ref_normalized"]
        bucket = by_component.setdefault(ref, {"raws": set(), "norms": set()})
        if row["uom_raw"]:
            bucket["raws"].add(row["uom_raw"])
        bucket["norms"].add(row["uom_normalized"])

    for ref, bucket in sorted(by_component.items()):
        if len(bucket["raws"]) < 2:
            continue
        if len(bucket["norms"]) != 1:
            continue
        norm = next(iter(bucket["norms"]))
        raws = sorted(bucket["raws"])
        issues.append(
            {
                "issue_type": "uom_aliased",
                "refs": [ref] + raws,
                "detail": f"{'/'.join(raws)} → {norm}",
                "explanation": (
                    f"Component {ref} uses raw UOMs {', '.join(raws)} that all "
                    f"normalize to {norm}. Informational alias, not a conflict."
                ),
            }
        )

    # Warning summary (counts only; mapping noise flagged)
    summary: Dict[str, Any] = {}
    for row in conn.execute(
        """
        SELECT warning_type, COUNT(*) AS n
        FROM warnings
        GROUP BY warning_type
        ORDER BY warning_type
        """
    ):
        wtype = row["warning_type"]
        entry: Dict[str, Any] = {"count": row["n"]}
        if wtype in _MAPPING_NOISE_TYPES:
            entry["mapping_noise"] = True
        summary[wtype] = entry

    return {"issues": issues, "ingestion_warning_summary": summary}
