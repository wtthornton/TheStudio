"""Tests for the P0 health gate module.

Verifies that the health gate correctly:
  1. Reports healthy status when all services are up.
  2. Names failed services with remediation hints on failure.
  3. Completes within the 15-second timeout budget.
  4. Produces a human-readable summary.

These tests can run without the Docker stack — they mock httpx and socket
to simulate healthy/unhealthy service responses.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from tests.p0.health import (
    HealthReport,
    ServiceStatus,
    check_stack_health,
)


class TestHealthReport:
    """Unit tests for HealthReport dataclass."""

    def test_all_healthy(self) -> None:
        """HealthReport.all_healthy is True when every service is healthy."""
        report = HealthReport(
            services=[
                ServiceStatus(name="Caddy + App", healthy=True, detail="HTTP 200"),
                ServiceStatus(name="Temporal", healthy=True, detail="OK (5ms)"),
                ServiceStatus(name="Postgres", healthy=True, detail="OK (2ms)"),
            ],
            duration_ms=120.0,
        )
        assert report.all_healthy is True
        assert report.failed == []

    def test_reports_failed_services(self) -> None:
        """HealthReport.failed lists only unhealthy services."""
        report = HealthReport(
            services=[
                ServiceStatus(name="Caddy + App", healthy=True),
                ServiceStatus(
                    name="Temporal",
                    healthy=False,
                    detail="Connection refused",
                    remediation="docker compose up temporal",
                ),
                ServiceStatus(name="Postgres", healthy=True),
            ],
            duration_ms=200.0,
        )
        assert report.all_healthy is False
        assert len(report.failed) == 1
        assert report.failed[0].name == "Temporal"

    def test_summary_includes_failed_service_name(self) -> None:
        """Summary output names failed services and includes remediation."""
        report = HealthReport(
            services=[
                ServiceStatus(
                    name="Caddy + App",
                    healthy=False,
                    detail="Connection refused",
                    remediation="cd infra && docker compose up caddy",
                ),
            ],
            duration_ms=50.0,
        )
        summary = report.summary()
        assert "Caddy + App" in summary
        assert "FAIL" in summary
        assert "Remediation" in summary
        assert "docker compose" in summary

    def test_summary_format_healthy(self) -> None:
        """Summary for all-healthy stack does not include Remediation section."""
        report = HealthReport(
            services=[
                ServiceStatus(name="Caddy + App", healthy=True, detail="HTTP 200"),
            ],
            duration_ms=80.0,
        )
        summary = report.summary()
        assert "OK" in summary
        assert "Remediation" not in summary


class TestCheckStackHealth:
    """Unit tests for check_stack_health (mocked HTTP — no Docker stack needed)."""

    def test_healthy_stack_returns_all_ok(self) -> None:
        """check_stack_health reports healthy when all probes succeed."""
        mock_healthz = MagicMock()
        mock_healthz.status_code = 200

        mock_admin_health = MagicMock()
        mock_admin_health.status_code = 200
        mock_admin_health.json.return_value = {
            "overall_status": "OK",
            "temporal": {"status": "OK", "latency_ms": 5},
            "jetstream": {"status": "OK", "latency_ms": 3},
            "postgres": {"status": "OK", "latency_ms": 2},
            "router": {"status": "OK", "latency_ms": 1},
        }

        def mock_get(url: str, **kwargs) -> MagicMock:
            if "/healthz" in url:
                return mock_healthz
            if "/admin/health" in url:
                return mock_admin_health
            raise ValueError(f"Unexpected URL: {url}")

        with (
            patch("tests.p0.health.httpx.get", side_effect=mock_get),
            patch("socket.create_connection") as mock_socket,
        ):
            mock_socket.return_value.__enter__ = MagicMock()
            mock_socket.return_value.__exit__ = MagicMock(return_value=False)

            report = check_stack_health(
                base_url="https://localhost:9443",
                admin_password="test-pass",
            )

        assert report.all_healthy is True
        service_names = [s.name for s in report.services]
        assert "Caddy + App" in service_names
        assert "Temporal" in service_names

    def test_caddy_down_names_caddy_as_failed(self) -> None:
        """When Caddy is unreachable, it is named as the failed service."""
        import httpx as _httpx

        with patch(
            "tests.p0.health.httpx.get",
            side_effect=_httpx.ConnectError("Connection refused"),
        ):
            report = check_stack_health(base_url="https://localhost:9443")

        assert report.all_healthy is False
        caddy = next(s for s in report.services if "Caddy" in s.name)
        assert caddy.healthy is False
        assert "Connection refused" in caddy.detail

    def test_completes_under_15_seconds(self) -> None:
        """Health check completes in under 15 seconds even on failure."""
        import httpx as _httpx

        with patch(
            "tests.p0.health.httpx.get",
            side_effect=_httpx.ConnectError("Connection refused"),
        ):
            report = check_stack_health(
                base_url="https://localhost:9443",
                timeout=5.0,
            )

        assert report.duration_ms < 15_000, (
            f"Health check took {report.duration_ms:.0f}ms (must be < 15000ms)"
        )

    def test_backend_failure_names_specific_service(self) -> None:
        """When a backend service is down, it's named specifically."""
        mock_healthz = MagicMock()
        mock_healthz.status_code = 200

        mock_admin_health = MagicMock()
        mock_admin_health.status_code = 200
        mock_admin_health.json.return_value = {
            "overall_status": "DEGRADED",
            "temporal": {"status": "OK", "latency_ms": 5},
            "jetstream": {"status": "ERROR", "error": "Connection refused"},
            "postgres": {"status": "OK", "latency_ms": 2},
            "router": {"status": "OK", "latency_ms": 1},
        }

        def mock_get(url: str, **kwargs) -> MagicMock:
            if "/healthz" in url:
                return mock_healthz
            if "/admin/health" in url:
                return mock_admin_health
            raise ValueError(f"Unexpected URL: {url}")

        with (
            patch("tests.p0.health.httpx.get", side_effect=mock_get),
            patch("socket.create_connection") as mock_socket,
        ):
            mock_socket.return_value.__enter__ = MagicMock()
            mock_socket.return_value.__exit__ = MagicMock(return_value=False)

            report = check_stack_health(
                base_url="https://localhost:9443",
                admin_password="test-pass",
            )

        assert report.all_healthy is False
        nats = next(s for s in report.services if "NATS" in s.name)
        assert nats.healthy is False
        assert "ERROR" in nats.detail
