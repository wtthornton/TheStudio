# Epic 7 — Platform Maturity (Phase 4)

> Saga — Epic Creator | Created: 2026-03-07

**Status:** Complete — Tool Hub, Model Gateway, Compliance Scorecard, Admin UI all delivered (Sprint 2: 5/5)

---

## 1. Title

**Platform Maturity: Tool Hub, Model Gateway, and Operational Targets**

---

## 2. Narrative

TheStudio has closed Phase 3 with a 60%+ single-pass success target enforced, 5 expert classes, 2 Service Context Packs, and a complete eval suite. The learning loop is closed; the quality bar is set.

Phase 4 moves the platform from "quality bar met" to "production-grade infrastructure." Two critical platform services are missing: the **Tool Hub** (governed MCP tooling for agents) and the **Model Gateway** (centralized LLM routing with budgets, fallbacks, and audit). Without these, agents make ad-hoc tool and model choices — undercutting determinism, cost control, and auditability.

Additionally, the Admin UI needs completion: **Policy & Guardrails Console**, **Model Spend Dashboard**, **Quarantine Operations**, and a **Repo Compliance Scorecard** that gates Execute-tier promotion. The compliance checker exists but has no UI integration or formal scorecard.

Finally, Phase 4 sets **operational targets** — reopen rate (<5%), lead time P95, and cycle time P95 — and makes them visible and tracked. These targets close the gap between "the system works" and "the system works predictably at scale."

---

## 3. References

- Architecture: `thestudioarc/25-tool-hub-mcp-toolkit.md` (Tool Hub)
- Architecture: `thestudioarc/26-model-runtime-and-routing.md` (Model Gateway)
- Architecture: `thestudioarc/23-admin-control-ui.md` (Admin UI full spec)
- Architecture: `thestudioarc/22-architecture-guardrails.md` (EffectiveRolePolicy)
- Roadmap: `thestudioarc/MERIDIAN-ROADMAP-AGGRESSIVE.md` (Phase 4, lines 166-191)
- Phase 3 closure: `docs/epics/EPIC-6-SPRINT-1-PROGRESS.md`
- Existing Admin UI: `src/admin/` (router, ui_router, rbac, audit, health, workflow_metrics, success_gate)
- Existing compliance: `src/compliance/` (checker, promotion)

---

## 4. Acceptance Criteria

### Tool Hub (MCP Gateway)

1. A `ToolCatalog` registry exists with tool suites, approval status (observe/suggest/execute), and versioning.
2. A `ToolProfile` configuration maps repo tiers to enabled tool suites.
3. Tool access is enforced by role + overlay + repo tier (EffectiveRolePolicy integration).
4. Every tool call is auditable: correlation_id, role, tool_suite, tool_name, outcome, duration.
5. At least 3 standard tool suites are defined (e.g., code-quality, context-retrieval, documentation).
6. Admin UI shows tool catalog, profiles per repo, and usage/error metrics.

### Model Gateway

7. A `ModelGateway` service routes LLM calls by workflow step, role, overlays, repo tier, and complexity.
8. Three model classes exist: FAST, BALANCED, STRONG — with routing rules per workflow step. Default mapping per `26-model-runtime-and-routing.md`: intake=FAST, context=FAST, intent=BALANCED, expert_routing=BALANCED, assembler=BALANCED, primary_agent=BALANCED, qa_eval=BALANCED. Role/overlay/tier overrides escalate to STRONG when risk flags or repeated failures warrant it.
9. Fallback chains execute automatically when a provider fails (same class first, then escalate).
10. Per-task and per-repo budget limits are enforced; exceeded budgets block further calls.
11. Every LLM call produces an audit record: correlation_id, step, provider, model, tokens, cost, latency, error_class.
12. Admin UI shows model spend by repo/step/provider, latency distribution, fallback rate, and error breakdown.

### Compliance Scorecard

13. A formal compliance scorecard evaluates repos against Execute-tier requirements. Scorecard checks: (a) branch protection rulesets enabled, (b) required reviewers configured for sensitive paths, (c) standard labels present, (d) Projects v2 fields configured, (e) evidence comment format validated on last 3 PRs, (f) idempotency guard active, (g) execution plane health = healthy. Pass = all checks green; any red check blocks promotion.
14. Execute-tier promotion is blocked unless the scorecard passes.
15. Scorecard results are visible in Admin UI with remediation guidance.

### Admin UI Completion

16. Policy & Guardrails Console shows mandatory coverage rules, policy violations, and repo compliance status.
17. Quarantine Operations UI shows quarantined signals with replay capability.
18. Model Spend Dashboard shows spend, latency, fallback, and error data per repo/step/provider.
19. Merge Mode Controls display and allow setting merge mode per repo.

### Operational Targets

20. Reopen rate target (<5% within 30 days) is defined, tracked, and visible in metrics.
21. Lead time P95 (intake to PR opened) is tracked and visible.
22. Cycle time P95 (PR opened to merge-ready) is tracked and visible.
23. All three targets are surfaced in the Admin UI metrics dashboard.

---

## 5. Constraints & Non-Goals

### Constraints

- Tool Hub governs access but does not host MCP servers — it is a policy/catalog layer, not a container runtime.
- Model Gateway is the only path for LLM calls — agents must not hold provider credentials directly.
- Compliance scorecard uses existing repo profile data; no new external integrations required.
- Admin UI uses existing HTMX + Jinja2 + Tailwind pattern — no frontend framework change.
- All new services must have unit tests with >80% coverage.

### Non-Goals

- **Actual MCP server deployment** — Tool Hub defines the catalog and policy; Docker MCP Toolkit hosting is out of scope.
- **Real LLM provider integration** — Model Gateway defines routing, budgets, and audit; actual API calls to Anthropic/OpenAI are out of scope for this epic.
- **10+ repos registered** — The roadmap mentions 10+ repos or 2+ execution planes as a scale target, but actual repo onboarding depends on external teams. The platform must support it; we don't need 10 real repos.
- **OpenClaw sidecar** — Documented as optional; not in scope.
- **Claude Code headless integration** — Documented in Model Gateway spec as optional; not in scope.

---

## 6. Stakeholders & Roles

| Role | Responsibility |
|------|---------------|
| Saga | Epic definition |
| Meridian | Epic and plan review |
| Helm | Sprint planning and execution |
| Platform team | Implementation |
| Admin operators | Primary users of Admin UI completion |

---

## 7. Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Tool catalog entries | >= 3 suites, >= 10 tools registered | `GET /admin/tools/catalog` |
| Model audit coverage | 100% of gateway calls have audit records | Count of calls vs audit records |
| Compliance scorecard pass rate | Queryable per repo | `GET /admin/repos/{id}/compliance` |
| Reopen rate visibility | Tracked with <5% target displayed | Admin UI metrics |
| Lead time P95 visibility | Tracked and displayed | Admin UI metrics |
| Admin UI page coverage | All Phase 4 consoles accessible | Manual verification |
| Test count | >= 80 new tests | pytest count |

---

## 8. Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Tool Hub and Model Gateway are large services — scope creep | Sprint overrun | Build schema and service layers first (Sprint 1), then API and UI (Sprint 2). Cut UI polish before cutting core logic. |
| Model Gateway routing rules are complex — edge cases in fallback chains | Bugs in production routing | Start with simple step-based routing; overlay/complexity escalation in later sprint. Comprehensive unit tests for fallback chains. |
| Compliance scorecard requirements not fully specified | Vague pass/fail criteria | Use the checklist from `23-admin-control-ui.md` (rulesets, required reviewers, evidence format, execution plane health) as the definitive list. |
| Admin UI scope is large (6+ new pages/consoles) | UI work dominates sprint | Reuse existing HTMX partial pattern; prioritize data-heavy pages (model spend, compliance) over interactive pages (quarantine replay). |
| Operational targets (reopen <5%, lead time P95) may not have enough data | Targets set but unmeasurable | Design for "insufficient data" state (like success gate); targets become enforced when sample count exceeds minimum. |

---

## Context & Assumptions

- Phase 3 is complete (7/7 deliverables, Epic 6 Sprint 1 closed).
- Admin UI core is built: fleet dashboard, repo management, workflow console, RBAC, audit log, metrics dashboard with success gate.
- Existing services to extend: `MetricsService`, `SuccessGateService`, `AuditService`, `RBACService`, `ComplianceChecker`.
- Database is SQLite via SQLAlchemy (can be swapped later); new tables needed for tool catalog, model audit, routing rules, budgets.
- The codebase uses FastAPI with dependency injection, Pydantic models, and pytest for testing.
