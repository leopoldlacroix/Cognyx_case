"""
Database connection utilities for Cognyx BOM Reuse Explorer.
"""
import sqlite3
from pathlib import Path

from app.db.schema import create_schema


def get_connection(db_path: str) -> sqlite3.Connection:
    """Get a database connection with foreign keys enabled and row factory set."""
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


def init_database(db_path: str) -> sqlite3.Connection:
    """Initialize the database: create directory if needed, create schema."""
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = get_connection(db_path)
    create_schema(conn)
    return conn
