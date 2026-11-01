import sqlite3
from pathlib import Path
from src.auth.auth_service import hash_password

DB_PATH = Path(__file__).resolve().parent.parent.parent / "cage_logs.db"


def get_connection():
    """Returns sqlite3 connection with Row factory and WAL mode enabled."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn


def init_db():
    """Initializes SQLite database schema, enables WAL mode, and safely migrates columns."""
    conn = get_connection()
    cursor = conn.cursor()

    # 1. Ensure WAL Mode
    cursor.execute("PRAGMA journal_mode=WAL;")

    # 2. Users Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 3. Logs Table
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

    # 4. Safe Column Migrations for logs table (old rows remain valid)
    cursor.execute("PRAGMA table_info(logs)")
    existing_cols = {row[1] for row in cursor.fetchall()}

    if "tier" not in existing_cols:
        cursor.execute("ALTER TABLE logs ADD COLUMN tier TEXT")
    if "triggered_chunk" not in existing_cols:
        cursor.execute("ALTER TABLE logs ADD COLUMN triggered_chunk TEXT")
    if "source_type" not in existing_cols:
        cursor.execute("ALTER TABLE logs ADD COLUMN source_type TEXT DEFAULT 'user_input'")
    if "user_id" not in existing_cols:
        cursor.execute("ALTER TABLE logs ADD COLUMN user_id INTEGER")
    if "is_demo" not in existing_cols:
        cursor.execute("ALTER TABLE logs ADD COLUMN is_demo INTEGER DEFAULT 0")
    if "protected" not in existing_cols:
        cursor.execute("ALTER TABLE logs ADD COLUMN protected INTEGER DEFAULT 0")
    if "matched_patterns" not in existing_cols:
        cursor.execute("ALTER TABLE logs ADD COLUMN matched_patterns TEXT")

    # 5. Create default demo user if not present (demo@cage.dev)
    cursor.execute("SELECT id FROM users WHERE email = 'demo@cage.dev'")
    demo_user = cursor.fetchone()
    if not demo_user:
        demo_pwd_hash = hash_password("demo1234")
        cursor.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            ("Demo User", "demo@cage.dev", demo_pwd_hash)
        )
        demo_user_id = cursor.lastrowid
    else:
        demo_user_id = demo_user["id"]

    # 6. API Keys Table (Strictly isolated by user_id)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS api_keys (
            id TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            prefix TEXT NOT NULL,
            full_key TEXT NOT NULL,
            environment TEXT NOT NULL,
            scope TEXT NOT NULL,
            created_at TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Active',
            last_used TEXT NOT NULL DEFAULT 'Never',
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)

    # Pre-seed 2 sample demonstration keys specifically for demo@cage.dev only if empty
    cursor.execute("SELECT COUNT(*) as count FROM api_keys WHERE user_id = ?", (demo_user_id,))
    if cursor.fetchone()["count"] == 0:
        cursor.execute("""
            INSERT INTO api_keys (id, user_id, name, prefix, full_key, environment, scope, created_at, status, last_used)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            "key_demo_prod",
            demo_user_id,
            "Production LLM Gateway",
            "cage_live_9f82••••••••••••a99c",
            "cage_live_9f82c07a51d84f93e2b10a99c7d41ef0",
            "Production",
            "Full Access (Scan + Demo)",
            "Oct 31, 2026",
            "Active",
            "Just now"
        ))
        cursor.execute("""
            INSERT INTO api_keys (id, user_id, name, prefix, full_key, environment, scope, created_at, status, last_used)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            "key_demo_staging",
            demo_user_id,
            "Staging Pipeline Agent",
            "cage_test_4a11••••••••••••7e23",
            "cage_test_4a11b89ef0321ca88921df0194877e23",
            "Staging",
            "Read-Only (Stats & Logs)",
            "Oct 28, 2026",
            "Active",
            "2 days ago"
        ))

    conn.commit()
    conn.close()


# Ensure table exists upon module import
init_db()
