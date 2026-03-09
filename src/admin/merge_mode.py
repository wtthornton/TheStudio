"""Merge mode controls — per-repo merge behavior for the Publisher.

Phase 4 deliverable: AC3 of Epic 10.
Controls how PRs are handled after verification + QA pass.
"""

from __future__ import annotations

import enum
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class MergeMode(enum.StrEnum):
    """Merge behavior for published PRs."""

    DRAFT_ONLY = "draft_only"
    REQUIRE_REVIEW = "require_review"
    AUTO_MERGE = "auto_merge"


MERGE_MODE_LABELS: dict[MergeMode, str] = {
    MergeMode.DRAFT_ONLY: "Draft Only",
    MergeMode.REQUIRE_REVIEW: "Require Review",
    MergeMode.AUTO_MERGE: "Auto Merge",
}


@dataclass
class RepoMergeConfig:
    """Per-repo merge configuration."""

    repo_id: str
    mode: MergeMode = MergeMode.DRAFT_ONLY

    def to_dict(self) -> dict[str, str]:
        return {
            "repo_id": self.repo_id,
            "mode": self.mode.value,
            "mode_label": MERGE_MODE_LABELS[self.mode],
        }


# In-memory store for merge mode per repo
_merge_modes: dict[str, MergeMode] = {}


def get_merge_mode(repo_id: str) -> MergeMode:
    """Get the merge mode for a repo (defaults to DRAFT_ONLY)."""
    return _merge_modes.get(repo_id, MergeMode.DRAFT_ONLY)


def set_merge_mode(repo_id: str, mode: MergeMode) -> None:
    """Set the merge mode for a repo."""
    _merge_modes[repo_id] = mode
    logger.info("Merge mode for %s set to %s", repo_id, mode.value)


def list_merge_modes() -> dict[str, MergeMode]:
    """List all configured merge modes."""
    return dict(_merge_modes)


def clear() -> None:
    """Clear all merge modes (for testing)."""
    _merge_modes.clear()
