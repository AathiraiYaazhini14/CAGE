import json
import math
import re
from pathlib import Path
from typing import Dict, Any, List, Tuple
import numpy as np
import pandas as pd
import joblib
from sklearn.linear_model import LogisticRegression

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
import sys
sys.path.insert(0, str(BACKEND_DIR))

from src.detection.v2.fusion_v2 import (
    analyze_v2_fusion_a,
    analyze_v2_fusion_b,
    extract_detection_features
)
from src.detection.v2.classifier_v2 import classify_v2

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

def get_word_count(text: str) -> int:
    return len(text.strip().split())

def assign_length_bin(wc: int) -> str:
    if wc < 30:
        return "<30"
    elif wc < 80:
        return "30-80"
    elif wc < 200:
        return "80-200"
    else:
        return "200+"

def run_length_bin_analysis(df: pd.DataFrame, split_name: str) -> Dict[str, Any]:
    df = df.copy()
    df["word_count"] = df["text"].apply(get_word_count)
    df["len_bin"] = df["word_count"].apply(assign_length_bin)
    
    bin_order = ["<30", "30-80", "80-200", "200+"]
    results = {}
    
    for b in bin_order:
        grp = df[df["len_bin"] == b]
        injections = grp[grp["label"] == 1]
        benign = grp[grp["label"] == 0]
        
        inj_total = len(injections)
        inj_caught = sum(injections["pred"] == 1)
        recall = (inj_caught / inj_total) if inj_total > 0 else 0.0
        
        ben_total = len(benign)
        ben_fp = sum(benign["pred"] == 1)
        fpr = (ben_fp / ben_total) if ben_total > 0 else 0.0
        
        results[b] = {
            "total_samples": len(grp),
            "injections_total": inj_total,
            "injections_detected": inj_caught,
            "recall": round(recall, 4),
            "benign_total": ben_total,
            "benign_fp": ben_fp,
            "fpr": round(fpr, 4)
        }
    return results

def run_stress_test(test_df: pd.DataFrame) -> Dict[str, Any]:
    print("\n--- Running Stress Test: Short Prompts Embedded Inside Long Documents ---", flush=True)
    test_df = test_df.copy()
    test_df["word_count"] = test_df["text"].apply(get_word_count)
    
    # 1. Select 50 short injections (< 50 words)
    short_injections = test_df[(test_df["label"] == 1) & (test_df["word_count"] < 50)].to_dict(orient="records")
    if len(short_injections) > 50:
        short_injections = short_injections[:50]
        
    # 2. Select 50 long benign documents (> 150 words)
    long_benign_docs = test_df[(test_df["label"] == 0) & (test_df["word_count"] > 150)].to_dict(orient="records")
    if len(long_benign_docs) < 50:
        # Fallback to any benign docs > 100 words
        long_benign_docs = test_df[(test_df["label"] == 0) & (test_df["word_count"] > 100)].to_dict(orient="records")
        
    # 3. Select 50 short benign prompts (< 30 words)
    short_benign_prompts = test_df[(test_df["label"] == 0) & (test_df["word_count"] < 30)].to_dict(orient="records")
    if len(short_benign_prompts) > 50:
        short_benign_prompts = short_benign_prompts[:50]
        
    # Create 50 embedded injection documents
    embedded_injection_cases = []
    for idx in range(min(50, len(short_injections))):
        inj = short_injections[idx]
        doc = long_benign_docs[idx % len(long_benign_docs)]
        
        doc_words = doc["text"].split()
        mid = len(doc_words) // 2
        part1 = " ".join(doc_words[:mid])
        part2 = " ".join(doc_words[mid:])
        
        combined_text = f"{part1}\n\n[DOCUMENT ATTACHMENT / NOTE]: {inj['text']}\n\n{part2}"
        embedded_injection_cases.append({
            "id": f"stress_inj_{idx:02d}",
            "text": combined_text,
            "original_injection_id": inj["id"],
            "original_injection_text": inj["text"],
            "label": 1,
            "source_type": "retrieved_document",
            "word_count": len(combined_text.split())
        })
        
    # Create 50 embedded benign prompt documents
    embedded_benign_cases = []
    for idx in range(min(50, len(short_benign_prompts))):
        ben = short_benign_prompts[idx]
        doc = long_benign_docs[(idx + 25) % len(long_benign_docs)]
        
        doc_words = doc["text"].split()
        mid = len(doc_words) // 2
        part1 = " ".join(doc_words[:mid])
        part2 = " ".join(doc_words[mid:])
        
        combined_text = f"{part1}\n\n[USER QUERY / CONTEXT]: {ben['text']}\n\n{part2}"
        embedded_benign_cases.append({
            "id": f"stress_ben_{idx:02d}",
            "text": combined_text,
            "original_prompt_id": ben["id"],
            "original_prompt_text": ben["text"],
            "label": 0,
            "source_type": "retrieved_document",
            "word_count": len(combined_text.split())
        })
        
    all_stress_cases = embedded_injection_cases + embedded_benign_cases
    stress_y = [c["label"] for c in all_stress_cases]
    
    # Evaluate Fusion A (threshold = 0.65)
    fusion_a_preds = []
    fusion_a_scores = []
    for c in all_stress_cases:
        res = analyze_v2_fusion_a(c["text"], source_type="retrieved_document", threshold=0.65)
        fusion_a_preds.append(1 if res["flagged"] else 0)
        fusion_a_scores.append(res["final_score"])
        c["fusion_a_score"] = res["final_score"]
        c["fusion_a_flagged"] = res["flagged"]
        
    # Evaluate Fusion B (threshold = 0.85)
    fusion_b_preds = []
    fusion_b_scores = []
    for c in all_stress_cases:
        res = analyze_v2_fusion_b(c["text"], source_type="retrieved_document", threshold=0.85)
        fusion_b_preds.append(1 if res["flagged"] else 0)
        fusion_b_scores.append(res["final_score"])
        c["fusion_b_score"] = res["final_score"]
        c["fusion_b_flagged"] = res["flagged"]
        
    metrics_a = calc_metrics(stress_y, fusion_a_preds)
    metrics_b = calc_metrics(stress_y, fusion_b_preds)
    
    # Injection recall specifically
    inj_y = stress_y[:len(embedded_injection_cases)]
    inj_preds_a = fusion_a_preds[:len(embedded_injection_cases)]
    inj_preds_b = fusion_b_preds[:len(embedded_injection_cases)]
    inj_rec_a = sum(inj_preds_a) / len(inj_y) if len(inj_y) > 0 else 0.0
    inj_rec_b = sum(inj_preds_b) / len(inj_y) if len(inj_y) > 0 else 0.0
    
    # Benign FPR specifically
    ben_y = stress_y[len(embedded_injection_cases):]
    ben_preds_a = fusion_a_preds[len(embedded_injection_cases):]
    ben_preds_b = fusion_b_preds[len(embedded_injection_cases):]
    ben_fpr_a = sum(ben_preds_a) / len(ben_y) if len(ben_y) > 0 else 0.0
    ben_fpr_b = sum(ben_preds_b) / len(ben_y) if len(ben_y) > 0 else 0.0
    
    print(f"Stress Test Results (N = {len(all_stress_cases)}, 50 Injections / 50 Benign embedded):")
    print(f"  Fusion A: Overall F1 = {metrics_a['f1']:.4f}, Injection Recall = {inj_rec_a:.4f} ({sum(inj_preds_a)}/50), Benign FPR = {ben_fpr_a:.4f} ({sum(ben_preds_a)}/50)")
    print(f"  Fusion B: Overall F1 = {metrics_b['f1']:.4f}, Injection Recall = {inj_rec_b:.4f} ({sum(inj_preds_b)}/50), Benign FPR = {ben_fpr_b:.4f} ({sum(ben_preds_b)}/50)")
    
    return {
        "fusion_a": metrics_a,
        "fusion_b": metrics_b,
        "injection_recall_a": round(inj_rec_a, 4),
        "injection_recall_b": round(inj_rec_b, 4),
        "benign_fpr_a": round(ben_fpr_a, 4),
        "benign_fpr_b": round(ben_fpr_b, 4),
        "stress_samples": all_stress_cases
    }

def run_stacker_ablation(dev_df: pd.DataFrame, test_df: pd.DataFrame) -> Dict[str, Any]:
    print("\n--- Training Ablated Stacker Variant (No log_len, No source_type) ---", flush=True)
    cache_path = BACKEND_DIR / "eval" / "validation" / "train_v2_feats_cache.joblib"
    
    if cache_path.exists():
        print(f"Loading cached training features from {cache_path}...", flush=True)
        cached = joblib.load(cache_path)
        X_tr = cached["X_tr"]
        y_tr = cached["y_tr"]
    else:
        train_records = load_jsonl(TRAIN_V2_PATH)
        print(f"Extracting 2-feature vectors [heur, classifier] for {len(train_records)} train samples...", flush=True)
        X_train_ablated = []
        y_train = []
        
        for idx, r in enumerate(train_records):
            if idx % 500 == 0:
                print(f"  Processed {idx}/{len(train_records)}...", flush=True)
            feat = extract_detection_features(r["text"], source_type="user_input")
            X_train_ablated.append([feat["heuristic_score"], feat["classifier_score"]])
            y_train.append(r["label"])
            
        X_tr = np.array(X_train_ablated)
        y_tr = np.array(y_train)
        joblib.dump({"X_tr": X_tr, "y_tr": y_tr}, cache_path)
        print(f"Saved feature cache to {cache_path}", flush=True)
    
    ablated_clf = LogisticRegression(class_weight="balanced", max_iter=500, random_state=42)
    ablated_clf.fit(X_tr, y_tr)
    
    # Feature coefficients
    coefs = {
        "heuristic_score_coef": round(float(ablated_clf.coef_[0][0]), 4),
        "classifier_score_coef": round(float(ablated_clf.coef_[0][1]), 4),
        "intercept": round(float(ablated_clf.intercept_[0]), 4)
    }
    print(f"Ablated Stacker Coefficients: Heur={coefs['heuristic_score_coef']}, Classifier={coefs['classifier_score_coef']}, Intercept={coefs['intercept']}")
    
    # Dev sweep to select optimal threshold
    dev_records = dev_df.to_dict(orient="records")
    dev_feats = [extract_detection_features(r["text"], source_type=r["source_type"]) for r in dev_records]
    X_dev = np.array([[f["heuristic_score"], f["classifier_score"]] for f in dev_feats])
    dev_probs = ablated_clf.predict_proba(X_dev)[:, 1]
    dev_y = [r["label"] for r in dev_records]
    
    best_t = 0.50
    best_f1 = -1.0
    for t in np.arange(0.10, 0.95, 0.05):
        preds = [1 if p >= t else 0 for p in dev_probs]
        m = calc_metrics(dev_y, preds)
        if m["f1"] > best_f1:
            best_f1 = m["f1"]
            best_t = round(float(t), 2)
            
    print(f"Optimal Threshold for Ablated Stacker on Dev: {best_t:.2f} (Dev F1: {best_f1:.4f})")
    dev_ablated_preds = [1 if p >= best_t else 0 for p in dev_probs]
    dev_ablated_metrics = calc_metrics(dev_y, dev_ablated_preds)
    
    # Evaluate on Frozen Test
    test_records = test_df.to_dict(orient="records")
    test_feats = [extract_detection_features(r["text"], source_type=r["source_type"]) for r in test_records]
    X_test = np.array([[f["heuristic_score"], f["classifier_score"]] for f in test_feats])
    test_probs = ablated_clf.predict_proba(X_test)[:, 1]
    test_y = [r["label"] for r in test_records]
    
    test_ablated_preds = [1 if p >= best_t else 0 for p in test_probs]
    test_ablated_metrics = calc_metrics(test_y, test_ablated_preds)
    
    print("\nAblated Stacker (Score-Only) vs Full Stacked Fusion B (with log_len + source_type):")
    print(f"  Dev  - Ablated: F1={dev_ablated_metrics['f1']:.4f}, Rec={dev_ablated_metrics['recall']:.4f}, FPR={dev_ablated_metrics['fpr']:.4f}")
    print(f"  Test - Ablated: F1={test_ablated_metrics['f1']:.4f}, Rec={test_ablated_metrics['recall']:.4f}, FPR={test_ablated_metrics['fpr']:.4f}")
    
    return {
        "coefficients": coefs,
        "dev_optimal_threshold": best_t,
        "dev_metrics": dev_ablated_metrics,
        "test_metrics": test_ablated_metrics
    }

def run_task3(dev_df: pd.DataFrame, test_df: pd.DataFrame):
    print("=" * 80)
    print("TASK 3: SHORTCUT TEST FOR FUSION B")
    print("=" * 80)
    
    dev_length_bins = run_length_bin_analysis(dev_df, "dev")
    test_length_bins = run_length_bin_analysis(test_df, "test")
    stress_test_results = run_stress_test(test_df)
    ablation_results = run_stacker_ablation(dev_df, test_df)
    
    return {
        "dev_length_bins": dev_length_bins,
        "test_length_bins": test_length_bins,
        "stress_test": stress_test_results,
        "stacker_ablation": ablation_results
    }

if __name__ == "__main__":
    from validate_fusion_b import run_task1
    res1 = run_task1()
    res3 = run_task3(res1["dev_df"], res1["test_df"])
