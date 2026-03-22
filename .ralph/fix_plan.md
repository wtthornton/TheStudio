# Fix Plan — TheStudio: Epic 37 — Phase 3: Interactive Controls & Governance

> Epic: `docs/epics/epic-37-phase3-interactive-controls.md`
> Status: NOT YET STARTED — Meridian review pending
> MVP Slices: 1 (Pause/Resume/Abort) + 4 (Budget Dashboard)
> Full Slices: 2 (Retry/Redirect), 3 (Trust Tier Config), 5 (Notifications)

---

## Epic 37 — Phase 3: Interactive Controls & Governance

### Slice 1: Pipeline Steering — Pause/Resume/Abort (MVP)

- [x] 37.1: Temporal signal handlers — pause_task and resume_task — `src/workflow/pipeline.py`. Add pause flag checked via `workflow.wait_condition()` before each activity. Pausing mid-activity waits for current activity to complete, then holds.
- [x] 37.2: Temporal signal handler — abort_task(reason) — `src/workflow/pipeline.py`, add PAUSED + ABORTED statuses to TaskPacket enum + transitions, store abort reason on TaskPacket metadata.
- [x] 37.3: Steering API endpoints — POST `/tasks/:id/pause`, `/resume`, `/abort` in `src/dashboard/steering.py`. Look up Temporal workflow ID, send signal. Return 202/404/409.
- [x] 37.4: Steering audit log model — `src/dashboard/models/steering_audit.py` with SteeringAuditLog (id, task_id, action enum, from_stage, to_stage, reason, timestamp, actor). Alembic migration + CRUD.
- [x] 37.5: Steering audit persistence in signal handlers — after each signal, persist audit entry via Temporal activity. Emit `pipeline.steering.action` event to NATS for SSE.
- [x] 37.6: Frontend — SteeringActionBar on TaskPacket detail — Pause/Resume toggle + Abort (with confirmation dialog + mandatory reason). Buttons disabled while action in flight. SSE updates state.
- [x] 37.7: Frontend — steering audit entries in TaskPacket timeline — wrench icon, action/reason/timestamp. GET `/tasks/:id/audit` endpoint.

### Slice 2: Pipeline Steering — Retry/Redirect

- [x] 37.8: Temporal signal handler — redirect_task(target_stage, reason) — set redirect flag, workflow loop re-enters at target stage after current activity completes. Validate target < current stage.
- [x] 37.9: Temporal signal handler — retry_stage — redirect to current stage, clear stage artifacts, re-enter.
- [x] 37.10: Steering API endpoints — POST `/tasks/:id/redirect` (body: target_stage + reason), POST `/tasks/:id/retry`. Validate target stage < current stage. Return 202/400.
- [x] 37.11: Frontend — RedirectModal (current stage, radio for valid earlier stages, required reason, warning about re-run scope) + RetryConfirmation dialog.

### Slice 3: Trust Tier Configuration

- [x] 37.12: Trust tier rule data model — `src/dashboard/models/trust_config.py`. TrustTierRule (id, priority, conditions JSON, assigned_tier, active, timestamps). SafetyBounds (max_auto_merge_lines, max_auto_merge_cost, max_loopbacks, mandatory_review_patterns). Migration.
- [x] 37.13: Task-level trust tier on TaskPacket — add `task_trust_tier` nullable field (observe/suggest/execute). Migration. Do NOT modify `src/reputation/tiers.py`.
- [x] 37.14: Trust tier rule evaluation engine — `src/dashboard/trust_engine.py`. Evaluate conditions (equals, less_than, greater_than, contains, matches_glob) against TaskPacket metadata. First match wins. Safety bounds override. Default tier fallback.
- [ ] 37.15: Trust tier CRUD API — GET/POST/PUT/DELETE `/trust/rules`, GET/PUT `/trust/safety-bounds`, GET/PUT `/trust/default-tier` in `src/dashboard/trust_router.py`.
- [ ] 37.16: Trust tier assignment at pipeline start — evaluate rule engine before first activity in Temporal workflow. Set `task_trust_tier` on TaskPacket. Emit `pipeline.trust_tier.assigned` event.
- [ ] 37.17: Frontend — TrustConfiguration settings panel + RuleBuilder (condition builder, tier assignment, priority, active toggle) + SafetyBoundsPanel + ActiveTierDisplay.
- [ ] 37.18: Trust tier audit log — log `trust_tier_assigned` / `trust_tier_overridden` to steering audit with matching rule ID, original tier, final tier.

### Slice 4: Budget Dashboard (MVP)

- [ ] 37.19: Budget API endpoints — `src/dashboard/budget_router.py`. GET `/budget/summary`, `/budget/history` (time series by model), `/budget/by-stage`, `/budget/by-model`. Source from existing ModelCallAudit + SpendReport.
- [ ] 37.20: Budget configuration API — GET/PUT `/budget/config`. Fields: daily_spend_warning, weekly_budget_cap, per_task_warning, pause_on_budget_exceeded, model_downgrade_on_approach, downgrade_threshold_percent. Persist to PostgreSQL. Migration.
- [ ] 37.21: Budget threshold checker — `src/dashboard/budget_checker.py`. Run after each cost_update event. Compare spend vs thresholds. If pause_on_budget_exceeded + cap breached → pause all active workflows. If downgrade → update model routing preference.
- [ ] 37.22: Frontend — BudgetDashboard view + SpendChart (stacked bar, Chart.js) + CostBreakdown (by-stage + by-model horizontal bars) + BudgetAlertConfig (threshold inputs + action toggles) + period selector (1d/7d/30d).
- [ ] 37.23: Per-task cost breakdown panel — add to TaskPacket detail view showing cost by stage and by model for that task.

### Slice 5: Notifications

- [ ] 37.24: Notification data model — `src/dashboard/models/notification.py`. Notification (id, type enum, title, message, task_id, read, created_at). Migration.
- [ ] 37.25: Notification API endpoints — `src/dashboard/notification_router.py`. GET `/notifications` (paginated, filterable, includes unread_count), PATCH `/notifications/:id/read`, POST `/notifications/mark-all-read`.
- [ ] 37.26: Notification generation from NATS — `src/dashboard/notification_generator.py`. JetStream consumer for `pipeline.gate.fail`, `pipeline.cost_update`, `pipeline.steering.action`, `pipeline.trust_tier.assigned`. Generate Notification records. Register as background task in app lifecycle.
- [ ] 37.27: Frontend — NotificationBell (top bar, unread count badge) + NotificationDropdown (New/Earlier sections, type icons, relative timestamps, mark-all-read) + NotificationItem (click-through to relevant view).
- [ ] 37.28: Settings activity log — SteeringActivityLog page with paginated, filterable table of all steering actions. GET `/steering/audit` endpoint.

---

## Completed Epics

- **Epic 36** — Phase 2: Planning Experience (29 stories across 4 slices COMPLETE)
- **Epic 35** — Phase 1: Pipeline Visibility (63 stories COMPLETE)
- **Epic 34** — Phase 0: SSE PoC + Frontend Scaffolding (14 stories COMPLETE)
- **Epics 0-33** — All prior epics COMPLETE
