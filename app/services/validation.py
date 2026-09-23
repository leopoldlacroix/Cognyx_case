"""
Validation service for Cognyx BOM Reuse Explorer.

Hard and soft validation for ingested rows.
"""
from typing import Any, Dict, List, Optional


def validate_hard(
    row: Dict[str, Any],
    source_system: str,
    table_name: str,
    column_map: Optional[Dict[str, str]] = None,
) -> Optional[str]:
    """
    Run hard validation checks on a parsed row.
    Returns rejection reason string if row fails, None if passes.

    Args:
        row: Raw CSV row dict (keys are CSV column names)
        source_system: Source system identifier (PLM, ERP, ENGINEERING)
        table_name: Target database table name
        column_map: Optional mapping from CSV column names to DB column names.
                    When provided, DB column names in required_id_fields are
                    reverse-mapped to CSV column names for lookup.
    """
    # Rule 1: Missing required identifier
    required_id_fields = {
        'plm_bom_line': ['component_ref_raw'],
        'plm_assembly': ['assembly_ref_raw'],
        'plm_variant': ['variant_ref_raw'],
        'erp_material': ['material_id_raw'],
        'erp_supplier': ['supplier_id_raw'],
        'engineering_note': ['object_reference_raw'],
    }

    if table_name in required_id_fields:
        for db_field in required_id_fields[table_name]:
            # Resolve CSV column name from column_map if provided
            csv_field = db_field
            if column_map:
                # Reverse lookup: find CSV col that maps to this DB col
                for csv_col, db_col in column_map.items():
                    if db_col == db_field:
                        csv_field = csv_col
                        break
            value = row.get(csv_field, '')
            if value is None or str(value).strip() == '':
                return f"Missing required identifier: {db_field}"

    # Rule 2: Unparseable quantity (BOM lines only)
    if table_name == 'plm_bom_line':
        # Resolve CSV column name for quantity
        qty_csv_field = 'quantity_raw'
        if column_map:
            for csv_col, db_col in column_map.items():
                if db_col == 'quantity_raw':
                    qty_csv_field = csv_col
                    break
        qty_raw = row.get(qty_csv_field, '')
        if qty_raw is not None and str(qty_raw).strip() != '':
            try:
                float(str(qty_raw).strip())
            except ValueError:
                return f"Unparseable quantity: '{qty_raw}'"

    return None


def check_row_structure(
    row: Dict[str, Any],
    expected_columns: List[str],
    table_name: str
) -> Optional[str]:
    """
    Check that row has the expected columns.
    Returns error message if mismatch, None if OK.
    """
    if expected_columns is None:
        return None
    
    row_keys = set(row.keys())
    expected_set = set(expected_columns)
    
    if row_keys != expected_set:
        missing = expected_set - row_keys
        extra = row_keys - expected_set
        parts = []
        if missing:
            parts.append(f"missing: {missing}")
        if extra:
            parts.append(f"extra: {extra}")
        return f"Wrong column count for {table_name}: {', '.join(parts)}"
    
    return None


# Known UOM values for soft validation
KNOWN_UOMS = {'EA', 'PCS', 'PC', 'PIECE', 'UNITS', 'SET', 'BOX', 'METER', 'M', 'MM', 'KG', 'L'}


def check_soft_validation(
    row: Dict[str, Any],
    source_system: str
) -> List[Dict[str, str]]:
    """
    Check row for soft validation issues.
    Returns list of warning dicts.
    """
    warnings = []
    
    # Check missing description
    desc = row.get('description_raw') or row.get('description')
    if not desc or str(desc).strip() == '':
        warnings.append({
            'warning_type': 'missing_description',
            'warning_message': f'Missing description for {source_system} row'
        })
    
    # Check unknown UOM
    uom = row.get('uom_raw') or row.get('uom')
    if uom and str(uom).strip().upper() not in KNOWN_UOMS:
        warnings.append({
            'warning_type': 'unknown_uom',
            'warning_message': f'Unknown UOM: {uom}'
        })
    
    # Check empty supplier
    supplier = row.get('supplier_raw') or row.get('supplier_name')
    if not supplier or str(supplier).strip() == '':
        warnings.append({
            'warning_type': 'empty_supplier',
            'warning_message': 'Missing supplier reference'
        })
    
    # Check contradictory quantity (<= 0)
    qty = row.get('quantity_raw') or row.get('quantity')
    if qty:
        try:
            qty_val = float(str(qty).replace(',', ''))
            if qty_val <= 0:
                warnings.append({
                    'warning_type': 'contradictory_field',
                    'warning_message': f'Quantity <= 0: {qty}'
                })
        except (ValueError, TypeError):
            pass  # Hard validation would catch unparseable
    
    return warnings
