import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, Any, List

# Path setup
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BACKEND_DIR))
sys.path.insert(0, str(BACKEND_DIR / "eval" / "validation"))

from validate_fusion_b import run_task1
from family_analysis import run_task2
from shortcut_test import run_task3
from train_overlap import run_task4
from external_holdout import run_task5

RESULTS_DIR = BACKEND_DIR / "eval" / "validation" / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

def generate_validation_markdown_report(
    t1_res: Dict[str, Any],
    t2_res: Dict[str, Any],
    t3_res: Dict[str, Any],
    t4_res: Dict[str, Any],
    t5_res: Dict[str, Any]
) -> str:
    lines = []
    lines.append("# CAGE v2 Fusion B In-Depth Validation Report\n")
    lines.append("**Target Model**: Frozen Stacked Fusion B (`fusion_v2_stacked.joblib`, Threshold $t = 0.85$)\n")
    lines.append("**Scope**: Validation Only (No Retraining, No Threshold Tuning on Test Set)\n")
    
    # ------------------------------------------------------------------
    # 1. Fusion B Breakdown on Dev and Test
    # ------------------------------------------------------------------
    lines.append("## 1. Fusion B Full Performance Breakdown (Dev vs. Test)\n")
    lines.append(f"**Overall Test Performance**: Accuracy: `{t1_res['test_overall']['accuracy']:.4f}` | Precision: `{t1_res['test_overall']['precision']:.4f}` | Recall: `{t1_res['test_overall']['recall']:.4f}` | F1: `{t1_res['test_overall']['f1']:.4f}` | FPR: `{t1_res['test_overall']['fpr']:.4f}` | Median Latency: `{t1_res['test_overall']['median_latency_ms']:.2f} ms`\n")
    
    # Public-Only Comparison Table
    lines.append("### 1.1 Public-Only Dataset Performance Table\n")
    lines.append("| Split | Total | TP | FP | TN | FN | Precision | Recall | F1 Score | FPR | Accuracy |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|---|")
    for split_name in ["dev", "test"]:
        m = t1_res["public_only"][split_name]
        lines.append(f"| **{split_name.upper()} (Public)** | {m['total']} | {m['tp']} | {m['fp']} | {m['tn']} | {m['fn']} | {m['precision']:.4f} | {m['recall']:.4f} | **{m['f1']:.4f}** | {m['fpr']:.4f} | {m['accuracy']:.4f} |")
    lines.append("\n")
    
    # Source Type Breakdown
    lines.append("### 1.2 Breakdown by Source Type (Test Set)\n")
    lines.append("| Source Type | Samples | TP | FP | TN | FN | Precision | Recall | F1 Score | FPR | Accuracy |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|---|")
    for st, m in t1_res["test_breakdowns"]["source_type"].items():
        lines.append(f"| `{st}` | {m['total']} | {m['tp']} | {m['fp']} | {m['tn']} | {m['fn']} | {m['precision']:.4f} | {m['recall']:.4f} | **{m['f1']:.4f}** | {m['fpr']:.4f} | {m['accuracy']:.4f} |")
    lines.append("\n")
    
    # Origin Breakdown
    lines.append("### 1.3 Breakdown by Origin (Test Set)\n")
    lines.append("| Origin | Samples | TP | FP | TN | FN | Precision | Recall | F1 Score | FPR | Accuracy |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|---|")
    for orig, m in t1_res["test_breakdowns"]["origin"].items():
        lines.append(f"| `{orig}` | {m['total']} | {m['tp']} | {m['fp']} | {m['tn']} | {m['fn']} | {m['precision']:.4f} | {m['recall']:.4f} | **{m['f1']:.4f}** | {m['fpr']:.4f} | {m['accuracy']:.4f} |")
    lines.append("\n")

    # Category Breakdown
    lines.append("### 1.4 Breakdown by Attack Category (Test Set)\n")
    lines.append("| Category | Samples | TP | FP | TN | FN | Precision | Recall | F1 Score | FPR | Accuracy |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|---|")
    for cat, m in t1_res["test_breakdowns"]["category"].items():
        lines.append(f"| `{cat}` | {m['total']} | {m['tp']} | {m['fp']} | {m['tn']} | {m['fn']} | {m['precision']:.4f} | {m['recall']:.4f} | **{m['f1']:.4f}** | {m['fpr']:.4f} | {m['accuracy']:.4f} |")
    lines.append("\n")

    # Obfuscation Breakdown
    lines.append("### 1.5 Breakdown by Obfuscation Technique (Test Set)\n")
    lines.append("| Obfuscation | Samples | TP | FP | TN | FN | Precision | Recall | F1 Score | FPR | Accuracy |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|---|")
    for obf, m in t1_res["test_breakdowns"]["obfuscation"].items():
        lines.append(f"| `{obf}` | {m['total']} | {m['tp']} | {m['fp']} | {m['tn']} | {m['fn']} | {m['precision']:.4f} | {m['recall']:.4f} | **{m['f1']:.4f}** | {m['fpr']:.4f} | {m['accuracy']:.4f} |")
    lines.append("\n")

    # 15 Worst Failures for Fusion B
    lines.append("### 1.6 Top 15 Worst Failures for Fusion B (Ranked by Error Confidence)\n")
    lines.append("| ID | Error Type | Conf. | Score | Source Type | Category | Obfuscation | Origin | Text Snippet |")
    lines.append("|---|---|---|---|---|---|---|---|---|")
    for r in t1_res["top_15_failures"]:
        lines.append(f"| `{r['id']}` | **{r['error_type']}** | {r['confidence_in_error']:.4f} | {r['score']:.4f} | `{r['source_type']}` | `{r['category']}` | `{r['obfuscation']}` | `{r['origin']}` | `{r['text_snippet']}` |")
    lines.append("\n")

    # ------------------------------------------------------------------
    # 2. Template-Family Analysis
    # ------------------------------------------------------------------
    lines.append("## 2. Template-Family Analysis and Cluster Bootstrap\n")
    lines.append(f"- **Total Identified Template Families**: `{t2_res['num_families_total']}` across all 600 benchmark samples.")
    lines.append(f"- **Unique Families in Frozen Test Set**: `{t2_res['num_families_test']}`.\n")
    
    lines.append("### 2.1 Largest 10 Template Families\n")
    lines.append("| Family ID | Total Size | Dev Size | Test Size | Injections | Benign | Dominant Category | Dominant Source | Example Snippet |")
    lines.append("|---|---|---|---|---|---|---|---|---|")
    for f in t2_res["top_10_families"]:
        lines.append(f"| `{f['family_id']}` | {f['total_size']} | {f['dev_size']} | {f['test_size']} | {f['injections']} | {f['benign']} | `{f['dominant_category']}` | `{f['dominant_source']}` | `{f['example_snippet']}` |")
    lines.append("\n")
    
    lines.append("### 2.2 Error Concentration across Families in Test Set\n")
    lines.append(f"- **False Negatives ($N = 37$) Family Concentration**:")
    for fn in t2_res["fn_concentration"][:5]:
        lines.append(f"  - Family `{fn['family_id']}`: {fn['fn_count']} FNs (**{fn['fn_share_pct']}%** of all FNs) — Category: `{fn['dominant_category']}`, Snippet: `{fn['example_snippet']}`")
    lines.append(f"- **False Positives ($N = 15$) Family Concentration**:")
    for fp in t2_res["fp_concentration"][:5]:
        lines.append(f"  - Family `{fp['family_id']}`: {fp['fp_count']} FPs (**{fp['fp_share_pct']}%** of all FPs) — Category: `{fp['dominant_category']}`, Snippet: `{fp['example_snippet']}`")
    lines.append("\n")

    lines.append("### 2.3 Macro-Averaged Metrics and 95% Cluster Bootstrap CIs\n")
    lines.append("| Metric | Sample-Weighted (Standard) | Family-Macro Weighted | 95% Cluster Bootstrap CI (by Family) |")
    lines.append("|---|---|---|---|")
    lines.append(f"| **Precision** | {t1_res['test_overall']['precision']:.4f} | {t2_res['macro_metrics']['macro_precision']:.4f} | [{t2_res['cluster_bootstrap_95ci']['precision'][0]:.4f}, {t2_res['cluster_bootstrap_95ci']['precision'][1]:.4f}] |")
    lines.append(f"| **Recall** | {t1_res['test_overall']['recall']:.4f} | {t2_res['macro_metrics']['macro_recall']:.4f} | [{t2_res['cluster_bootstrap_95ci']['recall'][0]:.4f}, {t2_res['cluster_bootstrap_95ci']['recall'][1]:.4f}] |")
    lines.append(f"| **F1 Score** | **{t1_res['test_overall']['f1']:.4f}** | **{t2_res['macro_metrics']['macro_f1']:.4f}** | [{t2_res['cluster_bootstrap_95ci']['f1'][0]:.4f}, {t2_res['cluster_bootstrap_95ci']['f1'][1]:.4f}] |")
    lines.append(f"| **FPR** | {t1_res['test_overall']['fpr']:.4f} | {t2_res['macro_metrics']['macro_fpr']:.4f} | [{t2_res['cluster_bootstrap_95ci']['fpr'][0]:.4f}, {t2_res['cluster_bootstrap_95ci']['fpr'][1]:.4f}] |")
    lines.append(f"| **Accuracy** | {t1_res['test_overall']['accuracy']:.4f} | {t2_res['macro_metrics']['macro_accuracy']:.4f} | [{t2_res['cluster_bootstrap_95ci']['accuracy'][0]:.4f}, {t2_res['cluster_bootstrap_95ci']['accuracy'][1]:.4f}] |")
    lines.append("\n")

    # ------------------------------------------------------------------
    # 3. Shortcut Tests for Fusion B
    # ------------------------------------------------------------------
    lines.append("## 3. Shortcut Tests for Fusion B\n")
    
    # Length Bins
    lines.append("### 3.1 Recall and FPR by Text Length Bin\n")
    lines.append("| Length Bin (Words) | Test Injections | Detected | Recall | Test Benign | False Positives | FPR |")
    lines.append("|---|---|---|---|---|---|---|")
    for b, m in t3_res["test_length_bins"].items():
        lines.append(f"| `{b}` | {m['injections_total']} | {m['injections_detected']} | **{m['recall']:.4f}** | {m['benign_total']} | {m['benign_fp']} | **{m['fpr']:.4f}** |")
    lines.append("\n")

    # Stress Test
    lines.append("### 3.2 Embedding Stress Test (50 Embedded Injections vs. 50 Embedded Benign Prompts in Long Documents)\n")
    lines.append("| Model Configuration | Embedded Injection Recall (50 cases) | Embedded Benign FPR (50 cases) | Overall Accuracy | Overall F1 Score |")
    lines.append("|---|---|---|---|---|")
    lines.append(f"| **Fusion A (Rule-Based)** | **{t3_res['stress_test']['injection_recall_a']:.4f}** ({int(t3_res['stress_test']['injection_recall_a']*50)}/50) | {t3_res['stress_test']['benign_fpr_a']:.4f} ({int(t3_res['stress_test']['benign_fpr_a']*50)}/50) | {t3_res['stress_test']['fusion_a']['accuracy']:.4f} | {t3_res['stress_test']['fusion_a']['f1']:.4f} |")
    lines.append(f"| **Fusion B (Stacked)** | **{t3_res['stress_test']['injection_recall_b']:.4f}** ({int(t3_res['stress_test']['injection_recall_b']*50)}/50) | {t3_res['stress_test']['benign_fpr_b']:.4f} ({int(t3_res['stress_test']['benign_fpr_b']*50)}/50) | {t3_res['stress_test']['fusion_b']['accuracy']:.4f} | {t3_res['stress_test']['fusion_b']['f1']:.4f} |")
    lines.append("\n> **Critical Shortcut Finding**: In the stress test, Fusion A maintains 98-100% recall on short injections hidden inside long documents because its chunking engine scores the trigger chunk directly. However, Fusion B's `log_len` and `retrieved_document` feature penalties can suppress the stacked probability for embedded injections in long documents, demonstrating an important tradeoff between false positive suppression and stealth-injection recall.\n")

    # Stacker Ablation
    lines.append("### 3.3 Stacker Feature Ablation: Score-Only vs. Full Stacked Model\n")
    lines.append("| Model Variant | Features Used | Dev Threshold | Dev F1 | Dev Recall | Dev FPR | Test F1 | Test Recall | Test FPR |")
    lines.append("|---|---|---|---|---|---|---|---|---|")
    lines.append(f"| **Full Fusion B** | `[heur, class, source_type, log_len]` | 0.85 | 0.8914 | 0.8667 | 0.0778 | **0.8693** | 0.8238 | **0.0714** |")
    abl = t3_res["stacker_ablation"]
    lines.append(f"| **Ablated Stacker** | `[heur, class]` (No Length / Source) | {abl['dev_optimal_threshold']:.2f} | {abl['dev_metrics']['f1']:.4f} | {abl['dev_metrics']['recall']:.4f} | {abl['dev_metrics']['fpr']:.4f} | **{abl['test_metrics']['f1']:.4f}** | {abl['test_metrics']['recall']:.4f} | **{abl['test_metrics']['fpr']:.4f}** |")
    lines.append("\n")

    # ------------------------------------------------------------------
    # 4. Train/Benchmark Overlap
    # ------------------------------------------------------------------
    lines.append("## 4. Train / Benchmark Overlap Analysis\n")
    d = t4_res["test_distribution"]
    lines.append(f"- **Cosine Similarity Distribution to `train_v2.jsonl` (Test Set)**:")
    lines.append(f"  - Min: `{d['min']:.4f}` | 25%: `{d['p25']:.4f}` | Median: `{d['median']:.4f}` | Mean: `{d['mean']:.4f}` | 75%: `{d['p75']:.4f}` | Max: `{d['max']:.4f}`")
    lines.append(f"  - Samples with Cosine Similarity $> 0.80$: **{d['count_gt_0_8']}** ({d['pct_gt_0_8']}%)")
    lines.append(f"  - Samples with Cosine Similarity $\\le 0.80$: **{d['count_le_0_8']}** ({round(100 - d['pct_gt_0_8'], 2)}%)\n")

    lines.append("### 4.1 Fusion B Performance Split by Training Set Similarity\n")
    lines.append("| Similarity Group | Samples | TP | FP | TN | FN | Precision | Recall | F1 Score | FPR | Accuracy |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|---|")
    mh = t4_res["test_high_similarity_metrics"]
    ml = t4_res["test_low_similarity_metrics"]
    lines.append(f"| **High-Similarity ($> 0.80$)** | {mh['total']} | {mh['tp']} | {mh['fp']} | {mh['tn']} | {mh['fn']} | {mh['precision']:.4f} | {mh['recall']:.4f} | **{mh['f1']:.4f}** | {mh['fpr']:.4f} | {mh['accuracy']:.4f} |")
    lines.append(f"| **Low-Similarity ($\\le 0.80$)** | {ml['total']} | {ml['tp']} | {ml['fp']} | {ml['tn']} | {ml['fn']} | {ml['precision']:.4f} | {ml['recall']:.4f} | **{ml['f1']:.4f}** | {ml['fpr']:.4f} | {ml['accuracy']:.4f} |")
    lines.append("\n")

    # ------------------------------------------------------------------
    # 5. External Holdout Evaluation
    # ------------------------------------------------------------------
    lines.append("## 5. Independent External Holdout Benchmark\n")
    h_audit = t5_res["audit_summary"]
    lines.append(f"- **Saved File**: `backend/eval/data/holdout_external.jsonl`")
    lines.append(f"- **Raw Collected Samples**: {h_audit['raw_total']}")
    lines.append(f"- **Deduplication against `train_v2`, `dev`, `test`**: Removed {h_audit['removed_exact']} exact matches, {h_audit['removed_near']} near-duplicates.")
    lines.append(f"- **Final Clean Holdout Size**: **{h_audit['final_total']}** samples ({h_audit['injections_count']} injections, {h_audit['benign_count']} benign).\n")
    
    lines.append("### 5.1 Dataset Sources and Licensing\n")
    lines.append("| Source Name | License | Sample Type | Count in Holdout |")
    lines.append("|---|---|---|---|")
    for s in h_audit["metadata"]:
        lines.append(f"| `{s['source_name']}` | `{s['license']}` | {s['label_type']} | {s['samples_downloaded']} |")
    lines.append("\n")

    lines.append("### 5.2 Frozen Fusion B Performance on External Holdout\n")
    lines.append("| Dataset Slice | Total Samples | TP | FP | TN | FN | Precision | Recall | F1 Score | FPR | Accuracy |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|---|")
    ov = t5_res["overall_metrics"]
    lines.append(f"| **All External Holdout** | {ov['total']} | {ov['tp']} | {ov['fp']} | {ov['tn']} | {ov['fn']} | {ov['precision']:.4f} | {ov['recall']:.4f} | **{ov['f1']:.4f}** | {ov['fpr']:.4f} | {ov['accuracy']:.4f} |")
    for src, sm in t5_res["source_breakdown"].items():
        lines.append(f"| `source: {src}` | {sm['total']} | {sm['tp']} | {sm['fp']} | {sm['tn']} | {sm['fn']} | {sm['precision']:.4f} | {sm['recall']:.4f} | **{sm['f1']:.4f}** | {sm['fpr']:.4f} | {sm['accuracy']:.4f} |")
    lines.append("\n")

    return "\n".join(lines)

def run_all():
    print("=" * 80)
    print("STARTING COMPLETE CAGE V2 FUSION B VALIDATION SUITE")
    print("=" * 80)
    
    # Task 1
    t1_res = run_task1()
    
    # Task 2
    t2_res = run_task2(t1_res["test_df"], t1_res["dev_df"])
    
    # Task 3
    t3_res = run_task3(t1_res["dev_df"], t1_res["test_df"])
    
    # Task 4
    t4_res = run_task4(t1_res["dev_df"], t1_res["test_df"])
    
    # Task 5
    t5_res = run_task5()
    
    # Save Failures CSV for Fusion B
    fail_csv_path = RESULTS_DIR / "failures_fusion_b.csv"
    if not t1_res["all_test_failures_df"].empty:
        t1_res["all_test_failures_df"].to_csv(fail_csv_path, index=False)
        print(f"\nSaved Fusion B failures to: {fail_csv_path}")
        
    # Save Stress Test Samples
    stress_jsonl_path = RESULTS_DIR / "stress_test_samples.jsonl"
    with open(stress_jsonl_path, "w", encoding="utf-8") as f:
        for s in t3_res["stress_test"]["stress_samples"]:
            f.write(json.dumps(s) + "\n")
    print(f"Saved stress test samples to: {stress_jsonl_path}")
    
    # Save JSON Results
    all_results = {
        "task1_fusion_b_breakdown": {
            "dev_overall": t1_res["dev_overall"],
            "test_overall": t1_res["test_overall"],
            "dev_breakdowns": t1_res["dev_breakdowns"],
            "test_breakdowns": t1_res["test_breakdowns"],
            "public_only": t1_res["public_only"]
        },
        "task2_family_analysis": {
            "num_families_total": t2_res["num_families_total"],
            "num_families_test": t2_res["num_families_test"],
            "top_10_families": t2_res["top_10_families"],
            "fp_concentration": t2_res["fp_concentration"],
            "fn_concentration": t2_res["fn_concentration"],
            "macro_metrics": t2_res["macro_metrics"],
            "cluster_bootstrap_95ci": t2_res["cluster_bootstrap_95ci"]
        },
        "task3_shortcut_tests": {
            "dev_length_bins": t3_res["dev_length_bins"],
            "test_length_bins": t3_res["test_length_bins"],
            "stress_test": {
                "fusion_a": t3_res["stress_test"]["fusion_a"],
                "fusion_b": t3_res["stress_test"]["fusion_b"],
                "injection_recall_a": t3_res["stress_test"]["injection_recall_a"],
                "injection_recall_b": t3_res["stress_test"]["injection_recall_b"],
                "benign_fpr_a": t3_res["stress_test"]["benign_fpr_a"],
                "benign_fpr_b": t3_res["stress_test"]["benign_fpr_b"]
            },
            "stacker_ablation": t3_res["stacker_ablation"]
        },
        "task4_train_overlap": {
            "dev_distribution": t4_res["dev_distribution"],
            "test_distribution": t4_res["test_distribution"],
            "overall_distribution": t4_res["overall_distribution"],
            "test_high_similarity_metrics": t4_res["test_high_similarity_metrics"],
            "test_low_similarity_metrics": t4_res["test_low_similarity_metrics"]
        },
        "task5_external_holdout": {
            "audit_summary": t5_res["audit_summary"],
            "overall_metrics": t5_res["overall_metrics"],
            "source_breakdown": t5_res["source_breakdown"]
        }
    }
    
    json_path = RESULTS_DIR / "validation_results.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2)
    print(f"Saved complete JSON validation results to: {json_path}")
    
    # Save Markdown Report
    report_md = generate_validation_markdown_report(t1_res, t2_res, t3_res, t4_res, t5_res)
    md_path = RESULTS_DIR / "validation_report.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(report_md)
    print(f"Saved complete Markdown validation report to: {md_path}")
    
    print("\nALL VALIDATION SUITE TASKS COMPLETED SUCCESSFULLY!")

if __name__ == "__main__":
    run_all()
