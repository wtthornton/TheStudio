"""FastAPI application for TheStudio."""

import asyncio
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from src.admin.platform_router import platform_router
from src.admin.readiness_routes import router as readiness_router
from src.admin.router import router as admin_router
from src.admin.ui_router import ui_router
from src.api.approval import router as approval_router
from src.approval.chat_router import router as chat_router
from src.compliance.router import router as compliance_router
from src.dashboard.router import router as dashboard_router
from src.ingress.webhook_handler import router as ingress_router
from src.observability.middleware import CorrelationMiddleware
from src.observability.tracing import init_tracing

_FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"
limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: initialize tracing, packs, experts, scheduler, and consumer."""
    import logging

    init_tracing()
    import src.context.packs  # noqa: F401 — registers production context packs
    from src.ingress.poll.scheduler import start_poll_scheduler
    from src.outcome.consumer import stop_signal_consumer
    from src.settings import settings

    _logger = logging.getLogger(__name__)

    # Run database migrations before any DB-dependent service starts
    if settings.store_backend == "postgres":
        try:
            from src.db.run_migrations import run_all as run_migrations

            await run_migrations()
            _logger.info("Database migrations applied successfully")
        except Exception:
            _logger.error("Failed to run database migrations", exc_info=True)
            raise

    # Scan and sync file-based experts at startup
    try:
        from src.db.connection import get_async_session
        from src.experts.config import get_experts_base_path
        from src.experts.registrar import sync_experts
        from src.experts.scanner import scan_expert_directories

        experts_path = get_experts_base_path()
        if experts_path.is_dir():
            scan_result = scan_expert_directories(experts_path)
            for err in scan_result.errors:
                _logger.warning(
                    "Expert scan error",
                    extra={"directory": str(err.directory), "error": err.error},
                )
            async with get_async_session() as session:
                sync_result = await sync_experts(session, scan_result.experts)
                _logger.info(
                    "Expert sync complete",
                    extra={
                        "created": len(sync_result.created),
                        "updated": len(sync_result.updated),
                        "unchanged": len(sync_result.unchanged),
                    },
                )
    except Exception:
        _logger.warning("Failed to sync experts at startup", exc_info=True)

    poll_task = start_poll_scheduler()

    # Start Temporal worker (executes pipeline workflow activities)
    worker_task = None
    try:
        from src.workflow.worker import start_worker_background

        worker_task = await start_worker_background()
    except Exception:
        _logger.warning("Failed to start Temporal worker", exc_info=True)

    # Start JetStream signal consumer (non-blocking, logs on failure)
    consumer_task = None
    try:
        from src.outcome.consumer import start_signal_consumer
        from src.settings import settings

        consumer_task = await start_signal_consumer(settings.nats_url)
    except Exception:
        import logging

        logging.getLogger(__name__).warning("Failed to start signal consumer", exc_info=True)

    # Start gate evidence consumer (non-blocking, logs on failure)
    gate_consumer_task = None
    try:
        from src.dashboard.gate_consumer import start_gate_consumer

        gate_consumer_task = await start_gate_consumer(settings.nats_url)
    except Exception:
        _logger.warning("Failed to start gate evidence consumer", exc_info=True)

    # Start budget threshold checker (non-blocking, logs on failure)
    budget_checker_task = None
    try:
        from src.dashboard.budget_checker import start_budget_checker

        budget_checker_task = await start_budget_checker(settings.nats_url)
    except Exception:
        _logger.warning("Failed to start budget checker consumer", exc_info=True)

    # Start notification generator (non-blocking, logs on failure)
    notification_generator_task = None
    try:
        from src.dashboard.notification_generator import start_notification_generator

        notification_generator_task = await start_notification_generator(settings.nats_url)
    except Exception:
        _logger.warning("Failed to start notification generator", exc_info=True)

    # Startup probe: warn if ralph mode is active but runtime is not ready
    if settings.agent_mode == "ralph":
        try:
            from src.agent.ralph_bridge import check_ralph_cli_available

            if not check_ralph_cli_available():
                _logger.warning(
                    "ralph.startup_probe.cli_missing",
                    extra={
                        "detail": (
                            "agent_mode='ralph' but 'claude' CLI not found in PATH. "
                            "Ralph mode will fail at runtime. "
                            "Set THESTUDIO_AGENT_MODE=legacy or install the Claude CLI."
                        )
                    },
                )
            else:
                _logger.info(
                    "ralph.startup_probe.ok",
                    extra={"agent_mode": "ralph", "cli_available": True},
                )
        except Exception:
            _logger.warning("ralph.startup_probe.error", exc_info=True)

    yield

    if worker_task is not None:
        worker_task.cancel()
        try:
            await worker_task
        except asyncio.CancelledError:
            pass
    if gate_consumer_task is not None:
        from src.dashboard.gate_consumer import stop_gate_consumer

        await stop_gate_consumer()
    if budget_checker_task is not None:
        from src.dashboard.budget_checker import stop_budget_checker

        await stop_budget_checker()
    if notification_generator_task is not None:
        from src.dashboard.notification_generator import stop_notification_generator

        await stop_notification_generator()
    if consumer_task is not None:
        await stop_signal_consumer()
    if poll_task is not None:
        poll_task.cancel()


app = FastAPI(title="TheStudio", version="0.1.0", lifespan=lifespan)
app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def _rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"})


app.add_middleware(CorrelationMiddleware)
app.include_router(ingress_router)
app.include_router(compliance_router)
app.include_router(admin_router)
app.include_router(readiness_router)
app.include_router(platform_router)
app.include_router(ui_router)
app.include_router(approval_router)
app.include_router(chat_router)
app.include_router(dashboard_router)

# Conditional static mount: serve frontend/dist/ at /dashboard/ when built
_dashboard_logger = logging.getLogger("thestudio.dashboard")
if _FRONTEND_DIST.is_dir() and (_FRONTEND_DIST / "index.html").is_file():
    _dashboard_index = (_FRONTEND_DIST / "index.html").read_text()

    # Mount static assets (JS, CSS, images) under /dashboard/assets etc.
    app.mount(
        "/dashboard/assets",
        StaticFiles(directory=str(_FRONTEND_DIST / "assets")),
        name="dashboard-assets",
    )
    # Serve other static files (favicon, icons) at /dashboard/ level
    app.mount(
        "/dashboard/static",
        StaticFiles(directory=str(_FRONTEND_DIST)),
        name="dashboard-static",
    )

    # Serve favicon.svg and icons.svg directly
    @app.get("/dashboard/favicon.svg", include_in_schema=False)
    async def _dashboard_favicon() -> HTMLResponse:
        favicon_path = _FRONTEND_DIST / "favicon.svg"
        return HTMLResponse(content=favicon_path.read_text(), media_type="image/svg+xml")

    @app.get("/dashboard/icons.svg", include_in_schema=False)
    async def _dashboard_icons() -> HTMLResponse:
        icons_path = _FRONTEND_DIST / "icons.svg"
        if icons_path.is_file():
            return HTMLResponse(content=icons_path.read_text(), media_type="image/svg+xml")
        return HTMLResponse(content="", status_code=404)

    # SPA catch-all: any /dashboard/* route returns index.html for client-side routing
    @app.get("/dashboard/{rest_of_path:path}", include_in_schema=False)
    async def _dashboard_spa(rest_of_path: str) -> HTMLResponse:
        return HTMLResponse(content=_dashboard_index)

    _dashboard_logger.info(
        "Dashboard UI mounted at /dashboard/",
        extra={
            "frontend_dist": str(_FRONTEND_DIST),
        },
    )
else:
    _dashboard_logger.warning(
        "Frontend dist not found — /dashboard/ UI will not be served. "
        "Run 'cd frontend && npm run build' to generate it.",
        extra={"expected_path": str(_FRONTEND_DIST)},
    )


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    """Unauthenticated liveness probe for load balancers and Docker health checks."""
    return {"status": "ok"}


@app.get("/readyz")
async def readyz() -> JSONResponse:
    """Readiness probe — checks database connectivity."""
    from sqlalchemy import text

    from src.db.connection import engine

    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return JSONResponse(content={"status": "ready"})
    except Exception as exc:
        return JSONResponse(status_code=503, content={"status": "not ready", "detail": str(exc)})


@app.get("/health/ralph")
async def ralph_health() -> JSONResponse:
    """Ralph-mode readiness probe.

    Checks whether the Ralph agent runtime is available and correctly configured.
    Returns 200 when Ralph mode is usable (or when agent_mode is not 'ralph').
    Returns 503 when agent_mode='ralph' but required components are missing.

    Response fields:
    - agent_mode: current THESTUDIO_AGENT_MODE setting
    - ralph_state_backend: current THESTUDIO_RALPH_STATE_BACKEND setting
    - cli_available: whether 'claude' binary is on PATH
    - sdk_importable: whether ralph_sdk can be imported
    - status: "ok" | "degraded" | "unavailable"
    """
    from src.agent.ralph_bridge import check_ralph_cli_available
    from src.settings import settings

    agent_mode = settings.agent_mode
    ralph_state_backend = settings.ralph_state_backend

    # Check CLI availability
    cli_available = check_ralph_cli_available()

    # Check SDK importability
    sdk_importable: bool
    try:
        import ralph_sdk  # noqa: F401

        sdk_importable = True
    except ImportError:
        sdk_importable = False

    payload: dict = {
        "agent_mode": agent_mode,
        "ralph_state_backend": ralph_state_backend,
        "cli_available": cli_available,
        "sdk_importable": sdk_importable,
    }

    if agent_mode != "ralph":
        # Ralph mode is not active — probe passes (no requirements to enforce)
        payload["status"] = "ok"
        payload["detail"] = f"agent_mode={agent_mode!r}; ralph checks not required"
        return JSONResponse(content=payload)

    # agent_mode == "ralph": both SDK and CLI must be available
    if sdk_importable and cli_available:
        payload["status"] = "ok"
        return JSONResponse(content=payload)

    missing: list[str] = []
    if not sdk_importable:
        missing.append("ralph_sdk not importable")
    if not cli_available:
        missing.append("claude CLI not found in PATH")

    payload["status"] = "unavailable"
    payload["missing"] = missing
    return JSONResponse(status_code=503, content=payload)
