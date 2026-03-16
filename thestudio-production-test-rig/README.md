# TheStudio Production Test Rig

Dedicated test repo for validating a **deployed** TheStudio instance (production or staging). This is a **multi-repo** setup: TheStudio is the application repo; this repo only runs tests against a live deployment. It does not start Docker or build TheStudio.

## Prerequisites

- Python 3.12+
- Deployed TheStudio (e.g. production `https://localhost:9443` or your staging URL; see TheStudio **docs/URLs.md** for all URLs)

## Setup

```bash
pip install -e ".[dev]"
cp .env.example .env
# Edit .env: set THESTUDIO_BASE_URL and WEBHOOK_SECRET to match your deployment.
```

## Configuration

| Variable | Required | Description |
|----------|----------|-------------|
| `THESTUDIO_BASE_URL` | Yes | Base URL of the deployment (e.g. `https://localhost:9443`). No trailing slash. |
| `WEBHOOK_SECRET` | Yes | Must match `THESTUDIO_WEBHOOK_SECRET` on the deployment (for signing webhooks). Get it from the deployment’s `infra/.env`. |
| `THESTUDIO_INSECURE_TLS` | No | Set to `1` to skip TLS verification (e.g. self-signed cert). |
| `THESTUDIO_ADMIN_USER` | No | `X-User-ID` for admin API. Default `dev-admin@localhost` (matches TheStudio mock auto-provision). |

## Run tests

```bash
pytest -v
```

Tests will skip with a clear message if the deployment is unreachable (e.g. wrong URL or not running).

## What is tested

Tests are organized into focused modules, each independently runnable:

| Module | Tests | What it validates |
|--------|-------|-------------------|
| `test_health.py` | 2 | `/healthz` and `/readyz` return 200 with expected JSON |
| `test_admin_api.py` | 6 | `/admin/health`, `/docs`, repo registration (POST/GET), detail, profile PATCH |
| `test_webhook.py` | 4 | Webhook HMAC-SHA256: valid sig (200/201), missing sig (401), bad sig (401/403), missing delivery (400) |
| `test_poll_intake.py` | 2 | Poll config via profile PATCH, poll E2E cycle via `/admin/poll/run` |
| `test_pipeline_smoke.py` | 1 | Webhook triggers TaskPacket creation for registered repo |

Run a single module: `pytest tests/test_webhook.py -v`

Contract details and endpoint-to-test mapping: see [TheStudio docs/production-test-rig-contract.md](../docs/production-test-rig-contract.md) in the TheStudio repo.

## CI

A GitHub Actions workflow is included for when this scaffold is used as its own repo:

- **Workflow:** `.github/workflows/production-smoke.yml` — runs `pytest -v` on push/PR to `main`/`master` and on `workflow_dispatch`.
- **Required secrets:** `THESTUDIO_BASE_URL`, `WEBHOOK_SECRET` (must match the deployment’s `THESTUDIO_WEBHOOK_SECRET`).
- **Optional variables:** `THESTUDIO_INSECURE_TLS` (e.g. `1` for self-signed cert), `THESTUDIO_ADMIN_USER`. Set `THESTUDIO_SKIP_SMOKE=true` to disable the job (e.g. in forks that don’t have secrets).

The job does **not** start or manage the deployment; it only runs tests against the URL you provide.

### Enabling CI in the new repo

After you create the new repository from this scaffold:

1. In GitHub, open the repo → **Settings** → **Secrets and variables** → **Actions**.
2. **Repository secrets** (required for the workflow to run against your deployment):
   - `THESTUDIO_BASE_URL` — e.g. `https://your-studio.example.com` or `https://localhost:9443` (no trailing slash).
   - `WEBHOOK_SECRET` — same value as `THESTUDIO_WEBHOOK_SECRET` on the deployment (copy from the deployment’s `infra/.env`).
3. **Variables** (optional): Add repository variables if needed:
   - `THESTUDIO_INSECURE_TLS` = `1` when the deployment uses a self-signed certificate.
   - `THESTUDIO_ADMIN_USER` — admin `X-User-ID` if different from `dev-admin@localhost`.
   - `THESTUDIO_SKIP_SMOKE` = `true` to disable the smoke job (e.g. in forks that don’t have secrets).
4. Push to `main` or `master`, or run the workflow manually via **Actions** → **Production smoke** → **Run workflow**.

If the secrets are not set, the workflow still runs but tests will skip with a message that the deployment is unreachable.

## Using this as a separate repo

This folder is a self-contained scaffold. To use it as its own repository:

1. **Copy the folder** as the root of a new repo (include `.github/` so CI is available):
   ```bash
   # Unix
   cp -r thestudio-production-test-rig /path/to/new-repo
   # Windows (PowerShell)
   Copy-Item -Recurse thestudio-production-test-rig C:\path\to\new-repo
   ```
   Then `cd` into the new directory.
2. **Initialize git** and add your remote:
   ```bash
   git init
   git add .
   git commit -m "Initial commit: production test rig"
   git remote add origin <your-remote-url>
   ```
3. **Configure environment:** Copy `.env.example` to `.env` and set `THESTUDIO_BASE_URL` and `WEBHOOK_SECRET` (from the deployment’s `infra/.env`). For CI, add the same as repository secrets.
4. **Run tests:** `pip install -e ".[dev]"` then `pytest -v`.

Contract and endpoint details live in the TheStudio repo: `docs/production-test-rig-contract.md`. When adding or changing production endpoints or auth, keep the contract and this test rig in sync.
