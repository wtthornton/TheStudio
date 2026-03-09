"""Unit tests for src/admin/merge_mode.py — Epic 10 AC3."""

import pytest

from src.admin.merge_mode import (
    MERGE_MODE_LABELS,
    MergeMode,
    RepoMergeConfig,
    clear,
    get_merge_mode,
    list_merge_modes,
    set_merge_mode,
)


@pytest.fixture(autouse=True)
def _reset_state():
    clear()
    yield
    clear()


class TestMergeModeEnum:
    def test_enum_values(self):
        assert MergeMode.DRAFT_ONLY == "draft_only"
        assert MergeMode.REQUIRE_REVIEW == "require_review"
        assert MergeMode.AUTO_MERGE == "auto_merge"

    def test_all_modes_have_labels(self):
        for mode in MergeMode:
            assert mode in MERGE_MODE_LABELS


class TestRepoMergeConfig:
    def test_default_mode_is_draft_only(self):
        config = RepoMergeConfig(repo_id="owner/repo")
        assert config.mode == MergeMode.DRAFT_ONLY

    def test_to_dict(self):
        config = RepoMergeConfig(repo_id="owner/repo", mode=MergeMode.AUTO_MERGE)
        d = config.to_dict()
        assert d["repo_id"] == "owner/repo"
        assert d["mode"] == "auto_merge"
        assert d["mode_label"] == "Auto Merge"

    def test_to_dict_all_modes(self):
        for mode in MergeMode:
            config = RepoMergeConfig(repo_id="r", mode=mode)
            d = config.to_dict()
            assert d["mode"] == mode.value
            assert d["mode_label"] == MERGE_MODE_LABELS[mode]


class TestGetSetMergeMode:
    def test_default_returns_draft_only(self):
        assert get_merge_mode("unknown/repo") == MergeMode.DRAFT_ONLY

    def test_set_and_get(self):
        set_merge_mode("owner/repo", MergeMode.REQUIRE_REVIEW)
        assert get_merge_mode("owner/repo") == MergeMode.REQUIRE_REVIEW

    def test_set_overwrites(self):
        set_merge_mode("owner/repo", MergeMode.REQUIRE_REVIEW)
        set_merge_mode("owner/repo", MergeMode.AUTO_MERGE)
        assert get_merge_mode("owner/repo") == MergeMode.AUTO_MERGE

    def test_different_repos_independent(self):
        set_merge_mode("repo-a", MergeMode.AUTO_MERGE)
        set_merge_mode("repo-b", MergeMode.REQUIRE_REVIEW)
        assert get_merge_mode("repo-a") == MergeMode.AUTO_MERGE
        assert get_merge_mode("repo-b") == MergeMode.REQUIRE_REVIEW


class TestListMergeModes:
    def test_empty_when_none_set(self):
        assert list_merge_modes() == {}

    def test_lists_all_set_modes(self):
        set_merge_mode("repo-a", MergeMode.AUTO_MERGE)
        set_merge_mode("repo-b", MergeMode.DRAFT_ONLY)
        modes = list_merge_modes()
        assert len(modes) == 2
        assert modes["repo-a"] == MergeMode.AUTO_MERGE
        assert modes["repo-b"] == MergeMode.DRAFT_ONLY

    def test_returns_copy(self):
        set_merge_mode("repo-a", MergeMode.AUTO_MERGE)
        modes = list_merge_modes()
        modes["repo-x"] = MergeMode.DRAFT_ONLY
        assert "repo-x" not in list_merge_modes()


class TestClear:
    def test_clear_removes_all(self):
        set_merge_mode("repo-a", MergeMode.AUTO_MERGE)
        set_merge_mode("repo-b", MergeMode.REQUIRE_REVIEW)
        clear()
        assert list_merge_modes() == {}
        assert get_merge_mode("repo-a") == MergeMode.DRAFT_ONLY
