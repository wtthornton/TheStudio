# TOOLS.md

## Purpose

Define the tool suites available to agents and the policy model for allowing tool use.

## Intent

Tools are capabilities behind policy. Agents do not get unrestricted tools. Tool access is granted by role, risk tier, and trust tier.

This file also supports skill packaging conventions, including the `allowed-tools` field described by the Agent Skills specification:
https://agentskills.io/specification

## Tool Suites (MCP-style grouping)

GitHub suite
- read issues, comments, labels
- create PRs and comments (Publisher only)

Repo suite
- read files, search, diff
- write changes to working branch (Primary Agent only)

CI suite
- trigger checks
- read check status and logs

Security suite
- secret scanning
- dependency audit
- static analysis

Observability suite
- read traces and logs (read-only)

## Policy rules

- All tools require correlation_id
- Write tools require intent version reference
- Sensitive tools require escalation triggers

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

## GitHub Tool Policy

GitHub tool policy (enforced)
- Only Publisher has GitHub write tools (create PR, comment, label, project updates)
- All other agents are read-only for GitHub
- All tool calls require correlation_id
- GitHub write calls require idempotency key and TaskPacket reference

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

## Tool Error Taxonomy

Tool servers must classify errors consistently so retries and escalation are deterministic.

Error classes
- transient: temporary failure, safe to retry with backoff
- rate_limited: external throttling, retry with longer backoff
- auth_failed: credential invalid or expired, do not retry; escalate
- policy_denied: forbidden action, do not retry; escalate
- permanent: invalid input or non-retryable external response, do not retry
- unknown: treat as permanent after N retries, quarantine for review

Retry mapping
- transient and rate_limited: retry with backoff
- auth_failed and policy_denied: stop and escalate
- permanent: stop and escalate or request input fix

Admin UI
- show error class distribution per repo
- show top failing tools and endpoints

## MCP Tool Hub

MCP Tool Hub

The platform may use an MCP Gateway (Docker MCP Toolkit or an OSS gateway) to host standard MCP servers as containers.

Rules
- tool access is controlled by EffectiveRolePolicy (role + overlays + repo tier)
- tools are grouped into named suites; roles allow suites, not individual ad hoc tools
- all tool calls require correlation_id
- any write-capable MCP tool must be explicitly gated and audited
- GitHub write actions remain Publisher-only, not MCP tools

See `25-tool-hub-mcp-toolkit.md`.

## Model Gateway

Model Gateway

All LLM calls must go through Model Gateway.

Rules
- agents do not call provider APIs directly
- every model call requires correlation_id and TaskPacket id
- model selection is policy-based (role + overlays + tier + complexity)
- spend and rate controls are enforced (stop conditions, fallbacks)
- model audit metadata is required (provider, model, tokens, latency, error class)

Optional engines
- Claude Code headless may be used as an optional coding engine in the per-repo execution plane
- it must be invoked under the same policy and audited like any other model call

See `26-model-runtime-and-routing.md`.

## Adversarial Input and Tool Policy

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

## Model Credential Custody

Enforcement boundary and key custody

To ensure Model Gateway is the only path to providers:
- provider API credentials are stored only in the Model Gateway service
- agent worker containers do not have provider keys
- any attempt to call providers directly is a policy violation

Audit requirement
- Model Gateway is the only component that can emit model spend and routing events.
- every model call must be recorded with correlation_id, step, provider, model, tokens, latency, and error class.

Incident controls
- Admin UI can disable a provider per repo
- Admin UI can force conservative routing (fast and balanced only)
