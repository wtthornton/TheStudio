---
name: evidence
description: Generate a standardized evidence comment for a PR
user-invocable: true
argument-hint: "[PR number or description of changes]"
allowed-tools: Read, Glob, Grep, Bash
---

Generate an evidence comment for: $ARGUMENTS

Read `thestudioarc/15-system-runtime-flow.md` for the evidence comment format.

Produce a standardized evidence comment with:

- **TaskPacket ID** + correlation_id (if available)
- **Intent Summary** — Goal statement from the Intent Specification
- **Acceptance Criteria** — Checklist format with checkboxes
- **What Changed** — High-level summary of modifications
- **Verification Results** — ruff, pytest, security scan results
- **Test Commands** — Exact commands to reproduce verification
- **Expert Coverage** — Which expert classes were consulted
- **Loopback Counts** — Number of verification/QA retries (if any)
- **Defect Categories** — Any defects found and their classification

This is the audit trail. Every PR tells the story of how it got here.
