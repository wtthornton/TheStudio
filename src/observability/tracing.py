"""OpenTelemetry SDK setup and TracerProvider configuration."""

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter, SpanExporter

from src.settings import settings


def init_tracing() -> TracerProvider:
    """Initialize the OpenTelemetry TracerProvider.

    Configures either console or OTLP exporter based on settings.
    """
    resource = Resource.create(
        {
            "service.name": settings.otel_service_name,
            "service.version": "0.1.0",
        }
    )

    provider = TracerProvider(resource=resource)

    exporter: SpanExporter
    if settings.otel_exporter == "otlp":
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

        exporter = OTLPSpanExporter(endpoint=settings.otel_otlp_endpoint)
    else:
        exporter = ConsoleSpanExporter()

    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    return provider


def get_tracer(name: str) -> trace.Tracer:
    """Get a named tracer from the global provider."""
    return trace.get_tracer(name)
