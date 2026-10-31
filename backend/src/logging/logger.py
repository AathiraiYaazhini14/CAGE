from typing import List, Dict, Any, Optional
from datetime import datetime
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
    source_type: Optional[str] = "user_input"
) -> int:
    """Inserts a request log entry into the database and returns the new row ID."""
    conn = get_connection()
    cursor = conn.cursor()

    val_passed = 1 if output_validation_passed is True else (0 if output_validation_passed is False else None)
    timestamp_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
        INSERT INTO logs (
            timestamp, input_text, heuristic_score, classifier_score, final_score,
            severity, attack_type, defense_action, output_validation_passed, latency_ms,
            tier, triggered_chunk, source_type
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
        source_type or "user_input"
    ))

    conn.commit()
    row_id = cursor.lastrowid
    conn.close()
    return row_id


def get_logs(limit: int = 100) -> List[Dict[str, Any]]:
    """Retrieves recent request logs sorted by timestamp descending."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            id, timestamp, input_text, heuristic_score, classifier_score, final_score,
            severity, attack_type, defense_action, output_validation_passed, latency_ms,
            tier, triggered_chunk, source_type
        FROM logs
        ORDER BY id DESC
        LIMIT ?
    """, (limit,))
    
    rows = cursor.fetchall()
    conn.close()

    result = []
    for row in rows:
        val_passed = bool(row["output_validation_passed"]) if row["output_validation_passed"] is not None else None
        result.append({
            "id": row["id"],
            "timestamp": row["timestamp"],
            "input_text": row["input_text"],
            "heuristic_score": row["heuristic_score"],
            "classifier_score": row["classifier_score"],
            "final_score": row["final_score"],
            "severity": row["severity"],
            "attack_type": row["attack_type"],
            "defense_action": row["defense_action"],
            "output_validation_passed": val_passed,
            "latency_ms": row["latency_ms"],
            "tier": row["tier"] if "tier" in row.keys() else None,
            "triggered_chunk": row["triggered_chunk"] if "triggered_chunk" in row.keys() else None,
            "source_type": row["source_type"] if "source_type" in row.keys() else "user_input",
        })

    return result
