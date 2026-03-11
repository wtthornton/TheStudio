# Story 17.5 — Admin UI: Poll Settings

> **As a** platform operator,
> **I want** to enable polling and set the interval per repo in the Admin UI,
> **so that** I can configure poll intake without API calls.

**Purpose:** Operators need a UI to enable polling and set intervals without using curl or the Admin API directly. This story delivers the Admin UI surface so poll config is accessible in the repo settings flow.

**Intent:** Add poll section to repo settings: toggle "Enable issue polling" and interval input (5–60 minutes). Persist via Admin API. Help text clarifies when to use polling (no public URL, webhook backup).

**Points:** 3 | **Size:** S  
**Epic:** 17 — Poll for Issues as Backup to Webhooks  
**Sprint:** B (Stories 17.3–17.5)  
**Depends on:** Story 17.4 (repo profile config)

---

## Description

Add a poll settings section to the repo settings view in Admin UI. Users can toggle polling on/off and set the poll interval (minutes).

## Tasks

- [ ] Add poll section to repo settings partial:
  - Toggle: "Enable issue polling (backup when webhooks unavailable)"
  - Number input: Poll interval (minutes), default 10, min 5, max 60
  - Help text: "Polling checks GitHub for new/updated issues. Use when webhooks are not available (e.g. no public URL)."
- [ ] Wire to Admin API PATCH for poll_enabled, poll_interval_minutes
- [ ] Ensure existing Playwright tests pass

## Acceptance Criteria

- [ ] Toggle and interval render in repo settings
- [ ] Changes persist via Admin API
- [ ] Existing tests pass

## Files Affected

| File | Action |
|------|--------|
| Admin UI templates (repo settings partial) | Modify |
| `src/admin/ui_router.py` or equivalent | Modify |
