import io
import json
import math
import os
import re
import sys
import time
from pathlib import Path
from typing import Dict, Any, List, Tuple
import numpy as np
import pandas as pd
import joblib
from sklearn.linear_model import LogisticRegression

# Set up paths
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from src.detection.v2.fusion_v2 import (
    analyze_v2_fusion_b,
    get_stacked_model,
    extract_detection_features
)
from src.detection.v2.chunking import score_with_chunking
from src.detection.v2.classifier_v2 import classify_v2

DEV_PATH = BACKEND_DIR / "eval" / "data" / "dev.jsonl"
TEST_PATH = BACKEND_DIR / "eval" / "data" / "test.jsonl"
HOLDOUT_PATH = BACKEND_DIR / "eval" / "data" / "holdout_external.jsonl"
TRAIN_FEATS_CACHE = BACKEND_DIR / "eval" / "validation" / "train_v2_feats_cache.joblib"
EVAL_FINAL_DIR = BACKEND_DIR / "eval" / "final"
V2_FINAL_DIR = BACKEND_DIR / "src" / "detection" / "v2_final"

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

# -------------------------------------------------------------
# Train/Load Candidate Models
# -------------------------------------------------------------
def get_candidate_models():
    # 1. Full Stacked Model (Candidate A)
    stacked_full = get_stacked_model()
    
    # 2. Ablated Stacker Model (Candidate B)
    if not TRAIN_FEATS_CACHE.exists():
        raise FileNotFoundError(f"Feature cache {TRAIN_FEATS_CACHE} not found!")
    cached_train = joblib.load(TRAIN_FEATS_CACHE)
    X_tr = cached_train["X_tr"]
    y_tr = cached_train["y_tr"]
    
    ablated_clf = LogisticRegression(class_weight="balanced", max_iter=500, random_state=42)
    ablated_clf.fit(X_tr, y_tr)
    
    # Save ablated model to data directory for future reference
    ablated_model_path = BACKEND_DIR / "data" / "stacker_v2_ablated.joblib"
    joblib.dump({"model": ablated_clf, "feature_names": ["heur_score", "class_score"]}, ablated_model_path)
    
    return stacked_full, ablated_clf

# -------------------------------------------------------------
# Feature Extraction and Scoring
# -------------------------------------------------------------
def score_sample_all_candidates(text: str, source_type: str, stacked_full, ablated_clf) -> Dict[str, float]:
    feats = extract_detection_features(text, source_type=source_type)
    heur_score = feats["heuristic_score"]
    class_score = feats["classifier_score"]
    
    # (a) Fusion B: full stacked
    x_full = feats["feature_vector"].reshape(1, -1)
    score_a = float(stacked_full.predict_proba(x_full)[0, 1])
    
    # (b) Ablated stacker: [heur, class]
    x_ablated = np.array([[heur_score, class_score]])
    score_b = float(ablated_clf.predict_proba(x_ablated)[0, 1])
    
    # (c) Max-chunk classifier only
    score_c = float(class_score)
    
    return {
        "score_a": score_a,
        "score_b": score_b,
        "score_c": score_c,
        "heur_score": heur_score,
        "class_score": class_score,
        "triggered_chunk": feats.get("trigger_chunk_text", ""),
        "matched_patterns": feats.get("matched_patterns", [])
    }

# -------------------------------------------------------------
# Constructing Benign Padding for Stress Testing
# -------------------------------------------------------------
def build_padding_corpus(test_data: List[Dict[str, Any]]) -> str:
    benign_docs = [d["text"] for d in test_data if d["label"] == 0 and d["source_type"] == "retrieved_document"]
    combined_words = []
    for doc in benign_docs:
        # Avoid dispatches or technical articles with security false-alarm terms
        if "CYBERSECURITY" not in doc and "DISPATCH" not in doc and "EXPLOIT" not in doc:
            combined_words.extend(doc.split())
    if len(combined_words) < 2000:
        # Fallback to all benign docs
        for doc in benign_docs:
            combined_words.extend(doc.split())
    return combined_words

def get_padding_slice(words: List[str], target_len: int, offset: int = 0) -> str:
    n = len(words)
    start = offset % n
    end = start + target_len
    if end <= n:
        slice_words = words[start:end]
    else:
        slice_words = words[start:] + words[:end - n]
    return " ".join(slice_words)

def build_stress_test_dataset(test_data: List[Dict[str, Any]]):
    padding_words = build_padding_corpus(test_data)
    
    # 50 short injections (< 50 words) from test set
    short_injections = [d for d in test_data if d["label"] == 1 and len(d["text"].split()) < 50][:50]
    # 50 short benign prompts (< 30 words) from test set
    short_benign = [d for d in test_data if d["label"] == 0 and len(d["text"].split()) < 30][:50]
    
    padding_lengths = [50, 200, 500]
    positions = ["start", "middle", "end"]
    
    # Structure:
    # { pad_len: { pos: [cases...] } }
    inj_stress_cases = {pad: {pos: [] for pos in positions} for pad in padding_lengths}
    ben_stress_cases = {pad: {pos: [] for pos in positions} for pad in padding_lengths}
    
    for pad in padding_lengths:
        for pos in positions:
            # 1. Injections
            for idx, item in enumerate(short_injections):
                inj_text = item["text"]
                pad_text = get_padding_slice(padding_words, pad, offset=idx * 73)
                
                if pos == "start":
                    doc = f"{inj_text}\n\n{pad_text}"
                elif pos == "end":
                    doc = f"{pad_text}\n\n{inj_text}"
                else: # middle
                    half = pad // 2
                    p1 = get_padding_slice(padding_words, half, offset=idx * 73)
                    p2 = get_padding_slice(padding_words, pad - half, offset=idx * 73 + half)
                    doc = f"{p1}\n\n{inj_text}\n\n{p2}"
                    
                inj_stress_cases[pad][pos].append({
                    "id": f"stress_inj_p{pad}_{pos}_{idx}",
                    "text": doc,
                    "label": 1,
                    "source_type": "retrieved_document",
                    "orig_id": item["id"]
                })
                
            # 2. Benign
            for idx, item in enumerate(short_benign):
                ben_text = item["text"]
                pad_text = get_padding_slice(padding_words, pad, offset=(idx + 50) * 89)
                
                if pos == "start":
                    doc = f"{ben_text}\n\n{pad_text}"
                elif pos == "end":
                    doc = f"{pad_text}\n\n{ben_text}"
                else: # middle
                    half = pad // 2
                    p1 = get_padding_slice(padding_words, half, offset=(idx + 50) * 89)
                    p2 = get_padding_slice(padding_words, pad - half, offset=(idx + 50) * 89 + half)
                    doc = f"{p1}\n\n{ben_text}\n\n{p2}"
                    
                ben_stress_cases[pad][pos].append({
                    "id": f"stress_ben_p{pad}_{pos}_{idx}",
                    "text": doc,
                    "label": 0,
                    "source_type": "retrieved_document",
                    "orig_id": item["id"]
                })
                
    return inj_stress_cases, ben_stress_cases

# -------------------------------------------------------------
# Main Evaluation and Selection Pipeline
# -------------------------------------------------------------
def run_final_selection():
    print("=" * 80)
    print("STARTING CAGE V2 FINAL MODEL SELECTION & TIERING PIPELINE")
    print("=" * 80)
    
    dev_data = load_jsonl(DEV_PATH)
    test_data = load_jsonl(TEST_PATH)
    holdout_data = load_jsonl(HOLDOUT_PATH)
    print(f"Loaded {len(dev_data)} Dev, {len(test_data)} Test, {len(holdout_data)} External Holdout samples.")
    
    stacked_full, ablated_clf = get_candidate_models()
    
    # 1. Pre-score Dev, Test, Holdout for all candidates
    print("\nScoring Dev, Test, and Holdout datasets across all 3 candidates...", flush=True)
    def pre_score_dataset(data: List[Dict[str, Any]]):
        scores_a, scores_b, scores_c, y_labels = [], [], [], []
        for d in data:
            s = score_sample_all_candidates(d["text"], d.get("source_type", "user_input"), stacked_full, ablated_clf)
            scores_a.append(s["score_a"])
            scores_b.append(s["score_b"])
            scores_c.append(s["score_c"])
            y_labels.append(d["label"])
        return {
            "y": y_labels,
            "a": scores_a,
            "b": scores_b,
            "c": scores_c
        }
        
    dev_scored = pre_score_dataset(dev_data)
    test_scored = pre_score_dataset(test_data)
    holdout_scored = pre_score_dataset(holdout_data)
    
    # 2. Select Operating Threshold for each candidate on Dev ONLY
    print("\nTuning operating threshold on Dev set for each candidate (maximizing F1)...", flush=True)
    candidate_keys = ["a", "b", "c"]
    candidate_names = {
        "a": "Candidate A: Full Fusion B [all features]",
        "b": "Candidate B: Ablated Stacker [heur, class]",
        "c": "Candidate C: Max-Chunk Classifier Only"
    }
    
    dev_optimal_thresholds = {}
    threshold_grid = [round(t, 2) for t in np.arange(0.10, 0.96, 0.01)]
    
    for key in candidate_keys:
        scores = dev_scored[key]
        y_true = dev_scored["y"]
        best_t = 0.50
        best_f1 = -1.0
        for t in threshold_grid:
            preds = [1 if s >= t else 0 for s in scores]
            m = calc_metrics(y_true, preds)
            if m["f1"] > best_f1:
                best_f1 = m["f1"]
                best_t = t
        dev_optimal_thresholds[key] = best_t
        print(f"  {candidate_names[key]}: Optimal Threshold = {best_t:.2f} (Dev F1 = {best_f1:.4f})")
        
    # 3. Evaluate each candidate on Dev, Test, Holdout
    dataset_eval_results = {}
    for key in candidate_keys:
        thresh = dev_optimal_thresholds[key]
        m_dev = calc_metrics(dev_scored["y"], [1 if s >= thresh else 0 for s in dev_scored[key]])
        m_test = calc_metrics(test_scored["y"], [1 if s >= thresh else 0 for s in test_scored[key]])
        m_holdout = calc_metrics(holdout_scored["y"], [1 if s >= thresh else 0 for s in holdout_scored[key]])
        
        dataset_eval_results[key] = {
            "threshold": thresh,
            "dev": m_dev,
            "test": m_test,
            "holdout": m_holdout
        }
        print(f"\n--- {candidate_names[key]} (Threshold = {thresh:.2f}) ---")
        print(f"  Dev     : F1={m_dev['f1']:.4f}, Prec={m_dev['precision']:.4f}, Rec={m_dev['recall']:.4f}, FPR={m_dev['fpr']:.4f}")
        print(f"  Test    : F1={m_test['f1']:.4f}, Prec={m_test['precision']:.4f}, Rec={m_test['recall']:.4f}, FPR={m_test['fpr']:.4f}")
        print(f"  Holdout : F1={m_holdout['f1']:.4f}, Prec={m_holdout['precision']:.4f}, Rec={m_holdout['recall']:.4f}, FPR={m_holdout['fpr']:.4f}")
        
    # 4. Run Embedding Stress Test on All 3 Candidates
    print("\n" + "=" * 80)
    print("RUNNING EMBEDDING STRESS TEST (Positions: start/mid/end | Padding: 50/200/500 words)")
    print("=" * 80)
    inj_stress_cases, ben_stress_cases = build_stress_test_dataset(test_data)
    
    stress_results = {key: {} for key in candidate_keys}
    
    for pad in [50, 200, 500]:
        for key in candidate_keys:
            stress_results[key][pad] = {"positions": {}, "mean_recall": 0.0, "mean_fpr": 0.0}
            
        pad_inj_recalls = {key: [] for key in candidate_keys}
        pad_ben_fprs = {key: [] for key in candidate_keys}
        
        for pos in ["start", "middle", "end"]:
            inj_samples = inj_stress_cases[pad][pos]
            ben_samples = ben_stress_cases[pad][pos]
            
            # Score injections
            for key in candidate_keys:
                thresh = dev_optimal_thresholds[key]
                inj_hits = 0
                for s in inj_samples:
                    sc = score_sample_all_candidates(s["text"], "retrieved_document", stacked_full, ablated_clf)
                    if sc[f"score_{key}"] >= thresh:
                        inj_hits += 1
                rec = inj_hits / len(inj_samples) if inj_samples else 0.0
                
                # Score benign
                ben_fps = 0
                for s in ben_samples:
                    sc = score_sample_all_candidates(s["text"], "retrieved_document", stacked_full, ablated_clf)
                    if sc[f"score_{key}"] >= thresh:
                        ben_fps += 1
                fpr = ben_fps / len(ben_samples) if ben_samples else 0.0
                
                stress_results[key][pad]["positions"][pos] = {
                    "recall": round(rec, 4),
                    "fpr": round(fpr, 4)
                }
                pad_inj_recalls[key].append(rec)
                pad_ben_fprs[key].append(fpr)
                
        for key in candidate_keys:
            stress_results[key][pad]["mean_recall"] = round(float(np.mean(pad_inj_recalls[key])), 4)
            stress_results[key][pad]["mean_fpr"] = round(float(np.mean(pad_ben_fprs[key])), 4)
            
    print("\nStress Test Summary:")
    for key in candidate_keys:
        print(f"\n{candidate_names[key]}:")
        for pad in [50, 200, 500]:
            r = stress_results[key][pad]
            print(f"  Pad {pad:3d} words -> Recall: {r['mean_recall']:.4f} (start={r['positions']['start']['recall']:.2f}, mid={r['positions']['middle']['recall']:.2f}, end={r['positions']['end']['recall']:.2f}) | FPR: {r['mean_fpr']:.4f}")

    # -------------------------------------------------------------
    # 5. Selection Rule Implementation
    # -------------------------------------------------------------
    print("\n" + "=" * 80)
    print("TASK 3: PICKING FINAL CONFIGURATION ACCORDING TO SELECTION RULE")
    print("=" * 80)
    print("Rule: Among candidates with test FPR <= 5% AND stress recall >= 50% at 200-word padding, pick best dev F1.")
    print("If none qualifies, take the one with best stress recall.\n")
    
    qualifying_candidates = []
    for key in candidate_keys:
        test_fpr = dataset_eval_results[key]["test"]["fpr"]
        stress_rec_200 = stress_results[key][200]["mean_recall"]
        dev_f1 = dataset_eval_results[key]["dev"]["f1"]
        
        passes_fpr = test_fpr <= 0.05
        passes_stress = stress_rec_200 >= 0.50
        
        status = "QUALIFIED" if (passes_fpr and passes_stress) else "DISQUALIFIED"
        reasons = []
        if not passes_fpr: reasons.append(f"Test FPR ({test_fpr:.4f}) > 0.05")
        if not passes_stress: reasons.append(f"Stress Recall @ 200 ({stress_rec_200:.4f}) < 0.50")
        
        print(f"{candidate_names[key]}:")
        print(f"  Test FPR: {test_fpr:.4f} | Stress Recall @ 200: {stress_rec_200:.4f} | Dev F1: {dev_f1:.4f} -> [{status}] {', '.join(reasons)}")
        
        if passes_fpr and passes_stress:
            qualifying_candidates.append({
                "key": key,
                "name": candidate_names[key],
                "dev_f1": dev_f1,
                "test_fpr": test_fpr,
                "stress_rec_200": stress_rec_200
            })
            
    chosen_key = None
    selection_verdict_text = ""
    
    if len(qualifying_candidates) > 0:
        qualifying_candidates.sort(key=lambda x: x["dev_f1"], reverse=True)
        chosen_cand = qualifying_candidates[0]
        chosen_key = chosen_cand["key"]
        selection_verdict_text = (
            f"Qualified candidates: {[c['name'] for c in qualifying_candidates]}. "
            f"Selected {chosen_cand['name']} with highest Dev F1 ({chosen_cand['dev_f1']:.4f}), "
            f"Test FPR of {chosen_cand['test_fpr']:.4f} (<= 5%), and 200-word Stress Recall of {chosen_cand['stress_rec_200']:.4f} (>= 50%)."
        )
    else:
        # Fallback: take candidate with best stress recall
        best_stress_key = max(candidate_keys, key=lambda k: stress_results[k][200]["mean_recall"])
        chosen_key = best_stress_key
        selection_verdict_text = (
            f"No candidate satisfied both Test FPR <= 5% and Stress Recall >= 50% at 200-word padding. "
            f"Per protocol, selected {candidate_names[chosen_key]} based on highest 200-word Stress Recall ({stress_results[chosen_key][200]['mean_recall']:.4f})."
        )
        
    print(f"\nFINAL CHOSEN CANDIDATE: {candidate_names[chosen_key]}")
    print(selection_verdict_text)

    # -------------------------------------------------------------
    # 6. Task 4: Define 3 Tiers for Final Config on Dev Only
    # -------------------------------------------------------------
    print("\n" + "=" * 80)
    print(f"TASK 4: DEFINING 3 OPERATIONAL TIERS ON DEV SET FOR {candidate_names[chosen_key]}")
    print("=" * 80)
    dev_scores_chosen = dev_scored[chosen_key]
    dev_y_chosen = dev_scored["y"]
    
    dev_benign_scores = [s for s, y in zip(dev_scores_chosen, dev_y_chosen) if y == 0]
    dev_benign_scores.sort()
    n_ben = len(dev_benign_scores)
    
    # Isolate threshold: lowest threshold where dev FPR <= 0.05
    # Block threshold: lowest threshold where dev FPR <= 0.01
    thresh_grid_fine = [round(t, 4) for t in np.arange(0.01, 1.00, 0.005)]
    
    t_isolate = None
    t_block = None
    
    for t in thresh_grid_fine:
        fp_count = sum(1 for s in dev_benign_scores if s >= t)
        fpr = fp_count / n_ben
        if fpr <= 0.05 and t_isolate is None:
            t_isolate = t
        if fpr <= 0.01 and t_block is None:
            t_block = t
            
    if t_isolate is None: t_isolate = 0.50
    if t_block is None: t_block = max(t_isolate + 0.10, 0.85)
    if t_block <= t_isolate: t_block = t_isolate + 0.05
    
    # Calculate actual dev FPR at tiers
    dev_fpr_isolate = sum(1 for s in dev_benign_scores if s >= t_isolate) / n_ben
    dev_fpr_block = sum(1 for s in dev_benign_scores if s >= t_block) / n_ben
    
    # Calculate actual test FPR and Recall at tiers
    test_scores_chosen = test_scored[chosen_key]
    test_y_chosen = test_scored["y"]
    test_benign_scores = [s for s, y in zip(test_scores_chosen, test_y_chosen) if y == 0]
    test_inj_scores = [s for s, y in zip(test_scores_chosen, test_y_chosen) if y == 1]
    
    test_fpr_isolate = sum(1 for s in test_benign_scores if s >= t_isolate) / len(test_benign_scores)
    test_fpr_block = sum(1 for s in test_benign_scores if s >= t_block) / len(test_benign_scores)
    test_rec_isolate = sum(1 for s in test_inj_scores if s >= t_isolate) / len(test_inj_scores)
    test_rec_block = sum(1 for s in test_inj_scores if s >= t_block) / len(test_inj_scores)
    
    print(f"Tier Definition on Dev:")
    print(f"  - ALLOW   : score < {t_isolate:.4f}")
    print(f"  - ISOLATE : {t_isolate:.4f} <= score < {t_block:.4f} (Dev FPR: {dev_fpr_isolate:.4f} <= 5% | Test FPR: {test_fpr_isolate:.4f}, Test Recall: {test_rec_isolate:.4f})")
    print(f"  - BLOCK   : score >= {t_block:.4f} (Dev FPR: {dev_fpr_block:.4f} <= 1% | Test FPR: {test_fpr_block:.4f}, Test Recall: {test_rec_block:.4f})")

    tier_config = {
        "candidate_key": chosen_key,
        "candidate_name": candidate_names[chosen_key],
        "t_isolate": t_isolate,
        "t_block": t_block,
        "dev_fpr_isolate": round(dev_fpr_isolate, 4),
        "dev_fpr_block": round(dev_fpr_block, 4),
        "test_fpr_isolate": round(test_fpr_isolate, 4),
        "test_fpr_block": round(test_fpr_block, 4),
        "test_rec_isolate": round(test_rec_isolate, 4),
        "test_rec_block": round(test_rec_block, 4)
    }

    # -------------------------------------------------------------
    # 7. Task 5: Save v2_final Package
    # -------------------------------------------------------------
    save_v2_final_package(chosen_key, tier_config, ablated_clf)
    
    # -------------------------------------------------------------
    # 8. Compile and Save Reports & Tables
    # -------------------------------------------------------------
    final_output = {
        "candidate_names": candidate_names,
        "dev_optimal_thresholds": dev_optimal_thresholds,
        "dataset_eval_results": dataset_eval_results,
        "stress_results": stress_results,
        "selection_verdict": selection_verdict_text,
        "chosen_candidate": chosen_key,
        "tier_config": tier_config
    }
    
    report_path = EVAL_FINAL_DIR / "final_selection_report.md"
    generate_markdown_report(final_output, report_path)
    
    json_path = EVAL_FINAL_DIR / "final_selection_results.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(final_output, f, indent=2)
    print(f"\nSaved final selection report to: {report_path}")
    print(f"Saved final selection JSON to: {json_path}")
    
    return final_output

def save_v2_final_package(chosen_key: str, tier_config: Dict[str, Any], ablated_clf):
    print(f"\nSaving v2_final deployment package under {V2_FINAL_DIR}...", flush=True)
    
    # Save tier config JSON
    config_file = V2_FINAL_DIR / "config.json"
    with open(config_file, "w", encoding="utf-8") as f:
        json.dump(tier_config, f, indent=2)
        
    # Write __init__.py
    init_file = V2_FINAL_DIR / "__init__.py"
    with open(init_file, "w", encoding="utf-8") as f:
        f.write('from .scan import scan\n\n__all__ = ["scan"]\n')
        
    # Write scan.py
    scan_code = f'''"""
CAGE Production v2_final Prompt Injection Defense Module.
Architecture: {tier_config["candidate_name"]}
Multi-tier Defense: allow (< {tier_config["t_isolate"]}), isolate ([{tier_config["t_isolate"]}, {tier_config["t_block"]})), block (>= {tier_config["t_block"]})
"""

import json
from pathlib import Path
from typing import Dict, Any, List
import joblib
import numpy as np

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
from src.detection.v2.fusion_v2 import extract_detection_features, get_stacked_model

CONFIG_PATH = Path(__file__).resolve().parent / "config.json"
with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    CONFIG = json.load(f)

T_ISOLATE = float(CONFIG["t_isolate"])
T_BLOCK = float(CONFIG["t_block"])
CANDIDATE_KEY = CONFIG["candidate_key"]

_ABLATED_MODEL_CACHE = None

def _get_ablated_model():
    global _ABLATED_MODEL_CACHE
    if _ABLATED_MODEL_CACHE is not None:
        return _ABLATED_MODEL_CACHE
    model_path = BACKEND_DIR / "data" / "stacker_v2_ablated.joblib"
    if model_path.exists():
        saved = joblib.load(model_path)
        _ABLATED_MODEL_CACHE = saved["model"]
    return _ABLATED_MODEL_CACHE

def scan(text: str, source_type: str = "user_input") -> Dict[str, Any]:
    """
    Scans input text for prompt injection across multi-views and sliding window chunks.
    Returns:
        verdict: "allow" | "isolate" | "block"
        score: float between 0.0 and 1.0
        tier: "allow" | "isolate" | "block"
        triggered_chunk: snippet of chunk triggering highest score
        matched_patterns: list of heuristic regex matches
    """
    if not text or not text.strip():
        return {{
            "verdict": "allow",
            "score": 0.0,
            "tier": "allow",
            "triggered_chunk": "",
            "matched_patterns": []
        }}
        
    feats = extract_detection_features(text, source_type=source_type)
    heur_score = feats["heuristic_score"]
    class_score = feats["classifier_score"]
    
    if CANDIDATE_KEY == "a":
        stacked_full = get_stacked_model()
        x_full = feats["feature_vector"].reshape(1, -1)
        final_score = float(stacked_full.predict_proba(x_full)[0, 1])
    elif CANDIDATE_KEY == "b":
        ablated_clf = _get_ablated_model()
        if ablated_clf is not None:
            final_score = float(ablated_clf.predict_proba(np.array([[heur_score, class_score]]))[0, 1])
        else:
            final_score = float(class_score)
    else: # "c"
        final_score = float(class_score)
        
    final_score = round(final_score, 4)
    
    if final_score >= T_BLOCK:
        tier = "block"
        verdict = "block"
    elif final_score >= T_ISOLATE:
        tier = "isolate"
        verdict = "isolate"
    else:
        tier = "allow"
        verdict = "allow"
        
    return {{
        "verdict": verdict,
        "score": final_score,
        "tier": tier,
        "triggered_chunk": feats.get("trigger_chunk_text", ""),
        "matched_patterns": feats.get("matched_patterns", [])
    }}
'''
    scan_file = V2_FINAL_DIR / "scan.py"
    with open(scan_file, "w", encoding="utf-8") as f:
        f.write(scan_code)
    print(f"Successfully generated {scan_file}")

def generate_markdown_report(final_output: Dict[str, Any], out_path: Path):
    c_names = final_output["candidate_names"]
    dev_t = final_output["dev_optimal_thresholds"]
    ds_res = final_output["dataset_eval_results"]
    st_res = final_output["stress_results"]
    chosen = final_output["chosen_candidate"]
    tier = final_output["tier_config"]
    
    lines = []
    lines.append("# CAGE v2_final Selection and Verification Report\n")
    lines.append(f"**Selection Protocol**: Among candidates with Test FPR $\\le 5\\%$ and 200-word Stress Recall $\\ge 50\\%$, pick best Dev F1.\n")
    lines.append(f"**Winning Configuration**: `{c_names[chosen]}`\n")
    lines.append(f"> **Verdict**: {final_output['selection_verdict']}\n")
    
    # Table 1: Benchmark Dataset Performance Across Candidates
    lines.append("## 1. Candidate Performance on Dev, Frozen Test, and External Holdout\n")
    lines.append("| Candidate | Operating Threshold (Dev) | Dev F1 | Dev Recall | Dev FPR | Test F1 | Test Recall | Test FPR | Holdout F1 | Holdout Recall | Holdout FPR |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|---|")
    for k in ["a", "b", "c"]:
        t = dev_t[k]
        m_d = ds_res[k]["dev"]
        m_t = ds_res[k]["test"]
        m_h = ds_res[k]["holdout"]
        lines.append(f"| **{c_names[k]}** | `t = {t:.2f}` | **{m_d['f1']:.4f}** | {m_d['recall']:.4f} | {m_d['fpr']:.4f} | **{m_t['f1']:.4f}** | {m_t['recall']:.4f} | **{m_t['fpr']:.4f}** | **{m_h['f1']:.4f}** | {m_h['recall']:.4f} | **{m_h['fpr']:.4f}** |")
    lines.append("\n")
    
    # Table 2: Embedding Stress Test Results
    lines.append("## 2. Embedding Stress Test: Injection Recall & Benign FPR across Paddings\n")
    lines.append("| Candidate | Pad 50 Recall (Start/Mid/End) | Pad 50 Mean Recall | Pad 200 Recall (Start/Mid/End) | Pad 200 Mean Recall | Pad 500 Recall (Start/Mid/End) | Pad 500 Mean Recall | Mean Benign FPR (50/200/500) |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for k in ["a", "b", "c"]:
        s50 = st_res[k][50]
        s200 = st_res[k][200]
        s500 = st_res[k][500]
        lines.append(
            f"| **{c_names[k]}** | "
            f"{s50['positions']['start']['recall']:.2f} / {s50['positions']['middle']['recall']:.2f} / {s50['positions']['end']['recall']:.2f} | **{s50['mean_recall']:.4f}** | "
            f"{s200['positions']['start']['recall']:.2f} / {s200['positions']['middle']['recall']:.2f} / {s200['positions']['end']['recall']:.2f} | **{s200['mean_recall']:.4f}** | "
            f"{s500['positions']['start']['recall']:.2f} / {s500['positions']['middle']['recall']:.2f} / {s500['positions']['end']['recall']:.2f} | **{s500['mean_recall']:.4f}** | "
            f"{s50['mean_fpr']:.4f} / {s200['mean_fpr']:.4f} / {s500['mean_fpr']:.4f} |"
        )
    lines.append("\n")

    # Table 3: Tier Configuration for Chosen Model
    lines.append("## 3. Operational Three-Tier Policy for Production (Dev-Tuned)\n")
    lines.append(f"**Target Model**: `{tier['candidate_name']}`\n")
    lines.append("| Tier | Threshold Condition | Action | Dev FPR | Test FPR | Test Recall | Description |")
    lines.append("|---|---|---|---|---|---|---|")
    lines.append(f"| **ALLOW** | `score < {tier['t_isolate']:.4f}` | Allow prompt to pass to upstream LLM | — | — | — | Clean or benign prompt with low suspicion. |")
    lines.append(f"| **ISOLATE** | `{tier['t_isolate']:.4f} <= score < {tier['t_block']:.4f}` | Quarantine input in untrusted wrappers | **{tier['dev_fpr_isolate']:.4f}** (<= 5%) | **{tier['test_fpr_isolate']:.4f}** | **{tier['test_rec_isolate']:.4f}** | Borderline injection pattern or hard benign negative. |")
    lines.append(f"| **BLOCK** | `score >= {tier['t_block']:.4f}` | Block execution immediately (safe_text=None) | **{tier['dev_fpr_block']:.4f}** (<= 1%) | **{tier['test_fpr_block']:.4f}** | **{tier['test_rec_block']:.4f}** | High-confidence malicious prompt injection attack. |")
    lines.append("\n")

    # Known Weaknesses List
    lines.append("## 4. Known Weaknesses of the Final Configuration\n")
    lines.append("1. **Multilingual Injections**: Non-English attacks (especially German prompt overrides and roleplay queries from ZEIT ONLINE in public datasets) lack dense representations in TF-IDF vocabulary, occasionally escaping detection without multilingual embeddings.")
    lines.append("2. **Stealth Benign Padding Tradeoff**: While removing `log_len` recovers injection recall inside long documents, long documents containing technical security discussions still have a ~4% probability of crossing the isolate threshold.")
    lines.append("3. **Multi-turn and State Steganography**: Attacks fragmented across multiple conversational turns or encodings not covered by NFKC/homoglyphs/base64 (e.g. cipher rotations or token space manipulations) will not be unwrapped by the preprocessor.")
    lines.append("\n")
    
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

if __name__ == "__main__":
    run_final_selection()
