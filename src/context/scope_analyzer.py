"""Scope analysis from GitHub issue content.

Examines issue title and body to estimate affected files and components.
Phase 0: keyword-based heuristics, not ML.
"""

import re
from dataclasses import dataclass, field

# Patterns that suggest file references
_FILE_PATTERN = re.compile(r"[\w/]+\.(?:py|ts|js|yaml|yml|json|toml|md|sql|sh)\b")
_COMPONENT_PATTERN = re.compile(
    r"\b(?:api|auth|database|db|frontend|backend|ingress|context|intent|"
    r"verification|publisher|agent|config|model|migration|test|ci|cd)\b",
    re.IGNORECASE,
)


@dataclass
class ScopeResult:
    """Structured scope analysis output."""

    affected_files_estimate: int = 0
    components: list[str] = field(default_factory=list)
    file_references: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "affected_files_estimate": self.affected_files_estimate,
            "components": self.components,
            "file_references": self.file_references,
        }


def analyze_scope(title: str, body: str) -> ScopeResult:
    """Analyze issue title + body for scope indicators.

    Returns estimated file count, detected components, and explicit file references.
    """
    text = f"{title}\n{body}"

    # Find explicit file references
    file_refs = list(set(_FILE_PATTERN.findall(text)))

    # Find component mentions
    component_matches = _COMPONENT_PATTERN.findall(text.lower())
    components = sorted(set(component_matches))

    # Estimate affected files
    if file_refs:
        affected = len(file_refs)
    elif components:
        # Rough heuristic: each component ~ 2-3 files
        affected = len(components) * 2
    else:
        affected = 1  # Default: single file change

    return ScopeResult(
        affected_files_estimate=affected,
        components=components,
        file_references=file_refs,
    )
