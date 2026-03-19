# Feature Flag Architecture

> All feature flags live in `src/settings.py` as `pydantic_settings.BaseSettings` fields.
> Every flag defaults to **off**. No existing deployment is affected by new features until explicitly enabled.

---

## How It Works

```
Environment Variable → Settings class → Runtime check
```

1. **Declaration**: Each flag is a typed field on `Settings(BaseSettings)` with a safe default.
2. **Loading**: `pydantic_settings` reads `THESTUDIO_*` environment variables at startup. No config files, no database lookups, no remote flag service.
3. **Usage**: Code checks `settings.<flag_name>` at the point of use. Feature-flagged code paths are guarded by simple `if` statements.
4. **Validation**: `@model_validator` methods enforce invariants (e.g., Execute tier cannot silently fall back to in-process).

Environment variable prefix: `THESTUDIO_`

Example: `THESTUDIO_PREFLIGHT_ENABLED=true` enables the preflight gate.

---

## Flag Inventory

### Pipeline Feature Flags

| Flag | Type | Default | Epic | Purpose |
|------|------|---------|------|---------|
| `preflight_enabled` | `bool` | `False` | 28 | Enable preflight plan review gate between Assembler and Implement |
| `preflight_tiers` | `list[str]` | `["execute"]` | 28 | Trust tiers that run preflight (only Execute by default) |
| `projects_v2_enabled` | `bool` | `False` | 29 | Enable GitHub Projects v2 board sync at pipeline status transitions |
| `meridian_portfolio_enabled` | `bool` | `False` | 29 | Enable scheduled Meridian portfolio health reviews |
| `meridian_portfolio_github_issue` | `bool` | `False` | 29 | Post portfolio health report to a pinned GitHub issue |
| `approval_auto_bypass` | `bool` | `False` | 30 | Skip human approval gate (dev/test only; blocked when github_provider=real + llm_provider=anthropic) |
| `intake_poll_enabled` | `bool` | `False` | 17 | Enable polling for new GitHub issues (backup to webhooks) |

### Infrastructure Provider Flags

| Flag | Type | Default | Epic | Purpose |
|------|------|---------|------|---------|
| `llm_provider` | `str` | `"mock"` | 8 | LLM backend: `"mock"` (rule-based) or `"anthropic"` (real API) |
| `github_provider` | `str` | `"mock"` | 8 | GitHub backend: `"mock"` or `"real"` |
| `store_backend` | `str` | `"memory"` | 8 | Storage backend: `"memory"` (in-process) or `"postgres"` |
| `agent_isolation` | `str` | `"process"` | 25 | Execution mode: `"process"` (in-process) or `"container"` (Docker) |

### Per-Agent LLM Toggles

| Flag | Type | Default | Epic | Purpose |
|------|------|---------|------|---------|
| `agent_llm_enabled` | `dict[str, bool]` | All `False` | 23 | Per-agent toggle: when `False`, agent uses rule-based fallback instead of LLM |

Supported agents: `primary_agent`, `intake_agent`, `context_agent`, `intent_agent`, `router_agent`, `recruiter_agent`, `assembler_agent`, `qa_agent`, `preflight_agent`

### Container Isolation Configuration

| Flag | Type | Default | Epic | Purpose |
|------|------|---------|------|---------|
| `agent_isolation_fallback` | `dict[str, str]` | `observe: allow, suggest: allow, execute: deny` | 25 | Fallback policy when Docker unavailable. Execute tier **must** be `deny` (enforced by validator) |
| `agent_container_cpu_limit` | `dict[str, float]` | `observe: 1.0, suggest: 2.0, execute: 4.0` | 25 | CPU cores per tier |
| `agent_container_memory_mb` | `dict[str, int]` | `observe: 512, suggest: 1024, execute: 2048` | 25 | Memory limit (MB) per tier |
| `agent_container_timeout_seconds` | `dict[str, int]` | `observe: 300, suggest: 600, execute: 1200` | 25 | Execution timeout per tier |

### Meridian Thresholds

| Flag | Type | Default | Epic | Purpose |
|------|------|---------|------|---------|
| `meridian_thresholds` | `dict[str, float]` | See below | 29 | Configurable health check thresholds |

Default thresholds:
- `blocked_ratio`: `0.20` — flag when >20% of active items are blocked
- `high_risk_concurrent`: `3` — flag when >3 high-risk items in progress
- `review_stale_hours`: `48` — flag items in review >48 hours
- `repo_concentration`: `0.50` — flag when one repo has >50% of active items
- `failure_rate`: `0.30` — flag when >30% of completed items failed
- `queued_stale_days`: `7` — flag items queued >7 days

---

## Design Principles

1. **Off by default.** Every feature flag ships disabled. Deployments opt-in explicitly.
2. **Environment variables only.** No config files, no database, no remote service. `THESTUDIO_*` prefix prevents collisions.
3. **Validated at startup.** Pydantic validates types and constraints before the app starts. Invalid configurations fail fast with clear error messages.
4. **Security invariants enforced.** `@model_validator` blocks unsafe combinations (e.g., Execute tier with `allow` fallback when container isolation is on).
5. **No runtime mutation.** `Settings` is constructed once at import time (`settings = Settings()`). Flags do not change during a process lifetime.
6. **Graduated rollout.** Provider flags (`llm_provider`, `github_provider`, `store_backend`) allow swapping backends without code changes. Agent LLM toggles allow enabling AI per-agent independently.

---

## Deployment Examples

### Minimal (development/testing)
```bash
# All defaults — mock providers, no features enabled
# Nothing to set, just run
uvicorn src.app:app --reload
```

### Enable Projects v2 sync
```bash
export THESTUDIO_PROJECTS_V2_ENABLED=true
export THESTUDIO_PROJECTS_V2_OWNER=my-org
export THESTUDIO_PROJECTS_V2_NUMBER=1
export THESTUDIO_PROJECTS_V2_TOKEN=ghp_xxx
```

### Enable Meridian portfolio review with GitHub issue reports
```bash
export THESTUDIO_MERIDIAN_PORTFOLIO_ENABLED=true
export THESTUDIO_MERIDIAN_PORTFOLIO_GITHUB_ISSUE=true
export THESTUDIO_MERIDIAN_PORTFOLIO_REPO=my-org/my-repo
```

### Production with real providers
```bash
export THESTUDIO_LLM_PROVIDER=anthropic
export THESTUDIO_GITHUB_PROVIDER=real
export THESTUDIO_STORE_BACKEND=postgres
export THESTUDIO_DATABASE_URL=postgresql+asyncpg://...
export THESTUDIO_ENCRYPTION_KEY=$(python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')
export THESTUDIO_ANTHROPIC_API_KEY=sk-ant-xxx
export THESTUDIO_AGENT_ISOLATION=container
```
