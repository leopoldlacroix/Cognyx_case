"""
Tests for validation module.
"""
import pytest
from app.services.validation import (
    validate_hard,
    check_row_structure,
    check_soft_validation,
)


class TestHardValidation:
    def test_missing_component_ref_returns_reason(self):
        row = {'component_ref_raw': '', 'variant_ref_raw': 'REGIO-STD'}
        result = validate_hard(row, 'PLM', 'plm_bom_line')
        assert result == "Missing required identifier: component_ref_raw"

    def test_missing_material_id_returns_reason(self):
        row = {'material_id_raw': ''}
        result = validate_hard(row, 'ERP', 'erp_material')
        assert result == "Missing required identifier: material_id_raw"

    def test_missing_supplier_id_returns_reason(self):
        row = {'supplier_id_raw': ''}
        result = validate_hard(row, 'ERP', 'erp_supplier')
        assert result == "Missing required identifier: supplier_id_raw"

    def test_missing_variant_ref_returns_reason(self):
        row = {'variant_ref_raw': ''}
        result = validate_hard(row, 'PLM', 'plm_variant')
        assert result == "Missing required identifier: variant_ref_raw"

    def test_missing_assembly_ref_returns_reason(self):
        row = {'assembly_ref_raw': ''}
        result = validate_hard(row, 'PLM', 'plm_assembly')
        assert result == "Missing required identifier: assembly_ref_raw"

    def test_missing_note_reference_returns_reason(self):
        row = {'object_reference_raw': ''}
        result = validate_hard(row, 'ENGINEERING', 'engineering_note')
        assert result == "Missing required identifier: object_reference_raw"

    def test_valid_quantity_passes(self):
        row = {'component_ref_raw': 'CTRL-AIR-01', 'quantity_raw': '1'}
        result = validate_hard(row, 'PLM', 'plm_bom_line')
        assert result is None

    def test_unparseable_quantity_returns_reason(self):
        row = {'component_ref_raw': 'CTRL-AIR-01', 'quantity_raw': 'one'}
        result = validate_hard(row, 'PLM', 'plm_bom_line')
        assert result == "Unparseable quantity: 'one'"

    def test_empty_quantity_passes(self):
        row = {'component_ref_raw': 'CTRL-AIR-01', 'quantity_raw': ''}
        result = validate_hard(row, 'PLM', 'plm_bom_line')
        assert result is None

    def test_whitespace_only_identifier_returns_reason(self):
        row = {'component_ref_raw': '   ', 'variant_ref_raw': 'REGIO-STD'}
        result = validate_hard(row, 'PLM', 'plm_bom_line')
        assert result == "Missing required identifier: component_ref_raw"

    def test_none_quantity_passes(self):
        row = {'component_ref_raw': 'CTRL-AIR-01', 'quantity_raw': None}
        result = validate_hard(row, 'PLM', 'plm_bom_line')
        assert result is None


class TestRowStructure:
    def test_matching_columns_passes(self):
        row = {'a': '1', 'b': '2'}
        result = check_row_structure(row, ['a', 'b'], 'test_table')
        assert result is None

    def test_missing_columns_returns_error(self):
        row = {'a': '1'}
        result = check_row_structure(row, ['a', 'b'], 'test_table')
        assert result is not None
        assert 'missing' in result

    def test_extra_columns_returns_error(self):
        row = {'a': '1', 'b': '2', 'c': '3'}
        result = check_row_structure(row, ['a', 'b'], 'test_table')
        assert result is not None
        assert 'extra' in result

    def test_none_expected_columns_passes(self):
        row = {'a': '1'}
        result = check_row_structure(row, None, 'test_table')
        assert result is None


class TestSoftValidation:
    def test_missing_description_warning(self):
        row = {'description_raw': '', 'uom_raw': 'EA', 'supplier_raw': 'Test Supplier'}
        warnings = check_soft_validation(row, 'PLM')
        assert any(w['warning_type'] == 'missing_description' for w in warnings)

    def test_unknown_uom_warning(self):
        row = {'description_raw': 'Test', 'uom_raw': 'XYZZY', 'supplier_raw': 'Test Supplier'}
        warnings = check_soft_validation(row, 'PLM')
        assert any(w['warning_type'] == 'unknown_uom' for w in warnings)

    def test_empty_supplier_warning(self):
        row = {'description_raw': 'Test', 'uom_raw': 'EA', 'supplier_raw': ''}
        warnings = check_soft_validation(row, 'PLM')
        assert any(w['warning_type'] == 'empty_supplier' for w in warnings)

    def test_no_warnings_for_valid_row(self):
        row = {'description_raw': 'Valid description', 'uom_raw': 'EA', 'supplier_raw': 'Valid Supplier'}
        warnings = check_soft_validation(row, 'PLM')
        assert len(warnings) == 0

    def test_multiple_warnings(self):
        row = {'description_raw': '', 'uom_raw': 'UNKNOWN', 'supplier_raw': ''}
        warnings = check_soft_validation(row, 'PLM')
        assert len(warnings) >= 2

    def test_known_uoms_no_warning(self):
        for uom in ['EA', 'PCS', 'PC', 'PIECE', 'UNITS', 'SET', 'BOX', 'METER', 'M', 'MM', 'KG', 'L']:
            row = {'description_raw': 'Test', 'uom_raw': uom, 'supplier_raw': 'Supplier'}
            warnings = check_soft_validation(row, 'PLM')
            assert not any(w['warning_type'] == 'unknown_uom' for w in warnings), f"UOM {uom} should not trigger warning"

    def test_contradictory_quantity_warning(self):
        row = {'description_raw': 'Test', 'uom_raw': 'EA', 'supplier_raw': 'Supplier', 'quantity_raw': '0'}
        warnings = check_soft_validation(row, 'PLM')
        assert any(w['warning_type'] == 'contradictory_field' for w in warnings)

    def test_negative_quantity_warning(self):
        row = {'description_raw': 'Test', 'uom_raw': 'EA', 'supplier_raw': 'Supplier', 'quantity_raw': '-1'}
        warnings = check_soft_validation(row, 'PLM')
        assert any(w['warning_type'] == 'contradictory_field' for w in warnings)
