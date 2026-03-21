"""Dashboard API router — /api/v1/dashboard/ endpoints."""

from fastapi import APIRouter

from src.dashboard.events import router as events_router
from src.dashboard.tasks import router as tasks_router

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])
router.include_router(events_router)
router.include_router(tasks_router)


@router.get("/health")
async def health() -> dict[str, str]:
    """Dashboard health check."""
    return {"status": "ok"}
