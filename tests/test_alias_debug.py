"""Quick alias debug tests."""
import pytest
from app.services.normalization import (
    normalize_uom,
    apply_uom_aliases,
    load_normalization_config,
)


def test_uom_normalization_pipeline():
    """Verify UOM normalization + alias works end-to-end."""
    config = load_normalization_config()
    
    # Test 'pcs' -> should become 'EA'
    normalized = normalize_uom('pcs')
    assert normalized == 'PCS', f"normalize_uom('pcs') = {normalized}, expected 'PCS'"
    
    result = apply_uom_aliases(normalized, config)
    assert result == 'EA', f"apply_uom_aliases('PCS') = {result}, expected 'EA'"
    
    # Test 'units' -> should become 'EA'
    normalized = normalize_uom('units')
    result = apply_uom_aliases(normalized, config)
    assert result == 'EA', f"apply_uom_aliases('UNITS') = {result}, expected 'EA'"
    
    # Test 'EA' -> should stay 'EA'
    normalized = normalize_uom('EA')
    result = apply_uom_aliases(normalized, config)
    assert result == 'EA', f"apply_uom_aliases('EA') = {result}, expected 'EA'"
    
    # Test 'METER' -> should stay 'METER' (no alias)
    normalized = normalize_uom('METER')
    result = apply_uom_aliases(normalized, config)
    assert result == 'METER', f"apply_uom_aliases('METER') = {result}, expected 'METER'"


def test_config_loaded():
    """Verify config has expected alias counts."""
    config = load_normalization_config()
    assert len(config['uom_aliases']) == 6, f"Expected 6 UOM aliases, got {len(config['uom_aliases'])}"
    assert 'PCS' in config['uom_aliases']
    assert config['uom_aliases']['PCS'] == 'EA'
