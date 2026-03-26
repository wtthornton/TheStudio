# Onboarding a Real Repo at Observe Tier

Step-by-step guide for registering your first GitHub repository with TheStudio.

## 1. Prerequisites

1. **TheStudio stack running.** Follow `docs/deployment.md` to start the full stack:
   ```bash
   docker compose -f docker-compose.dev.yml up -d
   ```
2. **Health check passes:**
   ```bash
   curl http://localhost:8000/healthz
   # Expected: {"status": "ok"}
   ```
3. **GitHub account** with admin access to the target repository.
4. **GitHub App created** (see Section 2 below) — or use `THESTUDIO_GITHUB_PROVIDER=mock` for testing without a real GitHub App.

## 2. GitHub App Setup

TheStudio connects to GitHub via a GitHub App for authentication and webhook delivery.

### Create the App

1. Go to **GitHub Settings > Developer settings > GitHub Apps > New GitHub App**
2. Fill in:
   - **Name:** `TheStudio-<your-org>` (must be globally unique)
   - **Homepage URL:** `https://your-domain` (or `http://localhost:8000` for dev)
   - **Webhook URL:** `https://your-domain/webhook/github`
     - For local dev with tunneling: use ngrok or similar to expose `http://localhost:8000/webhook/github`
   - **Webhook secret:** Generate a strong secret (e.g., `openssl rand -hex 32`)
3. **Permissions** (minimum required):
   - **Repository permissions:**
     - Issues: **Read** (to receive issue events)
     - Pull requests: **Read & Write** (to create draft PRs and post comments)
     - Contents: **Read & Write** (to push branches)
     - Metadata: **Read** (required by GitHub)
   - **Organization permissions:** None required
4. **Subscribe to events:**
   - Issues
   - Issue comments (optional — for future interactive features)
   - Pull request (optional — for merge lifecycle tracking)
5. Click **Create GitHub App**
6. Note the **App ID** from the app settings page
7. Generate a **Private Key** and download the `.pem` file

### Install the App

1. From the App settings, click **Install App**
2. Select your organization or personal account
3. Choose **Only select repositories** and pick the target repo
4. Note the **Installation ID** from the URL after installation (e.g., `https://github.com/settings/installations/12345678`)

### Configure TheStudio

Set these environment variables (or in `.env`):

```bash
THESTUDIO_GITHUB_APP_ID=<app-id>
THESTUDIO_GITHUB_PRIVATE_KEY_PATH=/path/to/private-key.pem
THESTUDIO_WEBHOOK_SECRET=<webhook-secret-from-step-2>
THESTUDIO_GITHUB_PROVIDER=real    # Switch from "mock" to "real"
```

## 3. Register the Repo via Admin API

```bash
curl -X POST http://localhost:8000/admin/repos \
  -H "Content-Type: application/json" \
  -d '{
    "owner": "your-org",
    "repo": "your-repo",
    "installation_id": 12345678,
    "default_branch": "main"
  }'
```

**Expected response:** `201 Created` with a repo profile JSON including `tier: "observe"`.

**Verify registration:**

```bash
curl http://localhost:8000/admin/repos
# Should list the newly registered repo
```

## 4. Register the Repo via Admin UI

Alternatively, use the browser-based Admin UI:

1. Navigate to `http://localhost:8000/admin/ui/repos`
2. Click **Register Repo**
3. Fill in:
   - **Owner:** `your-org`
   - **Repo:** `your-repo`
   - **Installation ID:** `12345678`
   - **Default Branch:** `main`
4. Click **Submit**
5. Verify the repo appears in the repository list with tier = **Observe**

## 5. Verify Webhook Connectivity

### Send a test event

1. Create a new issue in your GitHub repository
2. Add the label `agent:run` to the issue
3. TheStudio will receive the webhook and process the event

### What happens at Observe tier

At **Observe tier**, TheStudio will:

1. **Receive the webhook** — check `http://localhost:8000/admin/ui/workflows` for a new TaskPacket
2. **Run the 9-step pipeline:** Intake → Context → Intent → Router → Assembler → Agent → Verify → QA → Publish
3. **Create a TaskPacket** that tracks the work through the pipeline

**Important:** At Observe tier, TheStudio creates a TaskPacket and processes the issue through the pipeline, but the actual behavior depends on your LLM provider configuration:
- With `THESTUDIO_LLM_PROVIDER=mock` (default): pipeline runs with stub responses — useful for validating wiring
- With `THESTUDIO_LLM_PROVIDER=anthropic`: pipeline runs with real LLM calls and produces a draft PR with an evidence comment

### Verify in the Admin UI

- **Dashboard:** `http://localhost:8000/admin/ui/dashboard` — check fleet health and queue depth
- **Workflows:** `http://localhost:8000/admin/ui/workflows` — find your TaskPacket, check its status and step progression
- **Metrics:** `http://localhost:8000/admin/ui/metrics` — view success rates and loopback counts

If the pipeline completes successfully, you should see the TaskPacket reach `PUBLISHED` status.

## 6. Trust Tiers Explained

All repos start at **Observe** tier. Higher tiers require explicit promotion.

| Tier | What TheStudio Does | What Humans Do | Promotion Path |
|------|---------------------|----------------|----------------|
| **Observe** (default) | Creates TaskPacket, runs pipeline, creates draft PR | Review the draft PR manually; merge or close | Initial registration |
| **Suggest** | Same as Observe, but marks PR as **ready for review** when V+QA pass | Review and merge the PR | Pass compliance checker via Admin UI or `POST /admin/repos/{id}/promote` |
| **Execute** | Same as Suggest, plus **auto-merge** when approval signal received | Approve via API, chat, or Slack; merge happens automatically | Full compliance pass + established track record; requires `agent_isolation=container` for security |

**Key safety properties:**
- Observe tier **never writes to GitHub** unless `THESTUDIO_GITHUB_PROVIDER=real` is set
- Suggest tier creates PRs but **never merges** — a human must click merge
- Execute tier **auto-merges after human approval** and requires container isolation (`THESTUDIO_AGENT_MODE=container`, the production default) to prevent untrusted code from accessing internal infrastructure
- You can **pause** any repo at any time via Admin UI or `POST /admin/repos/{id}/pause`

## 7. Troubleshooting

| Symptom | Check |
|---------|-------|
| Webhook returns **401 Unauthorized** | Verify `THESTUDIO_WEBHOOK_SECRET` matches the secret configured in GitHub App |
| Webhook returns **200 OK** but no TaskPacket | Issue is missing the `agent:run` label, or the delivery ID is a duplicate (deduplication guard) |
| Pipeline stuck at **in_progress** | Check Temporal UI at `http://localhost:8233` for workflow status and activity errors |
| Verification fails repeatedly | Check ruff/pytest output in workflow history; max 2 loopbacks before failure |
| No PR created | Check Publisher logs; verify GitHub token has repo write permissions; confirm `THESTUDIO_GITHUB_PROVIDER=real` |
| Webhook not received at all | Confirm the webhook URL is reachable from GitHub (use ngrok for local dev); check GitHub App > Advanced > Recent Deliveries |
| Repo not found on registration | Verify the `owner` and `repo` fields exactly match the GitHub repository (case-sensitive) |
| Installation ID wrong | Check the URL after installing the GitHub App: `https://github.com/settings/installations/<installation_id>` |

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `THESTUDIO_DATABASE_URL` | Yes | PostgreSQL connection string |
| `THESTUDIO_TEMPORAL_HOST` | Yes | Temporal server address (default: `localhost:7233`) |
| `THESTUDIO_NATS_URL` | Yes | NATS JetStream address (default: `nats://localhost:4222`) |
| `THESTUDIO_WEBHOOK_SECRET` | Yes | GitHub webhook HMAC secret |
| `THESTUDIO_ENCRYPTION_KEY` | Yes | Fernet key for secret encryption (generate: `python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'`) |
| `THESTUDIO_GITHUB_APP_ID` | For real GitHub | GitHub App ID |
| `THESTUDIO_GITHUB_PRIVATE_KEY_PATH` | For real GitHub | Path to GitHub App private key `.pem` file |
| `THESTUDIO_LLM_PROVIDER` | No | `anthropic` (real LLM) or `mock` (default, stub responses) |
| `THESTUDIO_GITHUB_PROVIDER` | No | `real` (real GitHub API) or `mock` (default, no GitHub writes) |
| `THESTUDIO_ANTHROPIC_API_KEY` | For real LLM | Anthropic API key for Claude |
| `THESTUDIO_AGENT_MODE` | No | `legacy` (default local), `ralph`, or `container` (**production default**). See `docs/architecture/agent-container-isolation.md` |
| `THESTUDIO_AGENT_ISOLATION` | No | `process` (default local) or `container` (**production default**, required for Execute tier) |
