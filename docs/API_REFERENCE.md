# TheStudio Admin API Reference

**Base URL:** `/admin`
**Version:** Sprint 1 (Epic 4) — Complete
**Updated:** 2026-03-06

---

## Overview

The Admin API provides operational visibility and management capabilities for TheStudio platform. It enables operators to:

- Monitor system health and workflow metrics
- Manage repository registrations and configurations
- View and control workflow execution
- Enforce role-based access control
- Query audit logs for compliance

---

## Authentication

All endpoints require authentication via the `X-User-ID` header:

```
X-User-ID: user@example.com
```

Role-based permissions are enforced. See [RBAC](#rbac) section for role definitions.

---

## Endpoints

### Fleet Dashboard

#### GET /admin/health

Returns system health status for core infrastructure components.

**Permission:** `VIEW_HEALTH` (Viewer+)

**Response:**
```json
{
  "temporal": {
    "name": "temporal",
    "status": "OK",
    "latency_ms": 12.5,
    "details": {"host": "localhost:7233"}
  },
  "jetstream": {
    "name": "jetstream",
    "status": "OK",
    "latency_ms": 8.2,
    "details": {"url": "nats://localhost:4222"}
  },
  "postgres": {
    "name": "postgres",
    "status": "OK",
    "latency_ms": 5.1,
    "details": {"connection": "pooled"}
  },
  "router": {
    "name": "router",
    "status": "OK",
    "details": {"self_check": true}
  },
  "checked_at": "2026-03-06T10:30:00Z",
  "overall_status": "OK"
}
```

**Status Values:**
- `OK` — Service is healthy
- `DEGRADED` — Service is partially available
- `DOWN` — Service is unavailable

**Overall Status Logic:**
- All OK → OK
- Postgres or Router DOWN → DOWN
- Any other service DOWN → DEGRADED

---

#### GET /admin/workflows/metrics

Returns aggregate workflow metrics for the Fleet Dashboard.

**Permission:** `VIEW_METRICS` (Viewer+)

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `repo_id` | UUID | Optional. Filter metrics to a single repo |

**Response:**
```json
{
  "aggregate": {
    "running": 42,
    "stuck": 3,
    "failed": 5,
    "completed": 150
  },
  "queue_depth": 88,
  "pass_rate_24h": 78.5,
  "repos": [
    {
      "repo_id": "uuid",
      "repo_name": "owner/repo",
      "tier": "execute",
      "running": 6,
      "stuck": 0,
      "failed": 2,
      "completed": 48,
      "queue_depth": 12,
      "pass_rate_24h": 78.0,
      "has_elevated_failure_rate": false,
      "stuck_workflow_ids": []
    }
  ],
  "alerts": [
    {
      "alert_type": "stuck_workflows",
      "severity": "warning",
      "repo_name": "other/repo",
      "message": "2 workflow(s) stuck > 2h",
      "workflow_ids": ["wf-123", "wf-456"],
      "details": {"threshold_hours": 2}
    }
  ],
  "checked_at": "2026-03-06T10:30:00Z",
  "stuck_threshold_hours": 2
}
```

**Metrics Definitions:**
- `running` — Workflows currently in progress
- `stuck` — Running workflows exceeding stuck threshold (default: 2 hours)
- `failed` — Workflows that failed in the last 24 hours
- `completed` — Workflows that completed successfully in the last 24 hours
- `queue_depth` — Tasks waiting in Temporal task queue
- `pass_rate_24h` — Percentage of workflows completing on first attempt

**Alert Types:**
- `stuck_workflows` — Workflows running longer than threshold
- `elevated_failure_rate` — Repo failure rate exceeds threshold (default: 30%)

---

### Repo Management

#### GET /admin/repos

Returns all registered repositories with health status.

**Permission:** `VIEW_REPOS` (Viewer+)

**Response:**
```json
{
  "repos": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "owner": "homeiq",
      "repo": "platform",
      "tier": "execute",
      "status": "active",
      "installation_id": 12345,
      "health": "ok"
    }
  ],
  "total": 1
}
```

**Health Values:**
- `ok` — Active and healthy
- `degraded` — Paused or elevated failures
- `unknown` — Unable to determine

---

#### POST /admin/repos

Registers a new repository at Observe tier.

**Permission:** `REGISTER_REPO` (Admin)

**Request:**
```json
{
  "owner": "homeiq",
  "repo": "platform",
  "installation_id": 12345,
  "default_branch": "main"
}
```

**Response (201):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "owner": "homeiq",
  "repo": "platform",
  "tier": "observe",
  "installation_id": 12345,
  "message": "Registered homeiq/platform at Observe tier"
}
```

**Errors:**
- `409 Conflict` — Repository already registered

**Audit Event:** `repo_registered`

---

#### GET /admin/repos/{id}

Returns detailed repository profile.

**Permission:** `VIEW_REPOS` (Viewer+)

**Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "owner": "homeiq",
  "repo": "platform",
  "tier": "execute",
  "status": "active",
  "installation_id": 12345,
  "default_branch": "main",
  "required_checks": ["ruff", "pytest"],
  "tool_allowlist": ["edit_file", "run_tests"],
  "webhook_secret": "********",
  "writes_enabled": true,
  "created_at": "2026-03-06T10:00:00Z",
  "updated_at": "2026-03-06T10:30:00Z"
}
```

**Errors:**
- `404 Not Found` — Repository not found

---

#### PATCH /admin/repos/{id}/profile

Updates repository profile settings.

**Permission:** `UPDATE_REPO_PROFILE` (Admin)

**Request:**
```json
{
  "default_branch": "develop",
  "required_checks": ["ruff", "pytest", "mypy"],
  "tool_allowlist": ["edit_file", "run_tests", "bash"]
}
```

All fields are optional. Only provided fields are updated.

**Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "owner": "homeiq",
  "repo": "platform",
  "updated_fields": ["default_branch", "required_checks", "tool_allowlist"],
  "message": "Updated profile for homeiq/platform"
}
```

**Errors:**
- `404 Not Found` — Repository not found

**Audit Event:** `repo_profile_updated`

---

#### PATCH /admin/repos/{id}/tier

Admin override to change repository tier directly.

**Permission:** `CHANGE_REPO_TIER` (Admin)

**Request:**
```json
{
  "tier": "execute"
}
```

**Tier Values:** `observe`, `suggest`, `execute`

**Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "owner": "homeiq",
  "repo": "platform",
  "from_tier": "suggest",
  "to_tier": "execute",
  "message": "Changed tier for homeiq/platform: suggest → execute"
}
```

**Errors:**
- `404 Not Found` — Repository not found

**Audit Event:** `repo_tier_changed`

---

#### POST /admin/repos/{id}/pause

Pauses a repository (stops accepting new tasks).

**Permission:** `PAUSE_REPO` (Operator+)

**Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "owner": "homeiq",
  "repo": "platform",
  "status": "paused",
  "message": "Paused homeiq/platform"
}
```

**Errors:**
- `404 Not Found` — Repository not found

**Audit Event:** `repo_paused`

---

#### POST /admin/repos/{id}/resume

Resumes a paused repository.

**Permission:** `RESUME_REPO` (Operator+)

**Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "owner": "homeiq",
  "repo": "platform",
  "status": "active",
  "message": "Resumed homeiq/platform"
}
```

**Errors:**
- `404 Not Found` — Repository not found

**Audit Event:** `repo_resumed`

---

#### POST /admin/repos/{id}/writes

Toggles Publisher writes for a repository (freeze/unfreeze).

**Permission:** `TOGGLE_WRITES` (Admin)

**Request:**
```json
{
  "enabled": false
}
```

**Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "owner": "homeiq",
  "repo": "platform",
  "writes_enabled": false,
  "message": "Writes disabled for homeiq/platform"
}
```

**Errors:**
- `404 Not Found` — Repository not found

**Audit Event:** `repo_writes_toggled`

---

### Workflow Console

#### GET /admin/workflows

Returns paginated list of workflows with optional filters.

**Permission:** `VIEW_WORKFLOWS` (Viewer+)

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `repo_id` | UUID | Filter by repository |
| `status` | string | Filter by status: `running`, `stuck`, `completed`, `failed` |
| `limit` | int | Max results (default: 50, max: 100) |
| `offset` | int | Pagination offset |

**Response:**
```json
{
  "workflows": [
    {
      "workflow_id": "task-homeiq-platform-issue-123-abc123",
      "task_packet_id": "tp-uuid",
      "repo_name": "homeiq/platform",
      "issue_ref": "#123",
      "status": "running",
      "current_step": "implement",
      "started_at": "2026-03-06T10:00:00Z",
      "running_for_seconds": 3600
    }
  ],
  "total": 42,
  "limit": 50,
  "offset": 0
}
```

---

#### GET /admin/workflows/{id}

Returns detailed workflow information with timeline.

**Permission:** `VIEW_WORKFLOWS` (Viewer+)

**Response:**
```json
{
  "workflow_id": "task-homeiq-platform-issue-123-abc123",
  "task_packet_id": "tp-uuid",
  "repo_name": "homeiq/platform",
  "issue_ref": "#123",
  "status": "running",
  "current_step": "implement",
  "started_at": "2026-03-06T10:00:00Z",
  "completed_at": null,
  "running_for_seconds": 3600,
  "timeline": [
    {
      "step": "receive",
      "status": "completed",
      "started_at": "2026-03-06T10:00:00Z",
      "completed_at": "2026-03-06T10:00:05Z",
      "duration_seconds": 5
    },
    {
      "step": "implement",
      "status": "running",
      "started_at": "2026-03-06T10:00:05Z",
      "completed_at": null,
      "duration_seconds": null
    }
  ],
  "retry_info": {
    "attempt": 2,
    "max_attempts": 3,
    "last_failure_reason": "Lint check failed"
  },
  "escalation_info": null
}
```

**Errors:**
- `404 Not Found` — Workflow not found

---

#### POST /admin/workflows/{id}/rerun-verification

Reruns verification step for a workflow.

**Permission:** `RERUN_VERIFICATION` (Operator+)

**Request:**
```json
{
  "reason": "Lint errors fixed externally",
  "actor": "admin@example.com"
}
```

**Response:**
```json
{
  "workflow_id": "task-homeiq-platform-issue-123-abc123",
  "task_packet_id": "tp-uuid",
  "previous_step": "verify",
  "rerun_from_step": "verify",
  "idempotency_preserved": true,
  "message": "Verification rerun initiated for task-homeiq-platform-issue-123-abc123"
}
```

**Errors:**
- `404 Not Found` — Workflow not found
- `400 Bad Request` — Unsafe rerun (e.g., publish step)

**Audit Event:** `workflow_verification_rerun`

---

#### POST /admin/workflows/{id}/send-to-agent

Sends workflow back to Primary Agent for fix.

**Permission:** `SEND_TO_AGENT` (Operator+)

**Request:**
```json
{
  "reason": "Agent needs to fix implementation",
  "actor": "admin@example.com",
  "reset_workspace": false
}
```

**Response:**
```json
{
  "workflow_id": "task-homeiq-platform-issue-123-abc123",
  "task_packet_id": "tp-uuid",
  "sent_to_step": "implement",
  "workspace_reset": false,
  "idempotency_preserved": true,
  "message": "Workflow task-homeiq-platform-issue-123-abc123 sent back to agent"
}
```

**Errors:**
- `404 Not Found` — Workflow not found
- `400 Bad Request` — Unsafe rerun

**Audit Event:** `workflow_sent_to_agent`

---

#### POST /admin/workflows/{id}/escalate

Escalates workflow for human intervention.

**Permission:** `ESCALATE_WORKFLOW` (Operator+)

**Request:**
```json
{
  "reason": "Stuck for 4 hours",
  "actor": "admin@example.com",
  "owner": "oncall@example.com"
}
```

`owner` is optional.

**Response:**
```json
{
  "workflow_id": "task-homeiq-platform-issue-123-abc123",
  "task_packet_id": "tp-uuid",
  "escalated_at": "2026-03-06T14:00:00Z",
  "trigger": "Stuck for 4 hours",
  "owner": "oncall@example.com",
  "message": "Workflow task-homeiq-platform-issue-123-abc123 escalated for human review"
}
```

**Errors:**
- `404 Not Found` — Workflow not found

**Audit Event:** `workflow_escalated`

---

### RBAC

#### Roles

| Role | Description |
|------|-------------|
| `viewer` | Read-only access to dashboards and workflows |
| `operator` | Viewer + operational actions (pause, rerun, escalate) |
| `admin` | Operator + administrative actions (register, tier, writes, audit) |

#### Permissions by Role

| Permission | Viewer | Operator | Admin |
|------------|--------|----------|-------|
| `view_health` | ✅ | ✅ | ✅ |
| `view_metrics` | ✅ | ✅ | ✅ |
| `view_repos` | ✅ | ✅ | ✅ |
| `view_workflows` | ✅ | ✅ | ✅ |
| `pause_repo` | ❌ | ✅ | ✅ |
| `resume_repo` | ❌ | ✅ | ✅ |
| `rerun_verification` | ❌ | ✅ | ✅ |
| `send_to_agent` | ❌ | ✅ | ✅ |
| `escalate_workflow` | ❌ | ✅ | ✅ |
| `register_repo` | ❌ | ❌ | ✅ |
| `update_repo_profile` | ❌ | ❌ | ✅ |
| `change_repo_tier` | ❌ | ❌ | ✅ |
| `toggle_writes` | ❌ | ❌ | ✅ |
| `manage_users` | ❌ | ❌ | ✅ |
| `view_audit` | ❌ | ❌ | ✅ |

---

### Audit Log

#### GET /admin/audit

Queries the audit log with optional filters.

**Permission:** `VIEW_AUDIT` (Admin)

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `event_type` | string | Filter by event type |
| `actor` | string | Filter by actor (user) |
| `target_id` | string | Filter by target (repo ID or workflow ID) |
| `hours` | int | Filter to last N hours (1-720) |
| `limit` | int | Max entries (default: 100, max: 1000) |
| `offset` | int | Pagination offset |

**Event Types:**
- `repo_registered` — New repo registered
- `repo_profile_updated` — Repo profile changed
- `repo_tier_changed` — Repo tier changed
- `repo_paused` — Repo paused
- `repo_resumed` — Repo resumed
- `repo_writes_toggled` — Writes enabled/disabled
- `workflow_verification_rerun` — Verification rerun triggered
- `workflow_sent_to_agent` — Workflow sent to agent
- `workflow_escalated` — Workflow escalated

**Response:**
```json
{
  "entries": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "timestamp": "2026-03-06T14:00:00Z",
      "actor": "admin@example.com",
      "event_type": "repo_registered",
      "target_id": "660e8400-e29b-41d4-a716-446655440001",
      "details": {
        "owner": "homeiq",
        "repo": "platform",
        "tier": "observe",
        "installation_id": 12345
      }
    }
  ],
  "total": 150,
  "filtered_by": {
    "event_type": "repo_registered",
    "hours": 24
  }
}
```

---

## Error Responses

All endpoints return standard error responses:

```json
{
  "detail": "Error message describing the issue"
}
```

**Status Codes:**
- `400` — Bad request (invalid parameters)
- `401` — Unauthorized (authentication required)
- `403` — Forbidden (insufficient permissions)
- `404` — Not found (resource does not exist)
- `409` — Conflict (duplicate resource)
- `500` — Internal server error

---

## Configuration

The Admin API uses the following environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `THESTUDIO_TEMPORAL_HOST` | `localhost:7233` | Temporal server address |
| `THESTUDIO_TEMPORAL_NAMESPACE` | `default` | Temporal namespace |
| `THESTUDIO_TEMPORAL_TASK_QUEUE` | `thestudio-main` | Task queue name |
| `THESTUDIO_NATS_URL` | `nats://localhost:4222` | NATS server URL |
| `THESTUDIO_DATABASE_URL` | (see settings.py) | PostgreSQL connection string |

---

## Architecture Reference

See `thestudioarc/23-admin-control-ui.md` for full architecture documentation including:
- Fleet Dashboard mockups
- Repo Management controls
- Workflow Console timeline view
- RBAC role definitions
- Audit log requirements
