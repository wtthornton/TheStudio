"""FastAPI application for TheStudio."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from src.admin.platform_router import platform_router
from src.admin.router import router as admin_router
from src.admin.ui_router import ui_router
from src.compliance.router import router as compliance_router
from src.ingress.webhook_handler import router as ingress_router
from src.observability.middleware import CorrelationMiddleware
from src.observability.tracing import init_tracing

limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: initialize tracing, packs, scheduler, and consumer."""
    init_tracing()
    import src.context.packs  # noqa: F401 — registers production context packs
    from src.ingress.poll.scheduler import start_poll_scheduler
    from src.outcome.consumer import stop_signal_consumer

    poll_task = start_poll_scheduler()

    # Start JetStream signal consumer (non-blocking, logs on failure)
    consumer_task = None
    try:
        from src.outcome.consumer import start_signal_consumer
        from src.settings import settings

        consumer_task = await start_signal_consumer(settings.nats_url)
    except Exception:
        import logging

        logging.getLogger(__name__).warning("Failed to start signal consumer", exc_info=True)

    yield

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
app.include_router(platform_router)
app.include_router(ui_router)


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
