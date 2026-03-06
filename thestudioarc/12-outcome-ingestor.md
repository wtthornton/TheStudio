# 12 — Outcome Ingestor

## Purpose

Consume signals from the signal stream, normalize them by complexity, and produce aggregated indicators for the Reputation Engine.

## Intent

The intent is to keep learning consistent and auditable:
- signals are consumed from an event stream (no direct calls)
- normalization is stable and explainable
- attribution uses provenance

## Plane Placement

Platform Plane: signal consumption and aggregation

Agent Plane: Router consumes weights and analytics, not raw signals

## Responsibilities

- consume verification, QA, CI, and review signals from JetStream
- correlate signals to TaskPacket and context key
- normalize signals using Complexity Index
- attribute outcomes using provenance
- produce indicators for Reputation Engine

## Key Inputs

- signal stream events
- TaskPacket metadata (complexity, risk tier)
- provenance links from Assembler

## Key Outputs

- normalized indicators for reputation update
- anomaly detection events (excessive loopbacks, high defect pressure)

## Failure Handling

- missing correlation id: quarantine event and alert
- duplicate events: idempotent handling
- backfill and replay: reprocess from JetStream with deterministic aggregation

## Diagram

![Reputation Learning Flow](assets/reputation-learning-flow.svg)

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

## Correlation and Idempotency Rules

Signal handling rules
- every signal must include correlation_id and TaskPacket id
- signals are processed idempotently (duplicate safe)
- signals missing correlation_id are quarantined for operator review
- aggregation is deterministic for replay and backfill

Attribution inputs
- use provenance links from Assembler and the minimum record fields
- normalize by complexity and tier so hard tasks do not poison weights

## Quarantine and Dead-Letter Handling

Signals and workflow outputs are treated as data inputs and must be validated. Malformed or uncorrelated events must not poison learning.

Quarantine rules (must quarantine)
- missing correlation_id or TaskPacket id
- unknown TaskPacket
- unknown repo id
- invalid category or severity values
- duplicated event with conflicting payload (idempotency conflict)

Dead-letter rules
- events that cannot be parsed or validated after N attempts are moved to a dead-letter stream with the raw payload and failure reason.

Replay and correction
- quarantined events can be corrected by an operator (or automated fix) and replayed.
- replay must be deterministic: reprocessing produces the same aggregates given the same ordered event set.

Admin UI requirements
- show quarantined count by repo and category
- provide drill-down to failure reason and payload pointer
- provide replay action with audit log

## QA Signal Normalization

Outcome aggregation must bucket QA defects by category and severity and treat intent_gap as a separate class that affects intent quality metrics.

## Reopen Event Handling

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
