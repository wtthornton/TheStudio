"""Unit tests for src/outcome/quarantine.py — Epic 10 AC1."""

from uuid import uuid4

import pytest

from src.outcome.models import QuarantineReason
from src.outcome.quarantine import QuarantineStore, clear, get_quarantine_store


@pytest.fixture(autouse=True)
def _reset_state():
    clear()
    yield
    clear()


@pytest.fixture
def store() -> QuarantineStore:
    return QuarantineStore()


class TestQuarantine:
    def test_quarantine_returns_uuid(self, store):
        qid = store.quarantine(
            event_payload={"key": "value"},
            reason=QuarantineReason.MISSING_CORRELATION_ID,
        )
        assert qid is not None

    def test_quarantine_with_metadata(self, store):
        qid = store.quarantine(
            event_payload={"data": 1},
            reason=QuarantineReason.UNKNOWN_REPO,
            repo_id="owner/repo",
            category="verification_passed",
        )
        event = store.get_quarantined(qid)
        assert event is not None
        assert event.repo_id == "owner/repo"
        assert event.category == "verification_passed"
        assert event.reason == QuarantineReason.UNKNOWN_REPO


class TestListQuarantined:
    def test_empty(self, store):
        assert store.list_quarantined() == []

    def test_filter_by_repo(self, store):
        store.quarantine({"a": 1}, QuarantineReason.UNKNOWN_REPO, repo_id="repo-a")
        store.quarantine({"b": 2}, QuarantineReason.UNKNOWN_REPO, repo_id="repo-b")
        results = store.list_quarantined(repo_id="repo-a")
        assert len(results) == 1
        assert results[0].repo_id == "repo-a"

    def test_filter_by_reason(self, store):
        store.quarantine({"a": 1}, QuarantineReason.MISSING_CORRELATION_ID)
        store.quarantine({"b": 2}, QuarantineReason.UNKNOWN_REPO)
        results = store.list_quarantined(reason=QuarantineReason.UNKNOWN_REPO)
        assert len(results) == 1
        assert results[0].reason == QuarantineReason.UNKNOWN_REPO

    def test_filter_by_category(self, store):
        store.quarantine({"a": 1}, QuarantineReason.INVALID_EVENT, category="qa_passed")
        store.quarantine({"b": 2}, QuarantineReason.INVALID_EVENT, category="verify")
        results = store.list_quarantined(category="qa_passed")
        assert len(results) == 1

    def test_excludes_replayed_by_default(self, store):
        qid = store.quarantine({"a": 1}, QuarantineReason.MISSING_CORRELATION_ID)
        store.mark_replayed(qid)
        assert store.list_quarantined() == []

    def test_includes_replayed_when_requested(self, store):
        qid = store.quarantine({"a": 1}, QuarantineReason.MISSING_CORRELATION_ID)
        store.mark_replayed(qid)
        results = store.list_quarantined(include_replayed=True)
        assert len(results) == 1

    def test_pagination(self, store):
        for i in range(5):
            store.quarantine({"i": i}, QuarantineReason.MISSING_CORRELATION_ID)
        assert len(store.list_quarantined(limit=3)) == 3
        assert len(store.list_quarantined(limit=3, offset=3)) == 2


class TestGetQuarantined:
    def test_found(self, store):
        qid = store.quarantine({"data": 1}, QuarantineReason.UNKNOWN_REPO)
        event = store.get_quarantined(qid)
        assert event is not None
        assert event.event_payload == {"data": 1}

    def test_not_found(self, store):
        assert store.get_quarantined(uuid4()) is None


class TestMarkCorrected:
    def test_corrects_event(self, store):
        qid = store.quarantine({"bad": True}, QuarantineReason.INVALID_EVENT)
        assert store.mark_corrected(qid, {"fixed": True}) is True
        event = store.get_quarantined(qid)
        assert event.corrected_payload == {"fixed": True}
        assert event.corrected_at is not None

    def test_cannot_correct_replayed(self, store):
        qid = store.quarantine({"a": 1}, QuarantineReason.MISSING_CORRELATION_ID)
        store.mark_replayed(qid)
        assert store.mark_corrected(qid, {"fix": True}) is False

    def test_correct_not_found(self, store):
        assert store.mark_corrected(uuid4(), {}) is False


class TestMarkReplayed:
    def test_replays_event(self, store):
        qid = store.quarantine({"data": 1}, QuarantineReason.UNKNOWN_REPO)
        assert store.mark_replayed(qid) is True
        event = store.get_quarantined(qid)
        assert event.replayed_at is not None

    def test_replay_not_found(self, store):
        assert store.mark_replayed(uuid4()) is False


class TestCountByReason:
    def test_empty(self, store):
        assert store.count_by_reason() == {}

    def test_counts(self, store):
        store.quarantine({"a": 1}, QuarantineReason.MISSING_CORRELATION_ID)
        store.quarantine({"b": 2}, QuarantineReason.MISSING_CORRELATION_ID)
        store.quarantine({"c": 3}, QuarantineReason.UNKNOWN_REPO)
        counts = store.count_by_reason()
        assert counts[QuarantineReason.MISSING_CORRELATION_ID] == 2
        assert counts[QuarantineReason.UNKNOWN_REPO] == 1

    def test_excludes_replayed(self, store):
        qid = store.quarantine({"a": 1}, QuarantineReason.MISSING_CORRELATION_ID)
        store.quarantine({"b": 2}, QuarantineReason.MISSING_CORRELATION_ID)
        store.mark_replayed(qid)
        counts = store.count_by_reason()
        assert counts[QuarantineReason.MISSING_CORRELATION_ID] == 1

    def test_filter_by_repo(self, store):
        store.quarantine({"a": 1}, QuarantineReason.UNKNOWN_REPO, repo_id="r1")
        store.quarantine({"b": 2}, QuarantineReason.UNKNOWN_REPO, repo_id="r2")
        counts = store.count_by_reason(repo_id="r1")
        assert counts[QuarantineReason.UNKNOWN_REPO] == 1


class TestCountByCategory:
    def test_counts(self, store):
        store.quarantine({"a": 1}, QuarantineReason.INVALID_EVENT, category="qa")
        store.quarantine({"b": 2}, QuarantineReason.INVALID_EVENT, category="qa")
        store.quarantine({"c": 3}, QuarantineReason.INVALID_EVENT, category="verify")
        counts = store.count_by_category()
        assert counts["qa"] == 2
        assert counts["verify"] == 1

    def test_none_category_becomes_unknown(self, store):
        store.quarantine({"a": 1}, QuarantineReason.INVALID_EVENT)
        counts = store.count_by_category()
        assert counts["unknown"] == 1


class TestDelete:
    def test_delete_found(self, store):
        qid = store.quarantine({"a": 1}, QuarantineReason.UNKNOWN_REPO)
        assert store.delete(qid) is True
        assert store.get_quarantined(qid) is None

    def test_delete_not_found(self, store):
        assert store.delete(uuid4()) is False


class TestGetQuarantineStore:
    def test_returns_singleton(self):
        s1 = get_quarantine_store()
        s2 = get_quarantine_store()
        assert s1 is s2
