"""
Pytest configuration and fixtures.
"""
import pytest
import sqlite3
from pathlib import Path


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
