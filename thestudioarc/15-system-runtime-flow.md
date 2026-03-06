# 15 — System Runtime Flow (OSS Python Stack)

**TheStudio** - Intent in. Proof out.

## Purpose

Describe the end-to-end runtime flow from GitHub issue intake to PR publication and learning updates, using the OSS Python stack:
- Ingress Service gateway and tool policy
- Temporal for durable workflows and loopbacks
- Postgres + pgvector for artifacts and retrieval
- NATS JetStream for the signal stream
- FastAPI tool servers for controlled integration access
- OpenTelemetry-based observability

## Intent

The intent is to show how the architecture behaves under real conditions:
- how agents coordinate without free-form agent-to-agent chat
- how gates fail closed and loop back with evidence
- how signals flow asynchronously into learning

## Diagram

![Runtime System Flow](assets/runtime-system-flow.svg)

## Runtime Steps

1. Intake Agent receives GitHub work item and creates TaskPacket stub.
2. Context Manager Agent enriches TaskPacket and computes complexity.
3. Intent Builder Agent defines intent and consults intent experts via Router if needed.
4. Router selects expert subset; Recruiter creates experts if gaps exist.
5. Assembler produces plan + provenance + QA mapping.
6. Primary Agent implements changes and produces evidence.
7. Verification Gate runs checks, emits signals, loops back on failure.
8. QA Agent validates against intent, consults QA experts as needed, emits signals, loops back on failure.
9. Publisher posts PR and evidence to GitHub.

## Learning Loop

![Learning Loop](assets/runtime-learning-loop.svg)

Signals flow through JetStream to Outcome Ingestor and Reputation Engine.
Router uses updated weights for future selections.

## Agent Communication Model

Agents communicate through:
- artifacts in Postgres (TaskPacket, intent, outputs, plan, evidence)
- signals in JetStream (verification and QA events)
- narrow RPC calls for controlled queries (Router and Recruiter), with all outputs persisted for audit

## Admin UI Integration

This component should expose status, key metrics, and safe control hooks to the Admin UI via the Admin API (RBAC + audit log).

## Hybrid Runtime Model

The framework codebase is a single repository, but the runtime supports a hybrid deployment model:

Global Control Plane (shared)
- Ingress Service gateway, Temporal, JetStream, Postgres, Router, Recruiter, Outcome, Reputation, Admin UI
- stores standards, policies, expert library, reputation, and all TaskPackets

Per-Repo Execution Plane (scoped, repeatable)
- workspace checkout, repo-scoped tool servers, Primary Agent workers, Verification runner, Publisher
- credentials, caches, and toolchains scoped per repo profile

This hybrid model prevents repo-specific build and security concerns from leaking into the global plane, while still allowing global experts and learning to compound across repos.

## GitHub Interaction Points

GitHub Interaction Model (How, When, Why)

GitHub is the primary control surface for humans and the platform. Agents should not rely on hidden internal state. Every important decision should be visible in GitHub as either a label, a comment, a status check, or a project field update.

What we read from GitHub
- issues: title, body, labels, assignees, linked PRs, issue form fields
- comments: clarifications and stakeholder constraints
- projects: status fields (queued, in progress, blocked), priority, owner
- PRs: diffs, review outcomes, check statuses, merge state
- actions checks: pass/fail, logs, artifact links

What we write back to GitHub
- issue comments: intent summary, missing inputs, escalation notes
- labels: agent tier, risk flags, blocked reasons
- project fields: lifecycle state updates (queued, in progress, review, blocked, done)
- pull requests: create draft PRs, update description, attach evidence summary
- status checks: verification and QA results are reflected via CI and posted evidence

Which agents interact with GitHub and why
- Intake Agent
  - reads issue and labels to decide eligibility and role
  - writes minimal feedback when required info is missing (through Publisher path)
- Context Manager Agent
  - read-only, uses repo tools rather than writing to GitHub
  - may request clarifications by raising questions for Publisher to post
- Intent Builder Agent
  - read-only, produces intent and questions; Publisher posts clarifications if needed
- Primary Agent
  - does not publish directly; produces PR summary and evidence bundle for Publisher
- QA Agent
  - does not merge; can request rework and can request intent refinement
- Publisher (platform service in the execution plane)
  - the only writer for PR creation, label updates, and standardized evidence comments

Hard rules
- do not let non-publisher agents write to GitHub
- all writes are tied to a TaskPacket id and intent version
- draft PR first, ready-for-review only after verification and QA pass
- rulesets and required reviewers are enforced by GitHub; we do not bypass them

## GitHub Standards: Labels, Projects, Evidence

Standard GitHub Labels (Platform Standard)

These labels are the minimum standard across all registered repos. Repos may add local labels, but should not change meanings of standard labels.

Lifecycle and control
- agent:run
  - indicates the issue is eligible for automation; Intake Agent should enqueue the task
- agent:queued
  - task is in queue or awaiting workflow start
- agent:in-progress
  - workflow is running
- agent:blocked
  - workflow blocked; issue must contain a blocking reason comment
- agent:human-review
  - escalation triggered; requires human approval
- agent:paused
  - repo or workflow paused by Admin UI

Automation tier (repo profile may set defaults)
- tier:observe
- tier:suggest
- tier:execute

Work type
- type:bug
- type:feature
- type:refactor
- type:chore
- type:docs
- type:security

Risk triggers (these drive mandatory expert coverage and escalation rules)
- risk:auth
- risk:billing
- risk:export
- risk:migration
- risk:compliance
- risk:partner-api
- risk:infra

Quality and outcome signals (optional, but recommended for visibility)
- qa:rework
- qa:defect
- verification:failed
- verification:passed

Blocking reasons (optional but recommended)
- blocked:missing-info
- blocked:waiting-review
- blocked:ci-failing
- blocked:policy

Label rules
- only Publisher writes lifecycle labels in normal operation
- risk labels may be set by Intake Agent, but Publisher should normalize them
- issue templates should set type labels automatically when possible

Standard GitHub Projects v2 Fields (Platform Standard)

Projects v2 should be used as the standard lifecycle view across repos.

Recommended fields
- Status (single-select)
  - Backlog
  - Queued
  - In Progress
  - In Review
  - Blocked
  - Done

- Automation Tier (single-select)
  - Observe
  - Suggest
  - Execute

- Risk Tier (single-select)
  - Low
  - Medium
  - High

- Priority (single-select)
  - P0
  - P1
  - P2
  - P3

- Owner (text or single-select)
  - Team or person responsible for final approval

- Repo (text)
  - repo identifier to support a unified multi-repo project board

Workflow automations
- When agent:run applied, set Status = Queued and Automation Tier from repo default
- When PR opened and linked, set Status = In Progress
- When PR marked ready for review, set Status = In Review
- When agent:blocked applied, set Status = Blocked
- When merged/closed, set Status = Done

Why Projects fields matter
- gives humans a single view of the ecosystem without a custom UI
- allows the Admin UI to cross-check lifecycle state for consistency

Standard Agent Evidence Comment (PR)

Every agent-produced PR should contain a standardized evidence comment posted by the Publisher.
This becomes the review accelerant and the audit record.

Required contents
- TaskPacket id and correlation id
- Intent version and a one-paragraph summary
- Acceptance criteria checklist (checkbox format)
- What changed (high-level, not file-by-file)
- Evidence bundle
  - verification result summary
  - links to CI checks
  - test commands run (if local)
- Expert coverage summary
  - which expert classes were consulted
  - policy triggers that fired
- Loopback summary
  - verification loop count and top failure categories
  - QA loop count and defect categories

Why this matters
- reviewers can validate correctness quickly
- outcomes become measurable and attributable
- reduces back-and-forth in review comments

## GitHub Control Surface and Writer Enforcement

This system treats GitHub as the control surface and as untrusted input.

Trigger matrix (what starts work)
- issue opened: observe only, build visibility and readiness signals
- label agent:run: create a TaskPacket and start the workflow for eligible repos
- comment command /agent run: treated like agent:run, subject to same policy checks
- project field change: can move lifecycle state, but cannot bypass tier gates
- admin override: may pause a repo, disable writes, or change tier with audit log

Write authority (who can write to GitHub)
- Publisher is the only component allowed to write to GitHub (PR creation, comments, labels, project fields)
- This is enforced by GitHub App permissions and token scope, not by convention
- No other agent role receives GitHub write credentials

Diagram
![GitHub Control Surface](assets/github-control-surface.svg)

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

## Execution Plane Isolation

Hybrid isolation boundaries are enforced by credentials and deployment topology.

Global control plane (shared)
- Router, Recruiter, Expert Library, Reputation, Outcome Ingestor, Postgres, JetStream, Temporal, Admin UI
- No repo checkout and no repo-scoped secrets live here

Per-repo execution plane (scoped)
- workspace checkout and repo tools
- Primary Agent workers
- verification runner
- Publisher (GitHub writer for that repo)
- credentials scoped to a single repo and tier

Security rules
- no cross-repo credentials
- tokens are least privilege and rotated
- repo write permissions exist only in execution plane and only for Publisher

## Workflow Idempotency and Safe Reruns

Durable workflows require explicit idempotency rules, especially for GitHub writes.

Safe to rerun (idempotent or replayable)
- context construction
- intent construction and refinement
- routing and expert consults (prefer cached artifacts)
- QA evaluation (read-only)

Retryable with safeguards
- implementation step (requires branch reset or clean workspace rule)
- verification (retryable, but loop counts and categories must be recorded)

Not safe to rerun without guard
- publishing actions: PR creation, label updates, project field updates, evidence comments

Publisher idempotency guard
- use a deterministic idempotency key derived from TaskPacket id + intent version
- lookup existing PR for the TaskPacket before creating a new one
- treat repeated publish calls as updates to the same PR, not new PR creation
- record publish attempts in TaskPacket for audit

Diagram
![Workflow Idempotency Guard](assets/workflow-idempotency-guard.svg)

## Retry, Timeout, and Backoff Policy

The system must define deterministic retry, timeout, and backoff rules per workflow step. This prevents runaway retries and makes stuck workflows visible and actionable.

Workflow step policies (defaults, repo profile may tighten but not loosen for high-risk overlays)

| Step | Timeout | Retries | Backoff | Escalation trigger |
|---|---:|---:|---|---|
| Intake and registration check | 2m | 2 | exponential | repo not registered or tier blocks |
| Context build | 10m | 3 | exponential | repeated failure or missing pack gap |
| Intent build | 10m | 2 | exponential | missing required fields or conflicting constraints |
| Expert routing and consults | 15m | 2 | exponential | budget exceeded or missing coverage |
| Assemble plan and provenance | 10m | 2 | exponential | unresolved conflicts |
| Implementation (Primary Agent) | 60m | 2 | exponential | repeated same-category failures |
| Verification | 45m | 3 | bounded (see flake policy) | loop cap reached |
| QA validation | 30m | 2 | exponential | defect pressure high or intent gap |
| Publish to GitHub (Publisher) | 5m | 5 | fast retry | idempotency guard must prevent duplicates |
| Human approval wait | 7d | N/A | reminder cadence | escalate after thresholds |

Human approval wait policy
- The workflow may enter a waiting state for required reviewers or explicit human review.
- Reminder cadence: 24h, 72h, 7d.
- After 7 days, escalate to agent:human-review with a summary and block automation until resolved.

Admin UI requirements
- Show: current step, attempt count, next retry at, time in step, and escalation reason.

## Signal Quarantine and Replay

Signals and workflow outputs are treated as data inputs and must be validated. Malformed or uncorrelated events must not poison learning.

Quarantine rules (must quarantine)
- missing correlation_id or TaskPacket id
- unknown TaskPacket
- unknown repo id
- invalid category or severity values
- duplicated event with conflicting payload (idempotency conflict)

Dead-letter rules
- events that cannot be parsed or validated after N attempts are moved to a dead-letter stream with the raw payload and failure reason.

Replay and correction
- quarantined events can be corrected by an operator (or automated fix) and replayed.
- replay must be deterministic: reprocessing produces the same aggregates given the same ordered event set.

Admin UI requirements
- show quarantined count by repo and category
- provide drill-down to failure reason and payload pointer
- provide replay action with audit log

## Verification Flake Policy

See `13-verification-gate.md` for the flake policy, caps, and evidence requirements.

## GitHub Write Idempotency Rules

Publisher write actions must be idempotent and reconcile toward a desired state.

Idempotency key
- Use a deterministic idempotency key derived from TaskPacket id + intent version.

Write types and guard behavior
- PR create
  - lookup existing PR for TaskPacket; if found, do not create a new PR
  - if not found, create a draft PR
- Evidence comment
  - use a single pinned or uniquely-tagged comment and update it in place
  - do not spam multiple evidence comments on retries
- Labels
  - reconcile labels toward desired state (add missing, remove invalid lifecycle labels)
  - do not oscillate between states; workflow state is the source of truth
- Projects v2 fields
  - reconcile fields toward desired state
  - manual overrides are respected but flagged as drift in Admin UI

Acceptance
- Publisher retries never create duplicate PRs
- Evidence comment remains a single updated thread per TaskPacket

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

## Human Approval Wait States

Human approvals are first-class workflow states.

When to enter human wait
- agent:human-review label applied by policy
- required reviewer approvals missing for sensitive paths
- compliance or security escalation triggered
- repeated loopbacks exceed caps

Behavior
- workflow transitions to waiting state with a clear reason and required actions
- Publisher posts a summary comment to the issue or PR with what is needed
- reminders at 24h, 72h, 7d
- after 7d, escalate to owners and pause automation for that task until resolved

## Projects v2 Field Synchronization

Projects v2 fields must remain consistent with workflow state.

Source of truth
- Workflow state in Temporal is the source of truth for Status and Automation Tier fields.

Write behavior
- Publisher reconciles Projects fields toward desired state on state transitions.
- Manual edits to Projects fields are permitted but treated as overrides.
- Overrides are detected as drift and surfaced in Admin UI.

Conflict handling
- If drift persists beyond a threshold, the system posts a comment and requests human confirmation before reconciling.

## Evidence Bundle Requirements

See `13-verification-gate.md` for minimum evidence bundle requirements for pass and failure.

## Ingress Service

Ingress Service is the required entry point for GitHub events.

Responsibilities
- receive GitHub webhooks and validate signatures
- normalize events into a Work Request
- enforce repo tier gating by consulting Repo Registry
- start Temporal workflow with correlation identifiers

Note
- OpenClaw is optional and may be integrated later as a sidecar (see `24-openclaw-sidecar.md`).

## Model Execution

Agents call LLMs through the Model Gateway.

Model Gateway responsibilities
- route by workflow step, role + overlays, repo tier, and complexity
- enforce spend, token, and retry budgets
- handle provider failover and fallbacks
- record model audit metadata (model, tokens, cost, latency)

Claude Code headless is optional as a coding engine inside the per-repo execution plane and should be treated as a provider behind Model Gateway.

See `26-model-runtime-and-routing.md`.

## Ingress Idempotency and Dedupe

Ingress idempotency and dedupe

GitHub can deliver duplicate webhook events. Ingress must be idempotent.

Dedupe keys
- use GitHub delivery id (X-GitHub-Delivery) plus repo id as the primary dedupe key
- store dedupe keys in Postgres with TTL (example: 14 days) for replay protection

Idempotent TaskPacket creation
- creating a TaskPacket is keyed by (repo id, issue/PR id, event type) and must be idempotent
- if a TaskPacket already exists for the work item, Ingress must reuse it and append the new event to the task timeline

Workflow start idempotency
- Temporal workflow id must be derived from TaskPacket id
- starting the workflow must be idempotent: if workflow exists, Ingress does not start a new one

Admin UI visibility
- show suppressed duplicate events count per repo
- show most recent duplicate payload pointers for debugging

## Merge Policy

By default, Publisher stops at PR creation and evidence posting. Merge is human-driven unless repo policy explicitly enables auto-merge under strict constraints (see POLICIES.md).

## Ingress Dedupe TTL Clarification

TTL and late duplicates
- dedupe keys are retained for a fixed TTL to suppress duplicate deliveries within the normal retry window
- after TTL, a late duplicate delivery is treated as a new event, but it must still be safe:
  - TaskPacket creation remains idempotent by work-item key
  - workflow start remains idempotent by TaskPacket-derived workflow id, preventing parallel workflows for the same task
