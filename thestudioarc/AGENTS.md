# AGENTS.md

## Purpose

Define the agent roles, their primary responsibilities, and where they live in the Agent Plane vs Platform Plane architecture.

## Intent

This file is designed for agent runtimes that discover and load role definitions automatically. It provides a stable map of:
- which agents exist
- what they are responsible for
- what they must not do
- what artifacts they must produce

## Agent Plane Roles

- Intake Agent
- Context Manager Agent
- Intent Builder Agent
- Expert Router Agent
- Expert Recruiter Agent
- Assembler Agent
- Primary Agent (Developer, Architect, Planner)
- QA Agent
- Expert Agents (multiple classes)

## Platform Plane Services

- Work Queue
- Temporal workflows
- Postgres and pgvector
- Tool Servers (FastAPI)
- Verification Gate
- Publisher
- Signal Stream (JetStream)
- Outcome Ingestor
- Reputation Engine

## Required Operating Rules

- Agents communicate through artifacts and signals, not free-form chat.
- Gates fail closed. Agents cannot waive verification or QA.
- Every action must be traceable to a TaskPacket and Intent Specification.

## Standards

Agents must follow:
- `20-coding-standards.md`
- `21-project-structure.md`
- `22-architecture-guardrails.md`

## Roles and overlays

Roles are defined as base role specs plus overlay specs.

The platform computes an EffectiveRolePolicy per task:
- RoleSpec (base)
- OverlaySpecs (0 or more)
- Repo Profile overrides (allowed subset only)

EffectiveRolePolicy controls:
- allowed tools
- mandatory expert coverage
- verification and QA posture
- publishing posture

See `08-agent-roles.md`.
