"""
Normalization service for Cognyx BOM Reuse Explorer.

Generic normalization rules: whitespace collapse, casing standardization,
punctuation harmonization. Plus config-driven alias resolution.
"""
import json
import re
from pathlib import Path
from typing import Optional, Dict


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
    """Apply supplier aliases. Tries exact match first, then prefix matching."""
    if not normalized_supplier:
        return normalized_supplier
    supplier_aliases = config.get('supplier_aliases', {})
    # Exact match
    if normalized_supplier in supplier_aliases:
        return supplier_aliases[normalized_supplier]
    # Prefix match
    supplier_upper = normalized_supplier.upper()
    for alias, canonical in supplier_aliases.items():
        if supplier_upper.startswith(alias.upper()):
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
