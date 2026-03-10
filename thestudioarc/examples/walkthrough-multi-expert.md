# Pipeline Walkthrough: Multi-Expert Complex Change

**Story:** 14.3 — Pipeline walkthrough example (multi-expert path)
**Scenario:** Add rate limiting to the intake webhook with security review — new middleware, configuration schema, Redis dependency, and auth-path changes.
**Issue:** `acme/platform#587` — "Add per-repo rate limiting to intake webhook to prevent abuse"
**Trust tier:** Execute
**Outcome:** Multi-expert consult with conflict resolution, one verification loopback, draft PR published.

---

## Pipeline at a Glance

```
GitHub Issue #587
      |
  [1. Intake]       webhook → eligibility → TaskPacket (received), overlays: [security]
      |
  [2. Context]      enrichment → high complexity, risk_flags: auth + infra (enriched)
      |
  [3. Intent]       IntentSpec v1 → goal, AC, constraints, non-goals (intent_built)
      |
  [4. Router]       3 experts selected: security, infra, intake-service (routed)
      |
  [5. Assembler]    merge 3 expert outputs → conflict resolution → execution plan
      |
  [6. Implement]    Primary Agent edits 4 files → EvidenceBundle (in_progress)
      |
  [7. Verify]       ruff pass, pytest FAIL → loopback #1 → re-implement → pass
      |
  [8. QA]           intent validation → all criteria pass
      |
  [9. Publish]      draft PR + evidence comment + labels (published)
      |
  GitHub PR #588 (draft, awaiting human merge)
```

---

## Stage 1 — Intake

**Upstream:** GitHub `issues.labeled` webhook event
**Downstream:** Context Manager

The Ingress Service receives the webhook for issue #587. HMAC signature validates. The Intake Agent runs `evaluate_eligibility`: `agent:run` label present, repo registered, repo not paused, no active workflow. All gates pass.

`_select_base_role` maps `type:feature` to `BaseRole.DEVELOPER`. The issue carries `risk:auth` (rate limiting touches auth middleware), so the security overlay is applied immediately. `EffectiveRolePolicy.compute` produces a developer policy with `overlays=[security]`, which sets `publishing_posture=draft_until_checks` and adds `security` to `mandatory_expert_classes`.

**TaskPacket at end of Intake:**

```json
{
  "id": "tp-f7e6d5c4-b3a2-1098-7654-321fedcba098",
  "repo": "acme/platform",
  "issue_id": 587,
  "status": "received",
  "effective_role": {
    "base_role": "developer",
    "overlays": ["security"],
    "mandatory_expert_classes": ["security"],
    "publishing_posture": "draft_until_checks"
  }
}
```

**Labels applied by Intake:** `agent:queued`, `risk:auth`

---

## Stage 2 — Context

**Upstream:** TaskPacket (received)
**Downstream:** Intent Builder

The Context Manager inspects the repository. It reads the Repo Profile to find entry points and risk path triggers. The implied diff surface spans multiple files: the webhook handler, a new middleware module, configuration schema, and infrastructure (Redis dependency for rate-limit counters).

Risk path triggers fire for two categories: `auth` (middleware intercepts requests before authentication) and `infra` (new Redis dependency changes deployment topology). The Context Manager adds the `infra` overlay, expanding `mandatory_expert_classes` to `["security", "infra"]`.

The Complexity Index scores the change as `band=high`: four files across two services (webhook + Redis), schema changes for rate-limit config, cross-cutting middleware that affects all inbound traffic.

**TaskPacket at end of Context:**

```json
{
  "status": "enriched",
  "scope": {
    "files_touched": [
      "src/intake/webhook.py",
      "src/intake/middleware/rate_limiter.py",
      "src/intake/config.py",
      "docker-compose.yml"
    ],
    "entry_points": ["POST /webhook"]
  },
  "risk_flags": {
    "auth": true,
    "infra": true,
    "migration": false,
    "billing": false
  },
  "complexity_index": {
    "score": 7,
    "band": "high",
    "dimensions": { "files": 4, "services": 2, "schema_changes": 1 }
  }
}
```

---

## Stage 3 — Intent

**Upstream:** TaskPacket (enriched) + risk flags + repo standards
**Downstream:** Router

The Intent Builder reads the enriched TaskPacket and issue body. The high complexity and multiple risk flags produce a detailed IntentSpec with explicit security constraints and non-goals to prevent scope creep.

**IntentSpec v1:**

```json
{
  "id": "intent-2b3c4d5e-f6a7-8901-bcde-f01234567890",
  "taskpacket_id": "tp-f7e6d5c4-b3a2-1098-7654-321fedcba098",
  "version": 1,
  "goal": "Add per-repo rate limiting to the intake webhook so that abusive callers are throttled before reaching eligibility checks.",
  "constraints": [
    "Rate-limit state must use Redis with configurable TTL",
    "Rate limits must be configurable per repo via Repo Profile",
    "Must not block legitimate webhook traffic under normal load",
    "Must return HTTP 429 with Retry-After header when limit exceeded",
    "Middleware must execute before auth validation to protect against unauthenticated flood"
  ],
  "acceptance_criteria": [
    "POST /webhook returns 429 when rate limit is exceeded for a repo",
    "Rate-limit config is read from Repo Profile with sensible defaults",
    "Existing webhook paths (201, 400, 422) are unaffected under normal load",
    "Redis connection failure degrades gracefully (allow traffic, log warning)",
    "docker-compose.yml includes Redis service for local development"
  ],
  "non_goals": [
    "Do not implement global (non-repo-scoped) rate limiting",
    "Do not add rate limiting to any endpoint other than the intake webhook",
    "Do not modify the webhook response body schema for non-429 responses"
  ]
}
```

**TaskPacket fields updated:**

```json
{
  "status": "intent_built",
  "intent_spec_id": "intent-2b3c4d5e-f6a7-8901-bcde-f01234567890",
  "intent_version": 1
}
```

---

## Stage 4 — Router

**Upstream:** IntentSpec v1 + EffectiveRolePolicy
**Downstream:** Assembler

The Expert Router evaluates `mandatory_expert_classes` from the EffectiveRolePolicy: `["security", "infra"]`. Both must be satisfied or the pipeline blocks.

The Router then checks reputation-weighted scores for available experts in each class at `complexity=high`. It ranks candidates using `(reputation_weight * relevance_score)`:

| Expert               | Class    | Reputation | Relevance | Weighted Score |
|----------------------|----------|------------|-----------|----------------|
| security-reviewer-v3 | security | 0.91       | 0.94      | 0.855          |
| infra-deploy-v2      | infra    | 0.87       | 0.88      | 0.766          |
| auth-specialist-v1   | security | 0.78       | 0.82      | 0.640          |

The top expert per mandatory class is selected: `security-reviewer-v3` and `infra-deploy-v2`.

**Mandatory coverage rules** also trigger: the `intake-module-v2` Service Context Pack is required because the change touches `src/intake/`. This is not a full expert consult but provides module-specific conventions and patterns. The Router includes it as a third input source.

**Routing decision:**

```json
{
  "taskpacket_id": "tp-f7e6d5c4-b3a2-1098-7654-321fedcba098",
  "experts_consulted": ["security-reviewer-v3", "infra-deploy-v2"],
  "service_context_packs": ["intake-module-v2"],
  "mandatory_classes_satisfied": true,
  "consult_budget_used": 2,
  "routing_notes": "High complexity, security + infra overlays — full expert consult required"
}
```

Each expert receives the IntentSpec, the enriched scope, and the risk flags. They return structured guidance independently.

**Security expert output (abbreviated):**

```json
{
  "expert_id": "security-reviewer-v3",
  "recommendations": [
    "Use sliding-window algorithm, not fixed-window, to prevent burst attacks at boundary",
    "Rate-limit key must include repo identifier — never use raw IP alone",
    "Middleware must run before HMAC validation to avoid compute-based DoS"
  ],
  "constraints_added": ["Sliding-window counter required"],
  "risk_notes": "Placing middleware before auth is correct for flood protection but must not leak error details"
}
```

**Infra expert output (abbreviated):**

```json
{
  "expert_id": "infra-deploy-v2",
  "recommendations": [
    "Use Redis Cluster-compatible commands (no MULTI/EXEC) for future scaling",
    "Add health check for Redis in docker-compose",
    "Connection pooling via redis-py async with max_connections=20 default"
  ],
  "constraints_added": ["Redis Cluster-compatible commands only"],
  "risk_notes": "Redis failure must not take down the webhook — circuit breaker or graceful degradation required"
}
```

---

## Stage 5 — Assembler

**Upstream:** IntentSpec v1 + expert outputs + service context pack
**Downstream:** Primary Agent

The Assembler merges three input sources into a single execution plan. It detects one conflict between expert recommendations:

**Conflict detected:** The security expert recommends a sliding-window algorithm (which typically uses `MULTI/EXEC` for atomic counter updates), but the infra expert constrains commands to Redis Cluster-compatible operations (no `MULTI/EXEC`). These are incompatible.

**Resolution — intent as tiebreaker:** The IntentSpec constraint "Rate-limit state must use Redis with configurable TTL" does not mandate a specific algorithm. The Assembler resolves the conflict by selecting a Cluster-compatible sliding-window implementation using sorted sets with `ZADD` and `ZRANGEBYSCORE`, which satisfies both experts' core requirements. The resolution is recorded in provenance with both expert IDs so the learning pipeline can attribute the decision.

**Execution plan:**

```json
{
  "plan_id": "plan-a1b2c3d4-e5f6-7890-abcd-123456789abc",
  "taskpacket_id": "tp-f7e6d5c4-b3a2-1098-7654-321fedcba098",
  "intent_spec_id": "intent-2b3c4d5e-f6a7-8901-bcde-f01234567890",
  "steps": [
    "Create src/intake/middleware/rate_limiter.py with sliding-window using sorted sets",
    "Add rate-limit config fields to src/intake/config.py with per-repo defaults",
    "Wire middleware into src/intake/webhook.py before HMAC validation",
    "Add Redis service to docker-compose.yml with health check",
    "Add tests for 429 response, graceful degradation, and config defaults"
  ],
  "conflict_resolutions": [
    {
      "conflict": "Sliding-window algorithm vs Redis Cluster compatibility",
      "resolution": "Use sorted-set-based sliding window (ZADD/ZRANGEBYSCORE) — Cluster-safe",
      "sources": ["security-reviewer-v3", "infra-deploy-v2"],
      "tiebreaker": "intent_spec"
    }
  ],
  "provenance": [
    { "source": "security-reviewer-v3", "scope": "expert_consult" },
    { "source": "infra-deploy-v2", "scope": "expert_consult" },
    { "source": "intake-module-v2", "scope": "service_context_pack" }
  ]
}
```

---

## Stage 6 — Implement

**Upstream:** Execution plan + IntentSpec v1
**Downstream:** Verification Gate

The Primary Agent (Developer role with security + infra overlays) executes the plan. It creates the rate-limiter middleware, updates the config module with per-repo rate-limit fields, wires the middleware into the webhook handler, and adds a Redis service to `docker-compose.yml`.

The agent produces an EvidenceBundle summarizing all changes. TaskPacket status advances to `in_progress`.

**EvidenceBundle:**

```json
{
  "taskpacket_id": "tp-f7e6d5c4-b3a2-1098-7654-321fedcba098",
  "intent_version": 1,
  "files_changed": [
    "src/intake/middleware/rate_limiter.py",
    "src/intake/config.py",
    "src/intake/webhook.py",
    "docker-compose.yml"
  ],
  "agent_summary": "Added sliding-window rate limiter using Redis sorted sets. Middleware runs before HMAC validation. Graceful degradation on Redis failure. Per-repo config with defaults.",
  "loopback_attempt": 0
}
```

---

## Stage 7 — Verify

**Upstream:** EvidenceBundle + TaskPacket (in_progress)
**Downstream:** QA Agent

The Verification Gate loads the Repo Profile and reads `required_checks: ["ruff", "pytest"]`. It runs each check in sequence.

**Attempt 1 — FAIL:**

`run_ruff` passes with 0 violations. `run_pytest` fails: 1 test failure in `test_rate_limiter_graceful_degradation` — the test expects `ConnectionError` but the implementation raises `redis.exceptions.ConnectionError` (different exception hierarchy).

The gate emits a `verification_failed` signal and loops back to the Primary Agent with evidence.

```json
{
  "event": "verification_failed",
  "taskpacket_id": "tp-f7e6d5c4-b3a2-1098-7654-321fedcba098",
  "loopback_count": 1,
  "checks": [
    { "name": "ruff", "result": "passed", "details": "0 violations" },
    { "name": "pytest", "result": "failed", "details": "51 passed, 1 failed" }
  ],
  "failure_category": "test_assertion"
}
```

The Primary Agent fixes the exception handling to catch `redis.exceptions.ConnectionError` explicitly and re-submits.

**Attempt 2 — PASS:**

`run_ruff`: 0 violations. `run_pytest`: 52 passed, 0 failed. TaskPacket status advances to `verification_passed`.

```json
{
  "event": "verification_passed",
  "taskpacket_id": "tp-f7e6d5c4-b3a2-1098-7654-321fedcba098",
  "loopback_count": 1,
  "checks": [
    { "name": "ruff", "result": "passed", "details": "0 violations", "duration_ms": 410 },
    { "name": "pytest", "result": "passed", "details": "52 passed, 0 failed", "duration_ms": 6340 }
  ]
}
```

---

## Stage 8 — QA

**Upstream:** Verification signal + IntentSpec v1 + EvidenceBundle
**Downstream:** Publisher

The QA Agent validates the implementation against each acceptance criterion in IntentSpec v1. Because security and infra overlays are active, QA applies stricter validation: it checks that expert constraints were satisfied and that the conflict resolution produced a correct outcome.

**QA result:**

```json
{
  "passed": true,
  "defect_count": 0,
  "has_intent_gap": false,
  "criteria_results": [
    {
      "criterion": "POST /webhook returns 429 when rate limit exceeded",
      "passed": true,
      "evidence": "pytest: test_webhook_returns_429_on_rate_limit PASSED"
    },
    {
      "criterion": "Rate-limit config read from Repo Profile with defaults",
      "passed": true,
      "evidence": "Config module defines defaults; test validates override"
    },
    {
      "criterion": "Existing webhook paths unaffected under normal load",
      "passed": true,
      "evidence": "All prior webhook tests pass unchanged"
    },
    {
      "criterion": "Redis failure degrades gracefully",
      "passed": true,
      "evidence": "pytest: test_rate_limiter_graceful_degradation PASSED"
    },
    {
      "criterion": "docker-compose.yml includes Redis service",
      "passed": true,
      "evidence": "Diff confirms redis service with health check added"
    }
  ],
  "expert_constraint_validation": [
    { "constraint": "Sliding-window counter required", "satisfied": true },
    { "constraint": "Redis Cluster-compatible commands only", "satisfied": true }
  ]
}
```

---

## Stage 9 — Publish

**Upstream:** QA result + EvidenceBundle + IntentSpec v1
**Downstream:** GitHub (draft PR)

The Publisher creates a draft PR on the working branch. Because `publishing_posture=draft_until_checks` (from the security overlay), the PR remains in draft state until a human reviews. The evidence comment is posted with the `<!-- thestudio-evidence -->` marker for idempotent updates.

**TaskPacket at end of Publish:**

```json
{
  "status": "published",
  "loopback_count": 1
}
```

**Evidence comment (abbreviated):**

```
<!-- thestudio-evidence -->

## TheStudio Evidence

| Field            | Value                                        |
|------------------|----------------------------------------------|
| TaskPacket ID    | tp-f7e6d5c4-b3a2-1098-7654-321fedcba098     |
| Intent Version   | v1                                           |
| Verification     | PASSED (1 loopback)                          |
| QA               | PASSED                                       |

### Intent Summary

**Goal:** Add per-repo rate limiting to the intake webhook so that abusive
callers are throttled before reaching eligibility checks.

### Acceptance Criteria

- [x] POST /webhook returns 429 when rate limit exceeded
- [x] Rate-limit config read from Repo Profile with defaults
- [x] Existing webhook paths unaffected under normal load
- [x] Redis failure degrades gracefully
- [x] docker-compose.yml includes Redis service

### Expert Coverage

- security-reviewer-v3 (security) — mandatory, reputation 0.91
- infra-deploy-v2 (infra) — mandatory, reputation 0.87
- intake-module-v2 — service context pack

**Conflict resolutions:** 1 (sliding-window vs Cluster compatibility — resolved via sorted sets)

### Verification Results

| Check  | Result | Details                    |
|--------|--------|----------------------------|
| ruff   | PASSED | 0 violations               |
| pytest | PASSED | 52 passed, 0 failed        |

### Loopback Summary

- Verification loops: 1 (category: test_assertion)
- QA loops: 0

### Files Changed

- `src/intake/middleware/rate_limiter.py` (new)
- `src/intake/config.py`
- `src/intake/webhook.py`
- `docker-compose.yml`

---
*Generated by TheStudio — AI-augmented software delivery*
```

**Labels applied:** `verification:passed`, `agent:human-review`, `risk:auth`
**Projects v2 Status field:** `In Review`

---

## Signal and State Summary

| Stage      | TaskPacket Status      | Key Output                                     |
|------------|------------------------|-------------------------------------------------|
| Intake     | `received`             | TaskPacket created, security overlay applied    |
| Context    | `enriched`             | high complexity, auth + infra risk flags        |
| Intent     | `intent_built`         | IntentSpec v1 with 5 acceptance criteria        |
| Router     | `intent_built`         | 2 experts + 1 service context pack selected     |
| Assembler  | `intent_built`         | execution plan, 1 conflict resolved             |
| Implement  | `in_progress`          | EvidenceBundle, 4 files changed                 |
| Verify     | `verification_passed`  | 1 loopback (test_assertion), then passed        |
| QA         | `verification_passed`  | all criteria pass, expert constraints validated |
| Publish    | `published`            | draft PR #588, evidence comment posted          |

**Total loopbacks:** 1 (verification: test_assertion)
**Intent versions:** 1 (no refinement needed)
**Experts consulted:** 2 (security-reviewer-v3, infra-deploy-v2) + 1 service context pack
**Conflicts resolved:** 1 (sliding-window algorithm vs Redis Cluster compatibility)
