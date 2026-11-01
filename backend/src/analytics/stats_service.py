import json
from collections import Counter
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from src.logging.db import get_connection
from src.logging.logger import parse_log_row


def get_stats_data(user_id: Optional[int] = None, time_range: str = "30d") -> Dict[str, Any]:
    """
    Computes comprehensive analytics scoped to current user scans plus is_demo rows.
    Supports range: '24h', '7d', '30d'.
    """
    conn = get_connection()
    cursor = conn.cursor()

    now = datetime.utcnow()
    if time_range == "24h":
        since = now - timedelta(hours=24)
    elif time_range == "7d":
        since = now - timedelta(days=7)
    else:  # default 30d
        time_range = "30d"
        since = now - timedelta(days=30)

    since_str = since.strftime("%Y-%m-%d %H:%M:%S")

    # Scope condition
    if user_id is not None:
        where_clause = "WHERE timestamp >= ? AND (user_id = ? OR is_demo = 1)"
        params = [since_str, user_id]
    else:
        where_clause = "WHERE timestamp >= ?"
        params = [since_str]

    cursor.execute(f"SELECT * FROM logs {where_clause} ORDER BY id DESC", params)
    rows = cursor.fetchall()
    conn.close()

    total_scans = len(rows)
    tier_counts = {"allow": 0, "isolate": 0, "block": 0}
    latencies = []
    category_counts = Counter()
    source_counts = Counter()
    pattern_counts = Counter()
    blocked_count = 0
    non_allow_scans = []

    # 7 weekdays (0=Mon, 1=Tue, ..., 6=Sun) x 24 hours (0..23)
    weekday_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    heatmap_matrix = [[0 for _ in range(24)] for _ in range(7)]

    # Time-bucket setup
    # If 24h: hourly buckets
    # If 7d or 30d: daily buckets
    bucket_counts: Dict[str, Dict[str, int]] = {}

    if time_range == "24h":
        for h in range(24, -1, -1):
            b_dt = (now - timedelta(hours=h)).strftime("%Y-%m-%d %H:00")
            bucket_counts[b_dt] = {"allow": 0, "isolate": 0, "block": 0, "total": 0}
    elif time_range == "7d":
        for d in range(7, -1, -1):
            b_dt = (now - timedelta(days=d)).strftime("%Y-%m-%d")
            bucket_counts[b_dt] = {"allow": 0, "isolate": 0, "block": 0, "total": 0}
    else:
        for d in range(30, -1, -1):
            b_dt = (now - timedelta(days=d)).strftime("%Y-%m-%d")
            bucket_counts[b_dt] = {"allow": 0, "isolate": 0, "block": 0, "total": 0}

    for r in rows:
        parsed = parse_log_row(r)
        tier = parsed["tier"] or ("block" if parsed["defense_action"] == "blocked" else ("isolate" if parsed["defense_action"] == "isolated" else "allow"))
        if tier not in tier_counts:
            tier_counts[tier] = 0
        tier_counts[tier] += 1

        if tier == "block" or parsed["defense_action"] == "blocked":
            blocked_count += 1

        latencies.append(parsed["latency_ms"] or 0.0)

        # Category
        cat = parsed["attack_type"] or "none"
        category_counts[cat] += 1

        # Source type
        st = parsed["source_type"] or "user_input"
        source_counts[st] += 1

        # Patterns
        patterns = parsed["matched_patterns"]
        if patterns and isinstance(patterns, list):
            for pat in patterns:
                p_name = pat.get("pattern") or pat.get("matched_text") or pat.get("category")
                if p_name:
                    pattern_counts[str(p_name)] += 1

        # Timestamp analysis
        try:
            ts_dt = datetime.strptime(parsed["timestamp"], "%Y-%m-%d %H:%M:%S")
        except Exception:
            try:
                ts_dt = datetime.fromisoformat(parsed["timestamp"])
            except Exception:
                ts_dt = now

        # Heatmap (weekday x hour)
        w_day = ts_dt.weekday()  # 0=Monday, 6=Sunday
        hr = ts_dt.hour
        heatmap_matrix[w_day][hr] += 1

        # Bucket mapping
        if time_range == "24h":
            bucket_key = ts_dt.strftime("%Y-%m-%d %H:00")
        else:
            bucket_key = ts_dt.strftime("%Y-%m-%d")

        if bucket_key in bucket_counts:
            bucket_counts[bucket_key]["total"] += 1
            if tier in bucket_counts[bucket_key]:
                bucket_counts[bucket_key][tier] += 1

        # Non-allow scan records
        if tier != "allow" and len(non_allow_scans) < 10:
            non_allow_scans.append(parsed)

    avg_latency = round(sum(latencies) / len(latencies), 2) if latencies else 0.0
    block_rate = round(blocked_count / total_scans, 4) if total_scans > 0 else 0.0

    # Format buckets as list
    time_bucketed = [
        {"bucket": k, **v}
        for k, v in bucket_counts.items()
    ]

    # Top 5 patterns
    top_5_patterns = [
        {"pattern": pat, "count": cnt}
        for pat, cnt in pattern_counts.most_common(5)
    ]

    return {
        "time_range": time_range,
        "total_scans": total_scans,
        "totals_by_tier": tier_counts,
        "block_rate": block_rate,
        "average_latency_ms": avg_latency,
        "llm_calls_prevented": blocked_count,
        "time_bucketed_counts_per_tier": time_bucketed,
        "counts_by_attack_category": dict(category_counts),
        "counts_by_source_type": dict(source_counts),
        "top_5_matched_patterns": top_5_patterns,
        "hour_of_day_by_weekday_matrix": {
            "weekdays": weekday_names,
            "matrix": heatmap_matrix
        },
        "latest_non_allow_scans": non_allow_scans
    }

