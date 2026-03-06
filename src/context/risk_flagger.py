"""Risk flag detection from issue content.

Phase 0: keyword-based boolean flags. No ML.
"""

import re

# Keyword patterns for each risk category
_RISK_PATTERNS: dict[str, re.Pattern[str]] = {
    "risk_security": re.compile(
        r"\b(?:security|auth(?:entication|orization)?|credential|secret|"
        r"token|password|encrypt|decrypt|vulnerability|CVE|injection|XSS|CSRF)\b",
        re.IGNORECASE,
    ),
    "risk_breaking": re.compile(
        r"\b(?:breaking\s*change|deprecat|migration|backward|incompatible|"
        r"remove\s+(?:api|endpoint|field|column)|drop\s+(?:table|column))\b",
        re.IGNORECASE,
    ),
    "risk_cross_team": re.compile(
        r"\b(?:cross[\s-]?team|other\s+(?:repo|service|team)|shared\s+(?:api|library|module)|"
        r"upstream|downstream|dependency\s+on)\b",
        re.IGNORECASE,
    ),
    "risk_data": re.compile(
        r"\b(?:database|migration|schema|table|column|index|"
        r"ALTER\s+TABLE|DROP|data\s*loss|backup|rollback)\b",
        re.IGNORECASE,
    ),
}


def flag_risks(title: str, body: str) -> dict[str, bool]:
    """Detect risk flags from issue title and body.

    Returns dict with boolean values for each risk category.
    """
    text = f"{title}\n{body}"
    return {name: bool(pattern.search(text)) for name, pattern in _RISK_PATTERNS.items()}
