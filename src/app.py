"""FastAPI application for TheStudio."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.admin.router import router as admin_router
from src.compliance.router import router as compliance_router
from src.ingress.webhook_handler import router as ingress_router
from src.observability.middleware import CorrelationMiddleware
from src.observability.tracing import init_tracing


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: initialize tracing on startup."""
    init_tracing()
    yield


app = FastAPI(title="TheStudio", version="0.1.0", lifespan=lifespan)
app.add_middleware(CorrelationMiddleware)
app.include_router(ingress_router)
app.include_router(compliance_router)
app.include_router(admin_router)
