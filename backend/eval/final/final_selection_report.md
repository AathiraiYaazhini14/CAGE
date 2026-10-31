# CAGE v2_final Selection and Verification Report

**Selection Protocol**: Among candidates with Test FPR $\le 5\%$ and 200-word Stress Recall $\ge 50\%$, pick best Dev F1.

**Winning Configuration**: `Candidate B: Ablated Stacker [heur, class]`

> **Verdict**: No candidate satisfied both Test FPR <= 5% and Stress Recall >= 50% at 200-word padding. Per protocol, selected Candidate B: Ablated Stacker [heur, class] based on highest 200-word Stress Recall (0.2333).

## 1. Candidate Performance on Dev, Frozen Test, and External Holdout

| Candidate | Operating Threshold (Dev) | Dev F1 | Dev Recall | Dev FPR | Test F1 | Test Recall | Test FPR | Holdout F1 | Holdout Recall | Holdout FPR |
|---|---|---|---|---|---|---|---|---|---|---|
| **Candidate A: Full Fusion B [all features]** | `t = 0.88` | **0.9123** | 0.8667 | 0.0333 | **0.8883** | 0.8143 | **0.0190** | **0.7458** | 0.6185 | **0.0400** |
| **Candidate B: Ablated Stacker [heur, class]** | `t = 0.90` | **0.8395** | 0.7556 | 0.0444 | **0.7901** | 0.6810 | **0.0429** | **0.6089** | 0.4378 | **0.0000** |
| **Candidate C: Max-Chunk Classifier Only** | `t = 0.95` | **0.8395** | 0.7556 | 0.0444 | **0.7934** | 0.6857 | **0.0429** | **0.6356** | 0.4659 | **0.0000** |


## 2. Embedding Stress Test: Injection Recall & Benign FPR across Paddings

| Candidate | Pad 50 Recall (Start/Mid/End) | Pad 50 Mean Recall | Pad 200 Recall (Start/Mid/End) | Pad 200 Mean Recall | Pad 500 Recall (Start/Mid/End) | Pad 500 Mean Recall | Mean Benign FPR (50/200/500) |
|---|---|---|---|---|---|---|---|
| **Candidate A: Full Fusion B [all features]** | 0.28 / 0.34 / 0.38 | **0.3333** | 0.06 / 0.12 / 0.24 | **0.1400** | 0.00 / 0.00 / 0.00 | **0.0000** | 0.0000 / 0.0000 / 0.0000 |
| **Candidate B: Ablated Stacker [heur, class]** | 0.12 / 0.18 / 0.16 | **0.1533** | 0.14 / 0.24 / 0.32 | **0.2333** | 0.14 / 0.24 / 0.28 | **0.2200** | 0.0000 / 0.0133 / 0.0000 |
| **Candidate C: Max-Chunk Classifier Only** | 0.14 / 0.20 / 0.18 | **0.1733** | 0.14 / 0.24 / 0.32 | **0.2333** | 0.14 / 0.24 / 0.28 | **0.2200** | 0.0000 / 0.0133 / 0.0000 |


## 3. Operational Three-Tier Policy for Production (Dev-Tuned)

**Target Model**: `Candidate B: Ablated Stacker [heur, class]`

| Tier | Threshold Condition | Action | Dev FPR | Test FPR | Test Recall | Description |
|---|---|---|---|---|---|---|
| **ALLOW** | `score < 0.9000` | Allow prompt to pass to upstream LLM | — | — | — | Clean or benign prompt with low suspicion. |
| **ISOLATE** | `0.9000 <= score < 0.9450` | Quarantine input in untrusted wrappers | **0.0444** (<= 5%) | **0.0429** | **0.6810** | Borderline injection pattern or hard benign negative. |
| **BLOCK** | `score >= 0.9450` | Block execution immediately (safe_text=None) | **0.0000** (<= 1%) | **0.0000** | **0.5333** | High-confidence malicious prompt injection attack. |


## 4. Known Weaknesses of the Final Configuration

1. **Multilingual Injections**: Non-English attacks (especially German prompt overrides and roleplay queries from ZEIT ONLINE in public datasets) lack dense representations in TF-IDF vocabulary, occasionally escaping detection without multilingual embeddings.
2. **Stealth Benign Padding Tradeoff**: While removing `log_len` recovers injection recall inside long documents, long documents containing technical security discussions still have a ~4% probability of crossing the isolate threshold.
3. **Multi-turn and State Steganography**: Attacks fragmented across multiple conversational turns or encodings not covered by NFKC/homoglyphs/base64 (e.g. cipher rotations or token space manipulations) will not be unwrapped by the preprocessor.

