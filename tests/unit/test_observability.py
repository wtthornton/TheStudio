"""Unit tests for Observability (Story 0.9)."""

from uuid import uuid4

from opentelemetry import baggage, trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ReadableSpan, SimpleSpanProcessor, SpanExporter, SpanExportResult

from src.observability.conventions import ATTR_CORRELATION_ID, SPAN_INGRESS_RECEIVE
from src.observability.correlation import (
    BAGGAGE_CORRELATION_ID,
    generate_correlation_id,
    get_correlation_id,
    set_correlation_id,
)


class ListExporter(SpanExporter):
    """Simple in-memory span exporter for tests."""

    def __init__(self) -> None:
        self.spans: list[ReadableSpan] = []

    def export(self, spans: list[ReadableSpan]) -> SpanExportResult:  # type: ignore[override]
        self.spans.extend(spans)
        return SpanExportResult.SUCCESS

    def shutdown(self) -> None:
        pass


class TestCorrelationId:
    def test_generate_returns_uuid(self) -> None:
        cid = generate_correlation_id()
        assert cid is not None
        assert cid.version == 4

    def test_set_and_get_from_baggage(self) -> None:
        cid = uuid4()
        ctx = set_correlation_id(cid)
        retrieved = get_correlation_id(ctx)
        assert retrieved == cid

    def test_get_returns_none_when_not_set(self) -> None:
        from opentelemetry.context import Context

        ctx = Context()
        result = get_correlation_id(ctx)
        assert result is None

    def test_baggage_key_is_correct(self) -> None:
        assert BAGGAGE_CORRELATION_ID == "thestudio.correlation_id"


class TestSpanCreation:
    def test_span_with_standard_attributes(self) -> None:
        exporter = ListExporter()
        provider = TracerProvider()
        provider.add_span_processor(SimpleSpanProcessor(exporter))

        tracer = provider.get_tracer("test")
        cid = uuid4()

        with tracer.start_as_current_span(SPAN_INGRESS_RECEIVE) as span:
            span.set_attribute(ATTR_CORRELATION_ID, str(cid))

        assert len(exporter.spans) == 1
        assert exporter.spans[0].name == SPAN_INGRESS_RECEIVE
        assert exporter.spans[0].attributes is not None
        assert exporter.spans[0].attributes[ATTR_CORRELATION_ID] == str(cid)

    def test_error_recording(self) -> None:
        exporter = ListExporter()
        provider = TracerProvider()
        provider.add_span_processor(SimpleSpanProcessor(exporter))

        tracer = provider.get_tracer("test")

        try:
            with tracer.start_as_current_span("test.error"):
                raise ValueError("test error")
        except ValueError:
            pass

        assert len(exporter.spans) == 1
        assert exporter.spans[0].status.status_code == trace.StatusCode.ERROR


class TestBaggagePropagation:
    def test_baggage_propagates_across_contexts(self) -> None:
        cid = uuid4()
        ctx = set_correlation_id(cid)

        value = baggage.get_baggage(BAGGAGE_CORRELATION_ID, context=ctx)
        assert value == str(cid)
