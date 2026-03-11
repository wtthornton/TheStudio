# Docker Stack Smoke Tests

Automated tests that verify the full Docker Compose stack builds, starts, connects, and handles real HTTP traffic.

## Prerequisites

- Docker and Docker Compose installed
- Python dev dependencies installed (`pip install -e ".[dev]"`)

## Running locally

1. **Start the stack:** (app at `http://localhost:8000`; see [docs/URLs.md](../../docs/URLs.md) for all URLs)

   ```bash
   docker compose -f docker-compose.dev.yml up -d --build
   ```

2. **Wait for readiness:**

   ```bash
   python scripts/wait_for_stack.py --timeout 120
   ```

3. **Run the smoke tests:**

   ```bash
   pytest tests/docker/ -m docker -v
   ```

4. **Tear down:**

   ```bash
   docker compose -f docker-compose.dev.yml down -v
   ```

## What the tests cover

| Test file | What it proves |
|-----------|---------------|
| `test_api_smoke.py` | `/healthz`, `/admin/health`, `/docs`, and webhook endpoint respond correctly |
| `test_pipeline_smoke.py` | A webhook POST flows through intake and creates a TaskPacket (verified via admin API) |
| `test_lifecycle.py` | Graceful shutdown (exit 0), restart recovery, and Temporal dependency failure handling |

## CI integration

The `docker-smoke` job in `.github/workflows/ci.yml` runs these tests automatically on every PR and push to master. On failure, container logs are uploaded as a build artifact (`docker-compose-logs`).

## Reading CI failures

1. Check the **"Run Docker smoke tests"** step for the pytest failure output.
2. Download the **docker-compose-logs** artifact for container-level logs from all 4 services.
3. Common issues:
   - **Timeout in readiness:** A service failed to start. Check the logs for the specific service.
   - **401 on webhook:** The `THESTUDIO_WEBHOOK_SECRET` env var may not match the HMAC computation.
   - **Connection refused:** The app container may have crashed on startup — check app logs.

## Adding new smoke tests

1. Create a new test file in `tests/docker/`.
2. Add `pytestmark = pytest.mark.docker` at the top.
3. Use the `http_client` fixture for HTTP requests and `registered_repo` for webhook tests.
4. Use helpers from `conftest.py`: `build_webhook_headers()`, `make_issue_payload()`, `compute_signature()`.
5. Tests should be idempotent — runnable multiple times without cleanup.

## Design decisions

- **No in-process imports:** Tests use only HTTP via `httpx`. No application code is imported.
- **Dev-mode auto-auth:** Admin endpoints work without auth headers because `THESTUDIO_LLM_PROVIDER=mock` triggers auto-auth as admin.
- **Memory store:** `THESTUDIO_STORE_BACKEND=memory` means TaskPackets are in-memory; verification is via admin API, not database queries.
- **Temporal as dependency target:** Lifecycle tests target Temporal (not PostgreSQL) because the memory store means most endpoints don't use the database.
