# 01 — Expert Bench Architecture

## Purpose

Define the Expert Bench as the system for obtaining domain reasoning through modular experts, and converting that reasoning into an executable plan through the Assembler.

The Expert Bench exists to prevent “single model does everything” behavior. It allows:
- deep domain coverage
- bounded responsibilities
- auditable decision provenance
- measurable expert effectiveness via outcomes

## Intent

The intent of the Expert Bench is to provide high-signal advice while keeping:
- selection deterministic (through the Router)
- creation controlled (through the Recruiter)
- outputs mergeable (through structured expert output patterns)
- learning evidence-based (through provenance and outcome signals)

Experts are not allowed to “run the show.” They advise. The Primary Agent executes under hard gates.

## Plane Placement

Agent Plane: Router Agent, Recruiter Agent, Expert Agents, Assembler Agent

Platform Plane: Expert Library (registry and governance), persistence for outputs and provenance

## Skills

![Expert Creation Flow](assets/expert-recruiter-creation-flow.svg)

### Expert Skill Profile Template

Experts are specialized reasoning agents designed to be selected reliably and merged by the Assembler.

Core skills:
- domain reasoning (within explicit scope)
- intent alignment (recommendations tie back to goal, constraints, invariants)
- validation mindset (propose checks and tests)
- tool discipline (scoped tools only; no repo writes)
- structured outputs (recommendations, options, risks, validations, assumptions)
- edge case awareness (failure modes and mitigations)

Operating constraints:
- scope must be narrow and testable
- prefer checklists over narrative guidance
- avoid large refactor proposals unless intent explicitly requires them

Evaluation checks:
- recommendations reduce verification friction and QA defects for targeted contexts
- outputs are structured and mergeable
- experts avoid tool overreach

## Key Inputs

- TaskPacket and Intent Specification
- router policy triggers (risk flags and mandatory coverage rules)
- reputation weights and confidence
- standards and guardrails (coding, structure, architecture)

## Key Outputs

- expert outputs stored as structured artifacts
- assembled plan and provenance
- QA handoff mapping acceptance criteria to validations
- consult rationale (which experts were chosen and why)

## Internal Flow

![Expert Router Selection](assets/expert-router-selection-flow.svg)

High-level flow:
1. Router determines required expert classes and selects subset.
2. Recruiter ensures supply and creates experts when gaps exist.
3. Experts produce structured outputs.
4. Assembler merges outputs, resolves conflicts, records provenance.
5. Plan is handed to the Primary Agent and QA.

## Expert Subset Patterns

Parallel consults
- use when experts are independent (security + product + data)

Staged consults
- use when one expert’s output conditions another (partner API constraints then security review)

Mandatory coverage
- if risk flags trigger a class, that class must be included even if reputation is low

Budget enforcement
- keep subsets small and purposeful
- define stop conditions for re-consults

## Conflict Handling

Conflicts are expected. The Bench handles them explicitly:
- Assembler resolves conflicts using intent as tie-breaker
- if intent is insufficient, Assembler triggers intent refinement
- unresolved conflicts are escalated via POLICIES rules

## Failure Handling

- no expert found: Recruiter creates a new expert from template, starts in shadow/probation
- outputs unstructured or low quality: mark expert as ineligible and request revised version
- expert tool overreach: fail closed, deny tool access, require template update
- conflicts across high-risk domains: escalate to human review

## Signals and Learning Hooks

- expert_consulted (who, class, context key)
- expert_conflict_detected
- expert_created / expert_version_created
- consult_budget_exceeded

These signals feed Outcome Ingestor and Reputation Engine.
