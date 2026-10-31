import json
import time
import statistics
from pathlib import Path
import pandas as pd
import numpy as np

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
import sys
sys.path.insert(0, str(backend_dir))

from src.detection.heuristics import detect as heuristic_detect
from src.detection.classifier import classify as classifier_detect
from src.detection.fusion import analyze as fusion_analyze

EVAL_DIR = Path(__file__).resolve().parent
DATA_DIR = EVAL_DIR / "data"
RESULTS_DIR = EVAL_DIR / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

DEV_FILE = DATA_DIR / "dev.jsonl"
TEST_FILE = DATA_DIR / "test.jsonl"

def load_jsonl(file_path):
    data = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                data.append(json.loads(line))
    return data

def compute_metrics(y_true, y_pred, latencies=None):
    tp = sum(1 for yt, yp in zip(y_true, y_pred) if yt == 1 and yp == 1)
    fp = sum(1 for yt, yp in zip(y_true, y_pred) if yt == 0 and yp == 1)
    tn = sum(1 for yt, yp in zip(y_true, y_pred) if yt == 0 and yp == 0)
    fn = sum(1 for yt, yp in zip(y_true, y_pred) if yt == 1 and yp == 0)
    
    total = len(y_true)
    accuracy = (tp + tn) / total if total > 0 else 0.0
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
    
    median_lat = statistics.median(latencies) if latencies and len(latencies) > 0 else 0.0
    p95_lat = np.percentile(latencies, 95) if latencies and len(latencies) > 0 else 0.0
    
    return {
        "total": total,
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
        "accuracy": round(accuracy, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "fpr": round(fpr, 4),
        "median_latency_ms": round(median_lat, 3),
        "p95_latency_ms": round(p95_lat, 3)
    }

def run_evaluation():
    print("=" * 70)
    print("RUNNING CAGE EVALUATION HARNESS")
    print("=" * 70)
    
    dev_data = load_jsonl(DEV_FILE)
    test_data = load_jsonl(TEST_FILE)
    print(f"Loaded {len(dev_data)} Dev samples, {len(test_data)} Test samples (Frozen).")

    # -------------------------------------------------------------
    # 1. Evaluate Dev Set for Threshold Sweep (0.10 to 0.90)
    # -------------------------------------------------------------
    print("\n--- Sweeping Fusion Threshold on Dev Set (0.10 - 0.90) ---")
    dev_fused_scores = []
    dev_y_true = [item["label"] for item in dev_data]
    
    for item in dev_data:
        text = item["text"]
        res = fusion_analyze(text)
        dev_fused_scores.append(res["final_score"])
        
    thresholds = [round(t, 2) for t in np.arange(0.10, 0.95, 0.05)]
    sweep_results = []
    best_thresh = 0.30
    best_f1 = -1.0
    
    for t in thresholds:
        preds = [1 if s >= t else 0 for s in dev_fused_scores]
        m = compute_metrics(dev_y_true, preds)
        sweep_results.append({
            "threshold": t,
            "precision": m["precision"],
            "recall": m["recall"],
            "f1": m["f1"],
            "fpr": m["fpr"],
            "accuracy": m["accuracy"]
        })
        if m["f1"] > best_f1:
            best_f1 = m["f1"]
            best_thresh = t
            
    print(f"Sweep complete. Best Dev F1: {best_f1:.4f} at Threshold: {best_thresh:.2f}")

    # -------------------------------------------------------------
    # 2. Evaluate 4 Configs on Test Set (Frozen)
    # -------------------------------------------------------------
    print("\n--- Running Test Set Evaluation across 4 Configurations ---")
    
    test_y_true = [item["label"] for item in test_data]
    
    # Store predictions, raw scores, and latencies
    heur_preds = []
    heur_scores = []
    heur_lats = []
    
    class_preds = []
    class_scores = []
    class_lats = []
    
    fused_preds_default = []
    fused_preds_tuned = []
    fused_scores = []
    fused_lats = []
    
    baseline_preds = []
    baseline_lats = []
    
    full_test_eval_records = []
    
    for item in test_data:
        text = item["text"]
        
        # 1. Heuristics Only
        t0 = time.perf_counter()
        h_res = heuristic_detect(text)
        t1 = time.perf_counter()
        h_lat = (t1 - t0) * 1000
        h_score = float(h_res.score)
        h_pred = 1 if h_score >= 0.30 else 0
        heur_preds.append(h_pred)
        heur_scores.append(h_score)
        heur_lats.append(h_lat)
        
        # 2. Classifier Only (standard 0.50 threshold)
        t0 = time.perf_counter()
        c_score = float(classifier_detect(text))
        t1 = time.perf_counter()
        c_lat = (t1 - t0) * 1000
        c_pred = 1 if c_score >= 0.50 else 0
        class_preds.append(c_pred)
        class_scores.append(c_score)
        class_lats.append(c_lat)
        
        # 3. Fused (Current CAGE Pipeline with threshold 0.30 and tuned threshold)
        t0 = time.perf_counter()
        f_res = fusion_analyze(text)
        t1 = time.perf_counter()
        f_lat = (t1 - t0) * 1000
        f_score = float(f_res["final_score"])
        f_pred_default = 1 if f_score >= 0.30 else 0
        f_pred_tuned = 1 if f_score >= best_thresh else 0
        fused_preds_default.append(f_pred_default)
        fused_preds_tuned.append(f_pred_tuned)
        fused_scores.append(f_score)
        fused_lats.append(f_lat)
        
        # 4. Always-Benign Baseline
        t0 = time.perf_counter()
        b_pred = 0
        t1 = time.perf_counter()
        baseline_preds.append(b_pred)
        baseline_lats.append((t1 - t0) * 1000)
        
        full_test_eval_records.append({
            "id": item["id"],
            "text": item["text"],
            "label": item["label"],
            "source_type": item["source_type"],
            "category": item["category"],
            "obfuscation": item["obfuscation"],
            "origin": item["origin"],
            "heuristic_score": h_score,
            "classifier_score": c_score,
            "final_score": f_score,
            "pred_heuristics": h_pred,
            "pred_classifier": c_pred,
            "pred_fused_default": f_pred_default,
            "pred_fused_tuned": f_pred_tuned,
            "pred_baseline": b_pred
        })

    # Summary metrics for 4 configs
    metrics_heur = compute_metrics(test_y_true, heur_preds, heur_lats)
    metrics_class = compute_metrics(test_y_true, class_preds, class_lats)
    metrics_fused_default = compute_metrics(test_y_true, fused_preds_default, fused_lats)
    metrics_fused_tuned = compute_metrics(test_y_true, fused_preds_tuned, fused_lats)
    metrics_baseline = compute_metrics(test_y_true, baseline_preds, baseline_lats)
    
    configs_summary = {
        "heuristics_only (thresh 0.30)": metrics_heur,
        "classifier_only (thresh 0.50)": metrics_class,
        "fused_default (thresh 0.30)": metrics_fused_default,
        "fused_tuned_dev_optimal": {
            "tuned_threshold": best_thresh,
            **metrics_fused_tuned
        },
        "always_benign_baseline": metrics_baseline
    }

    # -------------------------------------------------------------
    # 3. Granular Breakdowns on Fused Pipeline (Current CAGE: 0.30)
    # -------------------------------------------------------------
    df_eval = pd.DataFrame(full_test_eval_records)
    
    # Per-Category Breakdown
    category_breakdown = {}
    for cat, group in df_eval.groupby("category"):
        m = compute_metrics(group["label"].tolist(), group["pred_fused_default"].tolist())
        category_breakdown[cat] = m
        
    # Per-Source-Type Breakdown
    source_breakdown = {}
    for st, group in df_eval.groupby("source_type"):
        m = compute_metrics(group["label"].tolist(), group["pred_fused_default"].tolist())
        source_breakdown[st] = m
        
    # Per-Obfuscation Breakdown
    obf_breakdown = {}
    for obf, group in df_eval.groupby("obfuscation"):
        m = compute_metrics(group["label"].tolist(), group["pred_fused_default"].tolist())
        obf_breakdown[obf] = m

    # -------------------------------------------------------------
    # 4. Failures Analysis (False Positives & False Negatives)
    # -------------------------------------------------------------
    failures = []
    for r in full_test_eval_records:
        y = r["label"]
        pred = r["pred_fused_default"]
        if y != pred:
            err_type = "False Positive" if pred == 1 else "False Negative"
            # Confidence of error
            conf = r["final_score"] if pred == 1 else (1.0 - r["final_score"])
            failures.append({
                "id": r["id"],
                "error_type": err_type,
                "confidence_in_error": round(conf, 4),
                "final_score": round(r["final_score"], 4),
                "heuristic_score": round(r["heuristic_score"], 4),
                "classifier_score": round(r["classifier_score"], 4),
                "source_type": r["source_type"],
                "category": r["category"],
                "obfuscation": r["obfuscation"],
                "origin": r["origin"],
                "text_snippet": r["text"][:120].replace("\n", " ") + ("..." if len(r["text"]) > 120 else "")
            })
            
    df_failures = pd.DataFrame(failures)
    # Sort by confidence in error descending
    if not df_failures.empty:
        df_failures = df_failures.sort_values("confidence_in_error", ascending=False)
        failures_csv_path = RESULTS_DIR / "failures.csv"
        df_failures.to_csv(failures_csv_path, index=False)
        print(f"Saved {len(df_failures)} failures to {failures_csv_path}")

    # -------------------------------------------------------------
    # 5. Save results.json
    # -------------------------------------------------------------
    results_json_data = {
        "dev_sweep": {
            "thresholds_tested": sweep_results,
            "best_threshold": best_thresh,
            "best_dev_f1": best_f1
        },
        "test_configurations": configs_summary,
        "breakdown_category": category_breakdown,
        "breakdown_source_type": source_breakdown,
        "breakdown_obfuscation": obf_breakdown,
        "total_failures_count": len(failures)
    }
    
    results_json_path = RESULTS_DIR / "results.json"
    with open(results_json_path, "w", encoding="utf-8") as f:
        json.dump(results_json_data, f, indent=2)
    print(f"Saved complete evaluation metrics to {results_json_path}")

    # -------------------------------------------------------------
    # 6. Generate RESULTS.md
    # -------------------------------------------------------------
    generate_markdown_report(
        configs_summary=configs_summary,
        dev_sweep=sweep_results,
        best_thresh=best_thresh,
        best_dev_f1=best_f1,
        cat_breakdown=category_breakdown,
        source_breakdown=source_breakdown,
        obf_breakdown=obf_breakdown,
        failures=df_failures.head(15).to_dict(orient="records") if not df_failures.empty else []
    )
    
    print("\nEvaluation complete! Output files generated in backend/eval/results/")

def generate_markdown_report(configs_summary, dev_sweep, best_thresh, best_dev_f1, cat_breakdown, source_breakdown, obf_breakdown, failures):
    lines = []
    lines.append("# CAGE Benchmark Evaluation Report (Part C)\n")
    lines.append(f"**Test Set Size**: 420 samples (Frozen, 50% Injection, 50% Benign) | **Dev Set Size**: 180 samples\n")
    
    # Table 1: Primary Configuration Comparison
    lines.append("## 1. System Configuration Comparison (Test Set)\n")
    lines.append("| Configuration | Accuracy | Precision | Recall | F1 Score | False Positive Rate | Median Latency | 95th% Latency |")
    lines.append("|---|---|---|---|---|---|---|---|")
    
    for name, m in configs_summary.items():
        lines.append(f"| **{name}** | {m['accuracy']:.4f} | {m['precision']:.4f} | {m['recall']:.4f} | **{m['f1']:.4f}** | {m['fpr']:.4f} | {m['median_latency_ms']:.2f} ms | {m['p95_latency_ms']:.2f} ms |")
    lines.append("\n")

    # Table 2: Dev Threshold Sweep
    lines.append("## 2. Dev Set Threshold Optimization Sweep\n")
    lines.append(f"Optimal threshold found on dev set: **`{best_thresh:.2f}`** with **Dev F1: `{best_dev_f1:.4f}`**.\n")
    lines.append("| Threshold | Precision | Recall | F1 Score | FPR | Accuracy |")
    lines.append("|---|---|---|---|---|---|")
    for s in dev_sweep:
        marker = " (Optimal)" if s["threshold"] == best_thresh else (" (Default)" if s["threshold"] == 0.30 else "")
        lines.append(f"| **{s['threshold']:.2f}**{marker} | {s['precision']:.4f} | {s['recall']:.4f} | **{s['f1']:.4f}** | {s['fpr']:.4f} | {s['accuracy']:.4f} |")
    lines.append("\n")

    # Table 3: Breakdown by Category
    lines.append("## 3. Performance Breakdown by Attack Category (Fused Default @ 0.30)\n")
    lines.append("| Category | Samples | TP | FP | TN | FN | Precision | Recall | F1 Score | FPR | Accuracy |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|---|")
    for cat, m in cat_breakdown.items():
        lines.append(f"| `{cat}` | {m['total']} | {m['tp']} | {m['fp']} | {m['tn']} | {m['fn']} | {m['precision']:.4f} | {m['recall']:.4f} | {m['f1']:.4f} | {m['fpr']:.4f} | {m['accuracy']:.4f} |")
    lines.append("\n")

    # Table 4: Breakdown by Source Type
    lines.append("## 4. Performance Breakdown by Source Type (Fused Default @ 0.30)\n")
    lines.append("| Source Type | Samples | TP | FP | TN | FN | Precision | Recall | F1 Score | FPR | Accuracy |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|---|")
    for st, m in source_breakdown.items():
        lines.append(f"| `{st}` | {m['total']} | {m['tp']} | {m['fp']} | {m['tn']} | {m['fn']} | {m['precision']:.4f} | {m['recall']:.4f} | {m['f1']:.4f} | {m['fpr']:.4f} | {m['accuracy']:.4f} |")
    lines.append("\n")

    # Table 5: Breakdown by Obfuscation
    lines.append("## 5. Performance Breakdown by Obfuscation Technique (Fused Default @ 0.30)\n")
    lines.append("| Obfuscation Technique | Samples | TP | FP | TN | FN | Precision | Recall | F1 Score | FPR | Accuracy |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|---|")
    for obf, m in obf_breakdown.items():
        lines.append(f"| `{obf}` | {m['total']} | {m['tp']} | {m['fp']} | {m['tn']} | {m['fn']} | {m['precision']:.4f} | {m['recall']:.4f} | {m['f1']:.4f} | {m['fpr']:.4f} | {m['accuracy']:.4f} |")
    lines.append("\n")

    # Table 6: 15 Worst Failures
    lines.append("## 6. Top 15 Worst Failures (Ranked by Error Confidence)\n")
    lines.append("| ID | Error Type | Conf. | Final Score | Heur. Score | Class. Score | Source Type | Category | Obfuscation | Input Snippet |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|")
    for r in failures:
        lines.append(f"| `{r['id']}` | **{r['error_type']}** | {r['confidence_in_error']:.4f} | {r['final_score']:.4f} | {r['heuristic_score']:.4f} | {r['classifier_score']:.4f} | `{r['source_type']}` | `{r['category']}` | `{r['obfuscation']}` | `{r['text_snippet']}` |")
    lines.append("\n")

    md_path = RESULTS_DIR / "RESULTS.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Saved human-readable Markdown report to {md_path}")

if __name__ == "__main__":
    run_evaluation()
