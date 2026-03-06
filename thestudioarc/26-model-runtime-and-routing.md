# 26 — Model Runtime and Routing (Multi-LLM)

## Purpose

Define how TheStudio runs agent reasoning and code generation using one or more LLM providers, while controlling cost, latency, and risk.

This document explains:
- how agents call models (worker pattern, not chatbots)
- how a Model Gateway selects models per step
- how we use best cost-per-performance through routing and fallbacks
- how Claude Code headless can be used as an optional execution engine
- how budgets and tier gates prevent runaway spend

## Intent

The intent is to produce predictable outcomes with measurable tradeoffs.

The platform must:
- route tasks to the cheapest model that can reliably succeed for the step
- use stronger models only when required by complexity, risk overlays, or repeated failure categories
- enforce spend and rate limits through policy, not discipline
- keep model choices explainable for audit and learning
- remain operational if one provider is rate limited or unavailable

## Plane Placement

Agent Plane
- agents request completions through Model Gateway
- agents never embed provider-specific logic

Platform Plane
- Model Gateway enforces routing rules, budgets, allowlists, and fallbacks
- Admin UI shows spend, latency, fallback rates, and error classes

## Architecture Diagram

![Model Runtime and Routing](assets/model-runtime-and-routing.svg)

## Core concepts

Model class
- fast: lowest cost, used for extraction, simple summarization, classification
- balanced: mid-cost, used for intent writing, planning, QA reasoning
- strong: highest capability, used for complex refactors, multi-file changes, high-risk overlays

Model Gateway
- single interface for all agents to call LLMs
- routes by workflow step, role + overlays, repo tier, complexity, and recent failure categories
- enforces budgets and stop conditions
- supports fallback and provider failover
- records audit metadata (model, tokens, cost, latency)

Repo tier effects
- observe: cheap models only, no code writing
- suggest: balanced models allowed; draft PR generation
- execute: strong models allowed only when justified by policy

## Routing rules by workflow step

Default routing (can be tightened by repo profile)

Intake and classification
- fast model
- strict token caps

Context build
- fast or balanced model for summarization, but prefer deterministic tools for code search and retrieval

Intent build
- balanced model by default
- strong model only when overlays trigger (security, compliance, billing) or repeated intent gap

Expert routing and consults
- balanced model for synthesis, but consult outputs should be tool and artifact heavy

Assembler
- balanced model for conflict resolution and plan synthesis
- strong model only when multi-domain conflicts persist

Primary Agent implementation
- balanced model for most work
- strong model for complex refactors, migrations, partner integration changes, high risk overlays
- deterministic tools (Tool Hub and repo tools) must be used to reduce model uncertainty

QA evaluation
- balanced model by default
- strong model for high risk overlays or repeated defect loops
- defect taxonomy must be enforced (see QA doc)

## Budgets and fallback

Budgets are defined in EffectiveRolePolicy and enforced in Model Gateway:
- per task max spend
- per step token caps
- max retries per model error class
- fallback order by provider and model class

Fallback examples
- strong model rate limited: fall back to alternative strong model on a different provider
- balanced model unavailable: fall back to fast model and tighten scope, then escalate if needed
- repeated same-category failures: escalate model class or require human review

## Claude Code headless (optional)

Claude Code can be used as an optional coding engine inside the per-repo execution plane.

Use cases
- complex multi-file edits
- refactor tasks with strong repo context
- batch remediation work under strict allowed tools

Guardrails
- Claude Code does not replace Model Gateway. It is an optional provider behind it.
- any Claude Code invocation must be recorded with correlation_id and evidence links
- tool permissions must be constrained with allowed-tools rules

Operational posture
- Claude Code subscription usage and API usage are separate cost models.
- For deterministic production automation, prefer API billing with explicit budgets.
- Subscription usage is best suited for human-driven sessions and experiments.

## Deterministic tooling first

TheStudio reduces model load by relying on deterministic MCP tooling for:
- code quality and security scanning
- dependency analysis
- documentation generation and validation
- browser automation checks

See `25-tool-hub-mcp-toolkit.md`.

## Admin UI requirements

Admin UI must show:
- model spend by repo and tier
- model latency distribution by step
- fallback rate by provider and model class
- model errors by error class (rate limited, transient, auth failed, policy denied, permanent)
- top tasks by cost and the reason (overlay, complexity, repeated failures)

## What we store for audit

Minimum model audit record per call
- correlation_id and TaskPacket id
- workflow step and role + overlays
- provider and model name
- tokens in and out
- latency
- error class (if any)
- fallback chain (if used)

This is required for reliable cost control and for diagnosing quality drift.

## Enforcement Boundary

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
