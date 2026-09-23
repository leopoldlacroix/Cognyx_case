"""
Tests for normalization module.
"""
import pytest
from app.services.normalization import (
    normalize_reference,
    normalize_description,
    normalize_uom,
    normalize_supplier,
    normalize_whitespace,
    normalize_punctuation,
)


class TestNormalizeReference:
    def test_uppercase(self):
        assert normalize_reference('ctrl-air-01') == 'CTRL-AIR-01'

    def test_whitespace_collapse(self):
        assert normalize_reference('CTRL  -  AIR-01') == 'CTRL-AIR-01'

    def test_punctuation_harmonization_underscore(self):
        assert normalize_reference('CTRL_AIR_01') == 'CTRL-AIR-01'

    def test_punctuation_harmonization_double_dash(self):
        assert normalize_reference('CTRL--AIR-01') == 'CTRL-AIR-01'

    def test_trim(self):
        assert normalize_reference('  CTRL-AIR-01  ') == 'CTRL-AIR-01'

    def test_none_input(self):
        assert normalize_reference(None) is None

    def test_empty_string(self):
        assert normalize_reference('') == ''


class TestNormalizeDescription:
    def test_preserve_case(self):
        assert normalize_description('HVAC Control Unit') == 'HVAC Control Unit'

    def test_whitespace_collapse(self):
        assert normalize_description('HVAC   Control    Unit') == 'HVAC Control Unit'

    def test_trim(self):
        assert normalize_description('  HVAC Control Unit  ') == 'HVAC Control Unit'

    def test_none_input(self):
        assert normalize_description(None) is None

    def test_empty_string(self):
        assert normalize_description('') == ''


class TestNormalizeUOM:
    def test_uppercase(self):
        assert normalize_uom('pcs') == 'PCS'
        assert normalize_uom('ea') == 'EA'

    def test_whitespace_trim(self):
        assert normalize_uom('  pcs  ') == 'PCS'

    def test_none_input(self):
        assert normalize_uom(None) is None


class TestNormalizeSupplier:
    def test_whitespace_collapse(self):
        assert normalize_supplier('Siemens   Mobility') == 'Siemens Mobility'

    def test_trim(self):
        assert normalize_supplier('  Siemens  ') == 'Siemens'

    def test_none_input(self):
        assert normalize_supplier(None) is None


class TestDeterministic:
    def test_same_input_same_output(self):
        test_input = '  Ctrl_AIR-01  '
        result1 = normalize_reference(test_input)
        result2 = normalize_reference(test_input)
        assert result1 == result2


class TestWhitespaceHelper:
    def test_collapse_multiple_spaces(self):
        assert normalize_whitespace('a   b    c') == 'a b c'

    def test_trim(self):
        assert normalize_whitespace('  hello  ') == 'hello'

    def test_none(self):
        assert normalize_whitespace(None) is None


class TestPunctuationHelper:
    def test_underscore_to_dash(self):
        assert normalize_punctuation('CTRL_AIR') == 'CTRL-AIR'

    def test_multiple_dashes(self):
        assert normalize_punctuation('CTRL---AIR') == 'CTRL-AIR'

    def test_leading_trailing_dash(self):
        assert normalize_punctuation('-CTRL-AIR-') == 'CTRL-AIR'

    def test_none(self):
        assert normalize_punctuation(None) is None


class TestERPNormalization:
    """Tests for ERP material normalization (NORM-05)."""

    def test_erp_supplier_mapping_matches_known_supplier(self, db_connection):
        """ERP materials have supplier_name_normalized populated from supplier master lookup."""
        from app.services.normalization import normalize_erp_materials
        from app.db.connection import get_connection

        conn = get_connection(':memory:')
        conn.execute("PRAGMA foreign_keys = ON")

        # Create schema
        from app.db.schema import create_schema
        create_schema(conn)

        # FK parent for ERP rows
        conn.execute(
            'INSERT INTO source_file (source_system, file_name, file_hash, ingested_at) '
            'VALUES (?, ?, ?, ?)',
            ('ERP', 'material_master.csv', 'testhash', '2026-01-01T00:00:00Z')
        )

        # Insert ERP supplier
        conn.execute(
            'INSERT INTO erp_supplier (source_file_id, source_row, supplier_id_raw, '
            'supplier_name_raw, country_raw, supplier_name_normalized) VALUES (?, ?, ?, ?, ?, ?)',
            (1, 1, 'SUP-001', 'Siemens Mobility GmbH', 'Germany', 'SIEMENS MOBILITY')
        )

        # Insert ERP material with matching supplier
        conn.execute(
            'INSERT INTO erp_material (source_file_id, source_row, material_id_raw, '
            'description_raw, material_type_raw, base_unit_raw, supplier_id_raw, '
            'category_raw, status_raw, cost_raw, material_id_normalized, '
            'description_normalized, supplier_name_normalized, base_unit_normalized) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (1, 2, 'MAT-10001', 'HVAC Control Unit', 'COMPONENT', 'EA', 'SUP-001',
             'HVAC', 'ACTIVE', 1850, 'MAT-10001', 'HVAC Control Unit', None, None)
        )
        conn.commit()

        # Run normalization
        stats = normalize_erp_materials(conn)

        # Verify
        result = conn.execute(
            'SELECT supplier_name_normalized, base_unit_normalized FROM erp_material '
            'WHERE material_id_raw = ?',
            ('MAT-10001',)
        ).fetchone()
        assert result['supplier_name_normalized'] == 'SIEMENS MOBILITY', \
            f"Expected 'SIEMENS MOBILITY', got {result['supplier_name_normalized']}"
        assert result['base_unit_normalized'] == 'EA'

    def test_erp_supplier_mapping_unmatched_emits_warning(self, db_connection):
        """Unmatched supplier IDs leave normalized NULL with warning."""
        from app.services.normalization import normalize_erp_materials
        from app.db.connection import get_connection

        conn = get_connection(':memory:')
        conn.execute("PRAGMA foreign_keys = ON")

        # Create schema
        from app.db.schema import create_schema
        create_schema(conn)

        # FK parent for ERP rows
        conn.execute(
            'INSERT INTO source_file (source_system, file_name, file_hash, ingested_at) '
            'VALUES (?, ?, ?, ?)',
            ('ERP', 'material_master.csv', 'testhash', '2026-01-01T00:00:00Z')
        )

        # Insert ERP material with unknown supplier (no supplier in master)
        conn.execute(
            'INSERT INTO erp_material (source_file_id, source_row, material_id_raw, '
            'description_raw, material_type_raw, base_unit_raw, supplier_id_raw, '
            'category_raw, status_raw, cost_raw, material_id_normalized, '
            'description_normalized, supplier_name_normalized, base_unit_normalized) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (1, 1, 'MAT-99999', 'Unknown Part', 'COMPONENT', 'EA', 'SUP-999',
             'UNKNOWN', 'ACTIVE', 100, 'MAT-99999', 'Unknown Part', None, None)
        )
        conn.commit()

        # Run normalization
        stats = normalize_erp_materials(conn)

        # Verify unmatched
        assert stats['unmatched'] == 1, f"Expected 1 unmatched, got {stats['unmatched']}"

        result = conn.execute(
            'SELECT supplier_name_normalized FROM erp_material WHERE id = 1'
        ).fetchone()
        assert result['supplier_name_normalized'] is None, \
            f"Expected NULL for unmatched supplier, got {result['supplier_name_normalized']}"

        # Verify warning was emitted
        warnings = conn.execute(
            "SELECT warning_type FROM warnings WHERE source_table = 'erp_material'"
        ).fetchall()
        assert len(warnings) == 1, f"Expected 1 warning, got {len(warnings)}"
        assert warnings[0]['warning_type'] == 'unmatched_supplier'

    def test_erp_uom_standardization(self, db_connection):
        """ERP materials have base_unit_normalized standardized via UOM aliases."""
        from app.services.normalization import normalize_erp_materials, load_normalization_config
        from app.db.connection import get_connection

        conn = get_connection(':memory:')
        conn.execute("PRAGMA foreign_keys = ON")

        # Create schema
        from app.db.schema import create_schema
        create_schema(conn)

        # FK parent for ERP rows
        conn.execute(
            'INSERT INTO source_file (source_system, file_name, file_hash, ingested_at) '
            'VALUES (?, ?, ?, ?)',
            ('ERP', 'material_master.csv', 'testhash', '2026-01-01T00:00:00Z')
        )

        # Matching supplier so unmatched_supplier warnings don't obscure UOM checks
        conn.execute(
            'INSERT INTO erp_supplier (source_file_id, source_row, supplier_id_raw, '
            'supplier_name_raw, country_raw, supplier_name_normalized) VALUES (?, ?, ?, ?, ?, ?)',
            (1, 1, 'SUP-001', 'Siemens Mobility GmbH', 'Germany', 'SIEMENS MOBILITY')
        )

        config = load_normalization_config()

        # Insert ERP material with various UOMs
        test_cases = [
            ('MAT-001', 'EA', 'EA', True),   # Already canonical
            ('MAT-002', 'PCS', 'EA', True),  # Alias to EA
            ('MAT-003', 'PIECE', 'EA', True),  # Alias to EA
            ('MAT-004', 'SET', 'EA', True),  # Alias to EA
            ('MAT-005', 'METER', 'METER', False),  # Unknown, kept as-is
        ]

        for mat_id, uom_raw, expected_norm, is_alias in test_cases:
            conn.execute(
                'INSERT INTO erp_material (source_file_id, source_row, material_id_raw, '
                'description_raw, material_type_raw, base_unit_raw, supplier_id_raw, '
                'category_raw, status_raw, cost_raw, material_id_normalized, '
                'description_normalized, supplier_name_normalized, base_unit_normalized) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                (1, 1, mat_id, 'Test Part', 'COMPONENT', uom_raw, 'SUP-001',
                 'TEST', 'ACTIVE', 100, mat_id, 'Test Part', 'SIEMENS MOBILITY', None)
            )
        conn.commit()

        # Run normalization
        stats = normalize_erp_materials(conn)

        # Verify UOM standardization
        assert stats['uom_normalized'] == 4, f"Expected 4 UOM normalized, got {stats['uom_normalized']}"
        assert stats['uom_unknown'] == 1, f"Expected 1 unknown UOM, got {stats['uom_unknown']}"

        # Check specific materials
        for mat_id, uom_raw, expected_norm, is_alias in test_cases:
            result = conn.execute(
                'SELECT base_unit_normalized FROM erp_material WHERE material_id_raw = ?',
                (mat_id,)
            ).fetchone()
            assert result['base_unit_normalized'] == expected_norm, \
                f"Material {mat_id}: expected {expected_norm}, got {result['base_unit_normalized']}"

        # Unknown UOM emits soft warning
        uom_warnings = conn.execute(
            "SELECT warning_type FROM warnings WHERE warning_type = 'unknown_uom'"
        ).fetchall()
        assert len(uom_warnings) == 1, f"Expected 1 unknown_uom warning, got {len(uom_warnings)}"
