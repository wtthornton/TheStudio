---
name: review
description: Run Meridian's 7-question review checklist on an epic or plan
user-invocable: true
context: fork
agent: meridian-reviewer
argument-hint: "[path to epic or plan document]"
allowed-tools: Read, Glob, Grep
---

Review this document: $ARGUMENTS

Read the document and `thestudioarc/personas/meridian-review-checklist.md`.

Determine if it's an epic (Saga output) or plan (Helm output), then run the
appropriate 7-question checklist.

**Epic Review (7 Questions):**
1. Is the goal statement specific enough to test against?
2. Are acceptance criteria testable at epic scale?
3. Are non-goals explicit?
4. Are dependencies identified with owners and dates?
5. Are success metrics measurable with existing instrumentation?
6. Can an AI agent implement without guessing scope?
7. Is the narrative compelling enough to justify the investment?

**Plan Review (7 Questions):**
1. Is the order of work justified?
2. Are sprint goals testable (objective + test + constraint)?
3. Are dependencies visible and tracked?
4. Is estimation reasoning recorded?
5. Are unknowns surfaced and buffered for?
6. Does the plan reflect learning from previous retros?
7. Can the team execute async without daily clarification?

For each item: **Pass** or **Gap** with specific feedback.
List all red flags. State what must be fixed before commit.
