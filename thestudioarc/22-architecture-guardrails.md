# 22 — Architecture Guardrails (Agent-Coded Systems)

## Purpose

Define architecture-level guardrails that apply across services and agents. Guardrails prevent unsafe or inconsistent system evolution.

## Intent

The intent is to ensure that agent-produced changes:
- preserve system boundaries
- remain observable and debuggable
- avoid hidden coupling and data leakage
- satisfy security and compliance constraints by default

---

## System Guardrails

Boundaries
- services communicate via APIs or events
- no cross-service direct database access
- no shared mutable state across services

Data
- data classification: identify sensitive data flows in intent and context
- data exports require explicit intent and compliance coverage

Operations
- migrations must be reversible or have a documented rollback
- rollouts must be staged when risk is medium or high
- feature flags for high-risk behavior changes

Security
- secret scanning required
- dependency audit required when dependencies change
- auth and authorization changes require security expert coverage

Agent change hygiene
- no large refactors unless explicitly requested in intent
- changes must be evidence-backed (tests, checks, logs)
- provenance must link key decisions to experts and sources

---

## Escalation Triggers (non-negotiable)

- auth or authorization changes
- billing, pricing, payments logic
- data exports or retention policy changes
- migrations or destructive operations
- compliance obligations (GDPR, ISO 27001, SOC2, PCI)

## Enforcement Points

Guardrails are enforced at:
- Intent Builder (constraints and invariants)
- Expert Router (mandatory coverage and escalation triggers)
- Verification Gate (deterministic checks)
- QA Agent (intent validation and defect classification)
- Publisher (write restrictions and evidence requirements)
