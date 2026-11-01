import json
import csv
import io
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from src.logging.db import get_connection


def log_request(
    input_text: str,
    heuristic_score: float,
    classifier_score: float,
    final_score: float,
    severity: str,
    attack_type: str,
    defense_action: str,
    output_validation_passed: Optional[bool],
    latency_ms: float,
    tier: Optional[str] = None,
    triggered_chunk: Optional[str] = None,
    source_type: Optional[str] = "user_input",
    user_id: Optional[int] = None,
    is_demo: int = 0,
    protected: int = 0,
    matched_patterns: Optional[Any] = None,
    timestamp: Optional[str] = None
) -> int:
    """Inserts a request log entry into the database and returns the new row ID."""
    conn = get_connection()
    cursor = conn.cursor()

    val_passed = 1 if output_validation_passed is True else (0 if output_validation_passed is False else None)
    timestamp_str = timestamp or datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    patterns_str = None
    if matched_patterns is not None:
        if isinstance(matched_patterns, str):
            patterns_str = matched_patterns
        else:
            try:
                patterns_str = json.dumps(matched_patterns)
            except Exception:
                patterns_str = str(matched_patterns)

    cursor.execute("""
        INSERT INTO logs (
            timestamp, input_text, heuristic_score, classifier_score, final_score,
            severity, attack_type, defense_action, output_validation_passed, latency_ms,
            tier, triggered_chunk, source_type, user_id, is_demo, protected, matched_patterns
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        timestamp_str,
        input_text,
        heuristic_score,
        classifier_score,
        final_score,
        severity,
        attack_type,
        defense_action,
        val_passed,
        round(latency_ms, 2),
        tier,
        triggered_chunk,
        source_type or "user_input",
        user_id,
        is_demo,
        protected,
        patterns_str
    ))

    conn.commit()
    row_id = cursor.lastrowid
    conn.close()
    return row_id


def parse_log_row(row: Any) -> Dict[str, Any]:
    """Helper to convert sqlite3.Row into dict format with JSON parsed fields."""
    val_passed = bool(row["output_validation_passed"]) if row["output_validation_passed"] is not None else None
    
    matched_patterns = []
    if "matched_patterns" in row.keys() and row["matched_patterns"]:
        try:
            matched_patterns = json.loads(row["matched_patterns"])
        except Exception:
            matched_patterns = []

    return {
        "id": row["id"],
        "timestamp": row["timestamp"],
        "input_text": row["input_text"],
        "text": row["input_text"],
        "heuristic_score": row["heuristic_score"],
        "classifier_score": row["classifier_score"],
        "final_score": row["final_score"],
        "score": row["final_score"],
        "severity": row["severity"],
        "attack_type": row["attack_type"],
        "defense_action": row["defense_action"],
        "action": row["defense_action"],
        "output_validation_passed": val_passed,
        "latency_ms": row["latency_ms"],
        "tier": row["tier"] if "tier" in row.keys() else None,
        "triggered_chunk": row["triggered_chunk"] if "triggered_chunk" in row.keys() else None,
        "source_type": row["source_type"] if "source_type" in row.keys() else "user_input",
        "user_id": row["user_id"] if "user_id" in row.keys() else None,
        "is_demo": row["is_demo"] if "is_demo" in row.keys() else 0,
        "protected": row["protected"] if "protected" in row.keys() else 0,
        "matched_patterns": matched_patterns,
    }


def get_logs(
    limit: int = 100,
    offset: int = 0,
    user_id: Optional[int] = None,
    time_range: Optional[str] = None,
    verdict: Optional[str] = None,
    category: Optional[str] = None,
    source_type: Optional[str] = None,
    search: Optional[str] = None,
    enforce_user_scope: bool = True,
    paged: bool = False
) -> Any:
    """
    Retrieves request logs with optional filtering, pagination, and user scoping.
    If enforce_user_scope is True and user_id is provided, includes user's rows PLUS is_demo=1 rows.
    """
    conn = get_connection()
    cursor = conn.cursor()

    conditions = []
    params = []

    if enforce_user_scope:
        if user_id is not None:
            conditions.append("(user_id = ? OR is_demo = 1)")
            params.append(user_id)
        else:
            conditions.append("is_demo = 0")

    if time_range:
        now = datetime.utcnow()
        if time_range == "24h":
            since = now - timedelta(hours=24)
            conditions.append("timestamp >= ?")
            params.append(since.strftime("%Y-%m-%d %H:%M:%S"))
        elif time_range == "7d":
            since = now - timedelta(days=7)
            conditions.append("timestamp >= ?")
            params.append(since.strftime("%Y-%m-%d %H:%M:%S"))
        elif time_range == "30d":
            since = now - timedelta(days=30)
            conditions.append("timestamp >= ?")
            params.append(since.strftime("%Y-%m-%d %H:%M:%S"))

    if verdict:
        conditions.append("(tier = ? OR defense_action = ?)")
        params.append(verdict.lower())
        params.append(verdict.lower())

    if category:
        conditions.append("attack_type = ?")
        params.append(category)

    if source_type:
        conditions.append("source_type = ?")
        params.append(source_type)

    if search:
        conditions.append("input_text LIKE ?")
        params.append(f"%{search.strip()}%")

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    # Total count
    count_query = f"SELECT COUNT(*) FROM logs {where_clause}"
    cursor.execute(count_query, params)
    total = cursor.fetchone()[0]

    # Query items
    query = f"""
        SELECT * FROM logs
        {where_clause}
        ORDER BY id DESC
        LIMIT ? OFFSET ?
    """
    params_paged = list(params) + [limit, offset]
    cursor.execute(query, params_paged)
    rows = cursor.fetchall()
    conn.close()

    items = [parse_log_row(r) for r in rows]
    if paged:
        return {
            "items": items,
            "total": total,
            "limit": limit,
            "offset": offset
        }
    return items


def get_log_by_id(log_id: int, user_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
    """Retrieves full detail of a specific log entry if authorized."""
    conn = get_connection()
    cursor = conn.cursor()

    if user_id is not None:
        cursor.execute("SELECT * FROM logs WHERE id = ? AND (user_id = ? OR is_demo = 1)", (log_id, user_id))
    else:
        cursor.execute("SELECT * FROM logs WHERE id = ?", (log_id,))

    row = cursor.fetchone()
    conn.close()

    if not row:
        return None
    return parse_log_row(row)


def export_logs_as_csv(
    user_id: Optional[int] = None,
    time_range: Optional[str] = None,
    verdict: Optional[str] = None,
    category: Optional[str] = None,
    source_type: Optional[str] = None,
    search: Optional[str] = None
) -> str:
    """Exports filtered logs to CSV string format."""
    items = get_logs(
        limit=5000,
        offset=0,
        user_id=user_id,
        time_range=time_range,
        verdict=verdict,
        category=category,
        source_type=source_type,
        search=search,
        enforce_user_scope=True if user_id is not None else False,
        paged=False
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "id", "timestamp", "source_type", "tier", "final_score",
        "defense_action", "attack_type", "latency_ms", "output_validation_passed",
        "is_demo", "protected", "input_text", "triggered_chunk"
    ])

    for item in items:
        writer.writerow([
            item["id"],
            item["timestamp"],
            item["source_type"],
            item["tier"] or item["action"],
            item["final_score"],
            item["defense_action"],
            item["attack_type"],
            item["latency_ms"],
            item["output_validation_passed"],
            item["is_demo"],
            item["protected"],
            item["input_text"].replace("\n", " ") if item["input_text"] else "",
            item["triggered_chunk"].replace("\n", " ") if item["triggered_chunk"] else ""
        ])

    return output.getvalue()
