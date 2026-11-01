import re
from typing import Dict, Any, List, Optional


SUSPICIOUS_PHRASES: List[str] = [
    "i have sent",
    "i have deleted",
    "executing command",
    "transferring",
    "system prompt is",
    "password is",
    "api key is",
]


def check_verbatim_overlap(system_prompt: str, response: str, min_words: int = 10) -> bool:
    """Checks if any N-word sequence from system_prompt appears verbatim in response."""
    if not system_prompt or not response:
        return False

    sys_words = re.findall(r'\b\w+\b', system_prompt.lower())
    resp_text = response.lower()

    if len(sys_words) < min_words:
        return False

    for i in range(len(sys_words) - min_words + 1):
        phrase = " ".join(sys_words[i:i + min_words])
        if phrase in resp_text:
            return True

    return False


def validate_output(llm_response: str, system_prompt: str = "", canary: Optional[str] = None) -> Dict[str, Any]:
    """
    Validates LLM output text for safety leaks, canary tokens, or dangerous unauthorized actions.
    Returns dict: {"passed": bool, "issues": List[str]}
    """
    if not llm_response:
        return {"passed": True, "issues": []}

    issues: List[str] = []
    resp_lower = llm_response.lower()

    # Check canary token leakage
    if canary and canary.lower() in resp_lower:
        issues.append(f"Canary secret leakage detected: '{canary}'")

    # Check 10+ word verbatim overlap with system prompt
    if system_prompt and check_verbatim_overlap(system_prompt, llm_response, min_words=10):
        issues.append("Verbatim system prompt leakage detected (10+ matching words).")

    # Check suspicious action phrases
    for phrase in SUSPICIOUS_PHRASES:
        if phrase in resp_lower:
            issues.append(f"Suspicious action phrase detected in output: '{phrase}'")

    passed = len(issues) == 0
    return {
        "passed": passed,
        "issues": issues
    }
