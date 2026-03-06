"""Tests for Story 4.2: Fleet Dashboard API — System Health.

Tests the HealthService for checking Temporal, JetStream, Postgres, Router.
"""

import asyncio
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.admin.health import (
    HealthService,
    ServiceHealth,
    ServiceStatus,
    SystemHealthResponse,
)


class TestServiceHealth:
    """Tests for ServiceHealth dataclass."""

    def test_to_dict_minimal(self) -> None:
        """to_dict returns minimal dict when no optional fields."""
        health = ServiceHealth(name="test", status=ServiceStatus.OK)
        result = health.to_dict()

        assert result == {"name": "test", "status": "OK"}

    def test_to_dict_full(self) -> None:
        """to_dict includes all optional fields when present."""
        health = ServiceHealth(
            name="test",
            status=ServiceStatus.DOWN,
            latency_ms=42.5,
            details={"host": "localhost"},
            error="Connection refused",
        )
        result = health.to_dict()

        assert result == {
            "name": "test",
            "status": "DOWN",
            "latency_ms": 42.5,
            "details": {"host": "localhost"},
            "error": "Connection refused",
        }


class TestSystemHealthResponse:
    """Tests for SystemHealthResponse dataclass."""

    def test_to_dict(self) -> None:
        """to_dict converts all services to dict format."""
        now = datetime.now(UTC)
        response = SystemHealthResponse(
            temporal=ServiceHealth(name="temporal", status=ServiceStatus.OK),
            jetstream=ServiceHealth(name="jetstream", status=ServiceStatus.OK),
            postgres=ServiceHealth(name="postgres", status=ServiceStatus.OK),
            router=ServiceHealth(name="router", status=ServiceStatus.OK),
            checked_at=now,
            overall_status=ServiceStatus.OK,
        )
        result = response.to_dict()

        assert result["temporal"]["status"] == "OK"
        assert result["jetstream"]["status"] == "OK"
        assert result["postgres"]["status"] == "OK"
        assert result["router"]["status"] == "OK"
        assert result["overall_status"] == "OK"
        assert result["checked_at"] == now.isoformat()


class TestHealthService:
    """Tests for HealthService."""

    @pytest.fixture
    def service(self) -> HealthService:
        """Create a HealthService with mock dependencies."""
        return HealthService(
            temporal_host="localhost:7233",
            nats_url="nats://localhost:4222",
            timeout_seconds=1.0,
        )

    @pytest.mark.asyncio
    async def test_check_router_always_ok(self, service: HealthService) -> None:
        """Router check is always OK (self-check)."""
        result = await service._check_router()

        assert result.name == "router"
        assert result.status == ServiceStatus.OK
        assert result.details.get("self_check") is True

    @pytest.mark.asyncio
    async def test_check_temporal_connection_refused(
        self, service: HealthService
    ) -> None:
        """Temporal check returns DOWN when connection refused."""
        with patch("asyncio.open_connection") as mock_conn:
            mock_conn.side_effect = ConnectionRefusedError("Connection refused")

            result = await service._check_temporal()

        assert result.name == "temporal"
        assert result.status == ServiceStatus.DOWN
        assert "Connection failed" in (result.error or "")

    @pytest.mark.asyncio
    async def test_check_temporal_timeout(self, service: HealthService) -> None:
        """Temporal check returns DOWN when timeout."""
        with patch("asyncio.open_connection") as mock_conn:
            mock_conn.side_effect = asyncio.TimeoutError()

            result = await service._check_temporal()

        assert result.name == "temporal"
        assert result.status == ServiceStatus.DOWN
        assert "timeout" in (result.error or "").lower()

    @pytest.mark.asyncio
    async def test_check_jetstream_connection_refused(
        self, service: HealthService
    ) -> None:
        """JetStream check returns DOWN when connection refused."""
        with patch("asyncio.open_connection") as mock_conn:
            mock_conn.side_effect = ConnectionRefusedError("Connection refused")

            result = await service._check_jetstream()

        assert result.name == "jetstream"
        assert result.status == ServiceStatus.DOWN
        assert "Connection failed" in (result.error or "")

    @pytest.mark.asyncio
    async def test_check_postgres_with_session(self, service: HealthService) -> None:
        """Postgres check uses provided session."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar.return_value = 1
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await service._check_postgres(session=mock_session)

        assert result.name == "postgres"
        assert result.status == ServiceStatus.OK
        assert result.details.get("connection") == "pooled"

    @pytest.mark.asyncio
    async def test_overall_status_all_ok(self, service: HealthService) -> None:
        """Overall status is OK when all services are OK."""
        services = [
            ServiceHealth(name="temporal", status=ServiceStatus.OK),
            ServiceHealth(name="jetstream", status=ServiceStatus.OK),
            ServiceHealth(name="postgres", status=ServiceStatus.OK),
            ServiceHealth(name="router", status=ServiceStatus.OK),
        ]

        result = service._compute_overall_status(services)

        assert result == ServiceStatus.OK

    @pytest.mark.asyncio
    async def test_overall_status_degraded_when_temporal_down(
        self, service: HealthService
    ) -> None:
        """Overall status is DEGRADED when non-critical service is down."""
        services = [
            ServiceHealth(name="temporal", status=ServiceStatus.DOWN),
            ServiceHealth(name="jetstream", status=ServiceStatus.OK),
            ServiceHealth(name="postgres", status=ServiceStatus.OK),
            ServiceHealth(name="router", status=ServiceStatus.OK),
        ]

        result = service._compute_overall_status(services)

        assert result == ServiceStatus.DEGRADED

    @pytest.mark.asyncio
    async def test_overall_status_down_when_postgres_down(
        self, service: HealthService
    ) -> None:
        """Overall status is DOWN when Postgres is down."""
        services = [
            ServiceHealth(name="temporal", status=ServiceStatus.OK),
            ServiceHealth(name="jetstream", status=ServiceStatus.OK),
            ServiceHealth(name="postgres", status=ServiceStatus.DOWN),
            ServiceHealth(name="router", status=ServiceStatus.OK),
        ]

        result = service._compute_overall_status(services)

        assert result == ServiceStatus.DOWN

    @pytest.mark.asyncio
    async def test_check_all_returns_health_response(
        self, service: HealthService
    ) -> None:
        """check_all returns SystemHealthResponse with all services."""
        with patch.object(
            service, "_check_temporal"
        ) as mock_temporal, patch.object(
            service, "_check_jetstream"
        ) as mock_jetstream, patch.object(
            service, "_check_postgres"
        ) as mock_postgres, patch.object(
            service, "_check_router"
        ) as mock_router:
            mock_temporal.return_value = ServiceHealth(
                name="temporal", status=ServiceStatus.OK
            )
            mock_jetstream.return_value = ServiceHealth(
                name="jetstream", status=ServiceStatus.OK
            )
            mock_postgres.return_value = ServiceHealth(
                name="postgres", status=ServiceStatus.OK
            )
            mock_router.return_value = ServiceHealth(
                name="router", status=ServiceStatus.OK
            )

            result = await service.check_all()

        assert isinstance(result, SystemHealthResponse)
        assert result.temporal.status == ServiceStatus.OK
        assert result.jetstream.status == ServiceStatus.OK
        assert result.postgres.status == ServiceStatus.OK
        assert result.router.status == ServiceStatus.OK
        assert result.overall_status == ServiceStatus.OK
        assert result.checked_at is not None

    @pytest.mark.asyncio
    async def test_check_all_handles_exceptions(self, service: HealthService) -> None:
        """check_all handles exceptions from individual checks."""
        with patch.object(
            service, "_check_temporal"
        ) as mock_temporal, patch.object(
            service, "_check_jetstream"
        ) as mock_jetstream, patch.object(
            service, "_check_postgres"
        ) as mock_postgres, patch.object(
            service, "_check_router"
        ) as mock_router:
            mock_temporal.side_effect = RuntimeError("Temporal error")
            mock_jetstream.return_value = ServiceHealth(
                name="jetstream", status=ServiceStatus.OK
            )
            mock_postgres.return_value = ServiceHealth(
                name="postgres", status=ServiceStatus.OK
            )
            mock_router.return_value = ServiceHealth(
                name="router", status=ServiceStatus.OK
            )

            result = await service.check_all()

        assert result.temporal.status == ServiceStatus.DOWN
        assert "Temporal error" in (result.temporal.error or "")
        assert result.overall_status == ServiceStatus.DEGRADED
