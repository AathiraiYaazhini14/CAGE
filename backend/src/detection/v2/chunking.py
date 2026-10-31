from typing import List, Dict, Any, Callable

def chunk_text(text: str, threshold_words: int = 80, window_words: int = 60, stride_words: int = 30) -> List[Dict[str, Any]]:
    """
    Splits text into overlapping chunks if word count exceeds threshold_words.
    Short text (<= threshold_words) returns a single chunk.
    For longer text, creates sliding windows of window_words with stride_words step.
    """
    if not text or not text.strip():
        return [{"chunk_index": 0, "start_word": 0, "end_word": 0, "chunk_text": ""}]
        
    words = text.strip().split()
    total_words = len(words)
    
    if total_words <= threshold_words:
        return [{
            "chunk_index": 0,
            "start_word": 0,
            "end_word": total_words,
            "chunk_text": text
        }]
        
    chunks = []
    start_idx = 0
    chunk_idx = 0
    
    while start_idx < total_words:
        end_idx = min(start_idx + window_words, total_words)
        chunk_words = words[start_idx:end_idx]
        chunk_str = " ".join(chunk_words)
        
        chunks.append({
            "chunk_index": chunk_idx,
            "start_word": start_idx,
            "end_word": end_idx,
            "chunk_text": chunk_str
        })
        
        if end_idx >= total_words:
            break
            
        start_idx += stride_words
        chunk_idx += 1
        
    return chunks

def score_with_chunking(
    text: str,
    score_fn: Callable[[str], float],
    threshold_words: int = 80,
    window_words: int = 60,
    stride_words: int = 30
) -> Dict[str, Any]:
    """
    Applies score_fn across all sliding chunks of text.
    Returns:
    - max_score: highest score observed across chunks
    - trigger_chunk_index: index of chunk that generated max_score
    - trigger_chunk_text: text snippet of the trigger chunk
    - num_chunks: total number of chunks evaluated
    - all_chunk_scores: list of individual scores per chunk
    """
    chunks = chunk_text(text, threshold_words=threshold_words, window_words=window_words, stride_words=stride_words)
    
    best_score = 0.0
    best_chunk_idx = 0
    best_chunk_text = chunks[0]["chunk_text"]
    scores = []
    
    for c in chunks:
        score = float(score_fn(c["chunk_text"]))
        scores.append(score)
        if score > best_score:
            best_score = score
            best_chunk_idx = c["chunk_index"]
            best_chunk_text = c["chunk_text"]
            
    # If all scores were 0.0, best_score is 0.0
    if not scores:
        best_score = 0.0
        
    return {
        "max_score": best_score,
        "trigger_chunk_index": best_chunk_idx,
        "trigger_chunk_text": best_chunk_text[:120] + ("..." if len(best_chunk_text) > 120 else ""),
        "num_chunks": len(chunks),
        "all_chunk_scores": scores
    }
