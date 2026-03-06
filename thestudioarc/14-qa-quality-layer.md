# 14 — QA Quality Layer

## Purpose

Validate outcomes against intent. QA is intent-first validation, not just test execution.
QA can consult QA experts via the Router when domain depth is required.

## Intent

The intent is to catch:
- intent mismatches
- regressions and invariant breaks
- missing edge cases
- compliance and business rule gaps

QA produces structured defect signals that feed learning and improve routing decisions.

## Plane Placement

Agent Plane: QA Agent performs judgment and validation

Platform Plane: signal emission and persistence; escalation enforcement

## Responsibilities

- validate acceptance criteria and invariants from intent
- review evidence bundle and targeted test results
- consult QA expert subset via Router when needed
- classify defects by severity and category
- emit QA signals to the signal stream
- trigger loopback to Primary Agent on failure

## Key Inputs

- Intent Specification and acceptance criteria
- evidence bundle from verification and agent execution
- plan mapping and provenance from Assembler
- QA expert consult outputs (subset)

## Key Outputs

- qa_passed, qa_defect, qa_rework signals
- defect list mapped to acceptance criteria
- intent refinement request when intent is ambiguous

## Failure Handling

- acceptance criteria missing: request intent refinement and block pass
- defects in high-risk domains: escalate per policy
- partner API mismatch: require updated validation and possible intent update

## Admin UI Integration

This component should expose status, key metrics, and safe control hooks to the Admin UI via the Admin API (RBAC + audit log).

## Defect Taxonomy and Severity

QA must emit consistent defect categories and severity. This is required for learning, fair attribution, and operational prioritization.

Defect categories
- intent_gap: acceptance criteria missing, conflicting, or untestable; requirements unclear
- implementation_bug: incorrect behavior relative to intent
- regression: previously working behavior broke
- security: auth, authorization, secrets, crypto, injection risk
- performance: latency, resource usage, throughput, scaling
- compliance: retention, export, residency, audit gaps
- partner_mismatch: integration mismatch, contract, rate limit, auth model
- operability: logging, metrics, alerts, rollback, runbook gaps

Severity rubric
- S0 critical: security breach risk, data loss, billing impact, compliance breach
- S1 high: major user impact or repeated failures likely
- S2 medium: limited impact, workaround exists
- S3 low: minor issue, cosmetic, or non-blocking improvement

Signal requirements
- qa_defect must include category, severity, and mapping to acceptance criteria or invariant.
- intent_gap must trigger intent refinement and block qa_passed.

Admin UI requirements
- show defect distribution by repo, category, and severity
- show intent_gap rate separately (this is a requirements quality metric)

## Reopen Handling

Reopen events are high-signal quality outcomes.

Sources
- issue reopened after merge
- new issue referencing the PR for a regression
- rollback PR linked to the original task

Handling
- treat reopen as a signal event linked to the original TaskPacket where possible
- classify reopen as intent_gap, implementation_bug, regression, or governance failure
- update metrics: reopen rate per repo, per role + overlays, per expert set

Attribution guidance
- intent_gap reopen impacts intent quality metrics
- regression reopen impacts execution and expert guidance depending on provenance
