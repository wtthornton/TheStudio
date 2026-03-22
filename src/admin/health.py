"""System health checking for Admin UI Fleet Dashboard.

Story 4.2: Fleet Dashboard API — System Health.
Architecture reference: thestudioarc/23-admin-control-ui.md (Fleet Dashboard mockup)

Checks health of:
- Temporal: Workflow engine connectivity
- JetStream: NATS message queue connectivity
- Postgres: Database connectivity
- Router: Self-check (always OK if responding)
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Any

from src.observability.tracing import get_tracer

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)
tracer = get_tracer("thestudio.admin.health")


class ServiceStatus(StrEnum):
    """Health status for a service."""

    OK = "OK"
    DEGRADED = "DEGRADED"
    DOWN = "DOWN"


@dataclass
class ServiceHealth:
    """Health status for a single service."""

    name: str
    status: ServiceStatus
    latency_ms: float | None = None
    details: dict[str, Any] = field(default_factory=dict)
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API response."""
        result: dict[str, Any] = {
            "name": self.name,
            "status": self.status.value,
        }
        if self.latency_ms is not None:
            result["latency_ms"] = self.latency_ms
        if self.details:
            result["details"] = self.details
        if self.error:
            result["error"] = self.error
        return result


@dataclass
class SystemHealthResponse:
    """Full system health response."""

    temporal: ServiceHealth
    jetstream: ServiceHealth
    postgres: ServiceHealth
    router: ServiceHealth
    checked_at: datetime
    overall_status: ServiceStatus

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "temporal": self.temporal.to_dict(),
            "jetstream": self.jetstream.to_dict(),
            "postgres": self.postgres.to_dict(),
            "router": self.router.to_dict(),
            "checked_at": self.checked_at.isoformat(),
            "overall_status": self.overall_status.value,
        }


class HealthService:
    """Service for checking system health.

    Usage:
        service = HealthService()
        health = await service.check_all()
    """

    def __init__(
        self,
        temporal_host: str | None = None,
        nats_url: str | None = None,
        timeout_seconds: float = 2.0,
    ) -> None:
        """Initialize health service.

        Args:
            temporal_host: Temporal server host:port. Defaults to settings.
            nats_url: NATS server URL. Defaults to settings.
            timeout_seconds: Timeout for each health check (default 2s).
        """
        self._temporal_host = temporal_host
        self._nats_url = nats_url
        self._timeout = timeout_seconds

    async def check_all(
        self,
        session: AsyncSession | None = None,
    ) -> SystemHealthResponse:
        """Check health of all services.

        Args:
            session: Optional database session for Postgres check.
                    If None, creates a new connection.

        Returns:
            SystemHealthResponse with status of all services.
        """
        with tracer.start_as_current_span("health.check_all") as span:
            results = await asyncio.gather(
                self._check_temporal(),
                self._check_jetstream(),
                self._check_postgres(session),
                self._check_router(),
                return_exceptions=True,
            )

            temporal_result, jetstream_result, postgres_result, router_result = results

            if isinstance(temporal_result, BaseException):
                logger.error("Temporal health check exception: %s", temporal_result)
                temporal = ServiceHealth(
                    name="temporal",
                    status=ServiceStatus.DOWN,
                    error=str(temporal_result),
                )
            else:
                temporal = temporal_result

            if isinstance(jetstream_result, BaseException):
                logger.error("JetStream health check exception: %s", jetstream_result)
                jetstream = ServiceHealth(
                    name="jetstream",
                    status=ServiceStatus.DOWN,
                    error=str(jetstream_result),
                )
            else:
                jetstream = jetstream_result

            if isinstance(postgres_result, BaseException):
                logger.error("Postgres health check exception: %s", postgres_result)
                postgres = ServiceHealth(
                    name="postgres",
                    status=ServiceStatus.DOWN,
                    error=str(postgres_result),
                )
            else:
                postgres = postgres_result

            if isinstance(router_result, BaseException):
                logger.error("Router health check exception: %s", router_result)
                router = ServiceHealth(
                    name="router",
                    status=ServiceStatus.DOWN,
                    error=str(router_result),
                )
            else:
                router = router_result

            overall = self._compute_overall_status([temporal, jetstream, postgres, router])

            span.set_attribute("thestudio.health.overall", overall.value)
            span.set_attribute("thestudio.health.temporal", temporal.status.value)
            span.set_attribute("thestudio.health.jetstream", jetstream.status.value)
            span.set_attribute("thestudio.health.postgres", postgres.status.value)

            checked_at = datetime.now(UTC)

            return SystemHealthResponse(
                temporal=temporal,
                jetstream=jetstream,
                postgres=postgres,
                router=router,
                checked_at=checked_at,
                overall_status=overall,
            )

    async def _check_temporal(self) -> ServiceHealth:
        """Check Temporal server health."""
        start = datetime.now(UTC)
        try:
            host = self._temporal_host
            if host is None:
                from src.settings import settings
                host = settings.temporal_host

            host_part, port_str = host.rsplit(":", 1)
            port = int(port_str)

            try:
                _reader, writer = await asyncio.wait_for(
                    asyncio.open_connection(host_part, port),
                    timeout=self._timeout,
                )
                writer.close()
                await writer.wait_closed()

                latency = (datetime.now(UTC) - start).total_seconds() * 1000

                return ServiceHealth(
                    name="temporal",
                    status=ServiceStatus.OK,
                    latency_ms=round(latency, 2),
                    details={"host": host},
                )
            except TimeoutError:
                return ServiceHealth(
                    name="temporal",
                    status=ServiceStatus.DOWN,
                    error=f"Connection timeout to {host}",
                    details={"host": host},
                )
            except (ConnectionRefusedError, OSError) as e:
                return ServiceHealth(
                    name="temporal",
                    status=ServiceStatus.DOWN,
                    error=f"Connection failed: {e}",
                    details={"host": host},
                )
        except Exception as e:
            logger.warning("Temporal health check failed: %s", e)
            return ServiceHealth(
                name="temporal",
                status=ServiceStatus.DOWN,
                error=str(e),
            )

    async def _check_jetstream(self) -> ServiceHealth:
        """Check NATS JetStream health."""
        start = datetime.now(UTC)
        try:
            url = self._nats_url
            if url is None:
                from src.settings import settings
                url = settings.nats_url

            host = url.replace("nats://", "").split(":")[0]
            port_str = url.replace("nats://", "").split(":")[-1]
            port = int(port_str) if port_str.isdigit() else 4222

            try:
                _reader, writer = await asyncio.wait_for(
                    asyncio.open_connection(host, port),
                    timeout=self._timeout,
                )
                writer.close()
                await writer.wait_closed()

                latency = (datetime.now(UTC) - start).total_seconds() * 1000

                return ServiceHealth(
                    name="jetstream",
                    status=ServiceStatus.OK,
                    latency_ms=round(latency, 2),
                    details={"url": url},
                )
            except TimeoutError:
                return ServiceHealth(
                    name="jetstream",
                    status=ServiceStatus.DOWN,
                    error=f"Connection timeout to {url}",
                    details={"url": url},
                )
            except (ConnectionRefusedError, OSError) as e:
                return ServiceHealth(
                    name="jetstream",
                    status=ServiceStatus.DOWN,
                    error=f"Connection failed: {e}",
                    details={"url": url},
                )
        except Exception as e:
            logger.warning("JetStream health check failed: %s", e)
            return ServiceHealth(
                name="jetstream",
                status=ServiceStatus.DOWN,
                error=str(e),
            )

    async def _check_postgres(
        self,
        session: AsyncSession | None = None,
    ) -> ServiceHealth:
        """Check Postgres database health."""
        start = datetime.now(UTC)
        try:
            if session is not None:
                from sqlalchemy import text
                result = await session.execute(text("SELECT 1"))
                result.scalar()
                latency = (datetime.now(UTC) - start).total_seconds() * 1000
                return ServiceHealth(
                    name="postgres",
                    status=ServiceStatus.OK,
                    latency_ms=round(latency, 2),
                    details={"connection": "pooled"},
                )

            from sqlalchemy import text
            from sqlalchemy.ext.asyncio import create_async_engine

            from src.settings import settings

            engine = create_async_engine(
                settings.database_url,
                pool_pre_ping=True,
            )

            try:
                async with engine.connect() as conn:
                    await asyncio.wait_for(
                        conn.execute(text("SELECT 1")),
                        timeout=self._timeout,
                    )
                latency = (datetime.now(UTC) - start).total_seconds() * 1000
                return ServiceHealth(
                    name="postgres",
                    status=ServiceStatus.OK,
                    latency_ms=round(latency, 2),
                    details={"connection": "new"},
                )
            except TimeoutError:
                return ServiceHealth(
                    name="postgres",
                    status=ServiceStatus.DOWN,
                    error="Query timeout",
                )
            finally:
                await engine.dispose()
        except Exception as e:
            logger.warning("Postgres health check failed: %s", e)
            return ServiceHealth(
                name="postgres",
                status=ServiceStatus.DOWN,
                error=str(e),
            )

    async def _check_router(self) -> ServiceHealth:
        """Check Router health (self-check).

        The router is always OK if this code is executing.
        This could be extended to check internal state in the future.
        """
        return ServiceHealth(
            name="router",
            status=ServiceStatus.OK,
            details={"self_check": True},
        )

    def _compute_overall_status(self, services: list[ServiceHealth]) -> ServiceStatus:
        """Compute overall status from individual service statuses.

        - All OK → OK
        - Any DOWN → DEGRADED (unless critical services are down)
        - Postgres DOWN or Router DOWN → DOWN
        """
        statuses = {s.name: s.status for s in services}

        if statuses.get("postgres") == ServiceStatus.DOWN:
            return ServiceStatus.DOWN
        if statuses.get("router") == ServiceStatus.DOWN:
            return ServiceStatus.DOWN

        if all(s.status == ServiceStatus.OK for s in services):
            return ServiceStatus.OK

        return ServiceStatus.DEGRADED
