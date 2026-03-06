# 10 — Expert Library

## Purpose

The Expert Library is the registry and governance store for all experts.
It is the source of truth for:
- expert identity and versioning
- capability metadata
- tool policies and restrictions
- lifecycle state (active, deprecated, retired)

## Intent

The intent is to keep expert management auditable and scalable:
- prevent duplication and sprawl
- enable controlled updates through versioning
- enforce governance constraints centrally

## Plane Placement

Platform Plane: library persistence and governance

Agent Plane: Router reads; Recruiter writes; agents do not bypass the library

## Diagram

![Expert Library Governance](assets/expert-library-governance.svg)

## Responsibilities

- store expert definitions and versions
- enforce required metadata (class, scope, non-goals)
- store tool policy bindings and trust tier eligibility
- support deprecation and retirement without breaking routing

## Key Inputs

- Recruiter writes (new experts and versions)
- governance rules from POLICIES.md
- taxonomy rules from Expert Taxonomy

## Key Outputs

- searchable expert candidates for Router
- version history and audit logs
- eligibility flags for routing

## Versioning rules

- prefer new version over new identity when scope changes
- deprecate experts with clear migration path
- keep backward compatibility for discoverability fields where possible

## Failure Handling

- conflicting metadata: reject write, require fix
- policy violation: reject expert registration
- duplicate detection: suggest version update instead of new identity

## Admin UI Integration

This component should expose status, key metrics, and safe control hooks to the Admin UI via the Admin API (RBAC + audit log).

## Local Expert Overlays

The Expert Library must support scoped experts and overlays:
- global experts usable across repos
- repo-scoped experts for repo conventions when needed
- service-group scoped experts for critical service clusters

Scope is expressed as metadata and enforced by routing rules. This avoids forked expert identities while allowing repo-specific guidance.
