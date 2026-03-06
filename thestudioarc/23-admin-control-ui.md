# 23 — Admin Control UI (Mockups and Architecture)

**TheStudio** - Intent in. Proof out.

## Purpose

Provide a control surface for the full ecosystem:
- what repos are registered and active
- what execution planes are deployed and healthy
- what workflows are running or stuck
- how experts perform per repo and context key
- where failures occur and what policies triggered

## Intent

The intent is to eat our own dogfood and continuously improve the system by making outcomes visible and actionable.
The UI should allow safe operational control without requiring database access or log spelunking.

## Architecture Diagram

![Admin UI Architecture](assets/admin-ui-architecture.svg)

## Core UI Modules

Fleet Dashboard
- system health and SLO-style summaries
- queue depth and workflow status by repo
- global services health (Temporal, JetStream, Postgres, Router)

Repo Management
- register repos and configure repo profile
- deploy, pause, resume, disable writes
- view repo tier (observe, suggest, execute)
- view recent outcomes and loopback rates

Task and Workflow Console
- active tasks and stuck workflows
- timeline view of workflow steps
- evidence and failure categories
- safe rerun controls

Expert Performance Console
- expert weights and confidence by repo and context key
- drift and degradation detection
- expert creation events and gaps

Policy and Guardrails Console
- mandatory coverage triggers and escalation events
- violations (tool overreach, policy blocks)
- repo compliance status (rulesets, required reviewers)

Metrics and Trends
- single-pass success rate (normalized by complexity)
- verification loopbacks by category
- QA defects by severity and category
- reopen rate
- time-to-green and time-to-PR

## UI Sketches (ASCII Mockups)

### Fleet Dashboard

+----------------------------------------------------------------------------------+
| Fleet Dashboard                                                                  |
+----------------------------------------------------------------------------------+
| Global Health:  Temporal: OK  JetStream: OK  Postgres: OK  Router: OK             |
| Workflows: Running 42  Stuck 3  Failed 1   Queue Depth: 88                        |
+----------------------------------------------------------------------------------+
| Repos (Top by activity)                                                          |
| Repo                  Tier     Status     Queue   Running  Stuck  24h Pass Rate  |
| homeiq/platform        EXEC     OK         12      6        0      78%            |
| homeiq/services        SUGG     DEGRADED   33      12       2      62%            |
| tango/core             OBS      OK         43      18       1      0%             |
+----------------------------------------------------------------------------------+
| Hot Alerts                                                                        |
| - homeiq/services: Verification failures spiking (lint)                           |
| - tango/core: 2 workflows stuck > 2h (missing intent fields)                      |
+----------------------------------------------------------------------------------+

### Repo Management

+----------------------------------------------------------------------------------+
| Repo Management                                                                  |
+----------------------------------------------------------------------------------+
| Repo: homeiq/services                                                            |
| Tier: EXECUTE    Writes: ENABLED     Plane Version: v1.6.2     Health: OK        |
+----------------------------------------------------------------------------------+
| Profile                                                                          |
| - Language: Python                                                               |
| - Build: uv + pytest + ruff                                                      |
| - Required checks: test, lint, secret-scan                                       |
| - Risk paths: /auth/** -> security coverage                                      |
| - Context packs: docs/service-packs/                                             |
+----------------------------------------------------------------------------------+
| Actions                                                                          |
| [Pause Repo]  [Disable Writes]  [Redeploy Plane]  [Delete Registration]          |
+----------------------------------------------------------------------------------+
| Recent Outcomes                                                                  |
| Single-pass: 74%   Avg loops: 1.3   QA defects: 2 (last 24h)   Reopens: 0        |
+----------------------------------------------------------------------------------+

### Task and Workflow Console

+----------------------------------------------------------------------------------+
| Workflow: Issue #4123 (homeiq/services)                                          |
+----------------------------------------------------------------------------------+
| Status: RUNNING   Step: Verification Gate   Attempts: 2   Complexity: HIGH       |
+----------------------------------------------------------------------------------+
| Timeline                                                                          |
| - Context built (ok)                                                             |
| - Intent v3 created (ok)                                                         |
| - Experts consulted (ok)                                                         |
| - Plan assembled (ok)                                                            |
| - Implementation (ok)                                                            |
| - Verification failed: lint (2x)                                                 |
+----------------------------------------------------------------------------------+
| Failure Evidence                                                                  |
| - ruff: F401 unused import in src/api/foo.py                                     |
+----------------------------------------------------------------------------------+
| Controls                                                                          |
| [Rerun Verification]  [Send to Agent for Fix]  [Escalate to Human]               |
+----------------------------------------------------------------------------------+

### Expert Performance Console

+----------------------------------------------------------------------------------+
| Expert Performance                                                               |
+----------------------------------------------------------------------------------+
| Expert: Security/Auth Expert   Scope: GLOBAL   Tier: TRUSTED   Confidence: HIGH  |
+----------------------------------------------------------------------------------+
| By Repo (last 30d)                                                               |
| Repo              Consults   Avg loops   QA defects   Net impact                 |
| homeiq/services    42         0.9         1            Positive                  |
| tango/core         11         1.8         3            Mixed                     |
+----------------------------------------------------------------------------------+
| Drift                                                                            |
| - Degrading in tango/core (rework up 30%)                                        |
+----------------------------------------------------------------------------------+
| Actions                                                                          |
| [Review Outputs]  [Create New Version]  [Demote to Probation]                    |
+----------------------------------------------------------------------------------+

## Operational Rules

- Control actions require RBAC and are fully audited.
- Repo write access can be disabled globally or per repo.
- Rerun controls must be limited to safe workflow steps.
- Any policy-triggered escalation must be visible and explainable.

## Continuous Improvement Loop

The UI should allow operators to:
- flag false positives or mis-attributions
- mark intent gaps vs implementation bugs
- request service context pack updates
- request expert version updates
- view which changes improved or degraded outcomes

## Repo Registry and Controls

Repo Registry and Repo Profile

Each monitored repository must be registered with a Repo Profile. The profile drives deterministic behavior across Context, Verification, Publishing, and governance.

Minimum profile fields
- repo identifier and default branch
- automation tier: observe, suggest, execute
- language and build system
- required checks and how to run them (local and CI)
- label taxonomy and risk triggers
- ruleset requirements and required reviewers mapping (paths to reviewers)
- locations for service context packs and docs
- tool suite allowlist and write restrictions
- secrets and credential scope (what the execution plane can access)

Why this matters
- Context Manager can find service packs and entry points consistently
- Verification Gate runs the correct checks with the correct toolchain
- Publisher obeys rulesets and required reviewers
- Router can enforce mandatory coverage rules based on paths and risk labels

## Hybrid Deployment Operations

The Admin UI must support:
- registering repos and editing Repo Profiles
- deploying, pausing, and resuming per-repo execution planes
- disabling writes (Publisher freeze) per repo
- viewing expert performance per repo and context key
- surfacing stuck workflows and safe rerun controls

## GitHub Standards Management

The Admin UI should support visibility (and optionally enforcement checks) for GitHub standards:

- Validate that standard labels exist and are used correctly
- Validate that Projects v2 fields exist and are updated by automation
- Validate that PRs include the standard evidence comment format
- Provide a per-repo compliance scorecard and remediation steps

## Repo Registration Lifecycle

Repos are onboarded through an explicit registration lifecycle and promotion tiers.

Lifecycle
1. Install GitHub App (scoped permissions)
2. Configure webhooks (issues, labels, PR events)
3. Create Repo Profile (commands, checks, risk path triggers, tool allowlists)
4. Start in Observe tier (read-only, no PR writes)
5. Deploy execution plane (workspace + workers + verification runner)
6. Enable Suggest tier (draft PR only, writes guarded)
7. Enable Execute tier (full workflow, enforced gates, ruleset expectations)
8. Continuous compliance checks (scorecard, drift alerts)

Diagram
![Repo Registration Lifecycle](assets/repo-registration-lifecycle.svg)

## Safe Reruns and Idempotency

Admin UI controls must respect idempotency rules.

Safe controls
- pause repo or disable writes
- rerun from context, intent, routing, QA
- rerun verification with counters preserved
- rerun implementation only with workspace reset policy

Unsafe controls unless guarded
- rerun publish steps without idempotency key and PR lookup

Diagram reference
![Workflow Idempotency Guard](assets/workflow-idempotency-guard.svg)

## Repo Compliance Scorecard

The Admin UI should show a per-repo compliance scorecard before allowing Suggest or Execute tiers.

Checks
- GitHub rulesets present and required checks configured
- required reviewer rules for sensitive paths (where applicable)
- issue forms available for agent-run work types
- standard labels and Projects fields configured
- Publisher write guard enabled (idempotency key + PR lookup)
- execution plane health and credentials scope verified

Promotion rule
- a repo cannot be promoted to Execute tier unless compliance score passes

## Workflow Retry and Timeout Visibility

The Admin UI must surface workflow durability details for every task:

- current workflow step
- attempt count for the step
- next retry time
- time in current step
- escalation trigger and owner
- whether the task is in a human wait state

This is required for on-call operations and for reliable promotion to Execute tier.

## Quarantine Operations

The Admin UI must support quarantine operations:
- view quarantined events and reasons
- replay quarantined events after correction
- view dead-letter counts and payload pointers
All actions must be audited.

## GitHub Write Safety

The Admin UI must show the last Publisher action, idempotency key, and the target PR id for every task.

## Execution Plane Lifecycle

Execution planes are deployed per repo or per repo group to isolate credentials and toolchains.

Plane states
- deploying: plane is starting, health checks pending
- healthy: ready to accept tasks
- degraded: partial failure, limited actions allowed (read-only or no-write mode)
- paused: plane does not accept new tasks
- stopped: plane terminated, tasks cannot dispatch

Pause semantics
- stop accepting new tasks immediately
- in-flight tasks either:
  - drain to a safe checkpoint (preferred), or
  - freeze at next safe boundary (no publish)
- writes can be disabled independently of pause (Publisher freeze)

Rollback semantics
- planes are versioned; rollback returns to last known good version
- rollback does not rewrite TaskPacket history; it resumes with new plane version

Admin UI controls
- deploy, pause, resume, stop, rollback
- disable writes (Publisher freeze)
- view health signals and last heartbeat

## Credential Scope and Rotation

Credentials must be scoped per repo and per tier.

Scope rules
- Observe tier: no write credentials
- Suggest tier: draft PR credentials only (no merge, limited writes)
- Execute tier: full Publisher write credentials, still constrained by rulesets and required reviewers

Rotation rules
- rotate tokens on a fixed cadence (example: every 30 days) or faster for high-risk repos
- emergency revoke must be immediate and auditable
- credentials are stored only in the repo execution plane secret store, never in the global control plane

Admin UI controls
- disable writes (Publisher freeze)
- revoke repo credentials
- rotate credentials

## Projects v2 Drift Detection

Projects v2 fields must remain consistent with workflow state.

Source of truth
- Workflow state in Temporal is the source of truth for Status and Automation Tier fields.

Write behavior
- Publisher reconciles Projects fields toward desired state on state transitions.
- Manual edits to Projects fields are permitted but treated as overrides.
- Overrides are detected as drift and surfaced in Admin UI.

Conflict handling
- If drift persists beyond a threshold, the system posts a comment and requests human confirmation before reconciling.

## Tool Error Visibility

Admin UI must show tool error class, endpoint, and last failure reason for any stuck workflow.

## Execute Tier Compliance Gate

Execute tier is earned. A repo cannot be promoted to Execute tier unless compliance checks pass.

Minimum compliance checks
- rulesets configured with required status checks for the repo
- required reviewer rules for sensitive paths (auth, billing, exports, infra) where applicable
- standard labels and Projects fields present
- evidence comment format enabled and validated
- Publisher idempotency guard enabled
- execution plane health checks passing
- credentials scoped and rotation configured

Admin UI requirements
- show compliance score and failures
- block promotion until all required checks pass

## Model Spend and Reliability

The Admin UI must include model and provider operational visibility:

Dashboards
- spend by repo, tier, and workflow step
- latency by provider and model class (fast, balanced, strong)
- fallback rate and fallback chains by provider
- error class distribution (rate limited, transient, auth failed, policy denied, permanent)
- top tasks by cost and the driver (overlay, complexity, repeated failures)

Controls
- set per repo spend caps and alert thresholds
- temporarily disable a provider for a repo
- force a repo into conservative routing mode (fast and balanced only) for incident response

## Ingress Dedupe Visibility

Admin UI must display deduped webhook events per repo and allow drill-down for debugging.

## Merge Mode Controls

Admin UI must display and control merge mode per repo. Default is human merge only.

## Tool Hub Governance

Admin UI must manage approved catalogs, profiles, and tool promotion states. See `25-tool-hub-mcp-toolkit.md`.

## Provider Controls

Admin UI must support disabling a provider per repo and forcing conservative routing mode.

## Repo Compliance Checker

Required reviewer compliance validation

Execute tier requires proof, not assumptions.

Compliance checker responsibilities
- verify rulesets exist and required status checks are configured
- verify required reviewer rules exist for sensitive paths (auth, billing, exports, infra) where applicable
- verify branch protections and merge settings match policy
- verify standard labels, Projects fields, and evidence comment format are in place

Promotion rule
- a repo cannot be promoted to Execute tier unless compliance checker passes.

Admin UI
- show compliance checker results and remediation steps
- block tier promotion until passing

## Ingress Dedupe TTL Clarification

Admin UI should distinguish suppressed duplicates within TTL from late duplicate deliveries after TTL, and show whether a workflow start was suppressed by idempotency.

## Compliance Checker Execution Point

Compliance checks run as a platform job triggered by Admin UI and tier promotion workflows. Results are persisted and required for promotion.
