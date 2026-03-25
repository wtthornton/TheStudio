# Epic 71 — Settings: Playwright Full-Stack Test Suite

**Status:** Draft
**Total Points:** 19
**Path:** `/admin/ui/settings`
**Slug:** `settings`

## Purpose

Multi-tab admin configuration hub with 6 tabs: API Keys, Infrastructure, Feature Flags, Agent Config, Budget Controls, Secrets. Each tab delivers domain-specific config controls via HTMX partial.

## Motivation

Settings controls the entire platform config — API keys, infrastructure connections, feature flags, agent behavior, budgets, and secrets. Broken settings tabs mean operators can't configure the platform.

## APIs Under Test

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/admin/settings` | Get all settings |
| GET | `/admin/ui/partials/settings` | Settings main partial |
| GET | `/admin/ui/partials/settings/api-keys` | API keys tab |
| POST | `/admin/ui/partials/settings/api-keys` | Create API key |
| GET | `/admin/ui/partials/settings/api-keys/reveal/{key}` | Reveal masked key |
| GET | `/admin/ui/partials/settings/infrastructure` | Infrastructure config |
| POST | `/admin/ui/partials/settings/infrastructure` | Update infrastructure |
| GET | `/admin/ui/partials/settings/feature-flags` | Feature flags |
| POST | `/admin/ui/partials/settings/feature-flags` | Update flags |
| GET | `/admin/ui/partials/settings/agent-config` | Agent config |
| POST | `/admin/ui/partials/settings/agent-config` | Update agent config |
| GET | `/admin/ui/partials/settings/budget-controls` | Budget controls |
| POST | `/admin/ui/partials/settings/budget-controls` | Update budget |
| GET | `/admin/ui/partials/settings/secrets` | Secrets |
| POST | `/admin/ui/partials/settings/secrets/rotate-key` | Rotate key |
| POST | `/admin/ui/partials/settings/secrets/regenerate-webhook` | Regenerate webhook |

## Components

- Tab navigation (HTMX-driven, 6 tabs)
- Form inputs per tab (text, number, toggle)
- Toggle switches (feature flags)
- Masked values with reveal controls (API keys, secrets)
- Action buttons (Reveal, Update, Rotate, Regenerate)
- Success/error feedback messages
- Empty state per tab

## Stories

| Story | Title | Points |
|-------|-------|--------|
| 71.1 | Page Intent & Semantic Content | 3 |
| 71.2 | API Endpoint Verification | 3 |
| 71.3 | Style Guide Compliance | 5 |
| 71.4 | Interactive Elements | 3 |
| 71.5 | Accessibility WCAG 2.2 AA | 3 |
| 71.6 | Visual Snapshot Baseline | 2 |

## Intent Checks

- All 6 tab links present (api-keys, infrastructure, feature-flags, agent-config, budget-controls, secrets)
- API Keys tab shows key names with masked values (***) and reveal/update controls
- Infrastructure tab shows connection strings, addresses, pool config
- Feature Flags tab shows toggleable flags (enabled/disabled)
- Agent Config tab shows model, timeout, retries, concurrency settings
- Budget Controls tab shows budget limits and utilization
- Secrets tab shows rotation controls (rotate key, regenerate webhook)

## Accessibility Specifics

- Tab navigation follows tablist/tab/tabpanel ARIA pattern
- Form inputs have associated labels
- Masked values are accessible (screen reader can identify masked vs revealed state)
- Destructive actions (rotate/regenerate) are clearly labeled
- Toggle switches have accessible names and state

## Definition of Done

- [ ] All 6 stories complete and merged
- [ ] Playwright tests pass in CI
- [ ] No accessibility violations (axe-core clean)
- [ ] Visual snapshots committed as baselines
