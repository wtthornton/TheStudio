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

## Personas (human-facing quality layer)

Three personas govern the human-facing inputs that the Agent Plane consumes. They sit upstream of the agent roles.

| Persona | Role | Feeds into |
|---------|------|------------|
| **Saga** | Epic creator — turns strategy into clear, testable epics | Intent Builder (epic → Intent Specification) |
| **Helm** | Planner & dev manager — turns backlog into order of work and testable sprint goals | Planner role, Context Manager (plan → scope, dependencies, risk flags) |
| **Meridian** | VP Success — reviewer & challenger of Saga and Helm | Quality gate before any epic or plan is committed; bar aligns with Verification, QA, and Outcome Ingestor |

**Chain:** Strategy/OKRs → Saga (epic) → Meridian (epic review) → Helm (plan) → Meridian (plan review) → Agent Plane execution.

**Handoff contract:** Approved epic + approved plan = sufficient input for the Agent Plane. Persona outputs are the source of truth for intent, scope, acceptance criteria, and non-goals that Intake, Context Manager, and Intent Builder consume.

Full persona docs: `personas/saga-epic-creator.md`, `personas/helm-planner-dev-manager.md`, `personas/meridian-vp-success.md`.
Review checklist: `personas/meridian-review-checklist.md`.
Tooling guide: `personas/tooling-guide.md`.

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
