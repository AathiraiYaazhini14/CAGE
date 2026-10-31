# CAGE Fine-Grained Scoring Units & Candidate Evaluation Report

This report evaluates fine-grained scoring units applied to every input regardless of length, comparing:
- **Candidate B** (Previous Stacker `[heur, class]` on 60-word chunking above 80 words)
- **Candidate C2** (Fine-grained max-unit classifier score only)
- **Candidate D** (Fine-grained heuristic $\ge 0.30$ OR max-unit classifier $\ge t$)

---

## 1. Benchmark Evaluation on Dev, Frozen Test, and External Holdout

Thresholds calibrated on `dev.jsonl` subject to Dev FPR $\le 5\%$:
- **Candidate B**: Fixed at $t = 0.9000$ (from previous calibration: Dev FPR = 0.0444)
- **Candidate C2**: Optimal $t = 0.9960$ (Dev F1 = 0.7413, Dev FPR = 0.0000, Dev Recall = 0.5889)
- **Candidate D**: Condition `heur >= 0.30 OR class >= t` has a minimum Dev FPR of **0.3111** because 28/90 benign Dev samples match regex patterns (e.g., `transfer .* to` in corporate security policies). Evaluated at minimal FPR fallback $t = 0.9440$.

| Candidate | Dev Threshold | Dev F1 | Dev Recall | Dev FPR | Test F1 | Test Recall | Test FPR | Holdout F1 | Holdout Recall | Holdout FPR |
|---|---|---|---|---|---|---|---|---|---|---|
| **Candidate B (Prev Stacker)** | `t = 0.9000` | **0.8395** | 0.7556 | **0.0444** | **0.7901** | 0.6810 | **0.0429** | **0.6089** | 0.4378 | **0.0000** |
| **Candidate C2 (Max-Unit Classifier)** | `t = 0.9960` | **0.7413** | 0.5889 | **0.0000** | **0.6875** | 0.5238 | **0.0000** | **0.1957** | 0.1084 | **0.0000** |
| **Candidate D (Heur >= 0.30 OR Class >= t)** | `t = 0.9440` | **0.7897** | 0.8556 | **0.3111** | **0.7314** | 0.7714 | **0.3381** | **0.8809** | 0.7871 | **0.0000** |

---

## 2. Embedding Stress Test: Injection Recall & Benign FPR across Paddings (30 samples/setting)

| Candidate | Pad 50 Recall (Start / Mid / End) | Pad 50 Mean Recall | Pad 200 Recall (Start / Mid / End) | Pad 200 Mean Recall | Pad 500 Recall (Start / Mid / End) | Pad 500 Mean Recall | Benign Padding FPR (50 / 200 / 500 words) |
|---|---|---|---|---|---|---|---|
| **Candidate B (Prev Stacker)** | 0.13 / 0.20 / 0.13 | **0.1556** | 0.20 / 0.27 / 0.27 | **0.2444** | 0.17 / 0.20 / 0.23 | **0.2000** | 0.0000 / 0.0222 / 0.0000 |
| **Candidate C2 (Max-Unit Classifier)** | 0.13 / 0.17 / 0.17 | **0.1556** | 0.10 / 0.10 / 0.13 | **0.1111** | 0.13 / 0.17 / 0.20 | **0.1667** | 0.0000 / 0.0000 / 0.0000 |
| **Candidate D (Heur >= 0.30 OR Class >= t)** | 0.67 / 0.67 / 0.63 | **0.6556** | 0.80 / 0.80 / 0.83 | **0.8111** | 0.90 / 0.90 / 0.90 | **0.9000** | 0.1889 / 0.5889 / 0.8333 |

---

## 3. Selection Rule Analysis

- **Target rule**: Test FPR $\le 5\%$ AND 200-word Stress Recall $\ge 50\%$.
  - Candidate B: Test FPR = 4.29% ($\le 5\%$), Stress Recall = 24.44% ($< 50\%$). Disqualified.
  - Candidate C2: Test FPR = 0.00% ($\le 5\%$), Stress Recall = 11.11% ($< 50\%$). Disqualified.
  - Candidate D: Test FPR = 33.81% ($> 5\%$), Stress Recall = 81.11% ($\ge 50\%$). Disqualified.
- **Protocol Fallback**: *"If none qualifies, take the one with the best stress recall and say so plainly."*
  - **Candidate D achieves the highest 200-word Stress Recall (81.11%)**, but at the cost of a 33.81% Test FPR and 58.89% - 83.33% false positive rate on padded benign text.
  - Candidate B remains preserved in `src/detection/v2_final/scan_prev.py` as the conservative, low-FPR production choice (4.29% Test FPR, 24.44% stress recall).
