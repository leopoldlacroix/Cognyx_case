"""
Source entity extraction — populate source_component / source_assembly /
source_supplier (and source_assembly_variant) from normalized raw tables.

Does not modify raw tables. Idempotent via UNIQUE(source_system, source_reference)
+ INSERT OR IGNORE.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Dict


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def extract_source_components(conn: sqlite3.Connection) -> Dict[str, int]:
    """Extract deduplicated source components from PLM BOM lines and ERP materials.

    Deduplicate by (source_system, source_reference) via UNIQUE + INSERT OR IGNORE.
    Return counts of newly inserted rows by source system.
    """
    now = _now()
    counts = {"PLM": 0, "ERP": 0}

    plm_rows = conn.execute(
        """
        SELECT id, component_ref_raw, component_ref_normalized, description_normalized
        FROM plm_bom_line
        WHERE component_ref_normalized IS NOT NULL
          AND component_ref_normalized != ''
          AND component_ref_raw IS NOT NULL
          AND component_ref_raw != ''
        ORDER BY id
        """
    ).fetchall()

    for row in plm_rows:
        cursor = conn.execute(
            """
            INSERT OR IGNORE INTO source_component (
                source_system, source_reference, normalized_reference,
                description, source_record_type, source_record_id, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "PLM",
                row["component_ref_raw"],
                row["component_ref_normalized"],
                row["description_normalized"],
                "BOM_LINE",
                row["id"],
                now,
            ),
        )
        counts["PLM"] += cursor.rowcount

    erp_rows = conn.execute(
        """
        SELECT id, material_id_raw, material_id_normalized, description_normalized
        FROM erp_material
        WHERE material_id_normalized IS NOT NULL
          AND material_id_normalized != ''
          AND material_id_raw IS NOT NULL
          AND material_id_raw != ''
        ORDER BY id
        """
    ).fetchall()

    for row in erp_rows:
        cursor = conn.execute(
            """
            INSERT OR IGNORE INTO source_component (
                source_system, source_reference, normalized_reference,
                description, source_record_type, source_record_id, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "ERP",
                row["material_id_raw"],
                row["material_id_normalized"],
                row["description_normalized"],
                "MATERIAL_MASTER",
                row["id"],
                now,
            ),
        )
        counts["ERP"] += cursor.rowcount

    conn.commit()
    return counts


def extract_source_assemblies(conn: sqlite3.Connection) -> Dict[str, int]:
    """Extract deduplicated source assemblies from PLM assembly_master.

    Also populate source_assembly_variant from plm_assembly.variant_ref_normalized.
    """
    now = _now()
    counts = {"PLM": 0, "variants": 0}

    rows = conn.execute(
        """
        SELECT id, assembly_ref_raw, assembly_ref_normalized,
               assembly_description_normalized
        FROM plm_assembly
        WHERE assembly_ref_normalized IS NOT NULL
          AND assembly_ref_normalized != ''
          AND assembly_ref_raw IS NOT NULL
          AND assembly_ref_raw != ''
        ORDER BY id
        """
    ).fetchall()

    for row in rows:
        cursor = conn.execute(
            """
            INSERT OR IGNORE INTO source_assembly (
                source_system, source_reference, normalized_reference,
                description, source_record_type, source_record_id, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "PLM",
                row["assembly_ref_raw"],
                row["assembly_ref_normalized"],
                row["assembly_description_normalized"],
                "ASSEMBLY_MASTER",
                row["id"],
                now,
            ),
        )
        counts["PLM"] += cursor.rowcount

    # Junction: preserve variant↔assembly linkage lost by flat source_assembly
    junction_rows = conn.execute(
        """
        SELECT sa.id AS source_assembly_id, pa.variant_ref_normalized
        FROM plm_assembly pa
        JOIN source_assembly sa
          ON sa.source_system = 'PLM'
         AND sa.source_reference = pa.assembly_ref_raw
        WHERE pa.variant_ref_normalized IS NOT NULL
          AND pa.variant_ref_normalized != ''
        ORDER BY pa.id
        """
    ).fetchall()

    for row in junction_rows:
        cursor = conn.execute(
            """
            INSERT OR IGNORE INTO source_assembly_variant (
                source_assembly_id, variant_ref_normalized, created_at
            ) VALUES (?, ?, ?)
            """,
            (row["source_assembly_id"], row["variant_ref_normalized"], now),
        )
        counts["variants"] += cursor.rowcount

    conn.commit()
    return counts


def extract_source_suppliers(conn: sqlite3.Connection) -> Dict[str, int]:
    """Extract deduplicated source suppliers from ERP supplier_master and PLM BOM."""
    now = _now()
    counts = {"PLM": 0, "ERP": 0}

    erp_rows = conn.execute(
        """
        SELECT id, supplier_id_raw, supplier_id_normalized,
               supplier_name_normalized, supplier_name_raw
        FROM erp_supplier
        WHERE supplier_id_raw IS NOT NULL
          AND supplier_id_raw != ''
        ORDER BY id
        """
    ).fetchall()

    for row in erp_rows:
        # Prefer name for cross-source matching; fall back to normalized ID
        normalized = row["supplier_name_normalized"] or row["supplier_id_normalized"]
        cursor = conn.execute(
            """
            INSERT OR IGNORE INTO source_supplier (
                source_system, source_reference, normalized_reference,
                description, source_record_type, source_record_id, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "ERP",
                row["supplier_id_raw"],
                normalized,
                row["supplier_name_raw"],
                "SUPPLIER_MASTER",
                row["id"],
                now,
            ),
        )
        counts["ERP"] += cursor.rowcount

    plm_rows = conn.execute(
        """
        SELECT id, supplier_raw, supplier_normalized
        FROM plm_bom_line
        WHERE supplier_raw IS NOT NULL
          AND supplier_raw != ''
        ORDER BY id
        """
    ).fetchall()

    for row in plm_rows:
        cursor = conn.execute(
            """
            INSERT OR IGNORE INTO source_supplier (
                source_system, source_reference, normalized_reference,
                description, source_record_type, source_record_id, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "PLM",
                row["supplier_raw"],
                row["supplier_normalized"],
                row["supplier_raw"],
                "BOM_LINE",
                row["id"],
                now,
            ),
        )
        counts["PLM"] += cursor.rowcount

    conn.commit()
    return counts


def run_source_extraction(conn: sqlite3.Connection) -> Dict:
    """Run assemblies → components → suppliers extraction; return combined counts."""
    assemblies = extract_source_assemblies(conn)
    components = extract_source_components(conn)
    suppliers = extract_source_suppliers(conn)
    return {
        "assemblies": assemblies,
        "components": components,
        "suppliers": suppliers,
    }
