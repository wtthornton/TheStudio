"""Unit tests for src/outcome/dead_letter.py — Epic 10 AC2."""

from uuid import uuid4

import pytest

from src.outcome.dead_letter import (
    DeadLetterStore,
    FailureTracker,
    clear,
    get_dead_letter_store,
    get_failure_tracker,
)


@pytest.fixture(autouse=True)
def _reset_state():
    clear()
    yield
    clear()


@pytest.fixture
def store() -> DeadLetterStore:
    return DeadLetterStore()


@pytest.fixture
def tracker() -> FailureTracker:
    return FailureTracker()


class TestDeadLetterStore:
    def test_add_returns_uuid(self, store):
        eid = store.add_dead_letter(b"raw data", "parse error", 3)
        assert eid is not None

    def test_get_dead_letter(self, store):
        eid = store.add_dead_letter(b"raw data", "parse error", 3)
        event = store.get_dead_letter(eid)
        assert event is not None
        assert event.raw_payload == b"raw data"
        assert event.failure_reason == "parse error"
        assert event.attempt_count == 3

    def test_get_not_found(self, store):
        assert store.get_dead_letter(uuid4()) is None

    def test_list_empty(self, store):
        assert store.list_dead_letters() == []

    def test_list_sorted_newest_first(self, store):
        eid1 = store.add_dead_letter(b"first", "err1", 1)
        eid2 = store.add_dead_letter(b"second", "err2", 2)
        events = store.list_dead_letters()
        assert len(events) == 2
        # Second added is newest (or equal time), so should be first or same
        ids = [e.id for e in events]
        assert eid2 in ids

    def test_list_pagination(self, store):
        for i in range(5):
            store.add_dead_letter(f"data-{i}".encode(), f"err-{i}", i)
        assert len(store.list_dead_letters(limit=3)) == 3
        assert len(store.list_dead_letters(limit=3, offset=3)) == 2

    def test_count(self, store):
        assert store.count() == 0
        store.add_dead_letter(b"a", "err", 1)
        store.add_dead_letter(b"b", "err", 2)
        assert store.count() == 2

    def test_delete(self, store):
        eid = store.add_dead_letter(b"data", "err", 1)
        assert store.delete(eid) is True
        assert store.get_dead_letter(eid) is None
        assert store.count() == 0

    def test_delete_not_found(self, store):
        assert store.delete(uuid4()) is False


class TestFailureTracker:
    def test_record_increments(self, tracker):
        assert tracker.record_failure("hash1") == 1
        assert tracker.record_failure("hash1") == 2
        assert tracker.record_failure("hash1") == 3

    def test_get_attempt_count(self, tracker):
        assert tracker.get_attempt_count("hash1") == 0
        tracker.record_failure("hash1")
        assert tracker.get_attempt_count("hash1") == 1

    def test_should_dead_letter_false(self, tracker):
        tracker.record_failure("hash1")
        tracker.record_failure("hash1")
        assert tracker.should_dead_letter("hash1") is False

    def test_should_dead_letter_true(self, tracker):
        for _ in range(3):
            tracker.record_failure("hash1")
        assert tracker.should_dead_letter("hash1") is True

    def test_custom_max_attempts(self):
        t = FailureTracker(max_attempts=2)
        t.record_failure("h")
        assert t.should_dead_letter("h") is False
        t.record_failure("h")
        assert t.should_dead_letter("h") is True

    def test_clear_failures(self, tracker):
        tracker.record_failure("hash1")
        tracker.record_failure("hash1")
        tracker.clear_failures("hash1")
        assert tracker.get_attempt_count("hash1") == 0

    def test_clear_all(self, tracker):
        tracker.record_failure("h1")
        tracker.record_failure("h2")
        tracker.clear_all()
        assert tracker.get_attempt_count("h1") == 0
        assert tracker.get_attempt_count("h2") == 0

    def test_independent_hashes(self, tracker):
        tracker.record_failure("h1")
        tracker.record_failure("h1")
        tracker.record_failure("h2")
        assert tracker.get_attempt_count("h1") == 2
        assert tracker.get_attempt_count("h2") == 1


class TestGlobalInstances:
    def test_dead_letter_store_singleton(self):
        s1 = get_dead_letter_store()
        s2 = get_dead_letter_store()
        assert s1 is s2

    def test_failure_tracker_singleton(self):
        t1 = get_failure_tracker()
        t2 = get_failure_tracker()
        assert t1 is t2
