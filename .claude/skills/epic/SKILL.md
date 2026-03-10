---
name: epic
description: Create a new epic using Saga's 8-part structure
user-invocable: true
context: fork
agent: saga-epic-creator
argument-hint: "[epic title or topic]"
allowed-tools: Read, Glob, Grep, Write, Edit
---

Create a new epic for: $ARGUMENTS

Use the Saga persona's 8-part structure from `thestudioarc/personas/saga-epic-creator.md`:

1. **Title** — Outcome-focused, not task-focused
2. **Narrative** — The user/business problem and why it matters now
3. **References** — Research, personas, OKRs, discovery artifacts
4. **Acceptance Criteria** — High-level, testable at epic scale (not story-level)
5. **Constraints & Non-Goals** — What's out of scope, regulatory limits, tech boundaries
6. **Stakeholders & Roles** — Owner, design, tech lead, QA, external parties
7. **Success Metrics** — Adoption, activation, time-to-value, revenue impact
8. **Context & Assumptions** — Business rules, dependencies, systems affected

The epic must be AI-ready: implementable by Claude/Cursor without guessing scope.
After writing, flag that it needs Meridian review before commit.
