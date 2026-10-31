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

from src.detection.heuristics import detect as heuristic_detect
from src.detection.v2.preprocess import get_views
from src.detection.v2.classifier_v2 import _get_model_v2
from src.detection.v2.fusion_v2 import extract_detection_features

DEV_PATH = BACKEND_DIR / "eval" / "data" / "dev.jsonl"
TEST_PATH = BACKEND_DIR / "eval" / "data" / "test.jsonl"
HOLDOUT_PATH = BACKEND_DIR / "eval" / "data" / "holdout_external.jsonl"
ABLATED_MODEL_PATH = BACKEND_DIR / "data" / "stacker_v2_ablated.joblib"
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
# Fine-Grained Unit Extraction
# -------------------------------------------------------------
def extract_fine_grained_units(text: str) -> List[str]:
    """
    Extracts fine-grained scoring units across all preprocessing views:
    (a) sentences/lines (split on . ! ? and newlines)
    (b) 15-word windows with stride 8
    (c) 60-word windows with stride 30
    (d) full view text
    Applied to EVERY input regardless of length (no 80-word minimum).
    """
    if not text or not text.strip():
        return [""]
        
    views = get_views(text)
    units = []
    seen = set()
    
    for v in views:
        v_clean = v.strip()
        if not v_clean:
            continue
            
        # (a) sentences/lines (split on . ! ? and newlines)
        raw_splits = re.split(r'[\r\n]+|[.!?]+', v_clean)
        for s in raw_splits:
            sc = s.strip()
            if sc and sc not in seen:
                units.append(sc)
                seen.add(sc)
                
        # Words for windowing
        words = v_clean.split()
        n = len(words)
        if n > 0:
            # (b) 15-word windows with stride 8
            if n <= 15:
                w15 = " ".join(words)
                if w15 not in seen:
                    units.append(w15)
                    seen.add(w15)
            else:
                idx = 0
                while idx < n:
                    end = min(idx + 15, n)
                    w15 = " ".join(words[idx:end])
                    if w15 not in seen:
                        units.append(w15)
                        seen.add(w15)
                    if end >= n:
                        break
                    idx += 8
                    
            # (c) 60-word windows with stride 30
            if n <= 60:
                w60 = " ".join(words)
                if w60 not in seen:
                    units.append(w60)
                    seen.add(w60)
            else:
                idx = 0
                while idx < n:
                    end = min(idx + 60, n)
                    w60 = " ".join(words[idx:end])
                    if w60 not in seen:
                        units.append(w60)
                        seen.add(w60)
                    if end >= n:
                        break
                    idx += 30
                    
        # (d) Full view text itself
        if v_clean not in seen:
            units.append(v_clean)
            seen.add(v_clean)
            
    return units if units else [text]

# -------------------------------------------------------------
# Scoring Pipeline
# -------------------------------------------------------------
class FineGrainedScorer:
    def __init__(self):
        self.vec, self.model = _get_model_v2()
        self.ablated_clf = None
        if ABLATED_MODEL_PATH.exists():
            saved = joblib.load(ABLATED_MODEL_PATH)
            self.ablated_clf = saved["model"]
            
    def score_text(self, text: str, source_type: str = "user_input") -> Dict[str, Any]:
        units = extract_fine_grained_units(text)
        
        # Batch TF-IDF + LogisticRegression calibration
        x_mat = self.vec.transform(units)
        probs = self.model.predict_proba(x_mat)[:, 1]
        
        # Heuristics on each unit
        h_results = [heuristic_detect(u) for u in units]
        h_scores = [hr.score for hr in h_results]
        
        max_c_idx = int(np.argmax(probs))
        max_c_score = float(probs[max_c_idx])
        trigger_unit_c = units[max_c_idx]
        
        max_h_idx = int(np.argmax(h_scores)) if h_scores else 0
        max_h_score = float(h_scores[max_h_idx]) if h_scores else 0.0
        trigger_unit_h = units[max_h_idx] if units else ""
        matched_patterns_all = []
        for hr in h_results:
            for mp in hr.matched_patterns:
                if mp not in matched_patterns_all:
                    matched_patterns_all.append(mp)
                    
        # Also compute Candidate B (previous ablated stacker with v2 chunking)
        # Using extract_detection_features from v2
        b_feats = extract_detection_features(text, source_type=source_type)
        if self.ablated_clf is not None:
            score_b = float(self.ablated_clf.predict_proba(
                np.array([[b_feats["heuristic_score"], b_feats["classifier_score"]]])
            )[0, 1])
        else:
            score_b = float(b_feats["classifier_score"])
            
        return {
            "max_c": max_c_score,
            "max_h": max_h_score,
            "trigger_unit_c": trigger_unit_c,
            "trigger_unit_h": trigger_unit_h,
            "score_b": score_b,
            "matched_patterns": matched_patterns_all,
            "units": units,
            "unit_c_scores": [float(p) for p in probs],
            "unit_h_scores": h_scores
        }

# -------------------------------------------------------------
# Stress Test Builder
# -------------------------------------------------------------
def build_padding_corpus(test_data: List[Dict[str, Any]]) -> List[str]:
    benign_docs = [d["text"] for d in test_data if d["label"] == 0 and d["source_type"] == "retrieved_document"]
    combined_words = []
    for doc in benign_docs:
        if "CYBERSECURITY" not in doc and "DISPATCH" not in doc and "EXPLOIT" not in doc:
            combined_words.extend(doc.split())
    if len(combined_words) < 2000:
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

def build_stress_dataset(test_data: List[Dict[str, Any]], sample_limit: int = 30):
    padding_words = build_padding_corpus(test_data)
    
    # Injections and Benign short prompts
    short_injections = [d for d in test_data if d["label"] == 1 and len(d["text"].split()) < 50][:sample_limit]
    short_benign = [d for d in test_data if d["label"] == 0 and len(d["text"].split()) < 30][:sample_limit]
    
    padding_lengths = [50, 200, 500]
    positions = ["start", "middle", "end"]
    
    inj_stress_cases = {pad: {pos: [] for pos in positions} for pad in padding_lengths}
    ben_stress_cases = {pad: {pos: [] for pos in positions} for pad in padding_lengths}
    
    for pad in padding_lengths:
        for pos in positions:
            for idx, item in enumerate(short_injections):
                inj_text = item["text"]
                pad_text = get_padding_slice(padding_words, pad, offset=idx * 73)
                if pos == "start":
                    doc = f"{inj_text}\n\n{pad_text}"
                elif pos == "end":
                    doc = f"{pad_text}\n\n{inj_text}"
                else:
                    half = pad // 2
                    p1 = get_padding_slice(padding_words, half, offset=idx * 73)
                    p2 = get_padding_slice(padding_words, pad - half, offset=idx * 73 + half)
                    doc = f"{p1}\n\n{inj_text}\n\n{p2}"
                    
                inj_stress_cases[pad][pos].append({
                    "id": f"stress_inj_p{pad}_{pos}_{idx}",
                    "text": doc,
                    "label": 1,
                    "orig_inj": inj_text,
                    "source_type": "retrieved_document"
                })
                
            for idx, item in enumerate(short_benign):
                ben_text = item["text"]
                pad_text = get_padding_slice(padding_words, pad, offset=(idx + 50) * 89)
                if pos == "start":
                    doc = f"{ben_text}\n\n{pad_text}"
                elif pos == "end":
                    doc = f"{pad_text}\n\n{ben_text}"
                else:
                    half = pad // 2
                    p1 = get_padding_slice(padding_words, half, offset=(idx + 50) * 89)
                    p2 = get_padding_slice(padding_words, pad - half, offset=(idx + 50) * 89 + half)
                    doc = f"{p1}\n\n{ben_text}\n\n{p2}"
                    
                ben_stress_cases[pad][pos].append({
                    "id": f"stress_ben_p{pad}_{pos}_{idx}",
                    "text": doc,
                    "label": 0,
                    "orig_ben": ben_text,
                    "source_type": "retrieved_document"
                })
                
    return inj_stress_cases, ben_stress_cases

def main():
    print("=" * 80)
    print("RUNNING FINE-GRAINED SCORING UNITS EVALUATION")
    print("=" * 80)
    
    scorer = FineGrainedScorer()
    
    dev_data = load_jsonl(DEV_PATH)
    test_data = load_jsonl(TEST_PATH)
    holdout_data = load_jsonl(HOLDOUT_PATH)
    print(f"Loaded {len(dev_data)} Dev, {len(test_data)} Test, {len(holdout_data)} External Holdout samples.")
    
    # 1. Score Dev, Test, Holdout
    print("\nScoring Dev samples...", flush=True)
    t0 = time.time()
    dev_scored = [scorer.score_text(d["text"], d.get("source_type", "user_input")) for d in dev_data]
    print(f"Scored {len(dev_data)} Dev in {time.time() - t0:.2f}s.")
    
    print("Scoring Test samples...", flush=True)
    t0 = time.time()
    test_scored = [scorer.score_text(d["text"], d.get("source_type", "user_input")) for d in test_data]
    print(f"Scored {len(test_data)} Test in {time.time() - t0:.2f}s.")
    
    print("Scoring Holdout samples...", flush=True)
    t0 = time.time()
    holdout_scored = [scorer.score_text(d["text"], d.get("source_type", "user_input")) for d in holdout_data]
    print(f"Scored {len(holdout_data)} Holdout in {time.time() - t0:.2f}s.")
    
    dev_y = [d["label"] for d in dev_data]
    test_y = [d["label"] for d in test_data]
    holdout_y = [d["label"] for d in holdout_data]
    
    # 2. Threshold Calibration on Dev ONLY
    print("\n" + "=" * 80)
    print("TASK 2: CALIBRATING THRESHOLDS ON DEV (Best F1 subject to Dev FPR <= 5%)")
    print("=" * 80)
    
    threshold_grid = [round(t, 4) for t in np.arange(0.01, 1.00, 0.002)]
    
    # Candidate B: Previous selected candidate (fixed threshold 0.90 from previous selection)
    t_b = 0.90
    m_dev_b = calc_metrics(dev_y, [1 if s["score_b"] >= t_b else 0 for s in dev_scored])
    print(f"Candidate B (Previous Stacker): Dev F1 = {m_dev_b['f1']:.4f}, FPR = {m_dev_b['fpr']:.4f}, Rec = {m_dev_b['recall']:.4f} at t={t_b}")
    
    # Candidate C2: max-unit classifier score only
    # Find t on dev with best F1 subject to dev FPR <= 5%
    best_t_c2 = None
    best_f1_c2 = -1.0
    best_m_dev_c2 = None
    
    for t in threshold_grid:
        preds = [1 if s["max_c"] >= t else 0 for s in dev_scored]
        m = calc_metrics(dev_y, preds)
        if m["fpr"] <= 0.05:
            if m["f1"] > best_f1_c2:
                best_f1_c2 = m["f1"]
                best_t_c2 = t
                best_m_dev_c2 = m
                
    if best_t_c2 is None:
        # If no threshold had FPR <= 0.05, take lowest FPR
        print("Warning: No threshold for C2 satisfied FPR <= 0.05. Taking threshold with minimal FPR.")
        best_t_c2 = max(threshold_grid)
        best_m_dev_c2 = calc_metrics(dev_y, [1 if s["max_c"] >= best_t_c2 else 0 for s in dev_scored])
        
    print(f"Candidate C2 (Max-Unit Classifier): Optimal t = {best_t_c2:.4f} -> Dev F1 = {best_m_dev_c2['f1']:.4f}, FPR = {best_m_dev_c2['fpr']:.4f}, Rec = {best_m_dev_c2['recall']:.4f}")
    
    # Candidate D: heuristic >= 0.30 OR max-unit classifier >= t
    # Find t on dev with best F1 subject to dev FPR <= 5%
    best_t_d = None
    best_f1_d = -1.0
    best_m_dev_d = None
    
    for t in threshold_grid:
        preds = [1 if (s["max_h"] >= 0.30 or s["max_c"] >= t) else 0 for s in dev_scored]
        m = calc_metrics(dev_y, preds)
        if m["fpr"] <= 0.05:
            if m["f1"] > best_f1_d:
                best_f1_d = m["f1"]
                best_t_d = t
                best_m_dev_d = m
                
    if best_t_d is None:
        print("Note: Candidate D has minimum Dev FPR > 0.05 (due to heuristic matches on benign security policies).")
        # Find threshold that minimizes FPR on dev
        min_fpr = 1.0
        for t in threshold_grid:
            preds = [1 if (s["max_h"] >= 0.30 or s["max_c"] >= t) else 0 for s in dev_scored]
            m = calc_metrics(dev_y, preds)
            if m["fpr"] < min_fpr:
                min_fpr = m["fpr"]
                best_t_d = t
                best_m_dev_d = m
        print(f"Candidate D (Min FPR fallback): t = {best_t_d:.4f} -> Dev F1 = {best_m_dev_d['f1']:.4f}, FPR = {best_m_dev_d['fpr']:.4f}, Rec = {best_m_dev_d['recall']:.4f}")
    else:
        print(f"Candidate D: Optimal t = {best_t_d:.4f} -> Dev F1 = {best_m_dev_d['f1']:.4f}, FPR = {best_m_dev_d['fpr']:.4f}, Rec = {best_m_dev_d['recall']:.4f}")

    # Evaluate all candidates on Test and Holdout
    m_test_b = calc_metrics(test_y, [1 if s["score_b"] >= t_b else 0 for s in test_scored])
    m_holdout_b = calc_metrics(holdout_y, [1 if s["score_b"] >= t_b else 0 for s in holdout_scored])
    
    m_test_c2 = calc_metrics(test_y, [1 if s["max_c"] >= best_t_c2 else 0 for s in test_scored])
    m_holdout_c2 = calc_metrics(holdout_y, [1 if s["max_c"] >= best_t_c2 else 0 for s in holdout_scored])
    
    m_test_d = calc_metrics(test_y, [1 if (s["max_h"] >= 0.30 or s["max_c"] >= best_t_d) else 0 for s in test_scored])
    m_holdout_d = calc_metrics(holdout_y, [1 if (s["max_h"] >= 0.30 or s["max_c"] >= best_t_d) else 0 for s in holdout_scored])
    
    print("\n--- Test and Holdout Metrics ---")
    print(f"Candidate B  : Test F1={m_test_b['f1']:.4f}, FPR={m_test_b['fpr']:.4f}, Rec={m_test_b['recall']:.4f} | Holdout F1={m_holdout_b['f1']:.4f}, FPR={m_holdout_b['fpr']:.4f}, Rec={m_holdout_b['recall']:.4f}")
    print(f"Candidate C2 : Test F1={m_test_c2['f1']:.4f}, FPR={m_test_c2['fpr']:.4f}, Rec={m_test_c2['recall']:.4f} | Holdout F1={m_holdout_c2['f1']:.4f}, FPR={m_holdout_c2['fpr']:.4f}, Rec={m_holdout_c2['recall']:.4f}")
    print(f"Candidate D  : Test F1={m_test_d['f1']:.4f}, FPR={m_test_d['fpr']:.4f}, Rec={m_test_d['recall']:.4f} | Holdout F1={m_holdout_d['f1']:.4f}, FPR={m_holdout_d['fpr']:.4f}, Rec={m_holdout_d['recall']:.4f}")

    # 3. Embedding Stress Test
    print("\n" + "=" * 80)
    print("TASK 3: RUNNING EMBEDDING STRESS TEST (30 samples per setting)")
    print("=" * 80)
    inj_stress_cases, ben_stress_cases = build_stress_dataset(test_data, sample_limit=30)
    
    stress_results = {"b": {}, "c2": {}, "d": {}}
    missed_injections = [] # To capture 10 examples missed by winning candidate
    
    for pad in [50, 200, 500]:
        for k in ["b", "c2", "d"]:
            stress_results[k][pad] = {"positions": {}, "mean_recall": 0.0, "mean_fpr": 0.0}
            
        pad_inj_recs = {"b": [], "c2": [], "d": []}
        pad_ben_fprs = {"b": [], "c2": [], "d": []}
        
        for pos in ["start", "middle", "end"]:
            inj_samples = inj_stress_cases[pad][pos]
            ben_samples = ben_stress_cases[pad][pos]
            
            # Score injections
            inj_scores = [scorer.score_text(s["text"], "retrieved_document") for s in inj_samples]
            ben_scores = [scorer.score_text(s["text"], "retrieved_document") for s in ben_samples]
            
            # Predictions
            # B
            b_inj_pred = [1 if s["score_b"] >= t_b else 0 for s in inj_scores]
            b_ben_pred = [1 if s["score_b"] >= t_b else 0 for s in ben_scores]
            # C2
            c2_inj_pred = [1 if s["max_c"] >= best_t_c2 else 0 for s in inj_scores]
            c2_ben_pred = [1 if s["max_c"] >= best_t_c2 else 0 for s in ben_scores]
            # D
            d_inj_pred = [1 if (s["max_h"] >= 0.30 or s["max_c"] >= best_t_d) else 0 for s in inj_scores]
            d_ben_pred = [1 if (s["max_h"] >= 0.30 or s["max_c"] >= best_t_d) else 0 for s in ben_scores]
            
            # Track missed
            for idx, (p_c2, p_d, sc, item) in enumerate(zip(c2_inj_pred, d_inj_pred, inj_scores, inj_samples)):
                if p_c2 == 0 and len(missed_injections) < 15:
                    missed_injections.append({
                        "pad": pad,
                        "pos": pos,
                        "orig_inj": item["orig_inj"],
                        "max_c": sc["max_c"],
                        "max_h": sc["max_h"],
                        "trigger_unit_c": sc["trigger_unit_c"],
                        "units": sc["units"][:5],
                        "unit_c_scores": sc["unit_c_scores"][:5]
                    })
                    
            r_b = sum(b_inj_pred) / len(b_inj_pred) if b_inj_pred else 0.0
            r_c2 = sum(c2_inj_pred) / len(c2_inj_pred) if c2_inj_pred else 0.0
            r_d = sum(d_inj_pred) / len(d_inj_pred) if d_inj_pred else 0.0
            
            f_b = sum(b_ben_pred) / len(b_ben_pred) if b_ben_pred else 0.0
            f_c2 = sum(c2_ben_pred) / len(c2_ben_pred) if c2_ben_pred else 0.0
            f_d = sum(d_ben_pred) / len(d_ben_pred) if d_ben_pred else 0.0
            
            stress_results["b"][pad]["positions"][pos] = {"recall": round(r_b, 4), "fpr": round(f_b, 4)}
            stress_results["c2"][pad]["positions"][pos] = {"recall": round(r_c2, 4), "fpr": round(f_c2, 4)}
            stress_results["d"][pad]["positions"][pos] = {"recall": round(r_d, 4), "fpr": round(f_d, 4)}
            
            pad_inj_recs["b"].append(r_b)
            pad_inj_recs["c2"].append(r_c2)
            pad_inj_recs["d"].append(r_d)
            
            pad_ben_fprs["b"].append(f_b)
            pad_ben_fprs["c2"].append(f_c2)
            pad_ben_fprs["d"].append(f_d)
            
        for k in ["b", "c2", "d"]:
            stress_results[k][pad]["mean_recall"] = round(float(np.mean(pad_inj_recs[k])), 4)
            stress_results[k][pad]["mean_fpr"] = round(float(np.mean(pad_ben_fprs[k])), 4)
            
    print("\nStress Test Results:")
    c_labels = {
        "b": "Candidate B (Prev Stacker [heur, class])",
        "c2": "Candidate C2 (Fine-grained Max-Unit Classifier)",
        "d": "Candidate D (Fine-grained Heur >= 0.30 OR Class >= t)"
    }
    for k in ["b", "c2", "d"]:
        print(f"\n{c_labels[k]}:")
        for pad in [50, 200, 500]:
            r = stress_results[k][pad]
            print(f"  Pad {pad:3d} -> Mean Recall: {r['mean_recall']:.4f} (start={r['positions']['start']['recall']:.2f}, mid={r['positions']['middle']['recall']:.2f}, end={r['positions']['end']['recall']:.2f}) | FPR: {r['mean_fpr']:.4f}")

    # 4. Selection Rule
    print("\n" + "=" * 80)
    print("TASK 4: APPLYING SELECTION RULE")
    print("=" * 80)
    print("Rule: Among candidates with test FPR <= 5% and stress recall >= 50% at 200-word padding, pick best dev F1.")
    print("If none qualifies, take the one with best stress recall and say so plainly.\n")
    
    cand_summary = {
        "b": {
            "name": c_labels["b"],
            "dev_f1": m_dev_b["f1"],
            "test_fpr": m_test_b["fpr"],
            "stress_rec_200": stress_results["b"][200]["mean_recall"]
        },
        "c2": {
            "name": c_labels["c2"],
            "dev_f1": best_m_dev_c2["f1"],
            "test_fpr": m_test_c2["fpr"],
            "stress_rec_200": stress_results["c2"][200]["mean_recall"]
        },
        "d": {
            "name": c_labels["d"],
            "dev_f1": best_m_dev_d["f1"],
            "test_fpr": m_test_d["fpr"],
            "stress_rec_200": stress_results["d"][200]["mean_recall"]
        }
    }
    
    qualifying = []
    for k, cs in cand_summary.items():
        passes_fpr = cs["test_fpr"] <= 0.05
        passes_stress = cs["stress_rec_200"] >= 0.50
        status = "QUALIFIED" if (passes_fpr and passes_stress) else "DISQUALIFIED"
        reasons = []
        if not passes_fpr: reasons.append(f"Test FPR ({cs['test_fpr']:.4f}) > 0.05")
        if not passes_stress: reasons.append(f"Stress Recall @ 200 ({cs['stress_rec_200']:.4f}) < 0.50")
        print(f"{cs['name']}:")
        print(f"  Test FPR: {cs['test_fpr']:.4f} | 200-word Stress Recall: {cs['stress_rec_200']:.4f} | Dev F1: {cs['dev_f1']:.4f} -> [{status}] {', '.join(reasons)}")
        if passes_fpr and passes_stress:
            qualifying.append(k)
            
    winner = None
    if qualifying:
        qualifying.sort(key=lambda k: cand_summary[k]["dev_f1"], reverse=True)
        winner = qualifying[0]
        verdict = f"Qualified candidate(s) found: {qualifying}. Selected {cand_summary[winner]['name']} with best Dev F1 ({cand_summary[winner]['dev_f1']:.4f})."
    else:
        # Fallback: best stress recall
        winner = max(["b", "c2", "d"], key=lambda k: cand_summary[k]["stress_rec_200"])
        verdict = (
            f"None of the candidates qualified under the 50% stress recall threshold at 200-word padding. "
            f"Per protocol, selected {cand_summary[winner]['name']} with the highest 200-word Stress Recall ({cand_summary[winner]['stress_rec_200']:.4f})."
        )
        
    print(f"\nWINNER: {cand_summary[winner]['name']}")
    print(f"Verdict: {verdict}")
    
    # Tier Policy for C2 (or Winner)
    # Isolate at Dev FPR <= 5%, Block at Dev FPR <= 1%
    dev_benign_c2 = [s["max_c"] for s, y in zip(dev_scored, dev_y) if y == 0]
    dev_benign_c2.sort()
    n_ben = len(dev_benign_c2)
    
    t_isolate_c2 = None
    t_block_c2 = None
    for t in threshold_grid:
        fp_count = sum(1 for s in dev_benign_c2 if s >= t)
        fpr = fp_count / n_ben
        if fpr <= 0.05 and t_isolate_c2 is None:
            t_isolate_c2 = t
        if fpr <= 0.01 and t_block_c2 is None:
            t_block_c2 = t
            
    if t_isolate_c2 is None: t_isolate_c2 = 0.99
    if t_block_c2 is None: t_block_c2 = 0.998
    
    print(f"\nDev-Tuned Tier Policy for C2:")
    print(f"  - ALLOW   : score < {t_isolate_c2:.4f}")
    print(f"  - ISOLATE : {t_isolate_c2:.4f} <= score < {t_block_c2:.4f}")
    print(f"  - BLOCK   : score >= {t_block_c2:.4f}")
    
    tier_config_c2 = {
        "candidate_key": "c2",
        "candidate_name": c_labels["c2"],
        "t_isolate": t_isolate_c2,
        "t_block": t_block_c2,
        "dev_fpr_isolate": round(sum(1 for s in dev_benign_c2 if s >= t_isolate_c2) / n_ben, 4),
        "dev_fpr_block": round(sum(1 for s in dev_benign_c2 if s >= t_block_c2) / n_ben, 4)
    }
    
    # Save results to JSON and Markdown
    results_payload = {
        "candidate_summary": cand_summary,
        "winner": winner,
        "verdict": verdict,
        "dataset_metrics": {
            "b": {"dev": m_dev_b, "test": m_test_b, "holdout": m_holdout_b},
            "c2": {"dev": best_m_dev_c2, "test": m_test_c2, "holdout": m_holdout_c2},
            "d": {"dev": best_m_dev_d, "test": m_test_d, "holdout": m_holdout_d}
        },
        "stress_results": stress_results,
        "tier_config_c2": tier_config_c2,
        "missed_injections": missed_injections[:10]
    }
    
    out_json = EVAL_FINAL_DIR / "fine_grained_eval_results.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(results_payload, f, indent=2)
    print(f"\nSaved fine-grained evaluation results to: {out_json}")
    
    # If winner is C2 or D, update scan.py and config.json
    if winner in ["c2", "d"]:
        update_production_module(winner, tier_config_c2, best_t_c2 if winner == "c2" else best_t_d)
    else:
        print("\nCandidate B remained winner. No changes made to production module.")

def update_production_module(winner_key: str, tier_config: Dict[str, Any], operational_thresh: float):
    print(f"\nUpdating src/detection/v2_final/ to {winner_key} as new winner...", flush=True)
    
    # Update config.json
    config_file = V2_FINAL_DIR / "config.json"
    cfg = {
        "candidate_key": winner_key,
        "candidate_name": tier_config["candidate_name"],
        "t_isolate": tier_config["t_isolate"],
        "t_block": tier_config["t_block"],
        "dev_fpr_isolate": tier_config["dev_fpr_isolate"],
        "dev_fpr_block": tier_config["dev_fpr_block"],
        "operational_threshold": operational_thresh
    }
    with open(config_file, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)
        
    # Generate scan.py for fine-grained scoring
    scan_code = f'''"""
CAGE Production v2_final Prompt Injection Defense Module (FINE-GRAINED SCORING UNITS).
Architecture: {tier_config["candidate_name"]}
Multi-tier Defense: allow (< {tier_config["t_isolate"]}), isolate ([{tier_config["t_isolate"]}, {tier_config["t_block"]})), block (>= {tier_config["t_block"]})
"""

import json
import re
from pathlib import Path
from typing import Dict, Any, List
import numpy as np

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
from src.detection.heuristics import detect as heuristic_detect
from src.detection.v2.preprocess import get_views
from src.detection.v2.classifier_v2 import _get_model_v2

CONFIG_PATH = Path(__file__).resolve().parent / "config.json"
with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    CONFIG = json.load(f)

T_ISOLATE = float(CONFIG["t_isolate"])
T_BLOCK = float(CONFIG["t_block"])
CANDIDATE_KEY = CONFIG["candidate_key"]

def extract_fine_grained_units(text: str) -> List[str]:
    """
    Extracts fine-grained scoring units across all preprocessing views:
    (a) sentences/lines (split on . ! ? and newlines)
    (b) 15-word windows with stride 8
    (c) 60-word windows with stride 30
    (d) full view text
    Applied to EVERY input regardless of length (no 80-word minimum).
    """
    if not text or not text.strip():
        return [""]
        
    views = get_views(text)
    units = []
    seen = set()
    
    for v in views:
        v_clean = v.strip()
        if not v_clean:
            continue
            
        # (a) sentences/lines
        raw_splits = re.split(r'[\\r\\n]+|[.!?]+', v_clean)
        for s in raw_splits:
            sc = s.strip()
            if sc and sc not in seen:
                units.append(sc)
                seen.add(sc)
                
        # (b) & (c) word windows
        words = v_clean.split()
        n = len(words)
        if n > 0:
            if n <= 15:
                w15 = " ".join(words)
                if w15 not in seen:
                    units.append(w15)
                    seen.add(w15)
            else:
                idx = 0
                while idx < n:
                    end = min(idx + 15, n)
                    w15 = " ".join(words[idx:end])
                    if w15 not in seen:
                        units.append(w15)
                        seen.add(w15)
                    if end >= n:
                        break
                    idx += 8
                    
            if n <= 60:
                w60 = " ".join(words)
                if w60 not in seen:
                    units.append(w60)
                    seen.add(w60)
            else:
                idx = 0
                while idx < n:
                    end = min(idx + 60, n)
                    w60 = " ".join(words[idx:end])
                    if w60 not in seen:
                        units.append(w60)
                        seen.add(w60)
                    if end >= n:
                        break
                    idx += 30
                    
        if v_clean not in seen:
            units.append(v_clean)
            seen.add(v_clean)
            
    return units if units else [text]

def scan(text: str, source_type: str = "user_input") -> Dict[str, Any]:
    """
    Scans input text for prompt injection across fine-grained units.
    Returns:
        verdict: "allow" | "isolate" | "block"
        score: float between 0.0 and 1.0
        tier: "allow" | "isolate" | "block"
        triggered_chunk: snippet of unit triggering highest score
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
        
    units = extract_fine_grained_units(text)
    vec, model = _get_model_v2()
    
    # Score units with classifier
    x_mat = vec.transform(units)
    probs = model.predict_proba(x_mat)[:, 1]
    
    # Score units with heuristics
    h_results = [heuristic_detect(u) for u in units]
    h_scores = [hr.score for hr in h_results]
    
    max_c_idx = int(np.argmax(probs))
    max_c = float(probs[max_c_idx])
    trigger_unit = units[max_c_idx]
    
    matched_patterns = []
    for hr in h_results:
        for mp in hr.matched_patterns:
            if mp not in matched_patterns:
                matched_patterns.append(mp)
                
    if CANDIDATE_KEY == "d":
        max_h = float(max(h_scores)) if h_scores else 0.0
        final_score = max(max_h, max_c)
    else:
        final_score = max_c
        
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
        "triggered_chunk": trigger_unit[:120] + ("..." if len(trigger_unit) > 120 else ""),
        "matched_patterns": matched_patterns
    }}
'''
    scan_file = V2_FINAL_DIR / "scan.py"
    with open(scan_file, "w", encoding="utf-8") as f:
        f.write(scan_code)
    print(f"Successfully wrote updated {scan_file}")

if __name__ == "__main__":
    main()
