# 05 — Expert Router

## Purpose

The Expert Router Agent is the single entry point for expert consultation.
It selects and orchestrates expert subsets for:
- intent construction
- planning and architecture decisions
- QA validation
- business and compliance coverage

## Intent

The intent is to keep expert consultation:
- minimal and high signal (small subsets)
- policy compliant (mandatory coverage rules)
- evidence-based (uses reputation weights and confidence)
- auditable (records routing rationale)

## Plane Placement

Agent Plane: Expert Router Agent

Platform Plane: reads Expert Library and Reputation; writes routing decisions for audit

## Diagram

![Router Selection Flow](assets/expert-router-selection-flow.svg)

## Responsibilities

- determine required expert classes from intent and risk flags
- select candidates by capability match plus reputation weight and confidence
- enforce mandatory coverage triggers (security, compliance, identity, billing, exports)
- decide consult pattern (parallel vs staged)
- enforce budget limits (time and cost) and stop conditions
- provide rationale and conflicts to the Assembler

## Key Inputs

- TaskPacket and Intent Specification
- Complexity Index and risk flags
- Expert Library metadata and taxonomy rules
- Reputation weights and confidence
- policy rules from POLICIES.md

## Key Outputs

- selected expert subset with rationale
- consultation plan (parallel or staged)
- stop conditions and escalation triggers
- conflicts flagged for Assembler

## Consultation Patterns

Parallel consult
- independent domains; faster turnaround

Staged consult
- dependencies; reduces wasted work

Shadow consult
- new experts run in shadow mode; Assembler may ignore unless approved

## Failure Handling

- no eligible experts: invoke Recruiter to create from template
- too many candidates: enforce cap and prioritize by risk and weight
- low confidence on high risk: prefer curated or human-backed experts; escalate if needed
- conflicting governance rules: stop and escalate

## Signals and Learning Hooks

- routing_decision_made (subset size, classes, rationale)
- mandatory_coverage_triggered
- budget_exceeded
- expert_gap_triggered (recruiter invoked)

## References

- Agent Skills spec: https://agentskills.io/specification

## Admin UI Integration

This component should expose status, key metrics, and safe control hooks to the Admin UI via the Admin API (RBAC + audit log).

## Repo Awareness

Router decisions are mostly global, but they must be repo-aware through:
- Repo Profile risk path triggers and required reviewer mappings
- local expert overlays for repo conventions or critical services
- repo-specific constraints that affect tool access and escalation
