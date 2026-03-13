"""Unit tests for poll feed."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.ingress.poll.feed import feed_issues_to_pipeline, synthetic_delivery_id


def test_synthetic_delivery_id_deterministic() -> None:
    """Same inputs produce same ID."""
    a = synthetic_delivery_id("owner/repo", 42, "2026-03-11T12:00:00Z")
    b = synthetic_delivery_id("owner/repo", 42, "2026-03-11T12:00:00Z")
    assert a == b


def test_synthetic_delivery_id_format() -> None:
    """ID starts with poll- and includes repo and issue."""
    d = synthetic_delivery_id("owner/repo", 42, "2026-03-11T12:00:00Z")
    assert d.startswith("poll-")
    assert "42" in d
    assert "owner" in d
    assert "repo" in d


def test_synthetic_delivery_id_differs_on_updated_at() -> None:
    """Different updated_at produces different ID."""
    a = synthetic_delivery_id("owner/repo", 42, "2026-03-11T12:00:00Z")
    b = synthetic_delivery_id("owner/repo", 42, "2026-03-11T13:00:00Z")
    assert a != b


def test_synthetic_delivery_id_differs_on_issue_number() -> None:
    """Different issue numbers produce different IDs."""
    a = synthetic_delivery_id("owner/repo", 42, "2026-03-11T12:00:00Z")
    b = synthetic_delivery_id("owner/repo", 43, "2026-03-11T12:00:00Z")
    assert a != b


@pytest.mark.asyncio
@patch("src.ingress.poll.feed.start_workflow", new_callable=AsyncMock)
@patch("src.ingress.poll.feed.create_taskpacket", new_callable=AsyncMock)
@patch("src.ingress.poll.feed.is_duplicate", new_callable=AsyncMock)
async def test_feed_issues_creates_taskpackets(
    mock_is_duplicate: AsyncMock,
    mock_create: AsyncMock,
    mock_start_workflow: AsyncMock,
) -> None:
    """New issues create TaskPackets and start workflows."""
    mock_is_duplicate.return_value = False
    mock_tp = MagicMock()
    mock_tp.id = uuid4()
    mock_create.return_value = mock_tp

    issues = [
        {"number": 1, "updated_at": "2026-03-11T12:00:00Z"},
        {"number": 2, "updated_at": "2026-03-11T13:00:00Z"},
    ]
    session = AsyncMock()
    count = await feed_issues_to_pipeline(session, issues, "owner/repo")

    assert count == 2
    assert mock_create.call_count == 2
    assert mock_start_workflow.call_count == 2


@pytest.mark.asyncio
@patch("src.ingress.poll.feed.start_workflow", new_callable=AsyncMock)
@patch("src.ingress.poll.feed.create_taskpacket", new_callable=AsyncMock)
@patch("src.ingress.poll.feed.is_duplicate", new_callable=AsyncMock)
async def test_feed_issues_skips_duplicates(
    mock_is_duplicate: AsyncMock,
    mock_create: AsyncMock,
    mock_start_workflow: AsyncMock,
) -> None:
    """Duplicate issues are skipped."""
    mock_is_duplicate.return_value = True

    issues = [{"number": 1, "updated_at": "2026-03-11T12:00:00Z"}]
    session = AsyncMock()
    count = await feed_issues_to_pipeline(session, issues, "owner/repo")

    assert count == 0
    mock_create.assert_not_called()
    mock_start_workflow.assert_not_called()


@pytest.mark.asyncio
@patch("src.ingress.poll.feed.start_workflow", new_callable=AsyncMock)
@patch("src.ingress.poll.feed.create_taskpacket", new_callable=AsyncMock)
@patch("src.ingress.poll.feed.is_duplicate", new_callable=AsyncMock)
async def test_feed_issues_skips_missing_fields(
    mock_is_duplicate: AsyncMock,
    mock_create: AsyncMock,
    mock_start_workflow: AsyncMock,
) -> None:
    """Issues missing number or updated_at are skipped."""
    issues = [
        {"updated_at": "2026-03-11T12:00:00Z"},  # missing number
        {"number": 1},  # missing updated_at
    ]
    session = AsyncMock()
    count = await feed_issues_to_pipeline(session, issues, "owner/repo")

    assert count == 0
    mock_is_duplicate.assert_not_called()


@pytest.mark.asyncio
@patch("src.ingress.poll.feed.start_workflow", new_callable=AsyncMock)
@patch("src.ingress.poll.feed.create_taskpacket", new_callable=AsyncMock)
@patch("src.ingress.poll.feed.is_duplicate", new_callable=AsyncMock)
async def test_feed_issues_mixed_new_and_duplicate(
    mock_is_duplicate: AsyncMock,
    mock_create: AsyncMock,
    mock_start_workflow: AsyncMock,
) -> None:
    """Mix of new and duplicate issues — only new ones create TaskPackets."""
    mock_is_duplicate.side_effect = [True, False]  # first dup, second new
    mock_tp = MagicMock()
    mock_tp.id = uuid4()
    mock_create.return_value = mock_tp

    issues = [
        {"number": 1, "updated_at": "2026-03-11T12:00:00Z"},
        {"number": 2, "updated_at": "2026-03-11T13:00:00Z"},
    ]
    session = AsyncMock()
    count = await feed_issues_to_pipeline(session, issues, "owner/repo")

    assert count == 1
    assert mock_create.call_count == 1
