"""Prompt Injection Guard — input scanning for all pipeline agents.

Epic 23, Story 1.11: Defends against crafted GitHub issues containing
prompt injection, role hijacking, credential exfiltration, and other
adversarial patterns. Based on patterns from Hermes Agent's
``_scan_memory_content()`` and Appendix E threat catalogue.

Architecture reference: thestudioarc/08-agent-roles.md
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from enum import StrEnum
from typing import Final

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


class ThreatCategory(StrEnum):
    """Categories of prompt-injection threats (Appendix E)."""

    PROMPT_INJECTION = "prompt_injection"
    ROLE_HIJACKING = "role_hijacking"
    INSTRUCTION_OVERRIDE = "instruction_override"
    CREDENTIAL_EXFILTRATION = "credential_exfiltration"
    SECRET_FILE_ACCESS = "secret_file_access"  # noqa: S105
    INVISIBLE_UNICODE = "invisible_unicode"
    THESTUDIO_SPECIFIC = "thestudio_specific"


@dataclass(frozen=True)
class ThreatMatch:
    """A single threat detected during input scanning."""

    pattern_name: str
    matched_text: str
    threat_category: ThreatCategory


# ---------------------------------------------------------------------------
# Pattern registry — compiled once at module load
# ---------------------------------------------------------------------------

_PatternEntry = tuple[str, re.Pattern[str], ThreatCategory]

_PATTERNS: Final[list[_PatternEntry]] = [
    # Prompt injection
    (
        "ignore_instructions",
        re.compile(r"ignore\s+(previous|all|above)\s+instructions", re.IGNORECASE),
        ThreatCategory.PROMPT_INJECTION,
    ),
    # Role hijacking
    (
        "role_hijacking",
        re.compile(r"you\s+are\s+now", re.IGNORECASE),
        ThreatCategory.ROLE_HIJACKING,
    ),
    # Instruction override
    (
        "system_prompt_override",
        re.compile(r"system\s+prompt\s+override", re.IGNORECASE),
        ThreatCategory.INSTRUCTION_OVERRIDE,
    ),
    (
        "disregard_rules",
        re.compile(r"disregard\s+your\s+rules", re.IGNORECASE),
        ThreatCategory.INSTRUCTION_OVERRIDE,
    ),
    # Credential exfiltration
    (
        "curl_credential_exfil",
        re.compile(
            r"curl\b.*\$\(?\s*(KEY|TOKEN|SECRET)",
            re.IGNORECASE,
        ),
        ThreatCategory.CREDENTIAL_EXFILTRATION,
    ),
    # Secret file access
    (
        "secret_file_cat",
        re.compile(
            r"cat\b.*(?:\.env|credentials|\.pgpass)",
            re.IGNORECASE,
        ),
        ThreatCategory.SECRET_FILE_ACCESS,
    ),
    # TheStudio-specific gate bypass
    (
        "skip_verification",
        re.compile(r"skip\s+verification", re.IGNORECASE),
        ThreatCategory.THESTUDIO_SPECIFIC,
    ),
    (
        "bypass_gate",
        re.compile(r"bypass\s+gate", re.IGNORECASE),
        ThreatCategory.THESTUDIO_SPECIFIC,
    ),
    (
        "auto_approve",
        re.compile(r"auto[- ]?approve", re.IGNORECASE),
        ThreatCategory.THESTUDIO_SPECIFIC,
    ),
]

# Invisible Unicode code points (zero-width joiners, directional overrides, etc.)
_INVISIBLE_CODEPOINTS: Final[frozenset[int]] = frozenset(
    [
        0x200B,  # ZERO WIDTH SPACE
        0x200C,  # ZERO WIDTH NON-JOINER
        0x200D,  # ZERO WIDTH JOINER
        0x2060,  # WORD JOINER
        0xFEFF,  # ZERO WIDTH NO-BREAK SPACE (BOM)
        0x202A,  # LEFT-TO-RIGHT EMBEDDING
        0x202B,  # RIGHT-TO-LEFT EMBEDDING
        0x202C,  # POP DIRECTIONAL FORMATTING
        0x202D,  # LEFT-TO-RIGHT OVERRIDE
        0x202E,  # RIGHT-TO-LEFT OVERRIDE
    ]
)

_INVISIBLE_RE: Final[re.Pattern[str]] = re.compile(
    "[" + "".join(chr(cp) for cp in sorted(_INVISIBLE_CODEPOINTS)) + "]"
)


# ---------------------------------------------------------------------------
# Scanning functions
# ---------------------------------------------------------------------------


def _scan_text(text: str) -> list[ThreatMatch]:
    """Run all pattern checks against *text* and return matches."""
    matches: list[ThreatMatch] = []

    # Regex-based patterns
    for name, pattern, category in _PATTERNS:
        for m in pattern.finditer(text):
            matches.append(
                ThreatMatch(
                    pattern_name=name,
                    matched_text=m.group(),
                    threat_category=category,
                )
            )

    # Invisible unicode scan
    for m in _INVISIBLE_RE.finditer(text):
        matches.append(
            ThreatMatch(
                pattern_name="invisible_unicode",
                matched_text=repr(m.group()),
                threat_category=ThreatCategory.INVISIBLE_UNICODE,
            )
        )

    return matches


def scan_agent_input(text: str) -> list[ThreatMatch]:
    """Scan free-form agent input (e.g. GitHub issue body) for threats.

    Returns a list of :class:`ThreatMatch` instances — empty means clean.
    """
    matches = _scan_text(text)
    if matches:
        logger.warning(
            "prompt_guard.scan_agent_input: %d threat(s) detected",
            len(matches),
            extra={"threat_count": len(matches)},
        )
    return matches


def scan_system_prompt(template: str, rendered: str) -> list[ThreatMatch]:
    """Scan a rendered system prompt for injected threats.

    Compares the *rendered* output (which includes user-supplied data) against
    known attack patterns.  The *template* is accepted for future
    differential analysis but the current implementation scans *rendered* only.

    Returns a list of :class:`ThreatMatch` instances — empty means clean.
    """
    matches = _scan_text(rendered)
    if matches:
        logger.warning(
            "prompt_guard.scan_system_prompt: %d threat(s) in rendered prompt",
            len(matches),
            extra={"threat_count": len(matches)},
        )
    return matches
