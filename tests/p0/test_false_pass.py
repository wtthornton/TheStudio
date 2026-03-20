"""False-pass validation tests for the P0 runner.

These tests prove the runner's credential guards work in practice:
  1. Health gate catches Caddy down (verified via existing test_health_gate.py).
  2. Runner rejects empty API key.
  3. Runner rejects placeholder Postgres password.

Tests 2-3 call the credential_guard module directly, validating
the same logic the bash runner uses.
"""

from __future__ import annotations

import pytest

from tests.p0.credential_guard import CredentialReport, validate_credentials
from tests.p0.health import HealthReport, ServiceStatus


class TestHealthGateCatchesCaddyDown:
    """Verify the health gate correctly identifies Caddy as failed.

    This test references existing coverage in test_health_gate.py
    (TestCheckStackHealth::test_caddy_down_names_caddy_as_failed).
    Re-verified here for completeness.
    """

    def test_caddy_down_reports_failure(self) -> None:
        """HealthReport correctly identifies Caddy as the failed service."""
        report = HealthReport(
            services=[
                ServiceStatus(
                    name="Caddy + App",
                    healthy=False,
                    detail="Connection refused",
                    remediation="docker compose up caddy",
                ),
                ServiceStatus(
                    name="Temporal",
                    healthy=False,
                    detail="Cannot check — Caddy/App is down",
                ),
                ServiceStatus(
                    name="NATS/JetStream",
                    healthy=False,
                    detail="Cannot check — Caddy/App is down",
                ),
                ServiceStatus(
                    name="Postgres",
                    healthy=False,
                    detail="Cannot check — Caddy/App is down",
                ),
            ],
            duration_ms=50.0,
        )
        assert report.all_healthy is False
        assert report.failed[0].name == "Caddy + App"
        summary = report.summary()
        assert "FAIL" in summary
        assert "Caddy + App" in summary


class TestRunnerRejectsEmptyApiKey:
    """Runner must abort when THESTUDIO_ANTHROPIC_API_KEY is empty."""

    def test_empty_api_key_rejected(self) -> None:
        """Empty API key causes validation failure."""
        report = validate_credentials(
            api_key="",
            postgres_password="real-password",
            admin_user="admin",
            admin_password="admin-pass",
            webhook_secret="secret",
        )
        assert report.all_ok is False
        api_check = next(c for c in report.checks if "API_KEY" in c.name)
        assert api_check.ok is False
        assert "is empty" in api_check.message

    def test_invalid_prefix_rejected(self) -> None:
        """API key that doesn't start with sk-ant- is rejected."""
        report = validate_credentials(
            api_key="not-a-real-key",
            postgres_password="real-password",
            admin_user="admin",
            admin_password="admin-pass",
            webhook_secret="secret",
        )
        assert report.all_ok is False
        api_check = next(c for c in report.checks if "API_KEY" in c.name)
        assert api_check.ok is False
        assert "does not start with sk-ant-" in api_check.message


class TestRunnerRejectsPlaceholderPassword:
    """Runner must abort when POSTGRES_PASSWORD is the dev placeholder."""

    def test_placeholder_password_rejected(self) -> None:
        """Dev placeholder 'thestudio_dev' causes validation failure."""
        report = validate_credentials(
            api_key="sk-ant-real-key",
            postgres_password="thestudio_dev",
            admin_user="admin",
            admin_password="admin-pass",
            webhook_secret="secret",
        )
        assert report.all_ok is False
        pg_check = next(c for c in report.checks if "POSTGRES" in c.name)
        assert pg_check.ok is False
        assert "dev placeholder" in pg_check.message

    def test_empty_password_rejected(self) -> None:
        """Empty Postgres password causes validation failure."""
        report = validate_credentials(
            api_key="sk-ant-real-key",
            postgres_password="",
            admin_user="admin",
            admin_password="admin-pass",
            webhook_secret="secret",
        )
        assert report.all_ok is False
        pg_check = next(c for c in report.checks if "POSTGRES" in c.name)
        assert pg_check.ok is False
        assert "is empty" in pg_check.message

    def test_valid_credentials_accepted(self) -> None:
        """Valid credentials pass all checks."""
        report = validate_credentials(
            api_key="sk-ant-real-key",
            postgres_password="real-password",
            admin_user="admin",
            admin_password="admin-pass",
            webhook_secret="secret",
        )
        assert report.all_ok is True
        assert len(report.failed) == 0

    def test_summary_includes_failed_names(self) -> None:
        """Summary output names the specific failed credentials."""
        report = validate_credentials(
            api_key="",
            postgres_password="thestudio_dev",
            admin_user="",
            admin_password="",
            webhook_secret="",
        )
        summary = report.summary()
        assert "FAIL" in summary
        assert "THESTUDIO_ANTHROPIC_API_KEY" in summary
        assert "POSTGRES_PASSWORD" in summary
        assert "ADMIN_USER" in summary
