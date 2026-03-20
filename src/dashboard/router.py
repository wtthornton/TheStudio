"""Dashboard API router — /api/v1/dashboard/ endpoints."""

from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


@router.get("/health")
async def health() -> dict[str, str]:
    """Dashboard health check."""
    return {"status": "ok"}
