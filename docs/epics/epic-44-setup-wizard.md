# Epic 44: First-Run Setup Wizard -- Guided Onboarding for New Users

> **Status:** DRAFT -- Pending Meridian Review
> **Epic Owner:** Primary Developer
> **Duration:** 2-3 weeks (3 slices, 10 stories)
> **Created:** 2026-03-23
> **Priority:** P1 -- New users cannot discover how to configure TheStudio without reading docs
> **Depends on:** Epic 34 (React SPA) COMPLETE, Epic 41 (Multi-Repo Onboarding) COMPLETE
> **Capacity:** Solo developer, 30 hours/week

---

## 1. Title

**First-Run Setup Wizard -- Guided Multi-Step Onboarding Replaces Blank Dashboard for New Users**

---

## 2. Narrative

A new user opens TheStudio for the first time and sees an empty dark dashboard: "0 active / 0 queued / $0.00". No repos are registered. No webhooks are configured. No trust tiers are set. The pipeline rail is empty. Every tab shows placeholder text. The user has no idea what to do.

The required setup steps are documented in `docs/deployment.md` and scattered across Admin UI pages, but nothing in the application itself guides users through them. The result: every new user must read external documentation, understand the 9-step pipeline conceptually, and manually discover the right Admin UI pages in the right order. This is a 30-60 minute time-to-first-value that should be 5 minutes.

This epic adds a multi-step setup wizard using `react-use-wizard` (MIT, hooks-based) in the React SPA. The wizard appears on first launch (detected via localStorage flag) and walks users through: health verification, first repo registration, webhook configuration, trust tier selection, LLM provider setup, and triggering a test issue. Each step validates before proceeding. On completion, the wizard sets a `setup_complete` flag and never appears again. Users can re-launch it from a help menu.

The wizard calls existing Admin API endpoints (`/admin/repos`, `/admin/health`, `/healthz`, `/readyz`). No new backend endpoints are needed. The wizard is purely frontend.

Why now: TheStudio is deployed to production (Epic 43 complete, Docker hardened). The next users after the primary developer will hit this wall immediately.

---

## 3. References

| Type | Reference | Relevance |
|------|-----------|-----------|
| Library | `react-use-wizard` (MIT, 664 stars) | Hooks-based wizard engine, bring-your-own UI |
| Source | `frontend/src/App.tsx` | Entry point where wizard gate checks localStorage |
| Source | `frontend/src/lib/api.ts` | Existing API client for health/repo calls |
| Source | `src/admin/router.py` | Admin API endpoints the wizard calls |
| Docs | `docs/deployment.md` | Steps the wizard must automate |
| Docs | `docs/URLs.md` | Health endpoints the wizard validates |
| Epic | `docs/epics/epic-41-multi-repo-onboarding.md` | Repo registration flow |

---

## 4. Acceptance Criteria

### AC1: Wizard Appears on First Launch

When a user opens the React SPA (`/dashboard/`) and `localStorage.getItem('thestudio_setup_complete')` is falsy, the setup wizard renders as a full-screen overlay instead of the dashboard. The dashboard is not accessible until the wizard is completed or explicitly skipped.

**Testable:** Clear localStorage, reload `/dashboard/`. Wizard overlay appears. Set `thestudio_setup_complete=true`, reload. Dashboard appears directly.

### AC2: Wizard Validates Each Step Before Proceeding

Each wizard step calls a real API endpoint and shows pass/fail status:
- Step 1 (Health): `GET /healthz` and `GET /readyz` return 200
- Step 2 (Repo): `POST /admin/repos` succeeds (201) or repo already exists (409)
- Step 3 (Webhook): User confirms webhook URL is configured in GitHub (manual step with verification link)
- Step 4 (Trust): User selects trust tier via dropdown, `PATCH /admin/repos/{id}/profile` succeeds
- Step 5 (LLM): `GET /admin/health` shows Anthropic API key is configured
- Step 6 (Test): User triggers a test issue, wizard polls for TaskPacket creation

**Testable:** Mock each API endpoint. Verify wizard blocks "Next" when API returns error. Verify wizard enables "Next" when API returns success.

### AC3: Wizard Completion Sets Persistent Flag

On final step completion, wizard writes `thestudio_setup_complete=true` to localStorage and transitions to the dashboard with the pipeline tab active. Subsequent visits skip the wizard.

**Testable:** Complete wizard. Verify localStorage flag. Reload page. Verify dashboard loads directly.

### AC4: Wizard Is Re-Launchable

A "Setup Wizard" menu item exists in the help menu (or settings). Clicking it clears the completion flag and re-opens the wizard.

**Testable:** Complete wizard. Click re-launch. Wizard opens.

### AC5: Skip Option Available

A "Skip setup" link is visible on every step. Clicking it sets the completion flag and goes directly to the dashboard. A subtle banner persists until setup is completed showing "Setup incomplete -- 3 of 6 steps done".

**Testable:** Open wizard. Click skip on step 2. Dashboard loads. Banner shows "Setup incomplete".

---

## 5. Constraints & Non-Goals

- Wizard is React SPA only. The HTMX Admin UI is not modified (Epic 49 handles unified navigation).
- Wizard calls existing Admin API endpoints. No new backend routes.
- Wizard does not create GitHub Apps or generate webhook secrets. It guides users to the right place and validates the result.
- No analytics or telemetry on wizard completion rates (future).
- The wizard does not handle multi-tenant or team onboarding.

---

## 6. Stakeholders & Roles

| Role | Who | Responsibility |
|------|-----|----------------|
| Primary Developer | Solo | Implementation, testing |
| First external user | TBD | Validation of flow clarity |

---

## 7. Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Time to first repo registered | < 5 minutes from first page load | Timed manual walkthrough by developer on clean install |
| Wizard completion steps | All 6 steps have passing API validation logic | Vitest: each step component renders, validates, and enables Next |
| Skip-to-dashboard path works | Skip link sets flag and renders dashboard | Vitest: skip flow test |

---

## 8. Context & Assumptions

- React SPA is the primary user-facing UI for pipeline operations.
- Admin API endpoints are stable and do not require auth in dev mode (auto-auth as admin).
- In production, the wizard must handle Caddy Basic Auth (credentials entered before wizard loads).
- `react-use-wizard` is installed as a frontend dependency.
- The wizard is client-side only; no backend state tracks wizard progress.

---

## 9. Story Map

### Slice 1: Wizard Infrastructure (4 stories, ~6h)

| Story | Title | Size | Description |
|-------|-------|------|-------------|
| 44.1 | Install react-use-wizard, create WizardShell component | S | `npm install react-use-wizard`. Create `frontend/src/components/wizard/WizardShell.tsx` with step navigation, progress bar, skip button. |
| 44.2 | Add wizard gate to App.tsx | S | Check localStorage flag on mount. Render WizardShell overlay when flag is falsy. Pass completion callback that sets flag and unmounts wizard. |
| 44.3 | Create HealthCheckStep component | S | Step 1: calls `/healthz` and `/readyz`, shows green/red status for each, enables Next on both green. |
| 44.4 | Create RepoRegistrationStep component | M | Step 2: form with owner/repo/installation_id fields. Calls `POST /admin/repos`. Handles 201 (success) and 409 (already exists). Shows validation errors. |

### Slice 2: Configuration Steps (4 stories, ~8h)

| Story | Title | Size | Description |
|-------|-------|------|-------------|
| 44.5 | Create WebhookConfigStep component | S | Step 3: displays webhook URL (`{base}/webhook/github`), copy button, link to GitHub App settings. Manual checkbox "I've configured the webhook". |
| 44.6 | Create TrustTierStep component | S | Step 4: dropdown with Observe/Suggest/Execute options and descriptions. Calls `PATCH /admin/repos/{id}/profile` with selected tier. |
| 44.7 | Create LLMProviderStep component | S | Step 5: calls `GET /admin/health`, checks if Anthropic key is configured. Shows status. If not configured, links to settings page. |
| 44.8 | Create TestIssueStep component | M | Step 6: button to create a test issue (pre-filled payload). Polls `/admin/workflows` for 30s to detect TaskPacket creation. Shows success animation on detection. |

### Slice 3: Polish & Edge Cases (2 stories, ~3h)

| Story | Title | Size | Description |
|-------|-------|------|-------------|
| 44.9 | Add skip flow and incomplete banner | S | Skip link on each step. Persistent banner in dashboard header showing "Setup incomplete -- N of 6 steps done" with resume link. |
| 44.10 | Add re-launch menu item and unit tests | S | "Setup Wizard" in help/settings menu. Vitest tests for WizardShell, gate logic, localStorage flag, skip flow. |

---

## 10. Meridian Review Status

**Status:** PENDING
