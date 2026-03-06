"""FastAPI middleware for OpenTelemetry tracing and correlation_id propagation."""

from uuid import UUID

from fastapi import Request
from opentelemetry import context, trace
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from src.observability.conventions import ATTR_CORRELATION_ID
from src.observability.correlation import attach_correlation_id, generate_correlation_id


class CorrelationMiddleware(BaseHTTPMiddleware):
    """Middleware that ensures every request has a correlation_id in OTel context."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Check for existing correlation_id header or generate new
        header_value = request.headers.get("X-Correlation-ID")
        if header_value:
            correlation_id = UUID(header_value)
        else:
            correlation_id = generate_correlation_id()

        token = attach_correlation_id(correlation_id)

        # Add to current span if one exists
        span = trace.get_current_span()
        if span.is_recording():
            span.set_attribute(ATTR_CORRELATION_ID, str(correlation_id))

        try:
            response = await call_next(request)
            response.headers["X-Correlation-ID"] = str(correlation_id)
            return response
        finally:
            context.detach(token)
