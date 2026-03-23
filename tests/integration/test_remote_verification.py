"""Integration tests for remote verification (Story 40.8).

These tests require network access and a valid GitHub token. They clone
the production test rig repo and run the full remote verification pipeline.

To run:
    INTEGRATION_TEST_TOKEN=ghp_xxx pytest tests/integration/test_remote_verification.py -m integration
"""

import os

import pytest

from src.verification.remote.orchestrator import verify_remote

_TOKEN = os.environ.get("INTEGRATION_TEST_TOKEN", "")
_OWNER = "wtthornton"
_REPO = "thestudio-production-test-rig"
_BRANCH = "main"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_remote_verify_known_good():
    """Clones test rig, runs verification, confirms all checks pass."""
    if not _TOKEN:
        pytest.skip("INTEGRATION_TEST_TOKEN not set")

    results = await verify_remote(
        owner=_OWNER,
        repo=_REPO,
        branch=_BRANCH,
        token=_TOKEN,
        changed_files=[],
        test_command="python -m pytest --tb=short -q",
        lint_command="ruff check .",
        install_command="pip install -e .",
        verify_timeout_seconds=300,
        clone_depth=1,
        clone_timeout=60,
        install_timeout=120,
        lint_timeout=60,
        test_timeout=120,
    )

    # At minimum install should have run
    assert len(results) >= 1
    # All steps should pass on the known-good test rig
    for cr in results:
        assert cr.passed, f"Check '{cr.name}' failed: {cr.details}"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_remote_verify_known_bad():
    """Clones test rig, introduces syntax error, confirms verification fails.

    Strategy: clone the repo normally, then use a modified test_command
    that deliberately fails (simulating a syntax error scenario).
    """
    if not _TOKEN:
        pytest.skip("INTEGRATION_TEST_TOKEN not set")

    # We can't easily modify files after clone in the orchestrator,
    # so instead we use a test command that will always fail
    results = await verify_remote(
        owner=_OWNER,
        repo=_REPO,
        branch=_BRANCH,
        token=_TOKEN,
        changed_files=[],
        test_command="python -c \"import sys; sys.exit(1)\"",
        lint_command="ruff check .",
        install_command="pip install -e .",
        verify_timeout_seconds=300,
        clone_depth=1,
        clone_timeout=60,
        install_timeout=120,
        lint_timeout=60,
        test_timeout=120,
    )

    # At least install + lint + test should have run
    assert len(results) >= 2
    # Find the remote_pytest result (or the deliberate failure)
    has_failure = any(not cr.passed for cr in results)
    assert has_failure, "Expected at least one check to fail with bad test command"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_remote_verify_clone_nonexistent_branch():
    """Cloning a nonexistent branch triggers the fallback path."""
    if not _TOKEN:
        pytest.skip("INTEGRATION_TEST_TOKEN not set")

    results = await verify_remote(
        owner=_OWNER,
        repo=_REPO,
        branch="nonexistent-branch-abc123",
        token=_TOKEN,
        changed_files=[],
        test_command="python -m pytest --tb=short -q",
        lint_command="ruff check .",
        install_command="pip install -e .",
        verify_timeout_seconds=300,
        clone_depth=1,
        clone_timeout=60,
        install_timeout=120,
        lint_timeout=60,
        test_timeout=120,
    )

    # Should still get results (via fallback to main branch)
    assert len(results) >= 1
