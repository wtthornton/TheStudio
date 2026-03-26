# Agent Container Isolation Architecture

> **Status:** Active (v0.3.0, 2026-03-26)
> **Epic:** 25 (Container Isolation), 43 (Ralph SDK Integration)
> **Owner:** Primary Developer

---

## Overview

The Primary Agent (pipeline stage 6: Implement) runs in an **ephemeral Docker
container** isolated from the platform infrastructure. This is the recommended
production architecture for TheStudio.

```
┌─────────────────────────────────────────────────────────┐
│  thestudio-net (platform network)                       │
│                                                         │
│  ┌─────────┐  ┌──────────┐  ┌────────┐  ┌──────┐      │
│  │ Caddy   │  │ Postgres │  │Temporal│  │ NATS │      │
│  │ :9080   │  │ :5432    │  │ :7233  │  │ :4222│      │
│  └────┬────┘  └──────────┘  └────────┘  └──────┘      │
│       │                                                 │
│  ┌────┴─────────────────────────────────────────┐      │
│  │  App Container (thestudio-prod-app)           │      │
│  │  ├── FastAPI (webhooks, admin UI, APIs)       │      │
│  │  ├── Temporal Worker (pipeline activities)    │      │
│  │  ├── ContainerManager (spawns agent)          │      │
│  │  └── docker.sock mounted (container control)  │      │
│  └──────────────┬───────────────────────────────┘      │
│                 │ docker.sock                           │
└─────────────────┼───────────────────────────────────────┘
                  │
                  ▼  spawns ephemeral container
┌─────────────────────────────────────────────────────────┐
│  agent-net (isolated network)                           │
│                                                         │
│  ┌──────────────────────────────────────────────┐      │
│  │  Agent Container (thestudio-agent:latest)     │      │
│  │                                               │      │
│  │  ├── Claude CLI (@anthropic-ai/claude-code)   │      │
│  │  ├── Ralph SDK (ralph_sdk Python package)     │      │
│  │  ├── Git (repo operations)                    │      │
│  │  ├── container_runner.py (entrypoint)         │      │
│  │  │                                            │      │
│  │  │  Input:  /workspace/task.json              │      │
│  │  │  Output: /workspace/result.json            │      │
│  │  │  Repo:   /workspace/repo/                  │      │
│  │  │                                            │      │
│  │  │  CAN reach:    GitHub API, Anthropic API   │      │
│  │  │  CANNOT reach: Postgres, Temporal, NATS    │      │
│  │  └────────────────────────────────────────────│      │
│  └──────────────────────────────────────────────┘      │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

## Agent Modes

| Mode | Env var | Who writes code | CLI needed | Container needed |
|------|---------|----------------|------------|-----------------|
| `legacy` | `THESTUDIO_AGENT_MODE=legacy` | Claude Agent SDK (direct API call) | No | No |
| `ralph` | `THESTUDIO_AGENT_MODE=ralph` | Ralph SDK → Claude CLI subprocess | Yes (in app) | No |
| `container` | `THESTUDIO_AGENT_MODE=container` | Ralph SDK → Claude CLI subprocess | Yes (in agent container) | Yes |

**Recommended:** `container` mode. The app container stays lean; the Claude CLI
is only installed in the agent image; agent code runs in network isolation.

## Security Model

### Network Isolation

The `agent-net` network is a separate Docker bridge. Agent containers connect
ONLY to `agent-net`. They cannot reach:

- PostgreSQL (port 5432) — no database access
- Temporal (port 7233) — no workflow manipulation
- NATS (port 4222) — no message queue access
- App (port 8000) — no admin API access

Outbound HTTPS is allowed for GitHub API and Anthropic API calls.

### Trust Tier Enforcement

| Tier | Isolation | Fallback if container unavailable |
|------|-----------|----------------------------------|
| Observe | Container preferred | Allow in-process fallback |
| Suggest | Container preferred | Allow in-process fallback |
| Execute | Container **required** | **Deny** — task fails |

Execute tier tasks auto-merge PRs. They MUST run in isolation. The
`isolation_policy.py` enforces this: `ContainerUnavailableError` is raised
if Docker is not available for Execute tier.

### Per-Tier Resource Limits

| Tier | CPU | Memory | Timeout | PIDs |
|------|-----|--------|---------|------|
| Observe | 0.5 | 256 MB | 180s | 128 |
| Suggest | 1.0 | 512 MB | 300s | 256 |
| Execute | 1.0 | 512 MB | 300s | 256 |

Configured via `settings.agent_container_cpu_limit`,
`settings.agent_container_memory_mb`,
`settings.agent_container_timeout_seconds`.

## Container Lifecycle

```
implement_activity (Temporal)
  │
  ├── 1. Build AgentTaskInput from TaskPacket + IntentSpec
  ├── 2. Write /workspace/task.json
  ├── 3. ContainerManager.launch()
  │       └── docker run thestudio-agent:latest
  │           --network agent-net
  │           --cpus {limit} --memory {limit}
  │           --label thestudio.role=agent
  │           -v /workspace:/workspace
  │           -e THESTUDIO_ANTHROPIC_API_KEY=...
  ├── 4. ContainerManager.wait() (with timeout + heartbeat)
  ├── 5. ContainerManager.collect_results()
  │       └── Read /workspace/result.json → AgentContainerResult
  ├── 6. ContainerManager.cleanup()
  │       └── Remove container
  └── 7. Convert AgentContainerResult → EvidenceBundle
```

### Orphan Reaper

`ContainerManager.reap_orphans()` removes agent containers older than 4 hours.
Labels: `thestudio.role=agent`. Prevents container leak on crash/timeout.

## Container Image

**Image:** `thestudio-agent:latest`
**Dockerfile:** `infra/Dockerfile.agent`

Contents:
- Python 3.12 slim + TheStudio source (`src/`)
- Ralph SDK (vendored at `vendor/ralph-sdk/`)
- Node.js 22 LTS + Claude CLI (`@anthropic-ai/claude-code`)
- Git (for repo operations)
- Non-root `agent` user

**Build:**
```bash
cd infra
docker compose -f docker-compose.prod.yml --profile build build agent-image
```

## Communication Protocol

All communication between the app and agent containers is via JSON files on
a mounted Docker volume. No network calls, no database, no message queue.

### Input: `/workspace/task.json`

```json
{
  "taskpacket_id": "uuid",
  "correlation_id": "uuid",
  "repo_url": "https://github.com/owner/repo",
  "system_prompt": "...",
  "intent_goal": "Add retry logic to webhook handler",
  "acceptance_criteria": ["..."],
  "max_turns": 30,
  "max_budget_usd": 5.0,
  "repo_tier": "observe"
}
```

### Output: `/workspace/result.json`

```json
{
  "success": true,
  "files_changed": ["src/webhook.py", "tests/test_webhook.py"],
  "agent_summary": "...",
  "tokens_used": 12500,
  "cost_usd": 0.28,
  "duration_ms": 45000,
  "exit_reason": "completed"
}
```

## Observability

All container lifecycle phases emit OTel spans:

| Span | What it measures |
|------|-----------------|
| `container.lifecycle` | Full launch → cleanup duration |
| `container.launch` | Time to start container |
| `container.wait` | Time agent runs (code generation) |
| `container.collect` | Time to read result.json |
| `container.cleanup` | Time to remove container |

Attributes: `container.id`, `container.image`, `container.exit_code`,
`container.oom_killed`, `container.timed_out`, `repo.tier`.

## Rollback

To revert to legacy mode (no containers):

```bash
# In infra/.env or docker-compose.prod.yml:
THESTUDIO_AGENT_MODE=legacy
THESTUDIO_AGENT_ISOLATION=process

# Restart app
docker compose -f docker-compose.prod.yml up -d app
```

No migration, no data loss. The `ralph_agent_state` table is ignored in
legacy mode.

## References

- `src/agent/container_manager.py` — ContainerManager (lifecycle, reaper)
- `src/agent/container_runner.py` — In-container entrypoint
- `src/agent/container_protocol.py` — AgentTaskInput / AgentContainerResult
- `src/agent/isolation_policy.py` — Trust tier enforcement
- `src/agent/primary_agent.py` — Mode dispatch (legacy/ralph/container)
- `infra/Dockerfile.agent` — Agent container image
- `infra/docker-compose.prod.yml` — Stack definition
