"""Correlation ID generation and propagation via OpenTelemetry baggage."""

from contextvars import Token
from uuid import UUID, uuid4

from opentelemetry import baggage, context
from opentelemetry.context import Context

BAGGAGE_CORRELATION_ID = "thestudio.correlation_id"


def generate_correlation_id() -> UUID:
    """Generate a new correlation_id (UUID v4)."""
    return uuid4()


def set_correlation_id(correlation_id: UUID, ctx: Context | None = None) -> Context:
    """Store correlation_id in OTel baggage for cross-process propagation."""
    return baggage.set_baggage(BAGGAGE_CORRELATION_ID, str(correlation_id), context=ctx)


def get_correlation_id(ctx: Context | None = None) -> UUID | None:
    """Extract correlation_id from OTel baggage."""
    value = baggage.get_baggage(BAGGAGE_CORRELATION_ID, context=ctx)
    if value is None:
        return None
    return UUID(str(value))


def attach_correlation_id(correlation_id: UUID) -> Token[Context]:
    """Set correlation_id in baggage and attach to current context. Returns token for detach."""
    new_ctx = set_correlation_id(correlation_id)
    return context.attach(new_ctx)
