---
name: intent
description: Build a structured Intent Specification for a task
user-invocable: true
argument-hint: "[GitHub issue number or task description]"
allowed-tools: Read, Glob, Grep, Write, Edit
---

Build an Intent Specification for: $ARGUMENTS

Read `thestudioarc/11-intent-layer.md` for full guidance on the Intent Specification format.

Produce a structured document with:

1. **Goal** — One clear outcome statement
2. **Constraints** — Technical, operational, compliance boundaries
3. **Invariants** — What must NOT change
4. **Acceptance Criteria** — Testable conditions (not aspirational)
5. **Non-Goals** — Explicit scope exclusions
6. **Assumptions** — What we're taking as given
7. **Open Questions** — Unresolved items that need answers before implementation

The Intent Specification is the definition of correctness. Every downstream step
(Router, Assembler, Primary Agent, Verification, QA) validates against it.
Make it precise enough that the QA Agent can verify implementation without ambiguity.
