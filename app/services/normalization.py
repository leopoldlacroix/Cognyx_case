"""
Normalization service for Cognyx BOM Reuse Explorer.

Generic normalization rules: whitespace collapse, casing standardization,
punctuation harmonization. Plus config-driven alias resolution.
"""
import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


def normalize_whitespace(s: Optional[str]) -> Optional[str]:
    """Collapse multiple whitespace to single space, trim."""
    if not s:
        return s
    return re.sub(r'\s+', ' ', s).strip()


def normalize_case_identifier(s: Optional[str]) -> Optional[str]:
    """Uppercase for reference identifiers."""
    if not s:
        return s
    return normalize_whitespace(s).upper()


def normalize_case_description(s: Optional[str]) -> Optional[str]:
    """Preserve case but trim for descriptions."""
    if not s:
        return s
    return normalize_whitespace(s)


def normalize_punctuation(s: Optional[str]) -> Optional[str]:
    """Harmonize dashes, underscores, periods in identifiers."""
    if not s:
        return s
    # Collapse whitespace around dashes/underscores
    s = re.sub(r'\s*[-_]\s*', '-', s)
    # Normalize any remaining sequences of dashes/underscores to single dash
    s = re.sub(r'[-_]+', '-', s)
    # Remove leading/trailing punctuation
    s = s.strip('-.')
    return s


def normalize_reference(raw: Optional[str]) -> Optional[str]:
    """Apply generic normalization to reference identifiers.

    Order: whitespace -> case (upper) -> punctuation
    """
    if not raw:
        return raw
    s = normalize_whitespace(raw)
    s = s.upper()
    s = normalize_punctuation(s)
    return s


def normalize_description(raw: Optional[str]) -> Optional[str]:
    """Apply generic normalization to descriptions.

    Order: whitespace -> preserve case -> light punctuation cleanup
    """
    if not raw:
        return raw
    return normalize_whitespace(raw)


def normalize_uom(raw: Optional[str]) -> Optional[str]:
    """Normalize UOM — generic cleanup only (aliases in PLAN-1.5)."""
    if not raw:
        return raw
    return normalize_whitespace(raw).upper()


def normalize_supplier(raw: Optional[str]) -> Optional[str]:
    """Normalize supplier name — generic cleanup only (aliases in PLAN-1.5)."""
    if not raw:
        return raw
    return normalize_whitespace(raw)


# --- Alias functions ---

def load_normalization_config() -> Dict:
    """Load normalization config from config/normalization.json."""
    config_path = Path(__file__).parent.parent.parent / 'config' / 'normalization.json'
    with open(config_path) as f:
        return json.load(f)


def apply_uom_aliases(normalized_uom: Optional[str], config: Dict) -> Optional[str]:
    """Apply UOM aliases. Returns canonical UOM or original if no alias found."""
    if not normalized_uom:
        return normalized_uom
    uom_aliases = config.get('uom_aliases', {})
    return uom_aliases.get(normalized_uom, normalized_uom)


def apply_supplier_aliases(normalized_supplier: Optional[str], config: Dict) -> Optional[str]:
    """Apply supplier aliases. Tries exact match first, then prefix matching.

    Both the input and config keys are normalized via normalize_reference
    for comparison, so hyphens/spaces/underscores don't break matching
    (e.g. 'KNORR BREMSE' matches config key 'KNORR-BREMSE').
    """
    if not normalized_supplier:
        return normalized_supplier

    supplier_aliases = config.get('supplier_aliases', {})

    # Normalize the input the same way config keys will be normalized
    # so punctuation discrepancies don't break matching
    norm_input = normalize_reference(normalized_supplier)

    # Build normalized lookup from config keys
    normalized_aliases: Dict[str, str] = {}
    for alias, canonical in supplier_aliases.items():
        norm_key = normalize_reference(alias)
        normalized_aliases[norm_key] = canonical

    # Exact match
    if norm_input in normalized_aliases:
        return normalized_aliases[norm_input]

    # Prefix match
    for norm_key, canonical in normalized_aliases.items():
        if norm_input.startswith(norm_key):
            return canonical

    return normalized_supplier


def apply_reference_aliases(normalized_reference: Optional[str], config: Dict) -> Optional[str]:
    """Apply reference aliases. Returns canonical reference or original if no alias found."""
    if not normalized_reference:
        return normalized_reference
    reference_aliases = config.get('reference_aliases', {})
    return reference_aliases.get(normalized_reference, normalized_reference)


def normalize_with_aliases(raw_value: Optional[str], field_type: str,
                          config: Optional[Dict] = None) -> Optional[str]:
    """Apply full normalization pipeline: generic rules + aliases.

    field_type: 'reference', 'description', 'uom', 'supplier'
    """
    if config is None:
        config = load_normalization_config()
    if not raw_value:
        return raw_value
    if field_type == 'reference':
        return apply_reference_aliases(normalize_reference(raw_value), config)
    elif field_type == 'uom':
        return apply_uom_aliases(normalize_uom(raw_value), config)
    elif field_type == 'supplier':
        return apply_supplier_aliases(normalize_supplier(raw_value), config)
    elif field_type == 'description':
        return normalize_description(raw_value)
    else:
        return normalize_whitespace(raw_value)


def normalize_erp_materials(conn: sqlite3.Connection, config: Optional[Dict] = None) -> Dict[str, Any]:
    """Normalize ERP material supplier references and UOM values (NORM-05).

    For each erp_material row:
    - Look up supplier_id_raw in erp_supplier.supplier_id_normalized
    - If found, populate supplier_name_normalized from erp_supplier.supplier_name_normalized
    - If not found, leave NULL and emit warning
    - Standardize base_unit_raw via UOM aliases from config

    Args:
        conn: Database connection
        config: Optional normalization config (loaded from config/normalization.json if None)

    Returns:
        Dict with stats: processed, matched, unmatched, uom_normalized, uom_unknown
    """
    if config is None:
        config = load_normalization_config()

    stats = {
        'processed': 0,
        'matched': 0,
        'unmatched': 0,
        'uom_normalized': 0,
        'uom_unknown': 0,
    }

    # Ensure supplier_id_normalized is populated (strip + upper — matches lookup compare)
    conn.execute(
        'UPDATE erp_supplier '
        'SET supplier_id_normalized = UPPER(TRIM(supplier_id_raw)) '
        'WHERE supplier_id_normalized IS NULL AND supplier_id_raw IS NOT NULL'
    )

    # Build supplier lookup: normalized_id → normalized_name
    # Match against supplier_id_normalized (which is the normalized form of supplier_id_raw)
    supplier_lookup = {}
    for row in conn.execute(
        'SELECT supplier_id_normalized, supplier_name_normalized '
        'FROM erp_supplier '
        'WHERE supplier_id_normalized IS NOT NULL '
        'AND supplier_name_normalized IS NOT NULL'
    ).fetchall():
        supplier_lookup[row['supplier_id_normalized']] = row['supplier_name_normalized']

    uom_aliases = config.get('uom_aliases', {})

    # Get all ERP materials with raw supplier_id
    materials = conn.execute(
        'SELECT id, supplier_id_raw, base_unit_raw FROM erp_material '
        'WHERE supplier_id_raw IS NOT NULL'
    ).fetchall()

    for mat in materials:
        stats['processed'] += 1
        mat_id = mat['id']
        supplier_id_raw = mat['supplier_id_raw']
        base_unit_raw = mat['base_unit_raw']

        # --- Supplier name mapping (NORM-05) ---
        matched_name = None
        # Try exact match against normalized supplier IDs
        for sup_id_norm, sup_name_norm in supplier_lookup.items():
            if supplier_id_raw.strip().upper() == sup_id_norm:
                matched_name = sup_name_norm
                break

        if matched_name:
            conn.execute(
                'UPDATE erp_material SET supplier_name_normalized = ? WHERE id = ?',
                (matched_name, mat_id)
            )
            stats['matched'] += 1
        else:
            stats['unmatched'] += 1
            # Emit soft warning for unmatched supplier
            from app.services.ingestion import add_warning
            add_warning(
                conn,
                'erp_material',
                mat_id,
                'unmatched_supplier',
                f"Supplier ID '{supplier_id_raw}' not found in ERP supplier master"
            )

        # --- UOM standardization (NORM-05) ---
        if base_unit_raw:
            raw_uom = base_unit_raw.strip().upper()
            normalized_uom = uom_aliases.get(raw_uom, raw_uom)
            conn.execute(
                'UPDATE erp_material SET base_unit_normalized = ? WHERE id = ?',
                (normalized_uom, mat_id)
            )
            # Known = alias key or canonical alias target (e.g. EA)
            known_uoms = set(uom_aliases.keys()) | set(uom_aliases.values())
            if raw_uom in known_uoms:
                stats['uom_normalized'] += 1
            else:
                stats['uom_unknown'] += 1
                from app.services.ingestion import add_warning
                add_warning(
                    conn,
                    'erp_material',
                    mat_id,
                    'unknown_uom',
                    f"Unknown UOM '{base_unit_raw}' left as '{normalized_uom}'"
                )

    conn.commit()
    return stats