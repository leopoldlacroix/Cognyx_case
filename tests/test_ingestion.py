"""
Tests for ingestion module.
"""
import pytest
import sqlite3
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def db_path(tmp_path):
    """Create a temporary database path."""
    return str(tmp_path / "test.db")


@pytest.fixture
def conn(db_path):
    """Create a fresh database connection with schema."""
    from app.db.connection import init_database
    init_database(db_path)
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    return connection


@pytest.fixture
def sample_csv(tmp_path):
    """Create a sample CSV file for testing."""
    csv_path = tmp_path / "sample.csv"
    csv_path.write_text("id,name,value\n1,Test,100\n")
    return csv_path


class TestComputeFileHash:
    def test_returns_hex_string(self, tmp_path):
        from app.services.ingestion import compute_file_hash
        
        csv_path = tmp_path / "test.csv"
        csv_path.write_text("test content")
        
        hash_value = compute_file_hash(csv_path)
        
        assert isinstance(hash_value, str)
        assert len(hash_value) == 64  # SHA-256 hex digest
        assert all(c in '0123456789abcdef' for c in hash_value)

    def test_is_deterministic(self, tmp_path):
        from app.services.ingestion import compute_file_hash
        
        csv_path = tmp_path / "test.csv"
        csv_path.write_text("test content")
        
        hash1 = compute_file_hash(csv_path)
        hash2 = compute_file_hash(csv_path)
        
        assert hash1 == hash2

    def test_different_files_different_hashes(self, tmp_path):
        from app.services.ingestion import compute_file_hash
        
        csv1 = tmp_path / "test1.csv"
        csv1.write_text("content 1")
        csv2 = tmp_path / "test2.csv"
        csv2.write_text("content 2")
        
        hash1 = compute_file_hash(csv1)
        hash2 = compute_file_hash(csv2)
        
        assert hash1 != hash2


class TestRegisterSourceFile:
    def test_creates_record(self, conn):
        from app.services.ingestion import register_source_file
        from datetime import datetime, timezone
        
        ingested_at = datetime.now(timezone.utc)
        source_id = register_source_file(
            conn, 'PLM', 'test.csv', 'abc123', ingested_at
        )
        
        assert source_id > 0
        row = conn.execute("SELECT * FROM source_file WHERE id = ?", (source_id,)).fetchone()
        assert row['file_name'] == 'test.csv'
        assert row['source_system'] == 'PLM'
        assert row['file_hash'] == 'abc123'

    def test_duplicate_returns_existing_id(self, conn):
        from app.services.ingestion import register_source_file
        from datetime import datetime, timezone
        
        ingested_at = datetime.now(timezone.utc)
        id1 = register_source_file(conn, 'PLM', 'test.csv', 'abc123', ingested_at)
        id2 = register_source_file(conn, 'PLM', 'test.csv', 'abc123', ingested_at)
        
        assert id1 == id2


class TestIngestCSVFile:
    def test_bom_export_preserves_raw_values(self, conn):
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
        
        stats = ingest_csv_file(conn, bom_path, 'PLM', 'plm_bom_line', column_map)
        
        assert stats['row_count'] > 0
        
        # Check raw value preservation
        row = conn.execute(
            "SELECT component_ref_raw, variant_ref_raw, quantity_raw FROM plm_bom_line WHERE source_row = 2"
        ).fetchone()
        assert row['component_ref_raw'] == 'CTRL-AIR-01'
        assert row['variant_ref_raw'] == 'REGIO-STD'
        assert row['quantity_raw'] == '1'

    def test_source_row_numbers_correct(self, conn):
        from app.services.ingestion import ingest_csv_file
        
        bom_path = Path('/home/leopold-lacroix/Desktop/Projects/Cognyx/data/inputs/plm/bom_export.csv')
        column_map = {
            'variant_ref': 'variant_ref_raw',
            'assembly_ref': 'assembly_ref_raw',
            'component_ref': 'component_ref_raw',
        }
        
        ingest_csv_file(conn, bom_path, 'PLM', 'plm_bom_line', column_map)
        
        # First data row should be source_row = 2
        row = conn.execute(
            "SELECT source_row FROM plm_bom_line ORDER BY source_row LIMIT 1"
        ).fetchone()
        assert row['source_row'] == 2

    def test_idempotent_reimport(self, conn):
        from app.services.ingestion import ingest_csv_file
        
        bom_path = Path('/home/leopold-lacroix/Desktop/Projects/Cognyx/data/inputs/plm/bom_export.csv')
        column_map = {
            'variant_ref': 'variant_ref_raw',
            'assembly_ref': 'assembly_ref_raw',
            'component_ref': 'component_ref_raw',
        }
        
        stats1 = ingest_csv_file(conn, bom_path, 'PLM', 'plm_bom_line', column_map)
        count1 = conn.execute("SELECT COUNT(*) as c FROM plm_bom_line").fetchone()['c']
        
        stats2 = ingest_csv_file(conn, bom_path, 'PLM', 'plm_bom_line', column_map)
        count2 = conn.execute("SELECT COUNT(*) as c FROM plm_bom_line").fetchone()['c']
        
        assert count1 == count2  # No duplicate rows
        assert conn.execute("SELECT COUNT(*) as c FROM source_file").fetchone()['c'] == 1


class TestIngestionStatus:
    def test_get_ingestion_status_returns_files(self, conn):
        from app.services.ingestion import get_ingestion_status
        
        status = get_ingestion_status(conn)
        
        assert isinstance(status, list)

    def test_status_shows_source_files(self, conn):
        from app.services.ingestion import ingest_csv_file, get_ingestion_status
        
        bom_path = Path('/home/leopold-lacroix/Desktop/Projects/Cognyx/data/inputs/plm/bom_export.csv')
        column_map = {
            'variant_ref': 'variant_ref_raw',
            'assembly_ref': 'assembly_ref_raw',
            'component_ref': 'component_ref_raw',
        }
        
        ingest_csv_file(conn, bom_path, 'PLM', 'plm_bom_line', column_map)
        
        status = get_ingestion_status(conn)
        assert len(status) >= 1
        assert status[0]['file_name'] == 'bom_export.csv'
