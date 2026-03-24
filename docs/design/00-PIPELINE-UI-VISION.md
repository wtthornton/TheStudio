# TheStudio Pipeline UI — Master Vision Document

**Status:** Design Draft
**Date:** 2026-03-20
**Purpose:** Define the vision, scope, and structure for TheStudio's rich interactive pipeline UI. This document is the entry point for all design specs and the source from which implementation epics and stories will be derived.

---

## 1. Executive Summary

TheStudio is an AI-augmented software delivery platform with a 9-stage pipeline (Intake → Context → Intent → Router → Assembler → Implement → Verify → QA → Publish). Today it operates as a headless backend — GitHub issues in, draft PRs out. The admin panel provides basic operational views but no pipeline visibility, no planning interface, and no interactive controls.

This initiative adds a **rich interactive frontend** that makes the pipeline visible, explorable, and steerable. The developer experience centers on three pillars:

1. **Plan with confidence** — Interactive planning tools that surface complexity, risk, and intent before a single line of code is written.
2. **Watch it work** — Real-time pipeline visualization showing TaskPackets flowing through stages, gates passing or failing, and agents executing.
3. **Steer when needed** — Interactive controls for trust tiers, pipeline intervention (pause, retry, redirect), and budget governance.

The result is not "AI writes code for you" but **"AI delivers software through a visible, auditable, steerable pipeline."**

---

## 2. Competitive Landscape

### Direct Competitors

| Product | Approach | Strength | TheStudio Differentiator |
|---------|----------|----------|--------------------------|
| **Devin** (Cognition, $10.2B) | Autonomous agent with workspace UI | Replay timeline, interactive planning, 67% PR merge rate | Multi-stage governed pipeline vs single agent |
| **Copilot Coding Agent** (GitHub) | Issue → spec → plan → code → PR | Native GitHub integration, massive distribution | Evidence-based trust tiers, formal gates |
| **Factory AI** ($50M Series B) | Specialized Droids (Knowledge, Code, Reliability, Product) | Enterprise governance, Command Center | Open pipeline architecture, 9 explicit stages |
| **Codegen** (3.0) | OS for code agents, analytics dashboard | Cost analytics, PR velocity metrics, SOC 2 | Reputation system, outcome learning |
| **Aperant** (Auto Claude, open source) | Electron desktop app, Kanban + terminals | Polished UI, multi-provider, parallel agents | Server-side durability, formal verification |

### Adjacent Tools

| Tool | Relevance | What to Learn |
|------|-----------|---------------|
| **Linear** | Gold standard for developer PM UI | Polish, speed, keyboard-driven interaction |
| **Plane** (open source) | GitHub-synced project management | Bidirectional sync patterns, Gantt views |
| **Temporal UI** | Workflow visualization (already in our stack) | Timeline view, compact view, real-time liveness |
| **Mission Control** (builderz-labs, open source) | Agent orchestration dashboard | 32-panel layout, 6-column Kanban, token tracking |
| **GitHub Agentic Workflows** (Feb 2026, tech preview) | Natural-language CI/CD with ProjectOps | Board automation, issue-driven patterns |

### Key Insight

Every competitor shows **one agent working**. TheStudio's UI shows **a governed pipeline with multiple stages, gates, evidence, and trust tiers**. This is the core differentiator and must be the central design theme.

---

## 3. Design Principles

1. **Pipeline-first.** The 9-stage pipeline is the organizing metaphor for everything. Navigation, status, metrics — all oriented around pipeline stages.

2. **Plan before build.** The planning experience (Intent Specification, risk assessment, expert routing) gets more UI investment than the execution view. Developers spend more time planning than watching agents code.

3. **Gates are visible.** Every gate transition is a first-class UI element with evidence, pass/fail status, and drill-down. If the user can't see the gate, they can't trust the pipeline.

4. **Intervene, don't micromanage.** Controls exist for steering (pause, retry, redirect) but the default is autonomous flow. The UI should make intervention easy without making it necessary.

5. **Evidence everywhere.** Every decision, every gate result, every cost — traceable and visible. No black boxes.

6. **Progressive disclosure.** The top-level view is a clean pipeline rail. Drill down for stage details. Drill deeper for agent logs. Don't overwhelm with information.

7. **Keyboard-first, mouse-friendly.** Following Linear's lead — fast keyboard navigation with mouse as fallback.

---

## 4. Information Architecture

### Primary Views

```
Dashboard (home)
├── Pipeline Rail            — Real-time 9-stage pipeline overview
├── Planning Board           — Issue intake, intent editing, risk assessment
├── Task Explorer            — All TaskPackets with filtering/search
├── Live Activity            — Real-time agent execution streams
├── Gate Inspector           — Gate results, evidence, pass rates
├── Cost & Budget            — Spend tracking, projections, alerts
├── Trust Configuration      — Trust tier rules, audit log
├── Reputation & Outcomes    — Agent performance, learning signals
└── Settings                 — GitHub sync, model gateway, notifications
```

### Navigation Model

- **Top bar:** Global search, active task count, cost ticker, notification bell
- **Left sidebar:** Primary view navigation (icons + labels, collapsible)
- **Main content:** Selected view with contextual panels
- **Right panel:** Detail/inspector panel (slides in on selection)
- **Bottom bar:** Active TaskPacket minimap (shows all in-flight work)

---

## 5. Document Suite

This vision is broken into five detailed design specifications:

| Document | Scope | Key Features |
|----------|-------|--------------|
| [01-PLANNING-EXPERIENCE.md](01-PLANNING-EXPERIENCE.md) | Issue intake, Intent Specification editor, complexity/risk dashboard, expert routing preview, roadmap & backlog views | Interactive planning before execution |
| [02-PIPELINE-VISUALIZATION.md](02-PIPELINE-VISUALIZATION.md) | Pipeline rail, TaskPacket timeline, live agent activity stream, gate inspector, loopback visualization | Making the pipeline visible and explorable |
| [03-INTERACTIVE-CONTROLS.md](03-INTERACTIVE-CONTROLS.md) | Trust tier configuration, pipeline steering (pause/retry/redirect/abort), budget governance, reputation dashboard | Steering the pipeline without micromanaging |
| [04-GITHUB-INTEGRATION-ANALYTICS.md](04-GITHUB-INTEGRATION-ANALYTICS.md) | Bidirectional GitHub Projects sync, PR evidence explorer, issue import, analytics dashboards, webhook real-time bridge | Deep GitHub integration and operational metrics |
| [05-TECHNOLOGY-ARCHITECTURE.md](05-TECHNOLOGY-ARCHITECTURE.md) | Frontend stack, real-time data flow, API contracts, component architecture, deployment model, migration path from current admin panel | How to build it |
| [06-BACKEND-REQUIREMENTS.md](06-BACKEND-REQUIREMENTS.md) | All backend work required to power the frontend: SSE/NATS bridge, event emission, dashboard API, Temporal signals, data model changes | What the backend needs to build (83 stories) |
| [07-THESTUDIO-UI-UX-STYLE-GUIDE.md](07-THESTUDIO-UI-UX-STYLE-GUIDE.md) | Formal UI/UX standards and single source of truth for frontend visual + interaction patterns across Admin Console and Pipeline app | Keep visuals and behavior consistent across all frontend surfaces |

---

## 6. User Personas

### Primary: Solo Developer / Small Team Lead

- Runs TheStudio against their own repos
- Wants to see what's happening, understand costs, and maintain quality
- Spends most time in Planning Board and Pipeline Rail
- Needs to trust the system before increasing autonomy

### Secondary: DevOps / Platform Engineer

- Configures trust tiers, budget limits, model routing
- Monitors pipeline health across multiple repos
- Spends most time in Cost & Budget, Trust Configuration, Gate Inspector

### Tertiary: Reviewer / Stakeholder

- Reviews draft PRs produced by the pipeline
- Wants evidence summaries and quality signals
- Spends most time in PR Evidence Explorer and Gate Inspector

---

## 7. Success Metrics

| Metric | Target | How Measured |
|--------|--------|--------------|
| Pipeline visibility | Developer can identify stage of any TaskPacket in < 3 seconds | User testing |
| Planning engagement | 80%+ of tasks have developer-reviewed Intent Specs | Intent review rate |
| Gate transparency | Every gate failure has a visible, actionable explanation | Gate inspector completeness |
| Trust tier adoption | Developers increase trust tier within 2 weeks of use | Tier change audit log |
| Cost awareness | Developer can predict cost of a task within 30% before execution | Cost projection accuracy |
| Time-to-intervention | Developer can pause/redirect a pipeline in < 10 seconds | UI interaction timing |

---

## 8. Phasing Strategy

> **Note:** Each phase includes both frontend AND backend work. Backend requirements are tracked in [06-BACKEND-REQUIREMENTS.md](06-BACKEND-REQUIREMENTS.md) (83 stories). Backend and frontend for each phase run mostly in series for a solo developer.

### Phase 0: Frontend Scaffolding + SSE Proof-of-Concept (~2-3 weeks)
- Vite + React + Zustand + Tailwind project scaffolding
- SSE-over-NATS bridge (backend: 7 stories)
- Minimal pipeline status page that proves real-time events work end-to-end
- **Exit criteria:** Browser displays live stage transitions from a real Temporal workflow
- **This phase validates the entire architecture. Do not proceed to Phase 1 without it.**

### Phase 1: Pipeline Visibility (~8-10 weeks incl. backend)
- **MVP:** Pipeline Rail with real-time stage status + TaskPacket list + Gate result cards
- **Full:** TaskPacket Timeline, Live Activity Stream, Loopback Visualization, Minimap
- Backend: SSE events from all stages, dashboard API, activity persistence (14 stories)

### Phase 2: Planning Experience (~8-10 weeks incl. backend)
- **MVP:** Triage queue (accept/reject) + Intent Spec viewer (read-only, approve/reject)
- **Full:** Intent editor, complexity dashboard, expert routing preview, backlog board, manual task creation
- Backend: Triage status, intent API, workflow wait points, routing API (18 stories)

### Phase 3: Interactive Controls (~10-12 weeks incl. backend)
- **MVP:** Pause/abort actions + budget dashboard (read-only)
- **Full:** Trust tier rule builder, retry/redirect, budget alerts, notifications
- Backend: Temporal signal handlers, trust rule engine, budget config, notifications (24 stories)

### Phase 4: GitHub Deep Integration (~5-7 weeks incl. backend)
- **MVP:** Issue import + PR evidence viewer
- **Full:** Bidirectional GitHub Projects sync, pipeline comments on issues, webhook bridge
- Backend: GitHub APIs, project sync, comment generation (12 stories)

### Phase 5: Analytics & Learning (~4-5 weeks incl. backend)
- **MVP:** Throughput chart + stage bottleneck analysis
- **Full:** Category breakdown, failure analysis, reputation dashboard, drift detection
- Backend: Analytics queries, drift computation (8 stories)

**Total estimated calendar time:** ~38-47 weeks (~9-12 months) for a solo developer. This is the full scope — MVP-only cuts per phase reduce this significantly.

---

## 9. Non-Goals (Explicit Exclusions)

These items are intentionally OUT OF SCOPE for this initiative:

1. **Mobile app.** The dashboard is desktop-first. Responsive tablet support is a stretch goal. A native mobile app is out of scope.
2. **Multi-repo management.** The dashboard manages one TheStudio instance connected to one primary repo. Multi-repo switching is deferred to Phase 5+ at earliest.
3. **Multi-user RBAC.** Phases 1-3 use the same single-user auth as the existing admin panel. Role-based access control is out of scope until Phase 4+.
4. **Admin panel replacement.** The existing Jinja-based admin panel continues to operate at `/admin/*`. The new dashboard runs at `/dashboard/*`. No admin features are removed or migrated.
5. **Data migration.** No existing data is migrated between systems. The dashboard reads the same PostgreSQL database the admin panel uses.
6. **External notification integrations.** Slack, Discord, email, or webhook notifications are Phase 4+ considerations, not committed scope.
7. **Custom themes.** The dashboard ships with dark mode (primary) and light mode (secondary). No custom theme builder.
8. **Plugin/extension system.** No plugin architecture for third-party dashboard extensions.
9. **Real-time collaboration.** No multi-user cursors, presence indicators, or shared editing. Single-user dashboard.
10. **GitLab support.** GitHub only. GitLab integration is a separate future initiative.

---

## 10. Open Questions

1. **SPA vs enhanced templates?** Current admin uses Jinja + HTMX. A rich pipeline UI likely needs React/Vite SPA. Do we replace the admin or run them side-by-side? → See [05-TECHNOLOGY-ARCHITECTURE.md](05-TECHNOLOGY-ARCHITECTURE.md)

2. **Multi-repo support?** Current design assumes one repo per TheStudio instance. Should the UI support switching between repos? → Defer to Phase 5.

3. **Mobile/responsive?** Is the pipeline UI primarily a desktop experience or does it need mobile views? → Desktop-first, responsive for tablets.

4. **Authentication?** The current admin panel has basic auth. A richer UI may need proper user accounts with roles. → Defer to Phase 3 (trust tiers need identity).

5. **Notifications?** Slack/Discord/email integration for gate failures, cost alerts, PR ready? → Defer to Phase 4.

---

## 11. References

### Competitor Documentation
- [Devin Interactive Planning](https://docs.devin.ai/work-with-devin/interactive-planning)
- [Devin Session Tools](https://docs.devin.ai/work-with-devin/devin-session-tools)
- [Factory AI Command Center](https://factory.ai)
- [Codegen 3.0 Analytics](https://docs.codegen.com/capabilities/analytics)
- [Aperant / Auto Claude](https://github.com/AndyMik90/Aperant)

### GitHub Platform
- [GitHub Projects v2 API](https://docs.github.com/en/issues/planning-and-tracking-with-projects/automating-your-project/using-the-api-to-manage-projects)
- [GitHub Agentic Workflows](https://github.github.com/gh-aw/)
- [GitHub Copilot Workspace](https://githubnext.com/projects/copilot-workspace)
- [IssueOps Documentation](https://issue-ops.github.io/docs/)

### Visualization
- [Temporal UI Timeline View](https://temporal.io/blog/lets-visualize-a-workflow)
- [Temporal UI Redesign](https://temporal.io/blog/the-dark-magic-of-workflow-exploration)
- [Running GitHub Actions through Temporal](https://temporal.io/blog/running-github-actions-temporal-guide)

### Open Source
- [Mission Control (builderz-labs)](https://github.com/builderz-labs/mission-control)
- [Plane.so](https://plane.so)
- [temporal-flow-web](https://github.com/itaisoudry/temporal-flow-web)

### Industry Analysis
- [Anthropic 2026 Agentic Coding Trends Report](https://resources.anthropic.com/hubfs/2026%20Agentic%20Coding%20Trends%20Report.pdf)
- [GitHub Agentic Workflows - InfoQ](https://www.infoq.com/news/2026/02/github-agentic-workflows/)
