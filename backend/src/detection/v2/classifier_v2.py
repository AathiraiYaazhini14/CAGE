import json
import os
from pathlib import Path
from typing import Dict, Any, Tuple
import joblib
import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, log_loss
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import FeatureUnion, Pipeline

DATA_DIR = Path(__file__).resolve().parent.parent.parent.parent / "eval" / "data"
TRAIN_V2_PATH = DATA_DIR / "train_v2.jsonl"
MODEL_SAVE_PATH = Path(__file__).resolve().parent.parent.parent.parent / "data" / "classifier_v2.joblib"

_MODEL_V2_CACHE = None

def get_feature_pipeline() -> FeatureUnion:
    """Builds word (1-2) and character_wb (3-5) n-gram TF-IDF feature union."""
    return FeatureUnion([
        ("word", TfidfVectorizer(
            ngram_range=(1, 2),
            min_df=2,
            max_features=25000,
            sublinear_tf=True
        )),
        ("char_wb", TfidfVectorizer(
            analyzer="char_wb",
            ngram_range=(3, 5),
            min_df=3,
            max_features=35000,
            sublinear_tf=True
        ))
    ])

def train_classifier_v2(train_path: str | Path = TRAIN_V2_PATH, save_path: str | Path = MODEL_SAVE_PATH) -> Dict[str, Any]:
    """
    Trains Classifier V2 using word+char_wb TF-IDF, Logistic Regression (balanced),
    and Platt probability calibration. Hyperparameters evaluated via 5-fold GroupKFold by template_id.
    """
    print(f"Loading training data from {train_path}...", flush=True)
    records = []
    with open(train_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))
                
    df = pd.DataFrame(records)
    X = df["text"].astype(str)
    y = df["label"].astype(int)
    groups = df["template_id"].astype(str)
    
    print(f"Dataset: {len(df)} samples across {df['template_id'].nunique()} unique template groups.", flush=True)
    
    # 5-fold GroupKFold hyperparameter sweep
    c_candidates = [0.5, 1.0, 3.0, 5.0, 10.0]
    best_c = 1.0
    best_cv_f1 = -1.0
    cv_records = []
    
    gkf = GroupKFold(n_splits=5)
    
    print("Evaluating C hyperparameter candidates with 5-fold GroupKFold...", flush=True)
    for c_val in c_candidates:
        fold_f1s = []
        fold_accs = []
        oof_preds = np.zeros(len(df))
        oof_probs = np.zeros(len(df))
        
        for fold, (train_idx, val_idx) in enumerate(gkf.split(X, y, groups)):
            X_tr, y_tr = X.iloc[train_idx], y.iloc[train_idx]
            X_val, y_val = X.iloc[val_idx], y.iloc[val_idx]
            
            vec = get_feature_pipeline()
            X_tr_vec = vec.fit_transform(X_tr)
            X_val_vec = vec.transform(X_val)
            
            clf = LogisticRegression(C=c_val, class_weight="balanced", max_iter=500, random_state=42)
            clf.fit(X_tr_vec, y_tr)
            
            val_probs = clf.predict_proba(X_val_vec)[:, 1]
            val_preds = (val_probs >= 0.5).astype(int)
            
            fold_f1s.append(f1_score(y_val, val_preds, zero_division=0))
            fold_accs.append(accuracy_score(y_val, val_preds))
            oof_probs[val_idx] = val_probs
            
        mean_f1 = float(np.mean(fold_f1s))
        mean_acc = float(np.mean(fold_accs))
        oof_loss = float(log_loss(y, oof_probs))
        
        cv_records.append({
            "C": c_val,
            "mean_cv_f1": round(mean_f1, 4),
            "mean_cv_acc": round(mean_acc, 4),
            "log_loss": round(oof_loss, 4)
        })
        print(f"  C={c_val:4.1f} | Mean CV F1: {mean_f1:.4f} | Accuracy: {mean_acc:.4f} | LogLoss: {oof_loss:.4f}", flush=True)
        
        if mean_f1 > best_cv_f1:
            best_cv_f1 = mean_f1
            best_c = c_val
            
    print(f"Selected Best C: {best_c} (CV F1: {best_cv_f1:.4f})", flush=True)
    
    # Final Fit on entire dataset with Calibration
    print("Fitting full feature pipeline and calibrated classifier...", flush=True)
    final_vec = get_feature_pipeline()
    X_vec = final_vec.fit_transform(X)
    
    base_clf = LogisticRegression(C=best_c, class_weight="balanced", max_iter=600, random_state=42)
    calibrated_clf = CalibratedClassifierCV(estimator=base_clf, method="sigmoid", cv=5)
    calibrated_clf.fit(X_vec, y)
    
    # Save model and vectorizer
    os.makedirs(Path(save_path).parent, exist_ok=True)
    joblib.dump({
        "vectorizer": final_vec,
        "model": calibrated_clf,
        "best_C": best_c,
        "cv_results": cv_records
    }, save_path)
    print(f"Successfully saved Classifier V2 to {save_path}", flush=True)
    
    global _MODEL_V2_CACHE
    _MODEL_V2_CACHE = (final_vec, calibrated_clf)
    
    return {
        "best_C": best_c,
        "best_cv_f1": best_cv_f1,
        "cv_records": cv_records
    }

def _get_model_v2() -> Tuple[FeatureUnion, Any]:
    global _MODEL_V2_CACHE
    if _MODEL_V2_CACHE is not None:
        return _MODEL_V2_CACHE
        
    if not MODEL_SAVE_PATH.exists():
        train_classifier_v2()
        
    saved = joblib.load(MODEL_SAVE_PATH)
    _MODEL_V2_CACHE = (saved["vectorizer"], saved["model"])
    return _MODEL_V2_CACHE

def classify_v2(text: str) -> float:
    """
    Predicts calibrated prompt injection probability using Classifier V2.
    Returns float score between 0.0 and 1.0.
    """
    if not text or not text.strip():
        return 0.0
        
    try:
        vec, model = _get_model_v2()
        x_vec = vec.transform([text])
        prob = float(model.predict_proba(x_vec)[0, 1])
        return min(1.0, max(0.0, round(prob, 4)))
    except Exception as e:
        print(f"[Classifier V2 Warning] Prediction error: {e}")
        return 0.0

if __name__ == "__main__":
    train_classifier_v2()
