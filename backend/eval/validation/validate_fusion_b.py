import json
import statistics
import time
from pathlib import Path
from typing import Dict, Any, List, Tuple
import pandas as pd
import numpy as np

# Path setups
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
import sys
sys.path.insert(0, str(BACKEND_DIR))

from src.detection.v2.fusion_v2 import analyze_v2_fusion_b

DEV_PATH = BACKEND_DIR / "eval" / "data" / "dev.jsonl"
TEST_PATH = BACKEND_DIR / "eval" / "data" / "test.jsonl"

FUSION_B_THRESHOLD = 0.85  # Chosen on Dev only during v2 benchmark

def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))
    return records

def calc_metrics(y_true: List[int], y_pred: List[int], latencies: List[float] = None) -> Dict[str, Any]:
    tp = sum(1 for yt, yp in zip(y_true, y_pred) if yt == 1 and yp == 1)
    fp = sum(1 for yt, yp in zip(y_true, y_pred) if yt == 0 and yp == 1)
    tn = sum(1 for yt, yp in zip(y_true, y_pred) if yt == 0 and yp == 0)
    fn = sum(1 for yt, yp in zip(y_true, y_pred) if yt == 1 and yp == 0)
    
    total = len(y_true)
    acc = (tp + tn) / total if total > 0 else 0.0
    prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (2 * prec * rec) / (prec + rec) if (prec + rec) > 0 else 0.0
    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
    
    med_lat = statistics.median(latencies) if latencies and len(latencies) > 0 else 0.0
    
    return {
        "total": total,
        "tp": tp, "fp": fp, "tn": tn, "fn": fn,
        "accuracy": round(acc, 4),
        "precision": round(prec, 4),
        "recall": round(rec, 4),
        "f1": round(f1, 4),
        "fpr": round(fpr, 4),
        "median_latency_ms": round(med_lat, 3)
    }

def evaluate_fusion_b_dataset(data: List[Dict[str, Any]]) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    rows = []
    latencies = []
    
    for item in data:
        t0 = time.perf_counter()
        res = analyze_v2_fusion_b(
            item["text"],
            source_type=item.get("source_type", "user_input"),
            threshold=FUSION_B_THRESHOLD
        )
        t1 = time.perf_counter()
        lat_ms = (t1 - t0) * 1000
        latencies.append(lat_ms)
        
        pred = 1 if res["flagged"] else 0
        score = float(res["final_score"])
        
        row = dict(item)
        if "language" not in row:
            row["language"] = "en"
        row["pred"] = pred
        row["score"] = score
        row["latency_ms"] = lat_ms
        rows.append(row)
        
    df = pd.DataFrame(rows)
    overall = calc_metrics(df["label"].tolist(), df["pred"].tolist(), latencies)
    return df, overall

def compute_group_breakdowns(df: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
    breakdowns = {}
    dimensions = ["source_type", "origin", "category", "language", "obfuscation"]
    
    for dim in dimensions:
        breakdowns[dim] = {}
        for val, grp in df.groupby(dim):
            breakdowns[dim][str(val)] = calc_metrics(grp["label"].tolist(), grp["pred"].tolist(), grp["latency_ms"].tolist())
            
    return breakdowns

def extract_worst_failures(df: pd.DataFrame, top_k: int = 15) -> List[Dict[str, Any]]:
    failures = []
    for _, row in df.iterrows():
        y = row["label"]
        p = row["pred"]
        if y != p:
            err_type = "False Positive" if p == 1 else "False Negative"
            # For false positive, confidence in error is score; for false negative, 1 - score
            conf = row["score"] if p == 1 else (1.0 - row["score"])
            failures.append({
                "id": row["id"],
                "error_type": err_type,
                "confidence_in_error": round(conf, 4),
                "score": round(row["score"], 4),
                "label": y,
                "prediction": p,
                "source_type": row["source_type"],
                "category": row["category"],
                "obfuscation": row["obfuscation"],
                "origin": row["origin"],
                "language": row.get("language", "en"),
                "text_snippet": row["text"][:120].replace("\n", " ") + ("..." if len(row["text"]) > 120 else "")
            })
            
    df_fail = pd.DataFrame(failures)
    if not df_fail.empty:
        df_fail = df_fail.sort_values("confidence_in_error", ascending=False)
        return df_fail.head(top_k).to_dict(orient="records"), df_fail
    return [], pd.DataFrame()

def run_task1():
    print("=" * 80)
    print("TASK 1: FUSION B FULL BREAKDOWN ON DEV AND TEST")
    print("=" * 80)
    
    dev_data = load_jsonl(DEV_PATH)
    test_data = load_jsonl(TEST_PATH)
    print(f"Loaded {len(dev_data)} Dev samples, {len(test_data)} Test samples.", flush=True)
    
    dev_df, dev_overall = evaluate_fusion_b_dataset(dev_data)
    test_df, test_overall = evaluate_fusion_b_dataset(test_data)
    
    print("\n--- Overall Performance (Threshold = 0.85) ---")
    print(f"Dev : Acc={dev_overall['accuracy']:.4f}, Prec={dev_overall['precision']:.4f}, Rec={dev_overall['recall']:.4f}, F1={dev_overall['f1']:.4f}, FPR={dev_overall['fpr']:.4f}")
    print(f"Test: Acc={test_overall['accuracy']:.4f}, Prec={test_overall['precision']:.4f}, Rec={test_overall['recall']:.4f}, F1={test_overall['f1']:.4f}, FPR={test_overall['fpr']:.4f}")
    
    dev_breakdowns = compute_group_breakdowns(dev_df)
    test_breakdowns = compute_group_breakdowns(test_df)
    
    # Public-only comparison table
    dev_pub = dev_df[dev_df["origin"] == "public"]
    test_pub = test_df[test_df["origin"] == "public"]
    
    pub_metrics = {
        "dev": calc_metrics(dev_pub["label"].tolist(), dev_pub["pred"].tolist(), dev_pub["latency_ms"].tolist()),
        "test": calc_metrics(test_pub["label"].tolist(), test_pub["pred"].tolist(), test_pub["latency_ms"].tolist())
    }
    
    top_failures, all_test_failures_df = extract_worst_failures(test_df, top_k=15)
    
    return {
        "dev_overall": dev_overall,
        "test_overall": test_overall,
        "dev_breakdowns": dev_breakdowns,
        "test_breakdowns": test_breakdowns,
        "public_only": pub_metrics,
        "top_15_failures": top_failures,
        "all_test_failures_df": all_test_failures_df,
        "dev_df": dev_df,
        "test_df": test_df
    }

if __name__ == "__main__":
    res = run_task1()
