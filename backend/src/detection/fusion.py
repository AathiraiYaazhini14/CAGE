import time
from typing import Dict, Any
from src.detection.heuristics import detect as heuristic_detect
from src.detection.classifier import classify as classifier_detect


def analyze(text: str) -> Dict[str, Any]:
    """
    Combines Heuristic and ML Classifier detection outputs using a 50/50 score fusion.
    Computes final risk score, severity level, categorizes attack types, and profiles stage latencies.
    """
    t0 = time.perf_counter()
    heuristic_res = heuristic_detect(text)
    t1 = time.perf_counter()
    classifier_score = float(classifier_detect(text))
    t2 = time.perf_counter()

    # 50/50 Weighted score fusion
    final_score = round(0.5 * float(heuristic_res.score) + 0.5 * classifier_score, 4)
    flagged = final_score >= 0.3

    # Determine severity
    if final_score < 0.3:
        severity = "none"
    elif 0.3 <= final_score <= 0.6:
        severity = "low"
    else:
        severity = "high"

    # Determine attack type
    attack_type = heuristic_res.attack_type
    if attack_type == "none" and flagged:
        attack_type = "unknown"

    t3 = time.perf_counter()

    heuristics_ms = max(0.01, round((t1 - t0) * 1000, 3))
    classifier_ms = max(0.01, round((t2 - t1) * 1000, 3))
    fusion_ms = max(0.01, round((t3 - t2) * 1000, 3))

    return {
        "final_score": final_score,
        "flagged": flagged,
        "severity": severity,
        "attack_type": attack_type,
        "heuristic_score": float(heuristic_res.score),
        "classifier_score": classifier_score,
        "matched_patterns": heuristic_res.matched_patterns,
        "stage_latencies": {
            "heuristics_ms": heuristics_ms,
            "classifier_ms": classifier_ms,
            "fusion_ms": fusion_ms,
        },
    }

