"""Dashboard API router — /api/v1/dashboard/ endpoints."""

from fastapi import APIRouter

from src.dashboard.activity import router as activity_router
from src.dashboard.analytics_router import router as analytics_router
from src.dashboard.auto_merge_router import router as auto_merge_router
from src.dashboard.board import router as board_router
from src.dashboard.budget_router import router as budget_router
from src.dashboard.events import router as events_router
from src.dashboard.gates import router as gates_router
from src.dashboard.github_router import router as github_router
from src.dashboard.notification_router import router as notification_router
from src.dashboard.planning import router as planning_router
from src.dashboard.pr_router import router as pr_router
from src.dashboard.reputation_router import router as reputation_router
from src.dashboard.steering import router as steering_router
from src.dashboard.tasks import router as tasks_router
from src.dashboard.trust_router import router as trust_router

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])
router.include_router(events_router)
router.include_router(tasks_router)
router.include_router(gates_router)
router.include_router(activity_router)
router.include_router(planning_router)
router.include_router(board_router)
router.include_router(steering_router)
router.include_router(trust_router)
router.include_router(budget_router)
router.include_router(notification_router)
router.include_router(github_router)
router.include_router(pr_router)
router.include_router(analytics_router)
router.include_router(reputation_router)
router.include_router(auto_merge_router)


@router.get("/health")
async def health() -> dict[str, str]:
    """Dashboard health check."""
    return {"status": "ok"}
