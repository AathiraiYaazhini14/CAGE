import re
from dataclasses import dataclass, field
from typing import List, Dict, Any


@dataclass
class DetectionResult:
    flagged: bool
    score: float
    matched_patterns: List[Dict[str, Any]] = field(default_factory=list)
    attack_type: str = "none"


PATTERN_GROUPS: Dict[str, Dict[str, Any]] = {
    "instruction_override": {
        "weight": 0.4,
        "patterns": [
            r"ignore all previous instructions",
            r"disregard previous instructions",
            r"forget everything (you were|you've been) told",
            r"new instructions:",
            r"system prompt is",
        ],
    },
    "role_override": {
        "weight": 0.35,
        "patterns": [
            r"you are now",
            r"act as if you are",
            r"pretend (you are|to be)",
            r"from now on you",
            r"switch to \w+ mode",
            r"switch to .* mode",
        ],
    },
    "prompt_extraction": {
        "weight": 0.3,
        "patterns": [
            r"reveal your system prompt",
            r"show me your instructions",
            r"what are your original instructions",
            r"repeat the text above",
        ],
    },
    "delimiter_injection": {
        "weight": 0.3,
        "patterns": [
            r"</system>",
            r"\[/admin\]",
            r"--- end of instructions",
            r"<\|im_start\|>",
            r"<\|im_end\|>",
        ],
    },
    "action_hijack": {
        "weight": 0.35,
        "patterns": [
            r"send an email to",
            r"execute this command",
            r"delete all files",
            r"transfer .* to",
        ],
    },
}


def detect(text: str) -> DetectionResult:
    """
    Analyzes input text for prompt injection attack patterns.
    - Lowercases text
    - Checks regex patterns across all defined pattern groups
    - Sums the weight of every matched group (capped at 1.0)
    - Flags text if score >= 0.3
    - Sets attack_type to the category of the first match ('none' if clean)
    - Returns details of matched patterns
    """
    if not text or not text.strip():
        return DetectionResult(flagged=False, score=0.0, matched_patterns=[], attack_type="none")

    cleaned_text = text.lower()
    matched_groups = set()
    matched_details = []
    first_attack_type = None

    for group_name, group_data in PATTERN_GROUPS.items():
        weight = group_data["weight"]
        patterns = group_data["patterns"]

        for pattern in patterns:
            match = re.search(pattern, cleaned_text, re.IGNORECASE)
            if match:
                matched_groups.add(group_name)
                if first_attack_type is None:
                    first_attack_type = group_name

                matched_details.append({
                    "category": group_name,
                    "pattern": pattern,
                    "matched_text": match.group(0),
                    "weight": weight
                })

    # Calculate total score based on matched groups sum, capped at 1.0
    total_score = sum(PATTERN_GROUPS[group]["weight"] for group in matched_groups)
    total_score = min(1.0, round(total_score, 2))

    flagged = total_score >= 0.3
    attack_type = first_attack_type if first_attack_type else "none"

    return DetectionResult(
        flagged=flagged,
        score=total_score,
        matched_patterns=matched_details,
        attack_type=attack_type
    )
