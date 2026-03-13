# Story 17.4 — Repo Profile and Per-Repo Poll Config

> **As a** platform operator,
> **I want** per-repo poll enable and interval configuration,
> **so that** I can enable polling only for repos that need it.

**Purpose:** Polling must be opt-in per repo. Without repo-level config, we could not enable polling for some repos while others use webhooks. This story delivers the persistence and API surface for per-repo poll settings.

**Intent:** Add `poll_enabled` and `poll_interval_minutes` to repo profile. Scheduler reads these fields; Admin API accepts updates. Default interval from env when null. No global poll without repo-level enable.

**Points:** 3 | **Size:** S  
**Epic:** 17 — Poll for Issues as Backup to Webhooks  
**Sprint:** B (Stories 17.3–17.5)  
**Depends on:** None (can be parallel with 17.1)

---

## Description

Add poll configuration fields to the repo profile. The scheduler reads `poll_enabled` and `poll_interval_minutes` (fallback to global env when null) to decide which repos to poll and at what interval.

## Tasks

- [x] Add to `src/repo/repo_profile.py`:
  - `poll_enabled: bool = False`
  - `poll_interval_minutes: int | None = None` (global default when null)
- [x] Add columns to `repo_profile` table via migration
- [x] Update Admin API `PATCH /admin/repos/{id}` to accept `poll_enabled`, `poll_interval_minutes`
- [x] Update repo profile CRUD to read/write these fields

## Acceptance Criteria

- [x] Repo profile stores poll_enabled and poll_interval_minutes
- [x] Admin API updates poll config
- [x] Scheduler reads poll_enabled from repo profile
- [x] Interval null → use THESTUDIO_INTAKE_POLL_INTERVAL_MINUTES

## Files Affected

| File | Action |
|------|--------|
| `src/repo/repo_profile.py` | Modify |
| `src/db/migrations/` | New migration |
| `src/admin/router.py` | Modify PATCH body |
