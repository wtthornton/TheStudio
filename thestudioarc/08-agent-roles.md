# 08 — Agent Roles

## Purpose

Define how the system assigns execution posture to the Primary Agent and how that posture is enforced across routing, tools, verification, QA, and publishing.

Roles are not a fixed list of agent binaries. A role is a policy configuration that changes behavior, required artifacts, tool access, and required coverage. This lets the platform scale to new kinds of work without changing code each time a new role is needed.

## Intent

The intent is to support a small set of base roles plus composable overlays so the system can handle many categories of work without role explosion.

This model must:
- keep roles understandable by humans
- keep behavior deterministic and auditable
- ensure tool access is least privilege
- ensure high risk changes trigger the correct expert coverage and gates
- allow repo-level overrides without forking role identities

## Plane Placement

Agent Plane: Primary Agent operates under an EffectiveRolePolicy.

Platform Plane: enforcement happens in Router policy, tool servers, Verification Gate, QA Agent, and Publisher rules.

## Role model summary

The platform uses:
- Base roles: small set, default execution posture
- Overlays: modifiers that add constraints, required coverage, and stricter gates
- EffectiveRolePolicy: computed policy applied at runtime

This is a base + overlays model:
- Developer + Partner API + Compliance is valid.
- We do not create a separate role identity for every combination.

## Diagram

![Role and Overlay Enforcement](assets/role-overlay-enforcement-flow.svg)

## RoleSpec

A RoleSpec defines the default operating posture for a Primary Agent.

A RoleSpec includes:

Identity
- name and purpose
- intended use cases

Activation
- default triggers (issue type, labels, issue form fields)
- required inputs before execution can start

Outputs
- required artifacts the role must produce (plan adherence, evidence, summaries)
- required PR content expectations (what Publisher must post)

Tool policy
- allowed tool suites
- denied tool suites
- write constraints (working branch only, no protected branches)
- budgets (limits on tool calls, time, retries)

Expert coverage expectations
- default required expert classes
- consult posture (minimal subset, staged when needed)

Quality posture
- verification expectations
- QA expectations
- loopback posture and stop conditions

Escalation triggers
- conditions that require human review
- conditions that require extra mandatory expert coverage

Repo overrides
- what can be overridden by Repo Profile and what cannot

## OverlaySpec

An OverlaySpec is a modifier applied to a base role without creating a new role identity.

An overlay includes:

Identity and intent
- name and why it exists

Triggers
- labels and issue form fields
- file path triggers from Repo Profile
- detection triggers from Context Manager (migrations, infra changes, partner integration touches)

Compatibility
- which base roles can accept this overlay
- conflicts with other overlays (rare and explicit)

Policy deltas
- tool policy delta (tighten or expand suites)
- expert coverage delta (mandatory classes and consult pattern)
- quality delta (extra verification checks, stricter QA posture)
- publishing delta (draft only, block ready-for-review until approval)
- budgets delta (reduce consult and loop caps, tighter time budgets)

Escalation triggers
- overlay-specific human review triggers

## EffectiveRolePolicy

EffectiveRolePolicy is the runtime policy applied to the workflow.

It is computed from:
- RoleSpec (base role)
- OverlaySpecs (0 or more)
- Repo Profile overrides (allowed subset only)
- task risk flags and complexity

EffectiveRolePolicy drives enforcement at:
- Router: mandatory coverage and consult budgets
- Tools: allowlists and denied actions
- Verification: required checks, evidence expectations, failure classification
- QA: intent validation strictness and defect expectations
- Publisher: draft vs ready-for-review, evidence comment requirements, label and project updates

## Role selection lifecycle

Role and overlay selection is staged and auditable.

1. Intake Agent
- selects base role from issue type and templates
- applies overlays from labels and issue form fields

2. Context Manager
- adds overlays from repo inspection (migrations detected, infra touched, partner integration present)
- may recommend base role change if classification is clearly wrong

3. Intent Builder
- requires overlays when constraints demand them (compliance, billing, security)

4. Expert Router
- enforces mandatory coverage implied by overlays
- cannot remove overlays

5. Admin UI
- can override base role and overlays per task or per repo
- every override is audited

Role changes after execution starts are allowed only when:
- Context Manager detected misclassification early
- Assembler plan indicates a different posture is required
- governance rules demand it

Any role change must be recorded as provenance and reflected back to GitHub in the evidence comment.

## Base role catalog

### Developer

Purpose
- implement code changes and tests aligned to intent

Common triggers
- type:bug, type:feature, type:chore
- default role for most work

Default outputs
- small, focused diffs
- tests mapped to acceptance criteria
- PR summary tied to intent and evidence

Default tool suites
- repo write (working branch)
- test runner
- CI read and trigger (as allowed by repo profile)

Default expert coverage
- none mandatory by default
- Router may consult technical or service context experts based on risk flags

Default quality posture
- standard verification checks for repo
- QA validates acceptance criteria

Budgets
- consult cap and loop caps set by repo profile
- stop and escalate on repeated failures in the same category

Escalation triggers
- any security, billing, export, migration, or compliance overlay present

### Architect

Purpose
- design or refactor system structure, interfaces, and boundaries

Common triggers
- type:refactor
- cross-service changes
- architecture change labels or templates

Default outputs
- architecture notes embedded in PR evidence comment
- migration or rollout notes when applicable
- tests and validation steps for boundary changes

Default tool suites
- repo write (working branch)
- doc updates allowed
- restricted dependency changes unless explicitly approved

Default expert coverage
- technical architecture expert likely
- security expert when auth boundaries touched

Default quality posture
- stricter on interface compatibility and backward compatibility
- QA focuses on invariants and regressions

Budgets
- higher consult budget than Developer for complex boundary work

Escalation triggers
- cross-service database or boundary violations
- infra changes without rollback plan

### Planner

Purpose
- break work into epics, stories, sequencing, and acceptance criteria improvements
- no code writing by default

Common triggers
- discovery and roadmap work
- large ambiguous feature requests
- missing acceptance criteria

Default outputs
- structured breakdown with dependencies and risks
- recommended overlays and required expert coverage for execution
- intent improvements where needed

Default tool suites
- read-only repo and docs tools
- no repo write tools

Default expert coverage
- business expert for domain workflow alignment when needed
- process/quality expert for SDLC guidance

Default quality posture
- focuses on completeness and testable criteria, not compilation

Budgets
- small consult budgets, staged consults preferred

Escalation triggers
- requirements conflict or missing stakeholder decisions

## Overlay catalog

Overlays are grouped so humans can reason about them and so merging rules are deterministic.

Overlay merge order:
1. Governance overlays
2. Change-type overlays
3. Operational overlays

If overlays conflict, the more restrictive behavior wins.

### Security overlay

When to apply
- risk:auth, auth path triggers, permission boundary changes, crypto, secrets

Policy delta
- mandatory security expert coverage
- stricter verification checks if repo supports them
- publishing defaults to draft until checks pass and required reviewers present

Escalation
- human review required for high risk auth changes

### Compliance overlay

When to apply
- risk:compliance, export or retention changes, residency impacts

Policy delta
- compliance expert coverage required
- intent must include data classification and constraints
- evidence comment must include compliance considerations

Escalation
- human approval for export or retention changes

### Billing overlay

When to apply
- risk:billing, pricing and payments paths

Policy delta
- mandatory business expert coverage
- required reviewers enforced through GitHub rulesets mapping

Escalation
- human review required when contract-impacting behavior changes

### Migration overlay

When to apply
- risk:migration label
- Context Manager detects migration files or destructive operations

Policy delta
- rollback plan required in evidence
- migration validation checks required
- QA must validate invariants and migration scenarios

Escalation
- destructive operations without rollback

### Partner API overlay

When to apply
- risk:partner-api label
- Context Manager detects partner integration paths

Policy delta
- partner expert coverage required
- evidence includes partner constraints and contract validation notes
- QA includes partner behavior validation

Escalation
- breaking partner auth model or quota changes

### Infra overlay

When to apply
- risk:infra label
- infra paths, deploy config changes, IaC changes

Policy delta
- infra expert coverage required
- stricter verification on config validation
- publishing draft until required reviewers exist

Escalation
- environment changes without staged rollout

### Hotfix overlay

When to apply
- urgent label, incident link, P0 priority

Policy delta
- minimal diff requirement
- tighter time budget
- increased escalation when verification fails repeatedly

Escalation
- any repeated loopbacks beyond cap

### High Risk overlay

When to apply
- complexity high
- many services impacted
- high blast radius

Policy delta
- additional mandatory coverage
- stricter QA posture
- draft PR only by default

Escalation
- unresolved conflicts or repeated loopbacks

## Signals and learning hooks

Role and overlays must be part of the context key for learning.

Signals to record:
- base role and overlays used
- loopback counts by category
- required coverage satisfied or violated
- PR evidence completeness score
- reopen rate for the role + overlay combination

This allows the Reputation Engine to learn:
- which experts perform best for specific role + overlay contexts
- which role configurations produce stable outcomes in specific repos

## Admin UI integration

The Admin UI should show:
- role and overlay selection per task
- overlay triggers that fired and why
- policy deltas applied (tools, required coverage, publishing posture)
- override actions with audit log

Operators should be able to:
- override role selection for a task
- add or remove overlays (with governance constraints)
- pause write actions for a repo

## Model Budget Posture

Model usage is governed by EffectiveRolePolicy.

Default posture by base role
- Developer: balanced by default; strong allowed when complexity high or risk overlays present
- Architect: balanced by default; strong allowed for cross-service refactors and interface work
- Planner: fast and balanced only; no strong model unless escalated for ambiguity

Overlay effects
- Security, Compliance, Billing: require balanced for intent and QA; strong allowed for implementation when needed
- Migration, Partner API, Infra: strong is allowed more often, but budgets tighten and evidence requirements increase
- Hotfix: prefers balanced with strict token caps; strong only if repeated failures occur
- High Risk: allows strong, but requires additional coverage and stricter QA

Budgets
- budgets are per task and per step, enforced in Model Gateway
- repeated same-category failures may escalate model class or trigger human review
