import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent.parent / "cage_logs.db"


def get_connection():
    """Returns sqlite3 connection with Row factory enabled."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initializes SQLite database schema and safely migrates columns for CAGE logs table."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            input_text TEXT,
            heuristic_score REAL,
            classifier_score REAL,
            final_score REAL,
            severity TEXT,
            attack_type TEXT,
            defense_action TEXT,
            output_validation_passed INTEGER,
            latency_ms REAL
        )
    """)
    cursor.execute("PRAGMA table_info(logs)")
    existing_cols = {row[1] for row in cursor.fetchall()}
    if "tier" not in existing_cols:
        cursor.execute("ALTER TABLE logs ADD COLUMN tier TEXT")
    if "triggered_chunk" not in existing_cols:
        cursor.execute("ALTER TABLE logs ADD COLUMN triggered_chunk TEXT")
    if "source_type" not in existing_cols:
        cursor.execute("ALTER TABLE logs ADD COLUMN source_type TEXT DEFAULT 'user_input'")
    conn.commit()
    conn.close()


# Ensure table exists upon module import
init_db()
