"""
CAGE Production v2_final Prompt Injection Defense Module (PREVIOUS CANDIDATE B VERSION).
Architecture: Candidate B: Ablated Stacker [heur, class]
Multi-tier Defense: allow (< 0.9), isolate ([0.9, 0.945)), block (>= 0.945)
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
        return {
            "verdict": "allow",
            "score": 0.0,
            "tier": "allow",
            "triggered_chunk": "",
            "matched_patterns": []
        }
        
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
        
    return {
        "verdict": verdict,
        "score": final_score,
        "tier": tier,
        "triggered_chunk": feats.get("trigger_chunk_text", ""),
        "matched_patterns": feats.get("matched_patterns", [])
    }
