import json
import math
import os
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

# Imports from CAGE codebase
import sys
backend_dir = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(backend_dir))

from src.detection.heuristics import detect as heuristic_detect
from src.detection.v2.preprocess import get_views
from src.detection.v2.chunking import score_with_chunking
from src.detection.v2.classifier_v2 import classify_v2

STACKED_MODEL_PATH = backend_dir / "data" / "fusion_v2_stacked.joblib"
TRAIN_V2_PATH = backend_dir / "eval" / "data" / "train_v2.jsonl"

_STACKED_MODEL_CACHE = None

def extract_detection_features(text: str, source_type: str = "user_input") -> Dict[str, Any]:
    """
    Extracts multi-view, chunked heuristic and classifier features from text:
    - Preprocesses text into multiple views (original, normalized, decoded base64).
    - Computes max heuristic score across views.
    - Computes max classifier score across sliding chunks for all views.
    - Identifies trigger chunk.
    """
    views = get_views(text)
    
    # 1. Heuristics across views
    best_heur_score = 0.0
    best_matched_patterns = []
    best_attack_type = "none"
    
    for v in views:
        h_res = heuristic_detect(v)
        if h_res.score > best_heur_score:
            best_heur_score = float(h_res.score)
            best_matched_patterns = h_res.matched_patterns
            best_attack_type = h_res.attack_type
            
    # 2. Classifier v2 across views with chunking
    best_class_score = 0.0
    best_trigger_chunk = ""
    best_chunk_idx = 0
    total_chunks = 1
    
    for v in views:
        chunk_res = score_with_chunking(v, classify_v2, threshold_words=80, window_words=60, stride_words=30)
        if chunk_res["max_score"] > best_class_score:
            best_class_score = float(chunk_res["max_score"])
            best_trigger_chunk = chunk_res["trigger_chunk_text"]
            best_chunk_idx = chunk_res["trigger_chunk_index"]
            total_chunks = chunk_res["num_chunks"]
            
    # Text length feature
    log_len = float(math.log1p(len(text)))
    
    # One-hot source_type: [is_user_input, is_retrieved_doc, is_tool_output]
    is_user = 1.0 if source_type == "user_input" else 0.0
    is_doc = 1.0 if source_type == "retrieved_document" else 0.0
    is_tool = 1.0 if source_type == "tool_output" else 0.0
    
    feature_vector = np.array([
        best_heur_score,
        best_class_score,
        is_user,
        is_doc,
        is_tool,
        log_len
    ], dtype=np.float32)
    
    return {
        "heuristic_score": best_heur_score,
        "classifier_score": best_class_score,
        "matched_patterns": best_matched_patterns,
        "attack_type": best_attack_type,
        "trigger_chunk_text": best_trigger_chunk,
        "trigger_chunk_index": best_chunk_idx,
        "num_chunks": total_chunks,
        "feature_vector": feature_vector,
        "log_len": log_len
    }

def train_stacked_fusion_model(train_path: str | Path = TRAIN_V2_PATH, save_path: str | Path = STACKED_MODEL_PATH):
    """Trains Fusion Variant B (Stacked Logistic Regression) on train_v2 data."""
    print("Training Stacked Fusion Model (Variant B)...", flush=True)
    records = []
    with open(train_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))
                
    # Sample subset for speed if needed, or use all 3200
    # To avoid long extraction time, extract features
    X_feats = []
    y_labels = []
    
    print(f"Extracting features for {len(records)} samples...", flush=True)
    for idx, r in enumerate(records):
        if idx % 500 == 0:
            print(f"  Processed {idx}/{len(records)} samples...", flush=True)
        feat = extract_detection_features(r["text"], source_type=r.get("source_type", "user_input"))
        X_feats.append(feat["feature_vector"])
        y_labels.append(r["label"])
        
    X_arr = np.array(X_feats)
    y_arr = np.array(y_labels)
    
    clf = LogisticRegression(class_weight="balanced", max_iter=500, random_state=42)
    clf.fit(X_arr, y_arr)
    
    os.makedirs(Path(save_path).parent, exist_ok=True)
    joblib.dump({
        "model": clf,
        "feature_names": ["heur_score", "class_score", "is_user", "is_doc", "is_tool", "log_len"]
    }, save_path)
    print(f"Saved stacked fusion model to {save_path}", flush=True)
    
    global _STACKED_MODEL_CACHE
    _STACKED_MODEL_CACHE = clf
    return clf

def get_stacked_model():
    global _STACKED_MODEL_CACHE
    if _STACKED_MODEL_CACHE is not None:
        return _STACKED_MODEL_CACHE
        
    if not STACKED_MODEL_PATH.exists():
        return train_stacked_fusion_model()
        
    saved = joblib.load(STACKED_MODEL_PATH)
    _STACKED_MODEL_CACHE = saved["model"]
    return _STACKED_MODEL_CACHE

def analyze_v2_fusion_a(
    text: str,
    source_type: str = "user_input",
    threshold: float = 0.50,
    per_source_thresholds: Optional[Dict[str, float]] = None
) -> Dict[str, Any]:
    """
    Fusion Variant A (Rule-based):
    Flag if heuristic_score >= 0.30 OR classifier_score >= t.
    Supports global threshold t or per-source_type thresholds.
    """
    feats = extract_detection_features(text, source_type=source_type)
    h_score = feats["heuristic_score"]
    c_score = feats["classifier_score"]
    
    # Determine effective classifier threshold
    eff_thresh = threshold
    if per_source_thresholds and source_type in per_source_thresholds:
        eff_thresh = per_source_thresholds[source_type]
        
    flagged = (h_score >= 0.30) or (c_score >= eff_thresh)
    
    # Combined final score: max of normalized signals or calibrated combination
    final_score = max(h_score, c_score)
    
    severity = "none"
    if flagged:
        severity = "high" if final_score >= 0.70 else "low"
        
    return {
        "final_score": round(final_score, 4),
        "flagged": flagged,
        "severity": severity,
        "attack_type": feats["attack_type"],
        "heuristic_score": h_score,
        "classifier_score": c_score,
        "matched_patterns": feats["matched_patterns"],
        "trigger_chunk_text": feats["trigger_chunk_text"],
        "trigger_chunk_index": feats["trigger_chunk_index"],
        "num_chunks": feats["num_chunks"],
        "variant": "fusion_a_rule_based",
        "threshold_used": eff_thresh
    }

def analyze_v2_fusion_b(
    text: str,
    source_type: str = "user_input",
    threshold: float = 0.50
) -> Dict[str, Any]:
    """
    Fusion Variant B (Stacked Logistic Regression):
    Passes [heur, class_chunk, is_user, is_doc, is_tool, log_len] into meta-classifier.
    """
    feats = extract_detection_features(text, source_type=source_type)
    stacked_model = get_stacked_model()
    
    x = feats["feature_vector"].reshape(1, -1)
    prob = float(stacked_model.predict_proba(x)[0, 1])
    flagged = prob >= threshold
    
    severity = "none"
    if flagged:
        severity = "high" if prob >= 0.70 else "low"
        
    return {
        "final_score": round(prob, 4),
        "flagged": flagged,
        "severity": severity,
        "attack_type": feats["attack_type"],
        "heuristic_score": feats["heuristic_score"],
        "classifier_score": feats["classifier_score"],
        "matched_patterns": feats["matched_patterns"],
        "trigger_chunk_text": feats["trigger_chunk_text"],
        "trigger_chunk_index": feats["trigger_chunk_index"],
        "num_chunks": feats["num_chunks"],
        "variant": "fusion_b_stacked",
        "threshold_used": threshold
    }
