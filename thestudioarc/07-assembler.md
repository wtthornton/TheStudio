# 07 — Assembler

## Purpose

The Assembler Agent merges expert outputs into a single executable plan aligned to intent.
It records provenance so outcomes can be attributed and learning is trustworthy.

## Intent

The intent is to convert distributed reasoning into:
- one coherent plan
- clear risk and validation steps
- explicit conflict handling
- provenance links from decisions to experts and sources

## Plane Placement

Agent Plane: Assembler Agent

Platform Plane: plan and provenance persistence

## Diagram

![Assembler Flow](assets/assembler-synthesis-flow.svg)

## Responsibilities

- normalize and merge expert outputs
- resolve conflicts using intent as tie-breaker
- create an implementation plan with checkpoints
- map plan validation steps to acceptance criteria
- generate QA handoff notes
- trigger intent refinement when needed

## Key Inputs

- Intent Specification
- expert outputs (structured)
- standards and guardrails
- context pointers from TaskPacket

## Key Outputs

- plan (steps + checkpoints)
- risk list and mitigations
- provenance map
- QA handoff mapping acceptance criteria to validations
- intent refinement request when ambiguity blocks decisions

## Conflict Handling Rules

- resolve based on intent constraints and invariants
- if unresolved due to missing intent, trigger intent refinement with explicit questions
- if conflict touches high-risk domains, escalate per policy

## Failure Handling

- expert outputs missing structure: request rerun or mark expert as ineligible
- plan requires cross-org decision: escalate to human-backed expert
- too many options: converge to one plan or present a single recommendation with rationale

## Signals and Learning Hooks

- plan_created
- conflict_detected
- intent_refinement_requested
- qa_handoff_created

## Admin UI Integration

This component should expose status, key metrics, and safe control hooks to the Admin UI via the Admin API (RBAC + audit log).

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
