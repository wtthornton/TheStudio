# 09 — Service Context Packs

## Purpose

Service Context Packs provide curated service knowledge so agents can reason about services without creating one expert per service.
They reduce expert sprawl and make context construction deterministic.

## Intent

The intent is to:
- scale across many services
- provide stable invariants and known pitfalls
- improve routing and planning quality
- reduce repeated discovery work

## Plane Placement

Platform Plane: packs are curated, versioned, and stored

Agent Plane: Context Manager attaches packs; agents and experts consume them

## Diagram

![Service Context Pack Lifecycle](assets/service-context-pack-lifecycle.svg)

## What a pack contains

- service purpose and boundaries
- invariants and non-negotiables
- key APIs and contracts
- dependencies and consumers
- deployment notes and rollback guidance
- known failure modes and runbooks
- links to prior incidents and PR patterns

## When to create a service specialist expert instead

Create a Service Expert when:
- service is high risk (identity, billing, exports)
- service has unique invariants not captured in a pack
- service changes frequently and causes regressions

## Maintenance model

- packs are owned by service owners or platform team
- updates are versioned and reviewed like code
- packs are updated when incidents reveal missing context

## Signals and Learning Hooks

- pack_missing_detected
- pack_updated
- pack_used_by_task
