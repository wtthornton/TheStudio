---
name: sprint
description: Plan a sprint using Helm's testable goal format
user-invocable: true
context: fork
agent: helm-planner
argument-hint: "[sprint number or focus area]"
allowed-tools: Read, Glob, Grep, Write, Edit
---

Plan sprint: $ARGUMENTS

Read `thestudioarc/personas/helm-planner-dev-manager.md` for full guidance. Produce:

1. **Sprint Goal** — Testable format: objective + test + constraint
2. **Ordered Backlog** — With rationale for sequence (why this order)
3. **Dependency List** — With owners and status
4. **Estimation Notes** — Reasoning and unknowns, not just points
5. **Capacity Allocation** — With buffer for unknowns (never 100%)

Flag that this plan needs Meridian review before commit.
