"""Base interface for verification check runners."""

from dataclasses import dataclass


@dataclass
class CheckResult:
    """Result from a single verification check."""

    name: str
    passed: bool
    details: str = ""
    duration_ms: int = 0
