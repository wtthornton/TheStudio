"""Unit tests for Repo Profile model validation (Story 0.8)."""

import pytest
from cryptography.fernet import Fernet
from pydantic import ValidationError

from src.repo.defaults import DEFAULT_REQUIRED_CHECKS, DEFAULT_TOOL_ALLOWLIST
from src.repo.repo_profile import RepoProfileCreate, RepoStatus, RepoTier
from src.repo.secrets import decrypt_secret, encrypt_secret


class TestRepoProfileCreate:
    def test_valid_create(self) -> None:
        data = RepoProfileCreate(
            owner="myorg",
            repo_name="myrepo",
            installation_id=12345,
            webhook_secret="whsec_test123",  # noqa: S106
        )
        assert data.owner == "myorg"
        assert data.repo_name == "myrepo"
        assert data.tier == RepoTier.OBSERVE

    def test_defaults_standard_checks(self) -> None:
        data = RepoProfileCreate(
            owner="o", repo_name="r", installation_id=1, webhook_secret="s"  # noqa: S106
        )
        assert data.required_checks == ["ruff", "pytest"]
        assert data.tool_allowlist == []

    def test_missing_required_fields(self) -> None:
        with pytest.raises(ValidationError):
            RepoProfileCreate()  # type: ignore[call-arg]


class TestRepoTier:
    def test_observe_is_default(self) -> None:
        assert RepoTier.OBSERVE.value == "observe"

    def test_invalid_tier(self) -> None:
        with pytest.raises(ValueError, match="nonexistent"):
            RepoTier("nonexistent")


class TestRepoStatus:
    def test_active_value(self) -> None:
        assert RepoStatus.ACTIVE.value == "active"

    def test_paused_value(self) -> None:
        assert RepoStatus.PAUSED.value == "paused"


class TestDefaults:
    def test_default_checks(self) -> None:
        assert DEFAULT_REQUIRED_CHECKS == ["ruff", "pytest"]

    def test_default_tools(self) -> None:
        assert "read_file" in DEFAULT_TOOL_ALLOWLIST
        assert "write_file" in DEFAULT_TOOL_ALLOWLIST


class TestSecretEncryption:
    @pytest.fixture(autouse=True)
    def _set_fernet_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        key = Fernet.generate_key().decode()
        monkeypatch.setattr("src.repo.secrets.settings", type("S", (), {"encryption_key": key})())
        # Reset cached fernet instance
        monkeypatch.setattr("src.repo.secrets._fernet", None)

    def test_roundtrip(self) -> None:
        original = "whsec_my_super_secret_key"
        encrypted = encrypt_secret(original)
        assert encrypted != original
        decrypted = decrypt_secret(encrypted)
        assert decrypted == original

    def test_different_encryptions(self) -> None:
        test_val = "test_secret"
        enc1 = encrypt_secret(test_val)
        enc2 = encrypt_secret(test_val)
        # Fernet uses a random IV, so encryptions differ
        assert enc1 != enc2
        assert decrypt_secret(enc1) == test_val
        assert decrypt_secret(enc2) == test_val
