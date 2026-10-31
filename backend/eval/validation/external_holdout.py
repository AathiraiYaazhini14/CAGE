import io
import json
import re
import ssl
import urllib.request
from pathlib import Path
from typing import Dict, Any, List, Set, Tuple
import pandas as pd

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
import sys
sys.path.insert(0, str(BACKEND_DIR))

from src.detection.v2.fusion_v2 import analyze_v2_fusion_b

TRAIN_V2_PATH = BACKEND_DIR / "eval" / "data" / "train_v2.jsonl"
DEV_PATH = BACKEND_DIR / "eval" / "data" / "dev.jsonl"
TEST_PATH = BACKEND_DIR / "eval" / "data" / "test.jsonl"
HOLDOUT_PATH = BACKEND_DIR / "eval" / "data" / "holdout_external.jsonl"

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

def get_char_5grams(text: str) -> Set[str]:
    t = text.lower().strip()
    if len(t) < 5:
        return {t}
    return {t[i:i+5] for i in range(len(t) - 4)}

def build_external_holdout_dataset() -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    print("=" * 80)
    print("TASK 5: DOWNLOADING AND CONSTRUCTING EXTERNAL HOLDOUT BENCHMARK")
    print("=" * 80)
    
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    dataset_metadata = []
    raw_holdout_samples = []
    
    # 1. Download XSTest (CC-BY 4.0) for hard benign negatives
    xstest_url = "https://raw.githubusercontent.com/paul-rottger/xstest/main/xstest_prompts.csv"
    print(f"1. Downloading XSTest from {xstest_url} (License: CC-BY 4.0)...", flush=True)
    df_xs = None
    for attempt in range(3):
        try:
            req = urllib.request.Request(xstest_url, headers=headers)
            with urllib.request.urlopen(req, context=ctx, timeout=15) as r:
                df_xs = pd.read_csv(io.BytesIO(r.read()))
            break
        except Exception as e:
            print(f"   [Retry {attempt+1}/3] Error downloading XSTest: {e}", flush=True)
            import time; time.sleep(2)
            
    if df_xs is not None:
        safe_xs = df_xs[df_xs["label"] == "safe"]
        for _, row in safe_xs.iterrows():
            raw_holdout_samples.append({
                "origin": "public",
                "source_name": "xstest",
                "text": str(row["prompt"]).strip(),
                "label": 0,
                "language": "en",
                "focus": row.get("focus", "")
            })
        dataset_metadata.append({
            "source_name": "xstest",
            "url": xstest_url,
            "license": "CC-BY 4.0",
            "samples_downloaded": len(safe_xs),
            "label_type": "safe (benign hard negatives)"
        })
        print(f"   [SUCCESS] Loaded {len(safe_xs)} benign hard-negative samples from XSTest.", flush=True)
    else:
        print("   [FAILED] Could not download XSTest after 3 attempts.", flush=True)
        
    # 2. Download Jailbreak_LLMs (MIT License) for real-world prompt injections / jailbreaks
    jb_url = "https://raw.githubusercontent.com/verazuo/jailbreak_llms/main/data/prompts/jailbreak_prompts_2023_12_25.csv"
    print(f"2. Downloading Jailbreak_LLMs from {jb_url} (License: MIT)...", flush=True)
    df_jb = None
    for attempt in range(3):
        try:
            req = urllib.request.Request(jb_url, headers=headers)
            with urllib.request.urlopen(req, context=ctx, timeout=25) as r:
                df_jb = pd.read_csv(io.BytesIO(r.read()))
            break
        except Exception as e:
            print(f"   [Retry {attempt+1}/3] Error downloading Jailbreak_LLMs: {e}", flush=True)
            import time; time.sleep(2)
            
    if df_jb is not None:
        jb_subset = df_jb.sample(n=min(250, len(df_jb)), random_state=42)
        for _, row in jb_subset.iterrows():
            raw_holdout_samples.append({
                "origin": "public",
                "source_name": "jailbreak_llms",
                "text": str(row["prompt"]).strip(),
                "label": 1,
                "language": "en",
                "community": str(row.get("community", ""))
            })
        dataset_metadata.append({
            "source_name": "jailbreak_llms",
            "url": jb_url,
            "license": "MIT",
            "samples_downloaded": len(jb_subset),
            "label_type": "jailbreak (prompt injection attacks)"
        })
        print(f"   [SUCCESS] Loaded {len(jb_subset)} adversarial injection samples from Jailbreak_LLMs.", flush=True)
    else:
        print("   [FAILED] Could not download Jailbreak_LLMs after 3 attempts.", flush=True)
        
    print(f"\nTotal raw external holdout samples collected: {len(raw_holdout_samples)}")
    
    # Deduplication against train_v2, dev, and test
    print("Deduplicating external holdout against train_v2, dev, and test sets...", flush=True)
    benchmark_texts = []
    for p in [TRAIN_V2_PATH, DEV_PATH, TEST_PATH]:
        for item in load_jsonl(p):
            benchmark_texts.append(item["text"])
            
    norm_bench_exact = {t.lower().strip() for t in benchmark_texts}
    bench_ngrams = [get_char_5grams(t) for t in benchmark_texts]
    bench_lens = [len(ng) for ng in bench_ngrams]
    
    clean_holdout = []
    removed_exact = 0
    removed_near = 0
    
    for item in raw_holdout_samples:
        txt = item["text"]
        norm_txt = txt.lower().strip()
        
        # 1. Exact match check
        if norm_txt in norm_bench_exact:
            removed_exact += 1
            continue
            
        # 2. Near-duplicate check (char 5-gram Jaccard > 0.80)
        item_ng = get_char_5grams(txt)
        item_len = len(item_ng)
        is_near_dup = False
        
        for b_ng, b_len in zip(bench_ngrams, bench_lens):
            if b_len < item_len * 0.8 or b_len > item_len / 0.8:
                continue
            inter = len(item_ng & b_ng)
            union = item_len + b_len - inter
            jacc = inter / union if union > 0 else 0.0
            if jacc > 0.80:
                is_near_dup = True
                break
                
        if is_near_dup:
            removed_near += 1
            continue
            
        clean_holdout.append({
            "origin": item["origin"],
            "source_name": item["source_name"],
            "text": item["text"],
            "label": item["label"],
            "language": item["language"]
        })
        
    print(f"Deduplication results: Removed {removed_exact} exact duplicates, {removed_near} near-duplicates.")
    print(f"Final clean external holdout count: {len(clean_holdout)} (Injections: {sum(1 for c in clean_holdout if c['label'] == 1)}, Benign: {sum(1 for c in clean_holdout if c['label'] == 0)})")
    
    # Save to holdout_external.jsonl
    HOLDOUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(HOLDOUT_PATH, "w", encoding="utf-8") as f:
        for item in clean_holdout:
            f.write(json.dumps(item) + "\n")
    print(f"Saved external holdout dataset to: {HOLDOUT_PATH}", flush=True)
    
    audit_summary = {
        "metadata": dataset_metadata,
        "raw_total": len(raw_holdout_samples),
        "removed_exact": removed_exact,
        "removed_near": removed_near,
        "final_total": len(clean_holdout),
        "injections_count": sum(1 for c in clean_holdout if c["label"] == 1),
        "benign_count": sum(1 for c in clean_holdout if c["label"] == 0)
    }
    return clean_holdout, audit_summary

def run_task5():
    clean_holdout, audit_summary = build_external_holdout_dataset()
    
    print("\n--- Evaluating Frozen Fusion B on External Holdout Dataset ---", flush=True)
    holdout_y = [c["label"] for c in clean_holdout]
    holdout_preds = []
    holdout_scores = []
    
    for c in clean_holdout:
        res = analyze_v2_fusion_b(c["text"], source_type="user_input", threshold=0.85)
        p = 1 if res["flagged"] else 0
        holdout_preds.append(p)
        holdout_scores.append(res["final_score"])
        c["pred"] = p
        c["score"] = res["final_score"]
        
    overall_metrics = calc_metrics(holdout_y, holdout_preds)
    
    # Breakdown by source
    df_holdout = pd.DataFrame(clean_holdout)
    source_breakdown = {}
    if not df_holdout.empty and "source_name" in df_holdout.columns:
        for src, grp in df_holdout.groupby("source_name"):
            source_breakdown[src] = calc_metrics(grp["label"].tolist(), grp["pred"].tolist())
        
    print(f"\nFrozen Fusion B Performance on External Holdout (Threshold = 0.85):")
    print(f"  Total Samples : {overall_metrics['total']}")
    print(f"  Accuracy      : {overall_metrics['accuracy']:.4f}")
    print(f"  Precision     : {overall_metrics['precision']:.4f}")
    print(f"  Recall        : {overall_metrics['recall']:.4f} ({overall_metrics['tp']}/{overall_metrics['tp'] + overall_metrics['fn']})")
    print(f"  F1 Score      : {overall_metrics['f1']:.4f}")
    print(f"  FPR           : {overall_metrics['fpr']:.4f} ({overall_metrics['fp']}/{overall_metrics['fp'] + overall_metrics['tn']})")
    
    print("\nBreakdown by Dataset Source:")
    for src, m in source_breakdown.items():
        print(f"  {src:18s} (Total={m['total']}): Prec={m['precision']:.4f}, Rec={m['recall']:.4f}, F1={m['f1']:.4f}, FPR={m['fpr']:.4f}")
        
    return {
        "audit_summary": audit_summary,
        "overall_metrics": overall_metrics,
        "source_breakdown": source_breakdown,
        "holdout_samples": clean_holdout
    }

if __name__ == "__main__":
    res = run_task5()
