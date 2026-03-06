# 25 — Tool Hub (MCP) and Docker MCP Toolkit Integration

## Purpose

Define how agents use a standardized Tool Hub for deterministic tooling through MCP servers, and how Docker MCP Toolkit can be used to host and manage common MCP tools.

This document covers:
- where MCP tooling fits in the agent platform
- standard tool suites the platform should provide
- how to add custom MCP tools safely, including later phase internal tooling like TappsMCP

## Intent

The Tool Hub exists to make agent output more deterministic and less dependent on model guesses.

The platform must:
- keep tool access least privilege and role-based
- keep GitHub write actions restricted to Publisher
- allow shared tools that work across repos (global tools)
- allow repo-specific tools to remain isolated per repo execution plane
- support a governed path to add custom tools that become company special sauce

## Plane Placement

Agent Plane
- agents consume tools (Context, Primary, QA, Assembler)

Platform Plane
- EffectiveRolePolicy determines allowed tool suites
- Tool servers and MCP tooling enforce allow and deny rules
- audit logging is required for tool calls
- Publisher remains the only GitHub writer

## Architecture Diagram

![Tool Hub and MCP Architecture](assets/tool-hub-mcp-architecture.svg)

## Core concepts

Tool suite
- a named group of tools that represent a capability (fetch web pages, browser automation, code quality scoring)
- tool suites are referenced by RoleSpec and OverlaySpec to allow or deny classes of tools

Profile
- a configuration set that selects which MCP servers are enabled and which tools are available
- profiles can be scoped by repo tier (observe, suggest, execute) and by repo group (python, node, infra)

Approved catalog
- the list of MCP servers and tool suites the platform will allow
- prevents tool sprawl and accidental introduction of risky tools

## How agents use the Tool Hub

Agents do not connect to arbitrary MCP servers.
Agents call MCP tools only through the Tool Hub, under EffectiveRolePolicy enforcement.

At runtime:
- the agent includes correlation_id on every tool call
- the system checks the role and overlays and verifies the tool suite is allowed
- tool output is persisted as evidence where appropriate
- any denied tool call is treated as a policy violation and escalates

## Standard tool suites (platform baseline)

These are recommended as standard, cross-repo tool suites.

Read and retrieval
- Fetch (reference retrieval, deterministic content fetch)
- Context retrieval (knowledge base and curated reference packs)

Browser automation
- Playwright (web UI validation, screenshot capture, scripted journeys)

Code quality and security (deterministic, no LLM calls)
- quality scoring and lint orchestration
- secret scanning
- dependency CVE scanning
- static analysis

Repository analysis (read-only, cross-repo)
- structure extraction
- dependency graph analysis
- circular dependency detection
- dead code detection

Documentation tooling (deterministic generation and validation)
- README and onboarding generation from templates
- changelog and release notes generation from git history
- doc drift and link integrity validation

Observability read-only tooling (later)
- traces and logs query (read-only)
- health and SLO views (read-only)

Notes
- repo write and GitHub write actions are not part of the Tool Hub baseline
- repo write remains in per repo execution plane tool servers
- GitHub write remains only in Publisher

## Docker MCP Toolkit fit

Docker MCP Toolkit can be used to host and manage MCP servers as containers and expose them through an MCP Gateway.

How it fits
- Docker MCP Toolkit hosts standard MCP servers as containers
- MCP Gateway becomes the single endpoint agents call for those tools
- Profiles and an approved catalog restrict which tools are enabled

Governance posture
- use profiles to separate observe, suggest, execute access
- use an approved catalog to prevent introducing unreviewed tools
- treat OAuth and remote tool connections as optional and policy gated

Important
- Docker MCP Toolkit is a hosting and management layer, not a governance authority
- our platform policy remains the source of truth for allowed tool suites

## Creating our own MCP tools

Custom MCP tools must follow platform rules:

1. Determinism first
- tools should produce reproducible outputs
- avoid hidden network calls without explicit inputs

2. Narrow scope
- each tool should do one thing well
- group tools into suites that match platform capabilities

3. Safe defaults
- read-only by default
- explicit allowlist for any write behavior
- require correlation_id and a task reference

4. Evidence and audit
- every tool call is auditable
- outputs that influence decisions are persisted as evidence

5. Versioned rollout
- new tools start in observe mode
- then suggest mode
- execute mode only after proven safe and useful

## Later phase internal tooling: TappsMCP

TappsMCP is a strong candidate to become a core part of the tooling special sauce because it is deterministic and focused on quality gates and documentation tooling.

Intended integration
- Add TappsMCP as a custom MCP server suite in the approved catalog
- Enable it in profiles for suggest and execute tiers
- Keep it read-only for analysis tools, and gate any write actions behind role and overlay policy

Suggested tool suite mapping
- Quality Gates suite: scoring, security scans, dependency analysis
- Documentation suite: doc generation, ADRs, release notes, drift validation
- Memory suite: persistent retrieval and memory operations, with governance rules

Operational benefit
- improves single-pass success by shifting quality checks earlier
- reduces QA defects by making validation deterministic
- creates measurable evidence artifacts that improve attribution

## What this changes in the architecture

- Tool access becomes standardized and composable through tool suites and profiles
- Agents rely less on guesswork and more on deterministic analysis
- Company tooling can be introduced safely as a cataloged, versioned capability

## Admin UI integration

The Admin UI should show:
- enabled tool profiles per repo
- tool usage by role and overlay
- tool error distribution by repo
- which tools contributed evidence to a PR

The Admin UI should allow:
- enabling or disabling tool profiles per repo
- promoting a tool from observe to suggest to execute eligibility (governed)

## Licensing and Deployment Posture

Docker MCP Toolkit posture

Default production posture (free and OSS friendly)
- Use an OSS MCP Gateway deployment for production Tool Hub hosting.
- Docker Desktop MCP Toolkit is allowed as a developer convenience only unless licensing terms are explicitly accepted.

Governance
- Only approved catalogs are enabled in production.
- Tools are promoted observe -> suggest -> execute using the same governance used for repo tiers.
- OAuth-based remote MCP connections are optional and must be explicitly allowed by policy.
