import json
from pathlib import Path
from typing import Dict, Any, List, Tuple
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
TRAIN_V2_PATH = BACKEND_DIR / "eval" / "data" / "train_v2.jsonl"
DEV_PATH = BACKEND_DIR / "eval" / "data" / "dev.jsonl"
TEST_PATH = BACKEND_DIR / "eval" / "data" / "test.jsonl"

def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))
    return records

def calc_metrics(y_true: List[int], y_pred: List[int]) -> Dict[str, Any]:
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
    
    return {
        "total": total,
        "tp": tp, "fp": fp, "tn": tn, "fn": fn,
        "accuracy": round(acc, 4),
        "precision": round(prec, 4),
        "recall": round(rec, 4),
        "f1": round(f1, 4),
        "fpr": round(fpr, 4)
    }

def run_task4(dev_df: pd.DataFrame, test_df: pd.DataFrame):
    print("=" * 80)
    print("TASK 4: TRAIN / BENCHMARK OVERLAP ANALYSIS")
    print("=" * 80)
    
    train_data = load_jsonl(TRAIN_V2_PATH)
    train_texts = [d["text"] for d in train_data]
    print(f"Loaded {len(train_texts)} train_v2 samples.", flush=True)
    
    print("Vectorizing train_v2 with word n-grams (1-2)...", flush=True)
    vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=1, max_features=35000)
    X_train = vectorizer.fit_transform(train_texts)
    
    dev_texts = dev_df["text"].tolist()
    test_texts = test_df["text"].tolist()
    
    X_dev = vectorizer.transform(dev_texts)
    X_test = vectorizer.transform(test_texts)
    
    # Compute max cosine similarity to any training sample
    print("Computing max cosine similarities for Dev and Test samples...", flush=True)
    # dev
    dev_sims = cosine_similarity(X_dev, X_train)
    dev_max_sims = np.max(dev_sims, axis=1)
    dev_df = dev_df.copy()
    dev_df["nearest_train_sim"] = dev_max_sims
    
    # test
    test_sims = cosine_similarity(X_test, X_train)
    test_max_sims = np.max(test_sims, axis=1)
    test_df = test_df.copy()
    test_df["nearest_train_sim"] = test_max_sims
    
    # Distribution stats for test
    all_sims = np.concatenate([dev_max_sims, test_max_sims])
    
    def summarize_distribution(arr: np.ndarray) -> Dict[str, Any]:
        return {
            "count": len(arr),
            "min": round(float(np.min(arr)), 4),
            "p25": round(float(np.percentile(arr, 25)), 4),
            "median": round(float(np.median(arr)), 4),
            "mean": round(float(np.mean(arr)), 4),
            "p75": round(float(np.percentile(arr, 75)), 4),
            "p90": round(float(np.percentile(arr, 90)), 4),
            "p95": round(float(np.percentile(arr, 95)), 4),
            "max": round(float(np.max(arr)), 4),
            "pct_gt_0_8": round(float(np.mean(arr > 0.8) * 100), 2),
            "pct_gt_0_9": round(float(np.mean(arr > 0.9) * 100), 2),
            "count_gt_0_8": int(np.sum(arr > 0.8)),
            "count_le_0_8": int(np.sum(arr <= 0.8))
        }
        
    dev_dist = summarize_distribution(dev_max_sims)
    test_dist = summarize_distribution(test_max_sims)
    overall_dist = summarize_distribution(all_sims)
    
    print("\nTest Set Similarity to train_v2 Distribution:")
    print(f"  Min={test_dist['min']:.4f}, 25%={test_dist['p25']:.4f}, Median={test_dist['median']:.4f}, Mean={test_dist['mean']:.4f}, 75%={test_dist['p75']:.4f}, Max={test_dist['max']:.4f}")
    print(f"  High-similarity (> 0.80): {test_dist['count_gt_0_8']} samples ({test_dist['pct_gt_0_8']}%)")
    print(f"  Low-similarity  (<= 0.80): {test_dist['count_le_0_8']} samples ({round(100 - test_dist['pct_gt_0_8'], 2)}%)")
    
    # Split metrics on test set
    test_high = test_df[test_df["nearest_train_sim"] > 0.8]
    test_low = test_df[test_df["nearest_train_sim"] <= 0.8]
    
    metrics_test_high = calc_metrics(test_high["label"].tolist(), test_high["pred"].tolist())
    metrics_test_low = calc_metrics(test_low["label"].tolist(), test_low["pred"].tolist())
    
    # Split metrics on dev set
    dev_high = dev_df[dev_df["nearest_train_sim"] > 0.8]
    dev_low = dev_df[dev_df["nearest_train_sim"] <= 0.8]
    metrics_dev_high = calc_metrics(dev_high["label"].tolist(), dev_high["pred"].tolist())
    metrics_dev_low = calc_metrics(dev_low["label"].tolist(), dev_low["pred"].tolist())
    
    print("\nFusion B Metrics Split by Similarity to train_v2 (Test Set):")
    print(f"  High-Similarity (> 0.80) [N={metrics_test_high['total']}]: F1={metrics_test_high['f1']:.4f}, Rec={metrics_test_high['recall']:.4f}, Prec={metrics_test_high['precision']:.4f}, FPR={metrics_test_high['fpr']:.4f}")
    print(f"  Low-Similarity  (<= 0.80) [N={metrics_test_low['total']}]: F1={metrics_test_low['f1']:.4f}, Rec={metrics_test_low['recall']:.4f}, Prec={metrics_test_low['precision']:.4f}, FPR={metrics_test_low['fpr']:.4f}")
    
    return {
        "dev_distribution": dev_dist,
        "test_distribution": test_dist,
        "overall_distribution": overall_dist,
        "test_high_similarity_metrics": metrics_test_high,
        "test_low_similarity_metrics": metrics_test_low,
        "dev_high_similarity_metrics": metrics_dev_high,
        "dev_low_similarity_metrics": metrics_dev_low
    }

if __name__ == "__main__":
    from validate_fusion_b import run_task1
    res1 = run_task1()
    res4 = run_task4(res1["dev_df"], res1["test_df"])
