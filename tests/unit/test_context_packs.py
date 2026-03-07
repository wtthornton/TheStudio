"""Tests for Service Context Pack schema and registry (Story 6.1)."""

import pytest

from src.context.service_context_pack import (
    PackRegistry,
    ServiceContextPack,
    get_context_packs,
    get_registry,
)


class TestServiceContextPack:
    """Tests for ServiceContextPack dataclass."""

    def test_to_dict_structure(self):
        pack = ServiceContextPack(
            name="test-pack", version="1.0",
            repo_patterns=["test-*"],
            conventions=["Use snake_case"],
            api_patterns=["REST endpoints"],
            constraints=["No raw SQL"],
            testing_notes=["Mock external calls"],
        )
        d = pack.to_dict()
        assert d["name"] == "test-pack"
        assert d["version"] == "1.0"
        assert d["content"]["conventions"] == ["Use snake_case"]
        assert d["content"]["api_patterns"] == ["REST endpoints"]
        assert d["content"]["constraints"] == ["No raw SQL"]
        assert d["content"]["testing_notes"] == ["Mock external calls"]

    def test_to_dict_empty_content(self):
        pack = ServiceContextPack(name="empty", version="0.1")
        d = pack.to_dict()
        assert d["content"]["conventions"] == []
        assert d["content"]["api_patterns"] == []

    def test_matches_repo_exact(self):
        pack = ServiceContextPack(name="p", version="1", repo_patterns=["my-repo"])
        assert pack.matches_repo("my-repo") is True
        assert pack.matches_repo("other-repo") is False

    def test_matches_repo_glob(self):
        pack = ServiceContextPack(name="p", version="1", repo_patterns=["api-*"])
        assert pack.matches_repo("api-gateway") is True
        assert pack.matches_repo("api-users") is True
        assert pack.matches_repo("web-frontend") is False

    def test_matches_repo_multiple_patterns(self):
        pack = ServiceContextPack(
            name="p", version="1", repo_patterns=["svc-*", "service-*"]
        )
        assert pack.matches_repo("svc-auth") is True
        assert pack.matches_repo("service-billing") is True
        assert pack.matches_repo("lib-utils") is False

    def test_matches_repo_no_patterns(self):
        pack = ServiceContextPack(name="p", version="1", repo_patterns=[])
        assert pack.matches_repo("anything") is False


class TestPackRegistry:
    """Tests for PackRegistry."""

    def test_register_and_get(self):
        registry = PackRegistry()
        pack = ServiceContextPack(name="p1", version="1", repo_patterns=["repo-a"])
        registry.register(pack)
        result = registry.get_packs("repo-a")
        assert len(result) == 1
        assert result[0].name == "p1"

    def test_get_packs_no_match(self):
        registry = PackRegistry()
        pack = ServiceContextPack(name="p1", version="1", repo_patterns=["repo-a"])
        registry.register(pack)
        assert registry.get_packs("repo-b") == []

    def test_multiple_packs_for_one_repo(self):
        registry = PackRegistry()
        registry.register(ServiceContextPack(name="p1", version="1", repo_patterns=["repo-*"]))
        registry.register(ServiceContextPack(name="p2", version="1", repo_patterns=["repo-alpha"]))
        result = registry.get_packs("repo-alpha")
        assert len(result) == 2
        names = {p.name for p in result}
        assert names == {"p1", "p2"}

    def test_all_packs(self):
        registry = PackRegistry()
        registry.register(ServiceContextPack(name="a", version="1"))
        registry.register(ServiceContextPack(name="b", version="1"))
        assert len(registry.all_packs) == 2

    def test_clear(self):
        registry = PackRegistry()
        registry.register(ServiceContextPack(name="a", version="1"))
        registry.clear()
        assert len(registry.all_packs) == 0


class TestGlobalRegistry:
    """Tests for global registry and get_context_packs."""

    def setup_method(self):
        get_registry().clear()

    def teardown_method(self):
        get_registry().clear()

    def test_get_context_packs_uses_registry(self):
        reg = get_registry()
        reg.register(ServiceContextPack(name="global-pack", version="1", repo_patterns=["g-*"]))
        result = get_context_packs("g-repo")
        assert len(result) == 1
        assert result[0].name == "global-pack"

    def test_get_context_packs_empty_when_no_match(self):
        assert get_context_packs("unknown-repo") == []
