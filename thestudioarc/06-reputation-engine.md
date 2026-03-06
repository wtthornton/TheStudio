# 06 — Reputation Engine

## Purpose

The Reputation Engine is the system of record for expert trust.
It computes weights and confidence that the Router uses for expert selection.

## Intent

The intent is evidence-based learning:
- experts gain influence through outcomes, not confidence
- weights are normalized by task complexity
- attribution uses provenance to avoid scapegoating

## Plane Placement

Platform Plane: reputation computation and persistence

Agent Plane: Router consumes weights; agents do not directly modify weights

## Diagram

![Reputation Learning Flow](assets/reputation-learning-flow.svg)

## Responsibilities

- store weights by expert and context key
- compute confidence (sample size awareness)
- handle decay and drift (avoid stale overconfidence)
- manage trust tier transitions (shadow, probation, trusted)
- publish weights to Router queries

## Inputs

- normalized indicators from Outcome Ingestor
- provenance links from Assembler outputs
- complexity index from TaskPacket

## Outputs

- weights and confidence per expert per context key
- drift signals (improving, stable, declining)
- trust tier eligibility changes

## Attribution Principles

- defects tied to missing acceptance criteria are intent issues, not expert issues
- defects tied to ignored expert guidance are execution or governance issues
- defects tied to expert recommendation choices can affect expert weight

## Failure Handling

- sparse data: keep weights conservative and confidence low
- noisy signals: apply smoothing and decay
- conflicting attribution: mark uncertain, require more evidence

## Signals and Learning Hooks

- weight_updated
- confidence_updated
- trust_tier_changed
- drift_detected

## References

- OpenTelemetry signals for tracing and metrics: https://opentelemetry.io/

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

## Confidence and Drift Discipline

Reputation must remain conservative when provenance or sample size is weak.

Rules
- low sample size keeps confidence low even if outcomes look good
- missing provenance reduces weight impact (avoid scapegoating)
- drift detection uses rolling windows and decay to prevent stale overconfidence

## QA Attribution Rules

Attribution rules for QA outcomes
- intent_gap defects impact intent quality metrics and may affect Intent Builder performance, not experts.
- implementation_bug and regression defects may impact Primary Agent execution and consulted expert guidance, based on provenance.
- compliance and security defects require mandatory coverage review; missing coverage is a routing and policy failure.
