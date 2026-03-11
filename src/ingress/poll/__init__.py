"""Poll intake — optional GitHub API polling for issue events.

Epic 17 — Poll for Issues as Backup to Webhooks.
Use when webhooks are unavailable (no public URL) or as backup.
"""

from src.ingress.poll.client import fetch_issues
from src.ingress.poll.models import PollConfig, PollResult, RateLimitError

__all__ = [
    "PollConfig",
    "PollResult",
    "RateLimitError",
    "fetch_issues",
]
