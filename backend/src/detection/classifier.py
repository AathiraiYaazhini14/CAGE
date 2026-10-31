import os
from pathlib import Path
from typing import Tuple, Dict, Any
import pandas as pd
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, f1_score

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
CSV_PATH = DATA_DIR / "training_samples.csv"
MODEL_PATH = DATA_DIR / "classifier_model.joblib"

_MODEL_CACHE: Tuple[TfidfVectorizer, LogisticRegression] | None = None


def train_classifier(csv_path: str | Path = CSV_PATH, model_save_path: str | Path = MODEL_PATH) -> Dict[str, float]:
    """
    Trains TF-IDF + Logistic Regression classifier on prompt dataset.
    Saves combined dict {'vectorizer': vec, 'model': model} to disk via joblib.
    Returns metrics dict with accuracy and f1 score.
    """
    df = pd.read_csv(csv_path)
    X = df['text'].astype(str)
    y = df['label'].astype(int)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=1)
    X_train_vec = vectorizer.fit_transform(X_train)
    X_test_vec = vectorizer.transform(X_test)

    model = LogisticRegression(C=1.0, max_iter=200, random_state=42)
    model.fit(X_train_vec, y_train)

    y_pred = model.predict(X_test_vec)
    acc = float(accuracy_score(y_test, y_pred))
    f1 = float(f1_score(y_test, y_pred, zero_division=0))

    os.makedirs(Path(model_save_path).parent, exist_ok=True)
    joblib.dump({"vectorizer": vectorizer, "model": model}, model_save_path)

    global _MODEL_CACHE
    _MODEL_CACHE = (vectorizer, model)

    return {"accuracy": acc, "f1": f1}


def _get_model() -> Tuple[TfidfVectorizer, LogisticRegression]:
    """Loads model from cache or disk."""
    global _MODEL_CACHE
    if _MODEL_CACHE is not None:
        return _MODEL_CACHE

    if not MODEL_PATH.exists():
        train_classifier()

    saved_data = joblib.load(MODEL_PATH)
    _MODEL_CACHE = (saved_data["vectorizer"], saved_data["model"])
    return _MODEL_CACHE


def classify(text: str) -> float:
    """
    Predicts prompt injection probability for given text using trained classifier.
    Returns float score between 0.0 and 1.0.
    """
    if not text or not text.strip():
        return 0.0

    try:
        vectorizer, model = _get_model()
        vec_text = vectorizer.transform([text])
        probabilities = model.predict_proba(vec_text)[0]
        # Class 1 is injection probability
        injection_prob = float(probabilities[1])
        return min(1.0, max(0.0, round(injection_prob, 4)))
    except Exception as e:
        print(f"[Classifier Warning] Error during classification: {e}")
        return 0.0


if __name__ == "__main__":
    print("Training CAGE prompt injection classifier...")
    metrics = train_classifier()
    print(f"[OK] Training completed. Test Accuracy: {metrics['accuracy']:.4f} | Test F1: {metrics['f1']:.4f}")
    print(f"Model saved to: {MODEL_PATH}")
