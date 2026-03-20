"""Dashboard API router — /api/v1/dashboard/ endpoints."""

from fastapi import APIRouter

from src.dashboard.events import router as events_router

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])
router.include_router(events_router)


@router.get("/health")
async def health() -> dict[str, str]:
    """Dashboard health check."""
    return {"status": "ok"}
