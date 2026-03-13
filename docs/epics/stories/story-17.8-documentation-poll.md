# Story 17.8 — Documentation and Deployment Notes

> **As a** platform operator,
> **I want** clear documentation for the poll feature,
> **so that** I know when and how to use it.

**Purpose:** Operators need clear guidance on when to enable polling and how to configure it. Without docs, they may misconfigure or misuse the feature. This story delivers the documentation so the poll feature is discoverable and correctly used.

**Intent:** Document `THESTUDIO_INTAKE_POLL_ENABLED`, `THESTUDIO_INTAKE_POLL_INTERVAL_MINUTES`, per-repo override, when to use (no public URL, webhook backup), when not to use (prefer webhooks). Add intake architecture doc describing webhook vs poll paths. Link to idea doc for rationale.

**Points:** 2 | **Size:** S  
**Epic:** 17 — Poll for Issues as Backup to Webhooks  
**Sprint:** C (Stories 17.6–17.8)  
**Depends on:** None (can be parallel)

---

## Description

Document the poll feature in deployment and intake docs. Operators need to know when to enable polling, how to configure it, and that webhooks remain preferred when a public URL exists.

## Tasks

- [x] Add poll section to `docs/deployment.md`:
  - `THESTUDIO_INTAKE_POLL_ENABLED` (default: false)
  - `THESTUDIO_INTAKE_POLL_INTERVAL_MINUTES` (default: 10)
  - Per-repo override via Admin UI
  - When to use: no public URL, webhook backup
  - When not to use: prefer webhooks when public URL exists
- [x] Create or expand `docs/ingress.md`:
  - Describe webhook path (primary) vs poll path (backup)
  - Diagram: both paths → TaskPacket creation → workflow
- [x] Link to `docs/ideas/poll-for-issues-backup.md` for rationale and research

## Acceptance Criteria

- [x] Deployment doc includes poll env vars and guidance
- [x] Intake doc describes both paths
- [x] Operator can enable poll from docs alone

## Files Affected

| File | Action |
|------|--------|
| `docs/deployment.md` | Modify |
| `docs/ingress.md` | Create or modify |
