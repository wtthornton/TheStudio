"""Tests for RepoProfileRow ORM model and Pydantic schemas — Epic 40 Story 40.0.

Validates that the new remote verification fields have correct column-level defaults,
are accepted in create/read/update schemas, and can be round-tripped via
from_attributes ORM loading.

Note: SQLAlchemy ORM column defaults (``default=...``) only fire on DB INSERT, not
on Python object instantiation.  For Python-unit tests (no live DB), we verify column
defaults by inspecting the ``__table__.columns`` metadata, and we verify field storage
by explicitly setting values and asserting them back.
"""

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import inspect as sa_inspect

from src.repo.repo_profile import (
    RepoProfileCreate,
    RepoProfileRead,
    RepoProfileRow,
    RepoProfileUpdate,
    RepoStatus,
    RepoTier,
)


def _col_default(col_name: str) -> object:
    """Return the Python-side column default value for a RepoProfileRow column."""
    col = RepoProfileRow.__table__.columns[col_name]
    return col.default.arg  # type: ignore[union-attr]


# ---------------------------------------------------------------------------
# RepoProfileRow ORM column-level defaults
# ---------------------------------------------------------------------------


class TestRepoProfileRowDefaults:
    """Verify that new remote verification columns carry correct column-level defaults.

    These are the values that PostgreSQL (and SQLAlchemy) will use on INSERT
    when the caller omits the field.
    """

    def test_remote_verification_enabled_default_false(self) -> None:
        assert _col_default("remote_verification_enabled") is False

    def test_test_command_default(self) -> None:
        assert _col_default("test_command") == "python -m pytest --tb=short -q"

    def test_lint_command_default(self) -> None:
        assert _col_default("lint_command") == "ruff check ."

    def test_install_command_default(self) -> None:
        assert _col_default("install_command") == "pip install -e ."

    def test_verify_timeout_seconds_default(self) -> None:
        assert _col_default("verify_timeout_seconds") == 900

    def test_clone_depth_default(self) -> None:
        assert _col_default("clone_depth") == 1

    def test_remote_verify_mode_default(self) -> None:
        assert _col_default("remote_verify_mode") == "subprocess"

    def test_remote_fields_can_be_overridden(self) -> None:
        row = RepoProfileRow(
            id=uuid4(),
            owner="acme",
            repo_name="myrepo",
            installation_id=1,
            webhook_secret_encrypted="enc",
            required_checks=[],
            tool_allowlist=[],
            remote_verification_enabled=True,
            test_command="pytest -x",
            lint_command="flake8 .",
            install_command="pip install -r requirements.txt",
            verify_timeout_seconds=600,
            clone_depth=5,
            remote_verify_mode="container",
        )
        assert row.remote_verification_enabled is True
        assert row.test_command == "pytest -x"
        assert row.lint_command == "flake8 ."
        assert row.install_command == "pip install -r requirements.txt"
        assert row.verify_timeout_seconds == 600
        assert row.clone_depth == 5
        assert row.remote_verify_mode == "container"


# ---------------------------------------------------------------------------
# RepoProfileRead Pydantic schema — from_attributes ORM round-trip
# ---------------------------------------------------------------------------


def _make_row(**overrides: object) -> RepoProfileRow:
    """Build a fully-populated RepoProfileRow for schema validation tests."""
    now = datetime(2026, 3, 22, 12, 0, 0, tzinfo=timezone.utc)
    defaults: dict = dict(
        id=uuid4(),
        owner="acme",
        repo_name="myrepo",
        installation_id=42,
        default_branch="main",
        tier=RepoTier.OBSERVE,
        required_checks=["ruff", "pytest"],
        tool_allowlist=[],
        webhook_secret_encrypted="enc",
        status=RepoStatus.ACTIVE,
        writes_enabled=True,
        poll_enabled=False,
        poll_interval_minutes=None,
        poll_etag=None,
        poll_last_modified=None,
        poll_since=None,
        poll_last_run_at=None,
        readiness_gate_enabled=False,
        merge_method="squash",
        remote_verification_enabled=False,
        test_command="python -m pytest --tb=short -q",
        lint_command="ruff check .",
        install_command="pip install -e .",
        verify_timeout_seconds=900,
        clone_depth=1,
        remote_verify_mode="subprocess",
        created_at=now,
        updated_at=now,
        deleted_at=None,
    )
    defaults.update(overrides)
    return RepoProfileRow(**defaults)


class TestRepoProfileReadSchema:
    """Validate the RepoProfileRead Pydantic schema handles remote verify fields."""

    def test_default_remote_fields_in_read(self) -> None:
        row = _make_row()
        profile = RepoProfileRead.model_validate(row)
        assert profile.remote_verification_enabled is False
        assert profile.test_command == "python -m pytest --tb=short -q"
        assert profile.lint_command == "ruff check ."
        assert profile.install_command == "pip install -e ."
        assert profile.verify_timeout_seconds == 900
        assert profile.clone_depth == 1
        assert profile.remote_verify_mode == "subprocess"

    def test_enabled_remote_fields_in_read(self) -> None:
        row = _make_row(
            remote_verification_enabled=True,
            test_command="pytest tests/ -v",
            lint_command="ruff check src/",
            install_command="pip install .[dev]",
            verify_timeout_seconds=300,
            clone_depth=10,
            remote_verify_mode="container",
        )
        profile = RepoProfileRead.model_validate(row)
        assert profile.remote_verification_enabled is True
        assert profile.test_command == "pytest tests/ -v"
        assert profile.lint_command == "ruff check src/"
        assert profile.install_command == "pip install .[dev]"
        assert profile.verify_timeout_seconds == 300
        assert profile.clone_depth == 10
        assert profile.remote_verify_mode == "container"

    def test_full_name_still_works(self) -> None:
        row = _make_row(owner="myorg", repo_name="myproject")
        profile = RepoProfileRead.model_validate(row)
        assert profile.full_name == "myorg/myproject"


# ---------------------------------------------------------------------------
# RepoProfileCreate — existing fields unaffected
# ---------------------------------------------------------------------------


class TestRepoProfileCreate:
    """Verify that RepoProfileCreate continues to work with no remote-verify fields required."""

    def test_create_minimal(self) -> None:
        create = RepoProfileCreate(
            owner="acme",
            repo_name="myrepo",
            installation_id=1,
            webhook_secret="secret",
        )
        assert create.owner == "acme"

    def test_create_does_not_expose_remote_fields(self) -> None:
        # RepoProfileCreate intentionally omits remote_verification fields
        # (they are server-side defaults). Verify no AttributeError.
        create = RepoProfileCreate(
            owner="acme",
            repo_name="myrepo",
            installation_id=1,
            webhook_secret="secret",
        )
        assert not hasattr(create, "remote_verification_enabled")


# ---------------------------------------------------------------------------
# RepoProfileUpdate — remote fields are optional patch fields
# ---------------------------------------------------------------------------


class TestRepoProfileUpdate:
    """Validate that RepoProfileUpdate accepts all new remote verify fields as optional."""

    def test_empty_update(self) -> None:
        update = RepoProfileUpdate()
        assert update.remote_verification_enabled is None
        assert update.test_command is None
        assert update.lint_command is None
        assert update.install_command is None
        assert update.verify_timeout_seconds is None
        assert update.clone_depth is None
        assert update.remote_verify_mode is None

    def test_enable_remote_verification(self) -> None:
        update = RepoProfileUpdate(remote_verification_enabled=True)
        assert update.remote_verification_enabled is True

    def test_partial_update_commands(self) -> None:
        update = RepoProfileUpdate(
            test_command="pytest -x --no-header",
            lint_command="ruff check --select E,W .",
        )
        assert update.test_command == "pytest -x --no-header"
        assert update.lint_command == "ruff check --select E,W ."
        assert update.install_command is None

    def test_update_all_remote_fields(self) -> None:
        update = RepoProfileUpdate(
            remote_verification_enabled=True,
            test_command="make test",
            lint_command="make lint",
            install_command="make install",
            verify_timeout_seconds=1200,
            clone_depth=0,
            remote_verify_mode="container",
        )
        assert update.remote_verification_enabled is True
        assert update.test_command == "make test"
        assert update.lint_command == "make lint"
        assert update.install_command == "make install"
        assert update.verify_timeout_seconds == 1200
        assert update.clone_depth == 0
        assert update.remote_verify_mode == "container"

    def test_disable_remote_verification(self) -> None:
        update = RepoProfileUpdate(remote_verification_enabled=False)
        assert update.remote_verification_enabled is False
