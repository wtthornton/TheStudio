"""Admin API router for fleet management and operational visibility.

Story 4.2+: Admin UI backend APIs.
Architecture reference: thestudioarc/23-admin-control-ui.md
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from src.admin.health import HealthService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["admin"])

# Service instances (lazy initialization)
_health_service: HealthService | None = None


def get_health_service() -> HealthService:
    """Get or create health service instance."""
    global _health_service
    if _health_service is None:
        _health_service = HealthService()
    return _health_service


def set_health_service(service: HealthService | None) -> None:
    """Set health service (for testing)."""
    global _health_service
    _health_service = service


class ServiceHealthResponse(BaseModel):
    """Health status for a single service."""

    name: str
    status: str
    latency_ms: float | None = None
    details: dict[str, Any] | None = None
    error: str | None = None


class HealthResponse(BaseModel):
    """System health response."""

    temporal: ServiceHealthResponse
    jetstream: ServiceHealthResponse
    postgres: ServiceHealthResponse
    router: ServiceHealthResponse
    checked_at: datetime
    overall_status: str


@router.get("/health", response_model=HealthResponse)
async def get_system_health() -> HealthResponse:
    """Get system health status.

    Checks health of: Temporal, JetStream, Postgres, Router.
    Each service returns OK, DEGRADED, or DOWN.

    Returns:
        HealthResponse with status of all services and overall status.
    """
    service = get_health_service()
    health = await service.check_all()

    return HealthResponse(
        temporal=ServiceHealthResponse(
            name=health.temporal.name,
            status=health.temporal.status.value,
            latency_ms=health.temporal.latency_ms,
            details=health.temporal.details or None,
            error=health.temporal.error,
        ),
        jetstream=ServiceHealthResponse(
            name=health.jetstream.name,
            status=health.jetstream.status.value,
            latency_ms=health.jetstream.latency_ms,
            details=health.jetstream.details or None,
            error=health.jetstream.error,
        ),
        postgres=ServiceHealthResponse(
            name=health.postgres.name,
            status=health.postgres.status.value,
            latency_ms=health.postgres.latency_ms,
            details=health.postgres.details or None,
            error=health.postgres.error,
        ),
        router=ServiceHealthResponse(
            name=health.router.name,
            status=health.router.status.value,
            latency_ms=health.router.latency_ms,
            details=health.router.details or None,
            error=health.router.error,
        ),
        checked_at=health.checked_at,
        overall_status=health.overall_status.value,
    )
