"""Adversarial pattern detector — scans issue text for suspicious patterns.

Detects prompt injection attempts, credential leaks, and tool manipulation
commands in GitHub issue titles and bodies before they enter the pipeline.

Architecture reference: POLICIES.md (adversarial input handling)
"""

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class SuspiciousPattern:
    """A pattern match found in the scanned text."""

    pattern_name: str
    matched_text: str
    severity: str  # "warning" or "block"


# Configurable list of adversarial pattern definitions.
# Each entry: {"name": str, "regex": str, "severity": "warning" | "block"}
ADVERSARIAL_PATTERNS: list[dict[str, str]] = [
    # Prompt injection patterns (block)
    {
        "name": "prompt_injection_ignore_previous",
        "regex": r"ignore\s+(?:all\s+)?previous\s+instructions",
        "severity": "block",
    },
    {
        "name": "prompt_injection_ignore_all",
        "regex": r"ignore\s+all\s+instructions",
        "severity": "block",
    },
    {
        "name": "prompt_injection_you_are_now",
        "regex": r"you\s+are\s+now",
        "severity": "block",
    },
    {
        "name": "prompt_injection_new_system_prompt",
        "regex": r"new\s+system\s+prompt",
        "severity": "block",
    },
    # Credential patterns (warning)
    {
        "name": "credential_password",
        "regex": r"password\s*:",
        "severity": "warning",
    },
    {
        "name": "credential_api_key",
        "regex": r"api_key\s*=",
        "severity": "warning",
    },
    {
        "name": "credential_secret",
        "regex": r"secret\s*:",
        "severity": "warning",
    },
    {
        "name": "credential_token",
        "regex": r"token\s*:",
        "severity": "warning",
    },
    {
        "name": "credential_private_key",
        "regex": r"private_key",
        "severity": "warning",
    },
    # Tool manipulation patterns (block)
    {
        "name": "tool_manipulation_run_command",
        "regex": r"run\s+command",
        "severity": "block",
    },
    {
        "name": "tool_manipulation_execute_shell",
        "regex": r"execute\s+shell",
        "severity": "block",
    },
    {
        "name": "tool_manipulation_merge_directly",
        "regex": r"merge\s+directly",
        "severity": "block",
    },
    {
        "name": "tool_manipulation_push_to_main",
        "regex": r"push\s+to\s+main",
        "severity": "block",
    },
    {
        "name": "tool_manipulation_delete_branch",
        "regex": r"delete\s+branch",
        "severity": "block",
    },
]


def detect_suspicious_patterns(text: str) -> list[SuspiciousPattern]:
    """Scan text against all configured adversarial patterns.

    Args:
        text: The text to scan (typically issue title + body).

    Returns:
        List of SuspiciousPattern matches found. Empty if clean.
    """
    matches: list[SuspiciousPattern] = []
    text_lower = text.lower()

    for pattern_config in ADVERSARIAL_PATTERNS:
        regex = pattern_config["regex"]
        match = re.search(regex, text_lower, re.IGNORECASE)
        if match:
            matches.append(
                SuspiciousPattern(
                    pattern_name=pattern_config["name"],
                    matched_text=match.group(0),
                    severity=pattern_config["severity"],
                )
            )

    return matches
