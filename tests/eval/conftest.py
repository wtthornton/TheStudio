"""Shared fixtures and markers for the evaluation test suite.

Epic 30, Story 30.1: Registers the ``requires_api_key`` and ``slow``
markers. Tests marked ``requires_api_key`` skip automatically when
``THESTUDIO_ANTHROPIC_API_KEY`` is not set.
"""

from __future__ import annotations

import os

import pytest


def pytest_configure(config: pytest.Config) -> None:
    """Register custom markers for eval tests."""
    config.addinivalue_line(
        "markers",
        "requires_api_key: skip when THESTUDIO_ANTHROPIC_API_KEY is not set",
    )
    config.addinivalue_line(
        "markers",
        "slow: marks tests as slow (deselect with -m 'not slow')",
    )


def pytest_collection_modifyitems(
    config: pytest.Config,
    items: list[pytest.Item],
) -> None:
    """Auto-skip tests marked ``requires_api_key`` when key is absent."""
    api_key = os.environ.get("THESTUDIO_ANTHROPIC_API_KEY", "")
    if api_key:
        return

    skip_marker = pytest.mark.skip(
        reason="THESTUDIO_ANTHROPIC_API_KEY not set — skipping API test",
    )
    for item in items:
        if "requires_api_key" in item.keywords:
            item.add_marker(skip_marker)
