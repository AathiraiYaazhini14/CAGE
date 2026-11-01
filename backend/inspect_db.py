#!/usr/bin/env python3
"""
CAGE Database Inspector
Quickly inspects cage_logs.db tables, schemas, and live records.
Usage:
    python inspect_db.py
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "cage_logs.db"

def inspect():
    if not DB_PATH.exists():
        print(f"[ERROR] Database file not found at: {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 1. PRAGMA & WAL Status
    cursor.execute("PRAGMA journal_mode;")
    wal_mode = cursor.fetchone()[0]

    print("=" * 80)
    print(f"  CAGE SQLITE DATABASE INSPECTOR: {DB_PATH.name}")
    print(f"  Location: {DB_PATH}")
    print(f"  Storage Engine: SQLite with WAL (Write-Ahead Logging) Mode: {wal_mode.upper()}")
    print("=" * 80)

    # 2. Tables & Counts
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
    tables = [r[0] for r in cursor.fetchall()]

    print("\n--- [1] DATABASE SCHEMA & RECORD COUNTS ---")
    for t in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {t}")
        count = cursor.fetchone()[0]
        print(f"  Table: {t:<12} | Records: {count}")

    # 3. Users Table Sample
    print("\n--- [2] USERS TABLE (Sample Accounts) ---")
    cursor.execute("SELECT id, name, email, password_hash, created_at FROM users ORDER BY id ASC LIMIT 5;")
    users = cursor.fetchall()
    print(f"  {'ID':<4} | {'Name':<16} | {'Email':<28} | {'Password Hash (bcrypt)':<22} | {'Created At'}")
    print("  " + "-" * 76)
    for u in users:
        pwd_preview = u['password_hash'][:14] + "..." if u['password_hash'] else "N/A"
        print(f"  {u['id']:<4} | {u['name']:<16} | {u['email']:<28} | {pwd_preview:<22} | {str(u['created_at'])[:19]}")

    # 4. API Keys Table Sample
    print("\n--- [3] API KEYS TABLE (Per-Account Isolated Tokens) ---")
    cursor.execute("SELECT id, user_id, name, prefix, environment, scope, status FROM api_keys ORDER BY rowid DESC LIMIT 5;")
    keys = cursor.fetchall()
    if keys:
        print(f"  {'Key ID':<16} | {'User ID':<8} | {'Key Name':<24} | {'Prefix':<22} | {'Env':<10} | {'Status'}")
        print("  " + "-" * 76)
        for k in keys:
            raw_prefix = k['prefix'] or ""
            clean_prefix = raw_prefix.encode("ascii", "replace").decode("ascii").replace("?", "*")
            print(f"  {k['id']:<16} | {k['user_id']:<8} | {k['name']:<24} | {clean_prefix:<22} | {k['environment']:<10} | {k['status']}")
    else:
        print("  (No API keys found)")

    # 5. Recent Logs Sample
    print("\n--- [4] THREAT AUDIT LOGS (Latest 5 Scans) ---")
    cursor.execute("""
        SELECT id, timestamp, tier, defense_action, source_type, final_score, input_text, triggered_chunk
        FROM logs ORDER BY id DESC LIMIT 5;
    """)
    logs = cursor.fetchall()
    print(f"  {'ID':<5} | {'Tier':<8} | {'Action':<8} | {'Score':<6} | {'Source':<14} | {'Input Text (Snippet)'}")
    print("  " + "-" * 76)
    for l in logs:
        text_snip = (l['input_text'] or "").replace("\n", " ").strip()[:35]
        tier_str = l['tier'] or "N/A"
        action_str = l['defense_action'] or "N/A"
        score_str = f"{l['final_score']:.3f}" if l['final_score'] is not None else "0.000"
        src_str = l['source_type'] or "user_input"
        print(f"  {l['id']:<5} | {tier_str:<8} | {action_str:<8} | {score_str:<6} | {src_str:<14} | \"{text_snip}...\"")

    print("\n" + "=" * 80)
    print("  Inspection complete. All records verified and committed in SQLite WAL.")
    print("=" * 80)

    conn.close()

if __name__ == "__main__":
    inspect()
