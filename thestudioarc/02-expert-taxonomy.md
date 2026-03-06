# 02 — Expert Taxonomy

## Purpose

Define the expert classification and boundaries that allow the Expert Bench to scale without devolving into an unmanageable set of overlapping experts.

Taxonomy provides:
- predictable discovery and routing
- governance boundaries for tool access and trust tiers
- clear creation rules that reduce expert sprawl

## Intent

The intent is to keep expert design maintainable and measurable:
- experts remain narrow and testable
- routing remains deterministic
- reputation scores reflect real domain performance rather than ambiguous scope

## Plane Placement

Agent Plane: Router uses taxonomy to select and constrain experts

Platform Plane: Taxonomy is enforced through library metadata and governance policies

## Diagram

![Expert Taxonomy](assets/expert-taxonomy-map.svg)

## Core Classes

Technical
- architecture, security, infra, data engineering, performance

Business
- domain rules, pricing, packaging, customer workflows

Partner APIs
- vendor integration behavior, auth models, rate limits, versioning

Service Specialists
- critical internal services with unique invariants and frequent changes

QA / Validation
- intent validation, regression analysis, test strategy

Process / Quality
- release readiness, operational hygiene, postmortems

Compliance
- ISO 27001, SOC2, GDPR, PCI, retention, residency

## Creation Rules

Create a new expert when:
- a domain is repeatedly consulted
- defects show consistent missing coverage
- governance requires specialized review
- a partner integration is common and failure-prone

Do not create a new expert when:
- a Service Context Pack is sufficient
- the capability is one-off and not maintainable
- a broader expert can be safely scoped down

## Scope Boundaries

- one expert, one primary domain responsibility
- experts must declare non-goals
- tool access is minimal and scoped
- compliance experts default to curated or human-backed patterns

## Anti-Patterns

- “god experts” that attempt to cover multiple unrelated domains
- experts with repo write privileges
- experts that require large context dumps to function
- creating a new expert identity for every task instead of versioning existing ones

## Skill Packaging Notes

Experts and agents should use progressive disclosure: load minimal discovery metadata first, then load full operating instructions and references only when activated.
