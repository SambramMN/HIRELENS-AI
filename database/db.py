import sqlite3
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from contextlib import contextmanager
from config import config

SCHEMA_FILE = Path(__file__).resolve().parent / "schema.sql"

@contextmanager
def get_db_connection():
    """Context manager for SQLite connection that enables foreign keys, WAL mode, and ensures closure."""
    conn = sqlite3.connect(config.DATABASE_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db():
    """Initialize database tables and indexes from schema.sql."""
    db_file = Path(config.DATABASE_PATH)
    db_file.parent.mkdir(parents=True, exist_ok=True)
    
    with get_db_connection() as conn:
        with open(SCHEMA_FILE, "r", encoding="utf-8") as f:
            conn.executescript(f.read())

def log_audit_event(event_type: str, record_id: Optional[str], description: str, metadata: Optional[Dict[str, Any]] = None, conn=None):
    """Record an audit event to the audit_logs table using existing conn or new one."""
    try:
        if conn is not None:
            conn.execute(
                """
                INSERT INTO audit_logs (event_type, record_id, description, metadata_json)
                VALUES (?, ?, ?, ?)
                """,
                (
                    event_type,
                    str(record_id) if record_id else None,
                    description,
                    json.dumps(metadata or {})
                )
            )
        else:
            with get_db_connection() as c:
                c.execute(
                    """
                    INSERT INTO audit_logs (event_type, record_id, description, metadata_json)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        event_type,
                        str(record_id) if record_id else None,
                        description,
                        json.dumps(metadata or {})
                    )
                )
    except Exception as e:
        print(f"[Audit Log Error] Failed to write event: {e}")
