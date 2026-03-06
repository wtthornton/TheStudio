# 03 — Context Manager

## Purpose

The Context Manager Agent turns an incoming GitHub issue into a structured TaskPacket that downstream agents can rely on.
It is the system’s scoping engine.

The Context Manager:
- identifies impacted services and surfaces
- attaches Service Context Packs
- computes Complexity Index for normalization and governance
- sets risk flags that drive mandatory expert coverage

## Intent

The intent is to prevent “garbage in, garbage out.”
Without structured context, intent becomes ambiguous, routing becomes noisy, and learning signals become untrustworthy.

The Context Manager uses progressive disclosure:
- attach only the minimal context needed to proceed
- use pointers and summaries rather than large code dumps

## Plane Placement

Agent Plane: Context Manager Agent

Platform Plane: TaskPacket persistence and correlation identifiers for tracing

## Diagram

![Context Manager Flow](assets/context-manager-flow.svg)

## Responsibilities

- interpret issue and restate goal in one sentence (goal statement, not solution)
- detect impacted services and surfaces (API, DB, infra, UI, partner APIs)
- attach Service Context Packs for impacted services
- locate key entry points and configuration touchpoints
- compute Complexity Index and record rationale
- emit risk flags for Router (auth, billing, exports, compliance, migrations)

## Key Inputs

- GitHub issue metadata and links
- repository pointers (branch/commit)
- Service Context Packs
- standards and guardrails (coding, structure, architecture)

## Key Outputs

- TaskPacket enriched with scope, surfaces, evidence pointers
- Complexity Index with reasons
- risk flags for mandatory expert coverage
- open questions for Intent Builder

## Failure Handling

- missing Service Context Pack: record pack gap and trigger pack creation request
- ambiguous impacted services: record uncertainty and request intent clarification
- hidden dependencies discovered later: update TaskPacket and emit correction signal

## Signals and Learning Hooks

- context_built with complexity and risk flags
- context_gap_detected (missing service pack)
- scope_changed (impacted service list changes)

## References

- Agent Skills spec: https://agentskills.io/specification

## Admin UI Integration

This component should expose status, key metrics, and safe control hooks to the Admin UI via the Admin API (RBAC + audit log).

## Repo Profile Dependencies

The Context Manager must consume the Repo Profile to locate:
- service context packs and doc roots
- repo layout conventions for service detection
- risk path mappings that influence downstream routing triggers
