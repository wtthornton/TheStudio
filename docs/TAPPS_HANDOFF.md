# TAPPS Handoff

> Project-wide quality and delivery status as of 2026-03-21 (addenda **2026-03-24** below). **Authoritative epic rollup:** `docs/epics/EPIC-STATUS-TRACKER.md`.

## Addendum — Epic 52 canonical UI modernization (2026-03-24)

Documentation and roll-up status for Epics **52–57** were synchronized: `docs/epics/epic-52-frontend-ui-modernization-master-plan.md` (execution log), `epic-52-traceability-matrix-style-guide-mapping.md`, `epic-52-gap-report-admin-vs-dashboard.md`, per-epic rollups in **53 / 54 / 57** epic files, story headers **53.2–53.3, 54.1–54.2, 57.1**, and `docs/epics/EPIC-STATUS-TRACKER.md` (new subsection under Phase 9). Implementation remains **partial** for 53.3, 54.2, 57.1; see those story files for evidence and remaining scope.

## Addendum — Canonical style guide, MCP frontend experts, and implementation pass (2026-03-24)

- **Canonical UI standard:** `docs/design/07-THESTUDIO-UI-UX-STYLE-GUIDE.md` — single source of truth for `/admin/ui/*` and `/dashboard/*`; linked from README, AGENTS.md, CLAUDE.md, `.github/copilot-instructions.md`, and Cursor rule `.cursor/rules/frontend-style-source-of-truth.mdc`.
- **TappsMCP + frontend:** `docs/TAPPS_MCP_FRONTEND_EXPERTS_BRIEF.md`; business experts extended in `.tapps-mcp/experts.yaml`.
- **Admin HTMX:** Self-loading section pattern (`data-admin-htmx-section`, `aria-label`, loading `role="status"` / `aria-live`) normalized across primary fleet and detail templates (Story **53.3** alignment).
- **Dashboard React:** Accessibility and interaction hardening in `SteeringActionBar`, `StageDetailPanel`, `EditPanel`, `ImportModal`, plus store/hook touchpoints (`useGitHubEvents`, `backlog-store`, `trust-store`) and related components (`ExpertTable`, `ProjectsSyncConfig`, `BacklogCard`) per Epic **54** style-guide work.
- **Testing / infra:** `tests/playwright/conftest.py` updates; Dockerfile and `.dockerignore` adjustments as in tree.
- **Git hygiene:** `.tapps-brain/` is local machine state — added to `.gitignore` (not committed).

## Project Status

**Phases 0–9:** Pipeline UI Phases **0–3** (Epics **34–37**) complete; **Epic 38** MVP (Slices **1–2**) in tree with Slices **3–4** remaining; **Epic 39** approved, not started. **Epics 44–50** and **47** (onboarding, help, empty states, Scalar docs, navigation, spotlights, tours) complete per `.ralph/fix_plan.md`. **Epics 52–57** (canonical UI modernization) in execution with partial story delivery — see `EPIC-STATUS-TRACKER.md`.
Epic **27** (Multi-Source Webhooks) deferred — no current demand.
Epic **51** (Ralph vendored SDK parity) in progress — gates **Epic 43**; handoff: `docs/handoffs/ralph-epic-51-next-agent-prompt.md`.
First real GitHub issue processed end-to-end (Issue #19 → PR #20, 2 min, $0.30).

---

## Delivery Summary

| Epic | Title | Phase | Status |
|------|-------|-------|--------|
| 0 | Foundation | 0 | Complete |
| 1 | Full Flow + Experts | 1 | Complete |
| 2 | Learning + Multi-repo | 2 | Complete |
| 3 | Execute Tier Compliance | 2 | Complete |
| 4 | Admin UI Core | 2 | Complete (9/9 stories) |
| 5 | Observability & Quality | 3 | Complete |
| 6 | Phase 3 Completion | 3 | Complete |
| 7 | Platform Maturity | 4 | Complete (2 sprints) |
| 8 | Production Readiness | 4 | Complete (2 sprints) |
| 9 | Docker Test Rig | 4 | Complete |
| 10 | Docker Test Hardening | 4 | Complete |
| 11 | Production Hardening Phase 1 | 4 | Complete |
| 12 | Playwright Admin UI Tests | 4 | Complete |
| 13 | Agent Persona Infrastructure | 4 | Complete |
| 14 | Agent Content Enrichment | 4 | Complete |
| 15 | E2E Integration & Real Repo Onboarding | 5 | Complete |
| 16 | Issue Readiness Gate | 5 | Complete |
| 17 | Poll for Issues (Backup) | 5 | Complete |
| 18 | Production E2E Test Suite | 5 | Complete |
| 19 | Critical Gaps Batch 1 | 5 | Complete |
| 20 | Critical Gaps Batch 2 | 5 | Complete |
| 21 | Human Approval Wait States | 5 | Complete |
| 22 | Execute Tier End-to-End | 5 | Complete |
| 23 | Unified Agent Framework | 5 | Complete |
| 24 | Chat Approval Workflows | 5 | Complete |
| 25 | Container Isolation | 5 | Complete |
| 26 | File-Based Expert Packaging | 5 | Complete |
| 27 | Multi-Source Webhooks | 5 | **Deferred** |
| 28 | Preflight Plan Review Gate | 6 | Complete |
| 29 | GitHub Projects v2 + Meridian Portfolio Review | 6 | Complete |
| 30 | Real Provider Integration & Validation | 7 | Complete (3 sprints) |
| 31 | Anthropic Max OAuth Adapter | 7 | Complete (2026-03-19) |
| 32 | Model Routing & Cost Optimization | 7 | Complete (5 slices) |
| 33 | P0 Deployment Test Harness | 8 | Complete (2 sprints) |
| 34 | Phase 0: SSE PoC + Frontend Scaffolding | 9 | Complete (14 stories) |
| 35 | Phase 1: Pipeline Visibility | 9 | Complete (63 stories) |
| 36 | Phase 2: Planning Experience | 9 | Complete (29 stories, 4 slices) |
| 37 | Phase 3: Interactive Controls | 9 | Complete (28 stories) |
| 38 | Phase 4: GitHub Integration | 9 | MVP complete (Slices 1–2); Slices 3–4 open |
| 39 | Phase 5: Analytics & Learning | 9 | Approved — not started |
| 44 | Setup Wizard | 9 | Complete (per fix_plan Sprint 6) |
| 45 | Contextual Help | 9 | Complete (per fix_plan Sprint 8) |
| 46 | Actionable Empty States | 9 | Complete (per fix_plan Sprint 4) |
| 47 | Product Tours | 9 | Complete (per fix_plan Sprint 9) |
| 48 | Scalar API Docs | 9 | Complete (per fix_plan Sprint 5) |
| 49 | Unified Navigation | 9 | Complete (per fix_plan Sprint 7) |
| 50 | Feature Spotlights | 9 | Complete (per fix_plan Sprint 10) |
| 43 | Ralph SDK as Primary Agent | 10 | Approved — gated on Epic 51 |
| 51 | Ralph Vendored SDK Parity | 10 | In progress |

---

## Recent Deliverables (2026-03-21)

### Epic 36: Planning Experience (29 stories, 4 slices)
- **Slice 1 — Triage Queue:** TRIAGE status, feature-flagged triage mode, accept/reject/edit endpoints, context pre-scan, TriageQueue frontend with SSE
- **Slice 2 — Intent Review:** Intent source tracking, Temporal wait point, approve/reject/edit/refine API, IntentEditor frontend with version diff
- **Slice 3 — Complexity + Routing:** MetricCard, RiskFlags, FileHeatmap, ComplexityDashboard, routing review wait point, ExpertCard, RoutingPreview with add/remove
- **Slice 4 — Backlog + Tasks:** 6-column Kanban board, board preferences persistence, manual task creation endpoint + modal, historical comparison query

### Epic 35: Pipeline Visibility (63 stories)
- Pipeline Rail, TaskPacket Timeline, Gate Inspector, Activity Stream
- Loopback arcs, Minimap, error states

### Epic 34: SSE PoC (14 stories)
- Dashboard API router, SSE bridge (NATS→EventSource), Vite+React+Zustand+Tailwind scaffolding

---

## Codebase Metrics (2026-03-21)

| Metric | Value |
|--------|-------|
| Source files (src/) | 165+ |
| Frontend components | 25+ React components |
| Test files | 130+ |
| Tests passing | 3,366+ |
| Coverage | 84% |
| Epics complete | 36/39 |

---

## Per-Agent Cost Baselines

| Agent | Model | Cost | Latency |
|-------|-------|------|---------|
| intake_agent | Haiku | $0.0007 | 1.8s |
| context_agent | Haiku | $0.0047 | 8.9s |
| intent_agent | Sonnet | $0.0309 | 38.5s |
| router_agent | Sonnet | $0.0142 | 16.4s |
| assembler_agent | Sonnet | $0.0309 | 35.3s |
| qa_agent | Sonnet | $0.0053 | 8.7s |
| **Total (6 agents)** | | **$0.087** | |
| Projected/issue (9 agents) | | ~$0.13 | |
| Monthly @ 50 issues/day | | ~$195 | |

---

## Next Actions

1. **Epic 51** — Ralph vendored SDK parity and evaluation backlog (`docs/handoffs/ralph-epic-51-next-agent-prompt.md`).
2. **Epic 38** — Slices **3–4** (Projects sync, pipeline comments / webhook bridge); see `epic-38-phase4-github-integration.md`.
3. **Stories 53.3 / 54.2 / 57.1** — Close remaining AC for canonical UI compliance (keyboard/SR sign-off, traceability matrix).
4. **Epic 39** — Phase 5 analytics and learning when capacity allows.
5. **Process harder issues** — Multi-file changes, bug fixes, refactoring tasks.
6. **Onboard second repo** — Test multi-repo support with real issues.
7. **Wire remote verification** — Run ruff/pytest on target repo via GitHub Actions or container.
8. **Execute tier promotion** — When ready for auto-merge with approval gates.
