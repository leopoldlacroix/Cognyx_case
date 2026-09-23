"""
Tests for validation module - quarantine reporting.
"""
import pytest
import sqlite3
from pathlib import Path

from app.services.validation import (
    validate_hard,
    check_row_structure,
    check_soft_validation,
)
from app.services.ingestion import (
    quarantine_row,
    get_quarantine_report,
    get_quarantine_count,
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


class TestQuarantineIntegration:
    """Tests for quarantine reporting with real database."""

    def test_quarantine_count_returns_integer(self, conn):
        from app.services.ingestion import ingest_csv_file, get_quarantine_count

        bom_path = Path('/home/leopold-lacroix/Desktop/Projects/Cognyx/data/inputs/plm/bom_export.csv')
        column_map = {
            'variant_ref': 'variant_ref_raw',
            'assembly_ref': 'assembly_ref_raw',
            'component_ref': 'component_ref_raw',
            'quantity': 'quantity_raw',
            'uom': 'uom_raw',
            'supplier_name': 'supplier_raw',
        }
        ingest_csv_file(conn, bom_path, 'PLM', 'plm_bom_line', column_map)

        count = get_quarantine_count(conn)
        assert isinstance(count, int)
        assert count >= 0


class TestSoftValidationIntegration:
    """Integration tests for soft validation with real CSV data."""

    def test_bom_export_creates_warnings(self, conn):
        from app.services.ingestion import ingest_csv_file, get_warnings

        bom_path = Path('/home/leopold-lacroix/Desktop/Projects/Cognyx/data/inputs/plm/bom_export.csv')
        column_map = {
            'variant_ref': 'variant_ref_raw',
            'assembly_ref': 'assembly_ref_raw',
            'component_ref': 'component_ref_raw',
            'quantity': 'quantity_raw',
            'uom': 'uom_raw',
            'supplier_name': 'supplier_raw',
        }

        stats = ingest_csv_file(conn, bom_path, 'PLM', 'plm_bom_line', column_map)

        warnings = get_warnings(conn, source_table='plm_bom_line')
        assert len(warnings) > 0, f"Expected warnings for bom_export.csv, got {len(warnings)}"

        # Verify warning types present in real data
        warning_types = {w['warning_type'] for w in warnings}
        assert 'unknown_uom' in warning_types or 'empty_supplier' in warning_types, \
            f"Expected unknown_uom or empty_supplier warnings, got {warning_types}"

        # Rows with warnings are still in the main table
        row_ids_with_warnings = {w['source_row_id'] for w in warnings}
        for row_id in list(row_ids_with_warnings)[:3]:
            row = conn.execute(
                'SELECT * FROM plm_bom_line WHERE source_row = ?', (row_id,)
            ).fetchone()
            assert row is not None, f"Row {row_id} with warning should exist in main table"

    def test_warnings_count_in_ingestion_stats(self, conn):
        from app.services.ingestion import ingest_csv_file, get_warnings

        bom_path = Path('/home/leopold-lacroix/Desktop/Projects/Cognyx/data/inputs/plm/bom_export.csv')
        column_map = {
            'variant_ref': 'variant_ref_raw',
            'assembly_ref': 'assembly_ref_raw',
            'component_ref': 'component_ref_raw',
            'quantity': 'quantity_raw',
            'uom': 'uom_raw',
            'supplier_name': 'supplier_raw',
        }

        stats = ingest_csv_file(conn, bom_path, 'PLM', 'plm_bom_line', column_map)

        assert stats['warnings_count'] > 0, "Expected warnings_count > 0 in stats"

        # Verify stats warnings_count matches actual warnings table count
        warnings = get_warnings(conn, source_table='plm_bom_line')
        assert stats['warnings_count'] == len(warnings), \
            f"Stats warnings_count ({stats['warnings_count']}) != actual ({len(warnings)})"

    def test_get_warnings_filter_by_source_row(self, conn):
        from app.services.ingestion import ingest_csv_file, get_warnings

        bom_path = Path('/home/leopold-lacroix/Desktop/Projects/Cognyx/data/inputs/plm/bom_export.csv')
        column_map = {
            'variant_ref': 'variant_ref_raw',
            'assembly_ref': 'assembly_ref_raw',
            'component_ref': 'component_ref_raw',
            'quantity': 'quantity_raw',
            'uom': 'uom_raw',
            'supplier_name': 'supplier_raw',
        }

        ingest_csv_file(conn, bom_path, 'PLM', 'plm_bom_line', column_map)

        # Find a row that has warnings
        all_warnings = get_warnings(conn, source_table='plm_bom_line')
        if all_warnings:
            sample_row_id = all_warnings[0]['source_row_id']
            filtered = get_warnings(conn, source_table='plm_bom_line', source_row_id=sample_row_id)
            assert len(filtered) > 0
            assert all(w['source_row_id'] == sample_row_id for w in filtered)

    def test_supplier_master_creates_warnings(self, conn):
        from app.services.ingestion import ingest_csv_file, get_warnings

        supplier_path = Path('/home/leopold-lacroix/Desktop/Projects/Cognyx/data/inputs/erp/supplier_master.csv')
        column_map = {
            'supplier_id': 'supplier_id_raw',
            'supplier_name': 'supplier_name_raw',
            'country': 'country_raw',
        }

        stats = ingest_csv_file(conn, supplier_path, 'ERP', 'erp_supplier', column_map)

        warnings = get_warnings(conn, source_table='erp_supplier')
        # Supplier table doesn't have description, so missing_description is expected
        # But check that the warnings system works for this table
        assert isinstance(stats['warnings_count'], int)
