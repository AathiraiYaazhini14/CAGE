import json
import re
import statistics
import time
from pathlib import Path
from typing import Dict, Any, List, Set, Tuple
import numpy as np
import pandas as pd

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
DEV_PATH = BACKEND_DIR / "eval" / "data" / "dev.jsonl"
TEST_PATH = BACKEND_DIR / "eval" / "data" / "test.jsonl"

def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))
    return records

def normalize_family_text(text: str) -> str:
    t = text.lower()
    t = re.sub(r'https?://\S+|www\.\S+', '<url>', t)
    t = re.sub(r'[\w\.-]+@[\w\.-]+\.\w+', '<email>', t)
    t = re.sub(r'\b[0-9a-fA-F]{8,}\b', '<id>', t)
    t = re.sub(r'\b[0-9a-fA-F-]{12,}\b', '<id>', t)
    t = re.sub(r'\d+', '<num>', t)
    t = re.sub(r'\s+', ' ', t).strip()
    return t

def get_char_5grams(text: str) -> Set[str]:
    if len(text) < 5:
        return {text}
    return {text[i:i+5] for i in range(len(text) - 4)}

class UnionFind:
    def __init__(self, n: int):
        self.parent = list(range(n))
        self.rank = [0] * n

    def find(self, i: int) -> int:
        if self.parent[i] != i:
            self.parent[i] = self.find(self.parent[i])
        return self.parent[i]

    def union(self, i: int, j: int):
        root_i = self.find(i)
        root_j = self.find(j)
        if root_i != root_j:
            if self.rank[root_i] < self.rank[root_j]:
                self.parent[root_i] = root_j
            elif self.rank[root_i] > self.rank[root_j]:
                self.parent[root_j] = root_i
            else:
                self.parent[root_j] = root_i
                self.rank[root_i] += 1

def cluster_benchmark_into_families(
    all_samples: List[Dict[str, Any]],
    jaccard_threshold: float = 0.70
) -> Tuple[List[int], Dict[int, List[int]]]:
    n = len(all_samples)
    print(f"Clustering {n} benchmark samples into families (Jaccard threshold = {jaccard_threshold})...", flush=True)
    
    # Pre-extract n-grams
    ngram_sets = []
    ngram_lens = []
    for s in all_samples:
        norm = normalize_family_text(s["text"])
        ng = get_char_5grams(norm)
        ngram_sets.append(ng)
        ngram_lens.append(len(ng))
        
    uf = UnionFind(n)
    
    # Fast pairwise Jaccard with length pruning
    edge_count = 0
    for i in range(n):
        s_i = ngram_sets[i]
        len_i = ngram_lens[i]
        min_len_j = len_i * jaccard_threshold
        max_len_j = len_i / jaccard_threshold
        
        for j in range(i + 1, n):
            len_j = ngram_lens[j]
            if len_j < min_len_j or len_j > max_len_j:
                continue
                
            # Compute Jaccard
            inter = len(s_i & ngram_sets[j])
            union = len_i + len_j - inter
            jacc = inter / union if union > 0 else 0.0
            
            if jacc >= jaccard_threshold:
                uf.union(i, j)
                edge_count += 1
                
    # Map to families
    family_map: Dict[int, List[int]] = {}
    sample_families = []
    for i in range(n):
        root = uf.find(i)
        sample_families.append(root)
        if root not in family_map:
            family_map[root] = []
        family_map[root].append(i)
        
    print(f"Created {len(family_map)} families connected by {edge_count} pairwise links.", flush=True)
    return sample_families, family_map

def run_task2(test_df: pd.DataFrame, dev_df: pd.DataFrame):
    print("=" * 80)
    print("TASK 2: TEMPLATE-FAMILY ANALYSIS AND CLUSTER BOOTSTRAP")
    print("=" * 80)
    
    dev_data = dev_df.to_dict(orient="records")
    test_data = test_df.to_dict(orient="records")
    
    all_samples = dev_data + test_data
    n_dev = len(dev_data)
    n_test = len(test_data)
    
    sample_families, family_map = cluster_benchmark_into_families(all_samples, jaccard_threshold=0.70)
    
    # Attach family_id to all samples
    for idx, fam_id in enumerate(sample_families):
        all_samples[idx]["family_id"] = fam_id
        
    dev_families = sample_families[:n_dev]
    test_families = sample_families[n_dev:]
    
    test_df_copy = test_df.copy()
    test_df_copy["family_id"] = test_families
    
    # 1. Largest 10 Families
    family_stats = []
    for fam_id, member_indices in family_map.items():
        members = [all_samples[idx] for idx in member_indices]
        total_sz = len(members)
        inj_cnt = sum(1 for m in members if m["label"] == 1)
        ben_cnt = sum(1 for m in members if m["label"] == 0)
        test_cnt = sum(1 for idx in member_indices if idx >= n_dev)
        dev_cnt = total_sz - test_cnt
        dom_cat = members[0]["category"]
        dom_src = members[0]["source_type"]
        sample_txt = members[0]["text"][:80].replace("\n", " ") + "..."
        family_stats.append({
            "family_id": fam_id,
            "total_size": total_sz,
            "dev_size": dev_cnt,
            "test_size": test_cnt,
            "injections": inj_cnt,
            "benign": ben_cnt,
            "dominant_category": dom_cat,
            "dominant_source": dom_src,
            "example_snippet": sample_txt
        })
        
    df_fam_stats = pd.DataFrame(family_stats).sort_values("total_size", ascending=False)
    top_10_families = df_fam_stats.head(10).to_dict(orient="records")
    
    # 2. Test Error Concentration across Families
    test_fps = test_df_copy[(test_df_copy["label"] == 0) & (test_df_copy["pred"] == 1)]
    test_fns = test_df_copy[(test_df_copy["label"] == 1) & (test_df_copy["pred"] == 0)]
    
    total_test_fps = len(test_fps)
    total_test_fns = len(test_fns)
    
    fp_family_counts = test_fps["family_id"].value_counts().to_dict()
    fn_family_counts = test_fns["family_id"].value_counts().to_dict()
    
    fp_concentration = []
    for fam_id, cnt in sorted(fp_family_counts.items(), key=lambda x: x[1], reverse=True):
        pct = (cnt / total_test_fps) * 100 if total_test_fps > 0 else 0.0
        fam_info = df_fam_stats[df_fam_stats["family_id"] == fam_id].iloc[0]
        fp_concentration.append({
            "family_id": fam_id,
            "fp_count": cnt,
            "fp_share_pct": round(pct, 2),
            "dominant_category": fam_info["dominant_category"],
            "dominant_source": fam_info["dominant_source"],
            "example_snippet": fam_info["example_snippet"]
        })
        
    fn_concentration = []
    for fam_id, cnt in sorted(fn_family_counts.items(), key=lambda x: x[1], reverse=True):
        pct = (cnt / total_test_fns) * 100 if total_test_fns > 0 else 0.0
        fam_info = df_fam_stats[df_fam_stats["family_id"] == fam_id].iloc[0]
        fn_concentration.append({
            "family_id": fam_id,
            "fn_count": cnt,
            "fn_share_pct": round(pct, 2),
            "dominant_category": fam_info["dominant_category"],
            "dominant_source": fam_info["dominant_source"],
            "example_snippet": fam_info["example_snippet"]
        })
        
    # 3. Recompute Fusion B metrics with families weighted equally (macro-weighted)
    # Each family present in test receives equal aggregate weight of 1.0.
    test_fam_sizes = test_df_copy["family_id"].value_counts().to_dict()
    test_df_copy["family_test_size"] = test_df_copy["family_id"].map(test_fam_sizes)
    test_df_copy["macro_weight"] = 1.0 / test_df_copy["family_test_size"]
    
    # Weighted confusion matrix
    w_tp = test_df_copy[(test_df_copy["label"] == 1) & (test_df_copy["pred"] == 1)]["macro_weight"].sum()
    w_fp = test_df_copy[(test_df_copy["label"] == 0) & (test_df_copy["pred"] == 1)]["macro_weight"].sum()
    w_tn = test_df_copy[(test_df_copy["label"] == 0) & (test_df_copy["pred"] == 0)]["macro_weight"].sum()
    w_fn = test_df_copy[(test_df_copy["label"] == 1) & (test_df_copy["pred"] == 0)]["macro_weight"].sum()
    
    macro_acc = (w_tp + w_tn) / (w_tp + w_fp + w_tn + w_fn)
    macro_prec = w_tp / (w_tp + w_fp) if (w_tp + w_fp) > 0 else 0.0
    macro_rec = w_tp / (w_tp + w_fn) if (w_tp + w_fn) > 0 else 0.0
    macro_f1 = (2 * macro_prec * macro_rec) / (macro_prec + macro_rec) if (macro_prec + macro_rec) > 0 else 0.0
    macro_fpr = w_fp / (w_fp + w_tn) if (w_fp + w_tn) > 0 else 0.0
    
    macro_metrics = {
        "weighted_tp": round(float(w_tp), 2),
        "weighted_fp": round(float(w_fp), 2),
        "weighted_tn": round(float(w_tn), 2),
        "weighted_fn": round(float(w_fn), 2),
        "macro_accuracy": round(float(macro_acc), 4),
        "macro_precision": round(float(macro_prec), 4),
        "macro_recall": round(float(macro_rec), 4),
        "macro_f1": round(float(macro_f1), 4),
        "macro_fpr": round(float(macro_fpr), 4)
    }
    
    # 4. 95% Cluster Bootstrap Confidence Intervals by Family
    print("Running 1,000 cluster bootstrap iterations by family on test set...", flush=True)
    rng = np.random.RandomState(42)
    unique_test_families = list(test_fam_sizes.keys())
    m_clusters = len(unique_test_families)
    
    # Group test samples by family
    family_to_test_rows = {}
    for fam_id, grp in test_df_copy.groupby("family_id"):
        family_to_test_rows[fam_id] = grp[["label", "pred"]].to_dict(orient="records")
        
    boot_accs, boot_precs, boot_recs, boot_f1s, boot_fprs = [], [], [], [], []
    
    for _ in range(1000):
        sampled_fam_ids = rng.choice(unique_test_families, size=m_clusters, replace=True)
        boot_y_true = []
        boot_y_pred = []
        for fid in sampled_fam_ids:
            for row in family_to_test_rows[fid]:
                boot_y_true.append(row["label"])
                boot_y_pred.append(row["pred"])
                
        # Calc metrics for this bootstrap sample
        tp = sum(1 for yt, yp in zip(boot_y_true, boot_y_pred) if yt == 1 and yp == 1)
        fp = sum(1 for yt, yp in zip(boot_y_true, boot_y_pred) if yt == 0 and yp == 1)
        tn = sum(1 for yt, yp in zip(boot_y_true, boot_y_pred) if yt == 0 and yp == 0)
        fn = sum(1 for yt, yp in zip(boot_y_true, boot_y_pred) if yt == 1 and yp == 0)
        
        acc = (tp + tn) / len(boot_y_true) if boot_y_true else 0.0
        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * prec * rec) / (prec + rec) if (prec + rec) > 0 else 0.0
        fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
        
        boot_accs.append(acc)
        boot_precs.append(prec)
        boot_recs.append(rec)
        boot_f1s.append(f1)
        boot_fprs.append(fpr)
        
    ci_95 = {
        "accuracy": [round(float(np.percentile(boot_accs, 2.5)), 4), round(float(np.percentile(boot_accs, 97.5)), 4)],
        "precision": [round(float(np.percentile(boot_precs, 2.5)), 4), round(float(np.percentile(boot_precs, 97.5)), 4)],
        "recall": [round(float(np.percentile(boot_recs, 2.5)), 4), round(float(np.percentile(boot_recs, 97.5)), 4)],
        "f1": [round(float(np.percentile(boot_f1s, 2.5)), 4), round(float(np.percentile(boot_f1s, 97.5)), 4)],
        "fpr": [round(float(np.percentile(boot_fprs, 2.5)), 4), round(float(np.percentile(boot_fprs, 97.5)), 4)]
    }
    
    print("\nTASK 2 SUMMARY:")
    print(f"Total Families Identified: {len(family_map)} (Test Families: {len(unique_test_families)})")
    print(f"Standard Test Metrics: F1 = 0.8693, Recall = 0.8238, FPR = 0.0714")
    print(f"Family-Macro Metrics : F1 = {macro_f1:.4f}, Recall = {macro_rec:.4f}, FPR = {macro_fpr:.4f}")
    print(f"95% Cluster Bootstrap CIs:")
    print(f"  Precision: [{ci_95['precision'][0]:.4f}, {ci_95['precision'][1]:.4f}]")
    print(f"  Recall   : [{ci_95['recall'][0]:.4f}, {ci_95['recall'][1]:.4f}]")
    print(f"  F1 Score : [{ci_95['f1'][0]:.4f}, {ci_95['f1'][1]:.4f}]")
    print(f"  FPR      : [{ci_95['fpr'][0]:.4f}, {ci_95['fpr'][1]:.4f}]")
    
    return {
        "num_families_total": len(family_map),
        "num_families_test": len(unique_test_families),
        "top_10_families": top_10_families,
        "fp_concentration": fp_concentration,
        "fn_concentration": fn_concentration,
        "macro_metrics": macro_metrics,
        "cluster_bootstrap_95ci": ci_95
    }

if __name__ == "__main__":
    from validate_fusion_b import run_task1
    res1 = run_task1()
    res2 = run_task2(res1["test_df"], res1["dev_df"])
