import base64
import re
import unicodedata
from typing import Dict, List, Set

# Cyrillic and Greek homoglyphs to Latin ASCII lookalikes
HOMOGLYPH_MAP = {
    # Cyrillic lowercase
    'а': 'a', 'с': 'c', 'е': 'e', 'о': 'o', 'р': 'p', 'х': 'x', 'у': 'y',
    'і': 'i', 'ј': 'j', 'ѕ': 's', 'ԁ': 'd', 'ԛ': 'q', 'ԝ': 'w', 'в': 'b',
    'г': 'g', 'к': 'k', 'м': 'm', 'н': 'n', 'т': 't', 'и': 'u',
    # Cyrillic uppercase
    'А': 'A', 'В': 'B', 'С': 'C', 'Е': 'E', 'Н': 'H', 'І': 'I', 'Ј': 'J',
    'К': 'K', 'М': 'M', 'О': 'O', 'Р': 'P', 'Ѕ': 'S', 'Т': 'T', 'Х': 'X',
    'Ү': 'Y', 'У': 'Y',
    # Greek lowercase
    'α': 'a', 'β': 'b', 'γ': 'g', 'δ': 'd', 'ε': 'e', 'ζ': 'z', 'η': 'h',
    'θ': 'th', 'ι': 'i', 'κ': 'k', 'λ': 'l', 'μ': 'm', 'ν': 'n', 'ξ': 'x',
    'ο': 'o', 'π': 'p', 'ρ': 'r', 'σ': 's', 'τ': 't', 'υ': 'u', 'φ': 'f',
    'χ': 'x', 'ψ': 'ps', 'ω': 'w',
    # Greek uppercase
    'Α': 'A', 'Β': 'B', 'Γ': 'G', 'Δ': 'D', 'Ε': 'E', 'Ζ': 'Z', 'Η': 'H',
    'Ι': 'I', 'Κ': 'K', 'Μ': 'M', 'Ν': 'N', 'Ο': 'O', 'Ρ': 'P', 'Τ': 'T',
    'Υ': 'Y', 'Χ': 'X'
}

# Zero-width and invisible format characters
ZERO_WIDTH_REGEX = re.compile(r'[\u200B\u200C\u200D\u200E\u200F\uFEFF\u00AD\u2060\u2000-\u200A\r]')

def replace_homoglyphs(text: str) -> str:
    """Replaces Cyrillic and Greek lookalike characters with their Latin equivalents."""
    return "".join(HOMOGLYPH_MAP.get(c, c) for c in text)

def extract_base64_payloads(text: str, min_len: int = 20) -> List[str]:
    """Finds candidate base64 strings and returns decoded printable UTF-8 / ASCII strings."""
    # Find contiguous base64 alphanumeric chunks
    candidates = re.findall(r'[A-Za-z0-9+/=]{' + str(min_len) + r',}', text)
    decoded_strings = []
    
    for cand in candidates:
        # Strip potential trailing padding artifacts
        clean_cand = cand.strip()
        # Add required padding if needed
        missing_padding = len(clean_cand) % 4
        if missing_padding:
            clean_cand += '=' * (4 - missing_padding)
        try:
            raw_bytes = base64.b64decode(clean_cand, validate=False)
            try:
                dec_text = raw_bytes.decode('utf-8')
            except UnicodeDecodeError:
                dec_text = raw_bytes.decode('latin-1', errors='ignore')
                
            # Check if majority of characters are printable and form meaningful text
            printable_count = sum(1 for ch in dec_text if ch.isprintable() or ch in ('\n', '\t', ' '))
            if len(dec_text) >= 6 and (printable_count / len(dec_text)) > 0.85:
                decoded_strings.append(dec_text.strip())
        except Exception:
            continue
            
    return decoded_strings

def normalize_text(text: str) -> str:
    """
    Applies comprehensive normalization:
    - Unicode NFKC
    - Homoglyph replacement (Cyrillic/Greek to Latin)
    - Zero-width character removal
    - HTML comment and markdown unwrapping
    - Whitespace & line-break collapse
    """
    if not text:
        return ""
        
    # 1. Unicode NFKC
    norm = unicodedata.normalize('NFKC', text)
    
    # 2. Remove zero-width characters
    norm = ZERO_WIDTH_REGEX.sub('', norm)
    
    # 3. Replace homoglyphs
    norm = replace_homoglyphs(norm)
    
    # 4. Unwrap HTML comments (keep inner content)
    norm = re.sub(r'<!--\s*(?:assistant:)?\s*(.*?)\s*-->', r' \1 ', norm, flags=re.DOTALL | re.IGNORECASE)
    
    # 5. Unwrap markdown formatting (keep inner content)
    # [link text](url "title") -> link text url title
    norm = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r' \1 \2 ', norm)
    # Inline code backticks
    norm = re.sub(r'`+([^`]+)`+', r' \1 ', norm)
    # Bold / italic asterisks & underscores
    norm = re.sub(r'[*_]{1,3}([^*_]+)[*_]{1,3}', r' \1 ', norm)
    # Blockquotes
    norm = re.sub(r'^\s*>\s*', ' ', norm, flags=re.MULTILINE)
    
    # 6. Unbreak hyphenated line wraps (e.g. "ig-\nnore" -> "ignore")
    norm = re.sub(r'(\w+)-\s*\n\s*(\w+)', r'\1\2', norm)
    # Replace markdown hr / divider breaks (e.g. "\n---\n")
    norm = re.sub(r'\n\s*---\s*\n', ' ', norm)
    
    # 7. Collapse all whitespace into single spaces
    norm = re.sub(r'\s+', ' ', norm).strip()
    
    return norm

def preprocess(text: str) -> Dict[str, str]:
    """
    Generates three views of the input:
    - original: unmodified input text
    - normalized: normalized, homoglyphs mapped, markdown & comments unpacked
    - decoded: normalized text augmented with any decoded base64 payloads
    """
    orig = text or ""
    norm = normalize_text(orig)
    
    b64_payloads = extract_base64_payloads(orig)
    if b64_payloads:
        decoded_additions = " ".join(normalize_text(p) for p in b64_payloads)
        dec = f"{norm} [DECODED_BASE64: {decoded_additions}]"
    else:
        dec = norm
        
    return {
        "original": orig,
        "normalized": norm,
        "decoded": dec
    }

def get_views(text: str) -> List[str]:
    """Returns unique, non-empty text views for multi-view evaluation."""
    views = preprocess(text)
    unique_views = []
    seen = set()
    for key in ["original", "normalized", "decoded"]:
        v = views[key].strip()
        if v and v not in seen:
            unique_views.append(v)
            seen.add(v)
    return unique_views
