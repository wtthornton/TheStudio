# 11 — Intent Layer

## Purpose

The Intent Builder Agent defines what correctness means before implementation begins.
It produces a structured Intent Specification that guides experts, planning, verification, QA validation, and reputation scoring.

## Intent

The intent is to eliminate ambiguity early.
Intent defines:
- goal (outcome)
- constraints (technical, operational, compliance)
- invariants (what must not change)
- acceptance criteria (testable definition of done)
- non-goals (scope boundaries)
- assumptions and open questions

## Plane Placement

Agent Plane: Intent Builder Agent

Platform Plane: intent is persisted, versioned, and referenced by QA and learning

## Responsibilities

- write the goal statement and scope boundaries
- identify constraints and invariants
- define acceptance criteria
- consult intent experts via Router when needed
- version intent when changes are required

## Key Inputs

- TaskPacket context and risk flags
- standards and guardrails
- expert consult outputs (intent subset)

## Key Outputs

- Intent Specification attached to TaskPacket
- routing triggers and escalation flags
- assumptions and unresolved questions

## Refinement Loop

Intent can be refined when:
- QA finds intent ambiguity or missing acceptance criteria
- Assembler detects conflicts that cannot be resolved without better constraints

Refinement must be versioned and traceable.

## Failure Handling

- incomplete requirements: request missing inputs via GitHub comment (Publisher path)
- conflicting constraints: escalate to human review per policy

## Admin UI Integration

This component should expose status, key metrics, and safe control hooks to the Admin UI via the Admin API (RBAC + audit log).
