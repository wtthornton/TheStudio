# Agent Maturity Log

Tracks maturity assignments for all agent definitions. Updated when agents are promoted or demoted.

## Maturity Tiers

| Tier | Definition |
|------|-----------|
| **proven** | Used successfully in 3+ real pipeline runs or planning cycles |
| **reviewed** | Peer-reviewed and used in development; not yet validated at scale |
| **draft** | Created but not validated in production |

## Current Assignments (2026-03-10)

| Agent | Maturity | Rationale |
|-------|----------|-----------|
| saga-epic-creator | **proven** | Used in every epic from Epic 0 through Epic 14. Produces consistent 8-part structure. |
| meridian-reviewer | **proven** | Used in every epic and plan review. 7-question checklist consistently applied. |
| helm-planner | **proven** | Used in every sprint plan from Epic 4 onward. Testable goal format established. |
| scout-tester | **proven** | Invoked on every code change session. Pytest patterns well-established. |
| sentinel-gatekeeper | **proven** | Gate logic used in verification and QA modules. Defect taxonomy defined. |
| forge-evidence | **reviewed** | Well-defined scope (publisher, outcome, reputation) but invoked less frequently than core personas. |
| compass-navigator | **reviewed** | Pipeline mapping is accurate and detailed. Used for architecture questions but not in automated flows. |
| tapps-researcher | **reviewed** | Functional as MCP research wrapper. Enriched with tech stack and escalation rules. Not deeply tested standalone. |
| tapps-reviewer | **reviewed** | Quality scoring works via MCP. Enriched with TheStudio patterns. Used proactively in sessions. |
| tapps-validator | **reviewed** | Validation pipeline functional. Enriched with risk tiers and blocking format. |
| tapps-review-fixer | **reviewed** | Combined review-fix pipeline works in worktrees. Used in parallel review pipelines. |

## Promotion History

_No promotions recorded yet. Agents start at their initial assignment above._
