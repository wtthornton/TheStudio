# POLICIES.md

## Purpose

Define governance rules that apply across the system.

## Intent

Policies are enforced by the Router, Verification Gate, Publisher, and QA outcomes.
Policies determine when the system must escalate or block automated action.

## Mandatory coverage triggers

- security expert required: auth, authorization, crypto, secret handling
- compliance expert required: data exports, retention, residency
- business expert required: billing, pricing, payments logic
- partner expert required: external API auth or quota changes

## Escalation triggers

- destructive migrations without rollback
- privileged access requests
- changes that could impact customer contracts or compliance posture

## Repo Tier Enforcement

Tier gating
- Observe: read-only, no PR writes
- Suggest: draft PR allowed, writes guarded, no ready-for-review without gates
- Execute: full workflow, hard gates enforced, ruleset expectations required

Trigger eligibility
- agent:run is honored only when the repo is registered and tier allows it
- execute tier triggers require repo compliance checks to be passing

Write control
- Admin UI can disable writes per repo (Publisher freeze)
- Human-review escalation blocks automation until cleared

Required controls
- Publisher is the only GitHub writer
- Verification and QA gates fail closed

## Human Approval Wait States

Human approvals are first-class workflow states.

When to enter human wait
- agent:human-review label applied by policy
- required reviewer approvals missing for sensitive paths
- compliance or security escalation triggered
- repeated loopbacks exceed caps

Behavior
- workflow transitions to waiting state with a clear reason and required actions
- Publisher posts a summary comment to the issue or PR with what is needed
- reminders at 24h, 72h, 7d
- after 7d, escalate to owners and pause automation for that task until resolved

## Execute Tier Compliance Gate

Execute tier is earned. A repo cannot be promoted to Execute tier unless compliance checks pass.

Minimum compliance checks
- rulesets configured with required status checks for the repo
- required reviewer rules for sensitive paths (auth, billing, exports, infra) where applicable
- standard labels and Projects fields present
- evidence comment format enabled and validated
- Publisher idempotency guard enabled
- execution plane health checks passing
- credentials scoped and rotation configured

Admin UI requirements
- show compliance score and failures
- block promotion until all required checks pass

## Adversarial Input Escalation

Suspicious GitHub payloads trigger escalation or tier reduction. See `00-overview.md` Adversarial Input Policy.

## Merge Policy

Merge policy

Default posture
- TheStudio does not merge PRs by default.
- Human merge is required for all repos until explicitly enabled by repo policy.

Optional auto-merge (future)
Auto-merge may be enabled only when:
- repo is in Execute tier and compliance score passes
- required reviewers are satisfied
- verification and QA gates pass
- repo policy explicitly enables auto-merge for specific low-risk labels and paths

Admin UI
- show merge mode per repo (human-only or auto-merge enabled)
- allow disabling auto-merge immediately (incident control)

## Repo Compliance Checker

Required reviewer compliance validation

Execute tier requires proof, not assumptions.

Compliance checker responsibilities
- verify rulesets exist and required status checks are configured
- verify required reviewer rules exist for sensitive paths (auth, billing, exports, infra) where applicable
- verify branch protections and merge settings match policy
- verify standard labels, Projects fields, and evidence comment format are in place

Promotion rule
- a repo cannot be promoted to Execute tier unless compliance checker passes.

Admin UI
- show compliance checker results and remediation steps
- block tier promotion until passing

## Compliance Checker Execution Point

Execution point

The compliance checker runs as a platform job and is invoked by:
- Admin UI when an operator views or requests tier promotion
- the tier promotion workflow step before enabling Suggest or Execute

Results
- results are persisted with timestamps and a pass/fail summary
- promotion logic must reference the latest passing result, not assumptions
- failures include remediation guidance and must block promotion
