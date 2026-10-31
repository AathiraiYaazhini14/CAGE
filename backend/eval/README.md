# CAGE Evaluation & Benchmarking Suite

This directory contains the independent evaluation harness, dataset curation scripts, and benchmark results for **CAGE (Context-Aware Guard for LLM Exploits)**.

Per project evaluation rules:
- No files in `backend/src/` or existing project tests have been modified.
- No models have been altered or retrained.
- All metrics are produced from direct, offline Python execution of the detection modules.

---

## Directory Structure

```
backend/eval/
├── data/
│   ├── benchmark.jsonl       # Complete 600-sample benchmark dataset
│   ├── dev.jsonl             # 30% development split (180 samples, threshold tuning)
│   └── test.jsonl            # 70% frozen test split (420 samples, strictly frozen)
├── results/
│   ├── diagnostics.md        # Part A probe diagnostic analysis
│   ├── RESULTS.md            # Part C formatted benchmark results and breakdowns
│   ├── results.json          # Machine-readable JSON metrics and threshold sweep
│   └── failures.csv          # Granular error log of all False Positives and False Negatives
├── build_benchmark.py        # Generates, fetches, obfuscates, and splits the benchmark
├── run_diagnostics.py        # Runs Part A probe diagnostic inputs
├── run_eval.py               # Runs Part C 4-config evaluation, threshold sweep, and breakdowns
└── README.md                 # This file
```

---

## 1. How to Regenerate the Benchmark Dataset

Run the following command from the `backend/` directory:

```bash
python eval/build_benchmark.py
```
*(Or with venv: `.\venv\Scripts\python.exe eval/build_benchmark.py` on Windows)*

This script:
1. Fetches public samples from Hugging Face (`deepset/prompt-injections`).
2. Synthesizes realistic 150–300 word documents (resumes, invoices, support tickets, security articles, corporate policies).
3. Synthesizes tool outputs and user inputs with hard negatives and 6 obfuscation techniques (`none`, `html_comment`, `markdown`, `base64`, `unicode_homoglyph`, `split_across_lines`).
4. Checks and removes overlaps with `data/training_samples.csv` and internal duplicates.
5. Produces exactly 600 samples (50% injection, 50% benign; 43.2% retrieved documents) and performs a stratified 30/70 split into `dev.jsonl` and frozen `test.jsonl`.

---

## 2. How to Run the Evaluation Harness

Run the following command from the `backend/` directory:

```bash
python eval/run_eval.py
```
*(Or with venv: `.\venv\Scripts\python.exe eval/run_eval.py` on Windows)*

This script:
1. Sweeps fusion threshold from 0.10 to 0.90 on `dev.jsonl` to locate the empirical $F_1$ optimum.
2. Directly evaluates 4 system configurations on `test.jsonl`:
   - `heuristics_only` (threshold 0.30)
   - `classifier_only` (threshold 0.50)
   - `fused_default` (current CAGE pipeline, threshold 0.30)
   - `always_benign_baseline`
3. Generates performance breakdowns by attack category, source type, and obfuscation technique.
4. Exports `eval/results/results.json`, `eval/results/RESULTS.md`, and `eval/results/failures.csv`.
