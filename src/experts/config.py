"""Expert system configuration — base path resolution.

Provides a single source of truth for where expert directories live.
Used by app.py lifespan and admin endpoints.
"""

import os
from pathlib import Path


def get_experts_base_path() -> Path:
    """Resolve the base path for expert directories.

    Uses EXPERTS_BASE_PATH env var if set, otherwise defaults to
    the ``experts/`` directory at the project root.
    """
    env_path = os.environ.get("EXPERTS_BASE_PATH")
    if env_path:
        return Path(env_path).resolve()
    # Default: project root / experts (two levels up from src/experts/config.py)
    return Path(__file__).resolve().parent.parent.parent / "experts"
