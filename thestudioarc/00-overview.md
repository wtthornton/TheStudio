# 00 — System Overview

**TheStudio** - Intent in. Proof out.

## Purpose

This document defines the architecture and operating philosophy of the Agent Expert Framework.

The framework converts GitHub issues into high-quality pull requests by combining:
- a set of role-based primary agents (developer, architect, planner)
- a bench of specialized experts across technical and business domains
- deterministic verification and QA validation with loopbacks on failure
- an outcome-driven learning loop that improves expert routing over time

The system is designed for scale: hundreds of experts, many domains, and many repositories, while keeping quality and auditability high.

## Intent

The intent of the system is to deliver reliable, repeatable, and measurable software changes while preserving a company’s institutional knowledge.

The system must:
- interpret work requests from GitHub
- build structured context and a Complexity Index to normalize outcomes
- define explicit intent before implementation begins
- consult domain experts and assemble a single plan with provenance
- execute changes safely using constrained tools
- enforce hard verification and QA gates with loopbacks on failure
- publish PRs with evidence back to GitHub
- ingest outcomes and update expert reputation weights

Primary target behavior:
- single-pass success (verification + QA pass on first attempt)
- when loopbacks occur, capture why, how many, and how expensive they were

## Architecture Summary

The architecture is best understood as two cooperating planes:
- Agent Plane: judgment and synthesis
- Platform Plane: durability, enforcement, evidence, and learning rails

This separation keeps the system agent-native without making conversational state the source of truth.

## Master Architecture Map

![Master Architecture Map](assets/master-system-map.svg)

This diagram is the visual index of the full architecture. Each box references the corresponding document number.

## Agent Plane and Platform Plane

![Agent and Platform Planes](assets/overview-agent-platform-planes.svg)

Agent Plane components are agents with focused skills and constrained tools. They provide judgment, synthesis, and decision making.

Platform Plane components provide durability, policy enforcement, deterministic verification, event streaming, and auditable persistence. These components do not negotiate results and do not rely on conversational state.

## Core System Artifacts

- TaskPacket: the durable work record for a single GitHub work item, enriched over time
- Intent Specification: the definition of correctness (goal, constraints, invariants, acceptance criteria, non-goals)
- Expert Outputs: structured guidance produced by selected experts
- Plan + Provenance: assembled plan plus attribution of decisions to experts and sources
- Evidence Bundle: tests, checks, logs, and notes attached to the PR
- Signals: verification, QA, CI, and operational events published to the signal stream
- Reputation Weights: expert trust and confidence used by the Router

## Loopbacks and Failure Accounting

Hard gates fail closed and loop back with evidence.
- Verification Gate failure loops back to the Primary Agent with evidence
- QA failure loops back to the Primary Agent with defect list and intent mapping
- Intent can be refined when QA identifies ambiguity or missing constraints

Verification and QA must emit failure counters and categories so Outcome Ingestor can normalize by Complexity Index and update reputation fairly.

## Expert Strategy at Scale

Key strategy:
- do not create one expert per service by default
- use Service Context Packs for the long tail of services
- promote “Service Experts” only when a service becomes high-change, high-risk, or frequently misunderstood

Expert classes supported:
- Technical (architecture, infra, security)
- Business (rules, workflow intent, product constraints)
- Partner APIs (external integrations)
- Services (internal systems, critical services)
- QA / Validation (test strategy, intent validation)
- Process / Quality (SDLC, release hygiene)
- Compliance (ISO 27001, SOC2, GDPR, PCI)

## Standards and Guardrails

Standards and guardrails exist to make AI-coded output consistent and reviewable.
- Coding Standards: `20-coding-standards.md`
- Project Structure: `21-project-structure.md`
- Architecture Guardrails: `22-architecture-guardrails.md`

Agent runtime files that define behavior and enforcement:
- `AGENTS.md`, `SOUL.md`, `TOOLS.md`, `POLICIES.md`, `EVALS.md`

## Key Metrics

Quality and reliability:
- single-pass success rate (verification + QA)
- verification failure rate by category (tests, lint, security, build)
- QA defect rate by severity and intent mismatch category
- reopen rate (issue reopened after merge)

Speed and throughput:
- lead time from issue intake to PR opened
- cycle time from PR opened to merge-ready
- time spent in loopbacks

Learning effectiveness:
- expert selection precision (did the chosen experts reduce failures)
- reputation stability and drift (do weights converge or oscillate)
- coverage compliance (were required expert classes consulted)

Reusable “special sauce”:
- reuse rate of Service Context Packs and prior patterns
- frequency of repeated intent patterns captured and reused

## Documentation Map

- Overview and System Story → `00-overview.md`
- Expert Bench Architecture → `01-expert-bench-architecture.md`
- Expert Taxonomy → `02-expert-taxonomy.md`
- Context Manager Agent → `03-context-manager.md`
- Expert Recruiter Agent → `04-expert-recruiter.md`
- Expert Router Agent → `05-expert-router.md`
- Reputation Engine → `06-reputation-engine.md`
- Assembler Agent → `07-assembler.md`
- Agent Roles → `08-agent-roles.md`
- Service Context Packs → `09-service-context-packs.md`
- Expert Library → `10-expert-library.md`
- Intent Layer → `11-intent-layer.md`
- Outcome Ingestor → `12-outcome-ingestor.md`
- Verification Gate → `13-verification-gate.md`
- QA Quality Layer → `14-qa-quality-layer.md`
- System Runtime Flow → `15-system-runtime-flow.md`
- Coding Standards → `20-coding-standards.md`
- Project Structure → `21-project-structure.md`
- Architecture Guardrails → `22-architecture-guardrails.md`

## Admin UI Integration

This component should expose status, key metrics, and safe control hooks to the Admin UI via the Admin API (RBAC + audit log).
- Admin Control UI → `23-admin-control-ui.md`

## Hybrid Runtime Model

The framework codebase is a single repository, but the runtime supports a hybrid deployment model:

Global Control Plane (shared)
- Ingress Service (GitHub webhook receiver), Temporal, JetStream, Postgres, Router, Recruiter, Outcome, Reputation, Admin UI
- stores standards, policies, expert library, reputation, and all TaskPackets

Per-Repo Execution Plane (scoped, repeatable)
- workspace checkout, repo-scoped tool servers, Primary Agent workers, Verification runner, Publisher
- credentials, caches, and toolchains scoped per repo profile

This hybrid model prevents repo-specific build and security concerns from leaking into the global plane, while still allowing global experts and learning to compound across repos.

## Repo Registration Profile

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

## GitHub Interaction Model

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

## Hybrid Topology Diagram

![Hybrid Runtime Topology](assets/hybrid-runtime-topology.svg)

## GitHub Standards: Labels and Projects

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

## Roles and Overlays

Agent Roles are implemented as a small set of base roles plus composable overlays.

Base roles
- Developer
- Architect
- Planner

Overlays
- governance overlays: security, compliance, billing
- change-type overlays: migration, partner API, infra
- operational overlays: hotfix, high risk

The EffectiveRolePolicy drives enforcement in Router, tool policy, Verification, QA, and Publisher.
See `08-agent-roles.md`.

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

## Provenance Minimum Record

Learning and reputation require a minimum provenance record so attribution is fair and auditable.

Minimum provenance fields
- TaskPacket id and correlation_id
- repo id and repo tier
- intent version (and prior intent versions if refined)
- base role and overlays (EffectiveRolePolicy)
- experts consulted (ids, versions, scope: global or repo overlay)
- plan id and decision provenance links
- verification outcomes (pass/fail, iterations, failure categories, time-to-green)
- QA outcomes (pass/defect/rework, severity, mapping to acceptance criteria)
- Publisher actions (PR id, evidence comment id, labels, project field updates)

Diagram
![Provenance Minimum Record](assets/provenance-minimum-record.svg)

## Operational Retry and Timeout Policy

See `15-system-runtime-flow.md` for the platform default retry, timeout, and backoff policy per workflow step.

## Operational Contract Updates

Operational contract updates were added to address runtime and operations gaps:

- step-level retry, timeout, and backoff policy
- quarantine and dead-letter handling for signals
- verification flake policy and evidence bundle requirements
- QA defect taxonomy with intent_gap classification
- execution plane lifecycle semantics and credential rotation
- Publisher idempotency matrix for all GitHub writes
- Projects v2 synchronization and drift detection
- reopen event handling and attribution
- compliance gate before Execute tier promotion

See `15-system-runtime-flow.md`, `23-admin-control-ui.md`, `TOOLS.md`, `POLICIES.md`, `13-verification-gate.md`, `14-qa-quality-layer.md`, and `12-outcome-ingestor.md`.

## OpenClaw Sidecar

OpenClaw is not required for the core platform.

If desired in later phases, OpenClaw can be integrated as an optional sidecar for interactive operations and multi-channel inputs, while keeping all durable state and GitHub writes inside the platform rails.

See `24-openclaw-sidecar.md`.

## Ingress Service

Ingress Service is the required entry point for GitHub events.

Responsibilities
- receive GitHub webhooks and validate signatures
- normalize events into Work Requests
- consult Repo Registry to enforce tier gating
- start Temporal workflows with correlation identifiers

## Tool Hub (MCP) Strategy

The platform uses a Tool Hub to provide deterministic MCP tooling to agents.

Key rules
- tools are grouped into suites and governed by RoleSpec and OverlaySpec
- tools are enabled through profiles and an approved catalog
- repo-specific tools remain isolated in per-repo execution planes
- Publisher is the only GitHub writer

See `25-tool-hub-mcp-toolkit.md`.

## Model Runtime and Routing

TheStudio uses a Model Gateway to route LLM calls by step, role + overlays, repo tier, complexity, and recent failure categories.

Goals
- best cost-per-performance by default
- deterministic fallbacks when providers are rate limited
- auditable model usage and spend per repo

See `26-model-runtime-and-routing.md`.

## Ingress Idempotency and Dedupe

Ingress must dedupe GitHub events and ensure idempotent TaskPacket creation and workflow starts. See `15-system-runtime-flow.md`.

## Adversarial Input Policy

Adversarial input and prompt injection defense

GitHub issues, comments, PR descriptions, and linked content are untrusted inputs.

Rules
- treat all GitHub text as data, not instructions
- only explicit commands in a strict allowlist are interpreted (example: /agent run)
- command parsing must ignore surrounding text and must not accept natural-language variants
- never allow text to expand tool permissions, tiers, or policy
- tool allowlists are enforced only by EffectiveRolePolicy and repo tier, not by user text

Sanitization
- strip or neutralize prompt-like instruction blocks from untrusted text before model calls
- do not paste entire untrusted threads into model prompts; use structured extraction
- record a risk flag when suspicious patterns are detected (tool requests, credential mentions, “ignore previous instructions”)

Escalation
- suspicious payloads require human review for execute tier actions
- repeated suspicious activity from a repo can force it into observe tier until reviewed

## v20 Critical Hardening Additions

v20 hardening additions were made to address production-critical gaps:

- Ingress webhook dedupe and idempotent workflow starts
- explicit adversarial input and prompt injection policy
- explicit merge policy (human merge by default)
- Tool Hub licensing and deployment posture (OSS gateway default)
- Model Gateway enforcement boundary and provider key custody
- compliance checker requirement for required reviewer rules and rulesets before Execute tier

## Release Label

This document set is branded as TheStudio Phase 1 (final_phase1).
