# Session Planning Process

## Overview

Every session follows the **persona chain** to ensure work is planned, reviewed, and trackable.
Run `/session-plan` at the start of any session to execute this automatically.

## The Persona Chain

```
Strategy/OKRs → Saga (epic) → Meridian (review) → Helm (plan) → Meridian (review) → Execution
```

| Persona | Role | Controls |
|---------|------|----------|
| **Saga** | Epic creator | Scope, acceptance criteria, success metrics |
| **Helm** | Sprint planner | Session plans, ordered work, testable goals |
| **Meridian** | Reviewer | Quality gate — nothing committed without her approval |

## Process Steps

### 1. Discover Open Epics

- Read `docs/TAPPS_HANDOFF.md` for project status
- Scan `docs/epics/epic-*.md` for all epics
- Classify: **Complete**, **Approved** (Meridian passed), **Draft** (needs review)
- Check `docs/sprints/` for existing plans
- Check `docs/epics/stories/` for implemented stories

### 2. Helm Plans the Session

Helm creates a sprint plan at `docs/sprints/sprint-epic{N}-s{sprint}.md` with:
- Testable sprint goal (objective + test + constraint)
- Ordered backlog with dependency rationale
- Estimation reasoning (not just points)
- Capacity with buffer (never 100%)
- Compressible stories (what to cut)
- Retro reference

### 3. Meridian Reviews

Meridian runs her 7-question checklist:
1. Order of work justified?
2. Sprint goals testable?
3. Dependencies visible?
4. Estimation reasoning recorded?
5. Unknowns surfaced and buffered?
6. Retro actions reflected?
7. Async-executable without daily clarification?

Verdict: **COMMITTABLE**, **CONDITIONAL PASS**, or **REJECTED**.

### 4. Fix and Commit

- Conditional: fix gaps, update status to COMMITTED
- Rejected: discuss with user, revise plan
- Committable: update status to COMMITTED

## Automation

- **Session start hook** (`.claude/hooks/tapps-session-start.sh`) prompts for `/session-plan`
- **Skill** (`.claude/skills/session-plan/SKILL.md`) orchestrates the full process
- Sprint plans are stored in `docs/sprints/`

## Key Rules

- No epic committed without Meridian review
- No plan committed without Meridian review
- No PR without evidence comment
- Gates fail closed
