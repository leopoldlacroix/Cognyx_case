"""
Ingestion service for Cognyx BOM Reuse Explorer.

Handles CSV file ingestion with full provenance tracking.
"""
import csv
import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.db.connection import get_connection
from app.services.validation import validate_hard, check_row_structure, check_soft_validation
from app.services.normalization import (
    normalize_reference,
    normalize_description,
    normalize_uom,
    normalize_supplier,
    apply_reference_aliases,
    apply_uom_aliases,
    apply_supplier_aliases,
)


def compute_file_hash(file_path: Path) -> str:
    """Compute SHA-256 hash of file contents."""
    hasher = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            hasher.update(chunk)
    return hasher.hexdigest()


def register_source_file(
    conn: sqlite3.Connection,
    source_system: str,
    file_name: str,
    file_hash: Optional[str],
    ingested_at: datetime
) -> int:
    """Register a source file and return its ID."""
    cursor = conn.execute("""
        INSERT OR IGNORE INTO source_file (source_system, file_name, file_hash, ingested_at)
        VALUES (?, ?, ?, ?)
    """, (source_system, file_name, file_hash, ingested_at.isoformat()))
    
    if cursor.rowcount > 0:
        return cursor.lastrowid
    
    # Already exists - fetch existing ID
    row = conn.execute("""
        SELECT id FROM source_file WHERE source_system = ? AND file_hash = ?
    """, (source_system, file_hash)).fetchone()
    return row['id']


def quarantine_row(
    conn: sqlite3.Connection,
    source_file_id: int,
    source_row: int,
    row: Dict[str, Any],
    reason: str
) -> None:
    """Insert a row into the quarantine table."""
    conn.execute("""
        INSERT INTO quarantine (source_file_id, source_row, raw_data, rejection_reason, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, (
        source_file_id,
        source_row,
        json.dumps(row, ensure_ascii=False),
        reason,
        datetime.now(timezone.utc).isoformat()
    ))
    conn.commit()


def ingest_csv_file(
    conn: sqlite3.Connection,
    file_path: Path,
    source_system: str,
    table_name: str,
    column_map: Dict[str, str],
    required_cols: Optional[set] = None
) -> Dict[str, Any]:
    """
    Ingest a CSV file into the specified table.
    
    Args:
        conn: Database connection
        file_path: Path to CSV file
        source_system: Source system identifier (PLM, ERP, ENGINEERING)
        table_name: Target database table name
        column_map: Mapping from CSV column names to database column names
        required_cols: Optional set of required CSV column names
    
    Returns:
        Dict with row_count, quarantined_count, warnings_count, source_file_id
    """
    file_hash = compute_file_hash(file_path)
    ingested_at = datetime.now(timezone.utc)
    
    # Register source file
    source_file_id = register_source_file(conn, source_system, file_path.name, file_hash, ingested_at)
    
    stats = {
        'row_count': 0,
        'quarantined_count': 0,
        'warnings_count': 0,
        'source_file_id': source_file_id
    }
    
    with open(file_path, 'r', encoding='utf-8', newline='') as f:
        reader = csv.DictReader(f)
        
        # Check for existing source file (idempotency)
        existing_count = conn.execute(
            f'SELECT COUNT(*) as c FROM {table_name} WHERE source_file_id = ?',
            (source_file_id,)
        ).fetchone()['c']
        
        if existing_count > 0:
            # File already ingested - return existing stats without re-processing
            stats['row_count'] = existing_count
            return stats
        
        # Validate required columns
        if required_cols:
            missing = required_cols - set(reader.fieldnames or [])
            if missing:
                quarantine_row(conn, source_file_id, 0, {'columns': list(reader.fieldnames or [])}, 
                              f"Missing required columns: {missing}")
                stats['quarantined_count'] += 1
                return stats
        
        for source_row, row in enumerate(reader, start=2):  # Header is row 1
            stats['row_count'] += 1
            
            # Hard validation (pass column_map so validate_hard can map DB names to CSV names)
            hard_failure = validate_hard(row, source_system, table_name, column_map)
            if hard_failure:
                quarantine_row(conn, source_file_id, source_row, row, hard_failure)
                stats['quarantined_count'] += 1
                continue

            # Soft validation — record warnings but let row continue
            soft_warnings = check_soft_validation(row, source_system)
            for warning in soft_warnings:
                add_warning(conn, table_name, source_row, warning['warning_type'], warning['warning_message'])
                stats['warnings_count'] += 1

            # Build insert values
            insert_values = {'source_file_id': source_file_id, 'source_row': source_row}

            for csv_col, db_col in column_map.items():
                value = row.get(csv_col)
                # Store NULL for missing optional fields, not empty string
                if value is None or str(value).strip() == '':
                    insert_values[db_col] = None
                else:
                    insert_values[db_col] = value

            # Apply normalization for fields that have _normalized counterparts
            _apply_normalization(insert_values, table_name, row)
            
            # Insert into target table
            columns = list(insert_values.keys())
            values = list(insert_values.values())
            
            conn.execute(f"""
                INSERT INTO {table_name} ({', '.join(columns)})
                VALUES ({', '.join(['?' for _ in columns])})
            """, values)
        
        conn.commit()
    
    return stats


def ingest_all_files(conn: sqlite3.Connection, base_path: Path) -> Dict[str, Any]:
    """
    Ingest all 6 CSV files from the data inputs directory.
    
    Returns a summary report dict.
    """
    files_config = [
        {
            'path': 'plm/bom_export.csv',
            'system': 'PLM',
            'table': 'plm_bom_line',
            'required_cols': {'variant_ref', 'assembly_ref', 'component_ref'},
            'column_map': {
                'variant_ref': 'variant_ref_raw',
                'assembly_ref': 'assembly_ref_raw',
                'component_ref': 'component_ref_raw',
                'component_description': 'description_raw',
                'quantity': 'quantity_raw',
                'uom': 'uom_raw',
                'supplier_name': 'supplier_raw',
                'line_status': 'line_status_raw',
            },
        },
        {
            'path': 'plm/assembly_master.csv',
            'system': 'PLM',
            'table': 'plm_assembly',
            'required_cols': {'plm_assembly_ref'},
            'column_map': {
                'plm_assembly_ref': 'assembly_ref_raw',
                'assembly_description': 'assembly_description_raw',
                'variant_ref': 'variant_ref_raw',
                'revision': 'revision_raw',
                'lifecycle': 'lifecycle_raw',
            },
        },
        {
            'path': 'plm/variant_configuration.csv',
            'system': 'PLM',
            'table': 'plm_variant',
            'required_cols': {'variant_ref'},
            'column_map': {
                'variant_ref': 'variant_ref_raw',
                'variant_name': 'variant_name_raw',
                'train_family': 'train_family_raw',
                'market': 'market_raw',
                'climate_class': 'climate_class_raw',
                'capacity_class': 'capacity_class_raw',
                'voltage_system': 'voltage_system_raw',
                'notes': 'notes_raw',
            },
        },
        {
            'path': 'erp/material_master.csv',
            'system': 'ERP',
            'table': 'erp_material',
            'required_cols': {'material_id'},
            'column_map': {
                'material_id': 'material_id_raw',
                'material_description': 'description_raw',
                'material_type': 'material_type_raw',
                'base_unit': 'base_unit_raw',
                'supplier_id': 'supplier_id_raw',
                'category': 'category_raw',
                'status': 'status_raw',
                'standard_cost_eur': 'cost_raw',
            },
        },
        {
            'path': 'erp/supplier_master.csv',
            'system': 'ERP',
            'table': 'erp_supplier',
            'required_cols': {'supplier_id'},
            'column_map': {
                'supplier_id': 'supplier_id_raw',
                'supplier_name': 'supplier_name_raw',
                'country': 'country_raw',
            },
        },
        {
            'path': 'engineering/technical_notes.csv',
            'system': 'ENGINEERING',
            'table': 'engineering_note',
            'required_cols': {'object_reference', 'object_type', 'note_text'},
            'column_map': {
                'object_reference': 'object_reference_raw',
                'object_type': 'object_type',
                'language': 'language',
                'author': 'author',
                'date': 'date',
                'note_text': 'note_text',
            },
        },
    ]
    
    summary = {
        'files': [],
        'total_rows': 0,
        'total_quarantined': 0,
        'total_warnings': 0
    }
    
    for config in files_config:
        file_path = base_path / config['path']
        if not file_path.exists():
            continue
        
        stats = ingest_csv_file(
            conn,
            file_path,
            config['system'],
            config['table'],
            config['column_map'],
            config.get('required_cols')
        )
        
        summary['files'].append({
            'file_name': file_path.name,
            'source_system': config['system'],
            'table': config['table'],
            'row_count': stats['row_count'],
            'quarantined_count': stats['quarantined_count'],
            'warnings_count': stats['warnings_count'],
            'source_file_id': stats['source_file_id']
        })
        
        summary['total_rows'] += stats['row_count']
        summary['total_quarantined'] += stats['quarantined_count']
        summary['total_warnings'] += stats['warnings_count']
    
    return summary


def get_ingestion_status(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    """Get ingestion status for all source files."""
    rows = conn.execute("""
        SELECT sf.id, sf.source_system, sf.file_name, sf.file_hash, sf.ingested_at,
               COUNT(DISTINCT plm_bom_line.id) as bom_lines,
               COUNT(DISTINCT plm_assembly.id) as assemblies,
               COUNT(DISTINCT plm_variant.id) as variants,
               COUNT(DISTINCT erp_material.id) as materials,
               COUNT(DISTINCT erp_supplier.id) as suppliers,
               COUNT(DISTINCT engineering_note.id) as notes
        FROM source_file sf
        LEFT JOIN plm_bom_line ON plm_bom_line.source_file_id = sf.id
        LEFT JOIN plm_assembly ON plm_assembly.source_file_id = sf.id
        LEFT JOIN plm_variant ON plm_variant.source_file_id = sf.id
        LEFT JOIN erp_material ON erp_material.source_file_id = sf.id
        LEFT JOIN erp_supplier ON erp_supplier.source_file_id = sf.id
        LEFT JOIN engineering_note ON engineering_note.source_file_id = sf.id
        GROUP BY sf.id
        ORDER BY sf.ingested_at
    """).fetchall()
    
    return [dict(r) for r in rows]


def get_quarantine_report(conn: sqlite3.Connection, source_file_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """Return quarantine records with file provenance."""
    if source_file_id:
        rows = conn.execute("""
            SELECT q.id, q.source_file_id, q.source_row, q.rejection_reason,
                   q.created_at, sf.file_name, sf.source_system
            FROM quarantine q
            JOIN source_file sf ON q.source_file_id = sf.id
            WHERE q.source_file_id = ?
            ORDER BY q.source_row
        """, (source_file_id,)).fetchall()
    else:
        rows = conn.execute("""
            SELECT q.id, q.source_file_id, q.source_row, q.rejection_reason,
                   q.created_at, sf.file_name, sf.source_system
            FROM quarantine q
            JOIN source_file sf ON q.source_file_id = sf.id
            ORDER BY sf.file_name, q.source_row
        """).fetchall()
    
    return [dict(r) for r in rows]


def get_quarantine_count(conn: sqlite3.Connection, source_file_id: Optional[int] = None) -> int:
    """Return count of quarantined rows."""
    if source_file_id:
        return conn.execute(
            'SELECT COUNT(*) as c FROM quarantine WHERE source_file_id = ?',
            (source_file_id,)
        ).fetchone()['c']
    return conn.execute('SELECT COUNT(*) as c FROM quarantine').fetchone()['c']


def add_warning(
    conn: sqlite3.Connection,
    source_table: str,
    source_row_id: int,
    warning_type: str,
    warning_message: str
) -> None:
    """Record a soft validation warning."""
    conn.execute("""
        INSERT INTO warnings (source_table, source_row_id, warning_type, warning_message, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, (source_table, source_row_id, warning_type, warning_message,
          datetime.now(timezone.utc).isoformat()))
    conn.commit()


def get_warnings(
    conn: sqlite3.Connection,
    source_table: Optional[str] = None,
    source_row_id: Optional[int] = None
) -> List[Dict[str, Any]]:
    """Return soft validation warnings, optionally filtered."""
    if source_table and source_row_id:
        rows = conn.execute("""
            SELECT id, source_table, source_row_id, warning_type, warning_message, created_at
            FROM warnings
            WHERE source_table = ? AND source_row_id = ?
            ORDER BY created_at
        """, (source_table, source_row_id)).fetchall()
    elif source_table:
        rows = conn.execute("""
            SELECT id, source_table, source_row_id, warning_type, warning_message, created_at
            FROM warnings
            WHERE source_table = ?
            ORDER BY created_at
        """, (source_table,)).fetchall()
    else:
        rows = conn.execute("""
            SELECT id, source_table, source_row_id, warning_type, warning_message, created_at
            FROM warnings
            ORDER BY created_at
        """).fetchall()
    return [dict(r) for r in rows]


def _apply_normalization(
    insert_values: Dict[str, Any],
    table_name: str,
    raw_row: Dict[str, Any],
    config: Optional[Dict] = None
) -> None:
    """Apply normalization + aliases to produce *_normalized values."""
    if config is None:
        from app.services.normalization import load_normalization_config
        config = load_normalization_config()

    if table_name == 'plm_bom_line':
        # Reference fields: generic normalize -> alias lookup
        insert_values['variant_ref_normalized'] = normalize_reference(raw_row.get('variant_ref'))
        insert_values['assembly_ref_normalized'] = normalize_reference(raw_row.get('assembly_ref'))
        raw_comp = raw_row.get('component_ref')
        generic_comp = normalize_reference(raw_comp)
        insert_values['component_ref_normalized'] = apply_reference_aliases(generic_comp, config)
        # Description (mapped from component_description → description_raw)
        desc_raw = insert_values.get('description_raw') or raw_row.get('component_description')
        insert_values['description_normalized'] = normalize_description(desc_raw)
        # UOM: generic -> alias
        raw_uom = raw_row.get('uom')
        generic_uom = normalize_uom(raw_uom)
        insert_values['uom_normalized'] = apply_uom_aliases(generic_uom, config)
        # Supplier: generic -> alias
        raw_sup = raw_row.get('supplier_name')
        generic_sup = normalize_supplier(raw_sup)
        insert_values['supplier_normalized'] = apply_supplier_aliases(generic_sup, config)
        # Quantity
        qty_raw = raw_row.get('quantity')
        if qty_raw:
            try:
                insert_values['quantity_normalized'] = float(str(qty_raw).replace(',', ''))
            except (ValueError, TypeError):
                insert_values['quantity_normalized'] = None
        else:
            insert_values['quantity_normalized'] = None

    elif table_name == 'plm_assembly':
        insert_values['assembly_ref_normalized'] = normalize_reference(raw_row.get('plm_assembly_ref'))
        insert_values['assembly_description_normalized'] = normalize_description(raw_row.get('assembly_description'))
        insert_values['variant_ref_normalized'] = normalize_reference(raw_row.get('variant_ref'))

    elif table_name == 'plm_variant':
        insert_values['variant_ref_normalized'] = normalize_reference(raw_row.get('variant_ref'))
        insert_values['variant_name_normalized'] = normalize_description(raw_row.get('variant_name'))

    elif table_name == 'erp_material':
        insert_values['material_id_normalized'] = normalize_reference(raw_row.get('material_id'))
        insert_values['description_normalized'] = normalize_description(raw_row.get('material_description'))
        # UOM: generic normalize -> alias (NORM-05)
        raw_uom = raw_row.get('base_unit')
        generic_uom = normalize_uom(raw_uom)
        insert_values['base_unit_normalized'] = apply_uom_aliases(generic_uom, config)
        # Supplier name: will be populated by normalize_erp_materials() post-ingestion (NORM-05)
        # For now, store the raw supplier_id for later lookup
