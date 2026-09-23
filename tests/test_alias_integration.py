"""Verify aliases are applied during real ingestion."""
import pytest
from pathlib import Path


class TestUOMAliasIngestion:
    """Verify UOM aliases applied during actual CSV ingestion."""

    def test_pcs_normalizes_to_ea_in_db(self, conn):
        """SCEN-C adjacent: pcs in CSV → EA in uom_normalized."""
        from app.services.ingestion import ingest_csv_file

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

        # Find rows where uom_raw is 'pcs' (case-insensitive)
        rows = conn.execute('''
            SELECT uom_raw, uom_normalized
            FROM plm_bom_line
            WHERE UPPER(uom_raw) = 'PCS'
            LIMIT 5
        ''').fetchall()

        assert len(rows) > 0, "Expected rows with uom_raw='pcs' in BOM data"
        for r in rows:
            assert r['uom_normalized'] == 'EA', \
                f"UOM alias failed: uom_raw={r['uom_raw']!r} should normalize to EA, got {r['uom_normalized']!r}"


class TestSupplierAliasIngestion:
    """Verify supplier aliases applied during actual CSV ingestion."""

    def test_siemens_normalizes_to_siemens_mobility(self, conn):
        """SIEMENS in CSV → SIEMENS MOBILITY in supplier_normalized."""
        from app.services.ingestion import ingest_csv_file

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

        rows = conn.execute('''
            SELECT supplier_raw, supplier_normalized
            FROM plm_bom_line
            WHERE supplier_raw IS NOT NULL
            ORDER BY supplier_raw
        ''').fetchall()

        for r in rows:
            raw_upper = r['supplier_raw'].upper()
            if 'SIEMENS' in raw_upper and 'SIEMENS MOBILITY' not in raw_upper:
                assert r['supplier_normalized'] == 'SIEMENS MOBILITY', \
                    f"Supplier alias failed: {r['supplier_raw']!r} → {r['supplier_normalized']!r}, expected SIEMENS MOBILITY"
