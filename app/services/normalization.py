"""
Normalization service for Cognyx BOM Reuse Explorer.

Generic normalization rules: whitespace collapse, casing standardization,
punctuation harmonization. Deterministic — same input always produces same output.
"""
import re
from typing import Optional


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
