"""Production Service Context Packs.

Defines and registers context packs for known service domains.
"""

from src.context.service_context_pack import ServiceContextPack, get_registry

FASTAPI_SERVICE_PACK = ServiceContextPack(
    name="fastapi-service",
    version="1.0",
    repo_patterns=["api-*", "svc-*", "service-*"],
    conventions=[
        "Use FastAPI router modules grouped by domain (e.g. src/admin/router.py)",
        "Dependency injection via Depends() for sessions, auth, and services",
        "Pydantic models for request/response schemas with strict validation",
        "Async endpoint handlers — no blocking I/O in request path",
        "HTTPException for error responses with appropriate status codes",
        "Structured logging with correlation IDs on all requests",
    ],
    api_patterns=[
        "RESTful resource naming: plural nouns for collections, singular for detail",
        "Query parameters for filtering and pagination (limit, offset, repo, tier)",
        "JSON responses with snake_case field names",
        "HTMX partial endpoints under /ui/partials/ for dynamic UI updates",
        "Permission checks via require_permission() decorator on all endpoints",
    ],
    constraints=[
        "No raw SQL — use SQLAlchemy async ORM exclusively",
        "No synchronous database calls in async handlers",
        "All endpoints require authentication context",
        "Response models must be serializable via to_dict() or Pydantic",
        "File uploads limited to 10MB",
    ],
    testing_notes=[
        "Use httpx.AsyncClient with ASGITransport for endpoint tests",
        "Mock database sessions via patch on get_async_session",
        "Use pytest.mark.asyncio for all async test functions",
        "Assert response status codes and key content fields",
    ],
)

DATA_PIPELINE_PACK = ServiceContextPack(
    name="data-pipeline",
    version="1.0",
    repo_patterns=["pipeline-*", "etl-*", "data-*", "ingest-*"],
    conventions=[
        "Idempotent processing — re-running the same input produces the same output",
        "Batch operations use chunked processing with configurable batch size",
        "All pipeline stages emit structured signals for observability",
        "Error records are quarantined, not dropped — dead-letter pattern",
        "Schema versioning on all data models with backward compatibility",
    ],
    api_patterns=[
        "Pipeline stages are composable functions: input -> output with side effects logged",
        "Use dataclasses for intermediate data representations",
        "Signal emission at stage boundaries (stage_started, stage_completed, stage_failed)",
        "Configuration via environment variables with sensible defaults",
    ],
    constraints=[
        "No in-memory accumulation of unbounded datasets — stream or paginate",
        "Retry logic must have exponential backoff with max attempts",
        "All timestamps in UTC ISO 8601 format",
        "Schema changes require migration path — no breaking changes without versioning",
        "Processing must be resumable after failure — checkpoint state",
    ],
    testing_notes=[
        "Test idempotency by running pipeline twice with same input",
        "Test error quarantine with intentionally malformed records",
        "Mock external data sources — no real API calls in unit tests",
        "Verify signal emission count and content at stage boundaries",
    ],
)


def register_production_packs() -> None:
    """Register all production context packs in the global registry."""
    registry = get_registry()
    registry.register(FASTAPI_SERVICE_PACK)
    registry.register(DATA_PIPELINE_PACK)


# Auto-register on import
register_production_packs()
