"""Unit tests for poll feed."""

from src.ingress.poll.feed import synthetic_delivery_id


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
