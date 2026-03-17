# Epic 24 — Chat Interface for Approval Workflows: Give Reviewers Context and Conversation Before They Sign Off

**Author:** Saga
**Date:** 2026-03-13
**Status:** Meridian Reviewed — Conditional Pass (2026-03-16)
**Target Sprint:** Multi-sprint (estimated 2-3 sprints after Epic 22 completes)
**Prerequisites:** Epic 21 (Human Approval Wait States) — complete. Epic 22 (Execute Tier) — complete.

---

## 1. Title

Chat Interface for Approval Workflows — Build a scoped review experience where human reviewers can see aggregated evidence, ask questions about proposed changes, and approve or reject from a dedicated interface with full audit trail and multi-channel notifications.

## 2. Narrative

TheStudio has a durable human approval wait state. When a TaskPacket reaches `AWAITING_APPROVAL` status for Suggest or Execute tier repos, the Temporal workflow posts a GitHub comment and waits up to 7 days for an `approve_publish` signal. There is an API endpoint at `POST /api/tasks/{id}/approve` that sends the signal. The machinery works.

The human experience does not.

**The reviewer gets a GitHub comment and a prayer.** The comment says "this needs approval." It does not show the intent specification, QA results, verification outcomes, evidence bundle, or diff summary in a structured, navigable format. The reviewer has to open the PR, read raw diffs, cross-reference the issue, and mentally reconstruct what the agent did and why. For a Suggest-tier repo where the whole point is human oversight, this is asking the reviewer to do the agent's job.

**There is no way to ask questions.** A reviewer who sees a modified file and thinks "why did you touch this?" has no recourse except to reject and re-run the entire pipeline. There is no conversational channel between the human and the context that produced the changes. The reviewer either trusts the evidence or throws it out. There is no middle ground.

**There is no structured rejection.** The rejection path does not exist as an API endpoint. To reject, you either let the 7-day timer expire (unacceptable) or hack around the approval endpoint. There is no required reason, no audit trail of why a task was rejected, and no signal back to the outcome pipeline.

**Notifications are GitHub-only.** The approval request lands as a GitHub comment. If the reviewer's workflow lives in Slack, they will not see it until they happen to check GitHub. The approval wait state has a 7-day timeout, but if the human never sees the notification, the timeout is not a safety net — it is the expected outcome.

This epic adds a chat-based approval interface. Not a general-purpose chat. Not a chatbot. A scoped review experience where:

1. The reviewer sees everything they need — intent, QA results, verification results, evidence highlights, diff summary — in one place.
2. The reviewer can ask questions about the changes, and an LLM with full review context answers them.
3. The reviewer approves or rejects with a single action, and the existing Temporal signal fires.
4. Every interaction is persisted for audit.
5. Notifications go where the reviewer already works — GitHub first, Slack second, more channels later.

The chat does not change the pipeline. It does not add a new approval mechanism. It is a UI layer on top of the existing `approve_publish` signal and `AWAITING_APPROVAL` wait state. The Temporal workflow does not know or care whether the signal came from the chat interface, the raw API, or a Slack button.

### Why Now

Epic 21 built the wait state. Epic 22 built the Execute tier. Both are complete. The Execute tier auto-merges PRs after approval — meaning the approval decision has real consequences. A reviewer approving an Execute-tier task is authorizing code to merge. They need more than a GitHub comment to make that decision responsibly.

The compliance case is straightforward: if TheStudio auto-merges code, the approval audit trail must show that the reviewer had access to the evidence and made an informed decision. "They got a GitHub comment" is not that.

## 3. References

| Artifact | Location |
|----------|----------|
| Approval API (existing) | `src/api/approval.py` |
| Pipeline workflow (approval wait state) | `src/workflow/pipeline.py` |
| Evidence comment formatting | `src/publisher/evidence_comment.py` |
| Admin UI router | `src/admin/ui_router.py` |
| RBAC system | `src/admin/rbac.py` |
| Model Gateway | `src/admin/model_gateway.py` |
| TaskPacket model | `src/models/taskpacket.py` |
| TaskPacket CRUD | `src/models/taskpacket_crud.py` |
| Intent Specification model | `src/intent/intent_spec.py` |
| QA Agent / QA result | `src/qa/qa_agent.py` |
| Verification Gate | `src/verification/gate.py` |
| Evidence Bundle | `src/agent/evidence.py` |
| DB base and connection | `src/db/base.py`, `src/db/connection.py` |
| Settings | `src/settings.py` |
| Coding standards | `thestudioarc/20-coding-standards.md` |
| Architecture overview | `thestudioarc/00-overview.md` |
| System runtime flow | `thestudioarc/15-system-runtime-flow.md` |
| Epic 21 (Approval Wait States) | `docs/epics/epic-21-human-approval-wait-states.md` |
| Epic 22 (Execute Tier) | `docs/epics/epic-22-execute-tier-end-to-end.md` |

## 4. Acceptance Criteria

### Review Context

1. **`ReviewContext` model exists.** `src/approval/review_context.py` contains a Pydantic model that aggregates: TaskPacket summary (id, repo, status, tier), intent specification (goal, constraints, acceptance criteria), QA result summary (passed/failed, defect count, categories), verification result summary (checks with pass/fail), evidence bundle highlights (files changed, line counts, agent summary), diff summary (files added/modified/removed, total lines), and the repo trust tier.

2. **`build_review_context()` assembles from DB.** An async function queries the TaskPacket, related intent spec, QA results, verification results, and evidence bundle, then returns a populated `ReviewContext`. Returns `None` if the TaskPacket does not exist or is not in `AWAITING_APPROVAL` status.

### Chat Persistence

3. **`ApprovalChat` SQLAlchemy model exists.** `approval_chat` table with columns: `id` (UUID PK), `taskpacket_id` (FK to taskpackets), `created_by` (str), `status` (enum: active, resolved, expired), `created_at`, `resolved_at`. One active chat per TaskPacket (unique constraint on taskpacket_id + status=active).

4. **`ApprovalChatMessage` SQLAlchemy model exists.** `approval_chat_message` table with columns: `id` (UUID PK), `chat_id` (FK to approval_chat), `role` (enum: user, assistant, system), `content` (text), `created_at`. Ordered by created_at.

5. **Alembic migration exists.** Creates both tables with proper FKs, indexes, and constraints.

6. **CRUD functions exist.** `create_chat`, `get_chat_by_taskpacket`, `add_message`, `get_messages`, `resolve_chat`, `expire_chat` in `src/approval/chat_crud.py`.

### Chat API

7. **`GET /api/tasks/{id}/review` returns context + history.** Response includes `ReviewContext` and the full chat message history. Returns 404 if TaskPacket not found, 409 if not in `AWAITING_APPROVAL`. Creates the chat thread on first access if none exists.

8. **`POST /api/tasks/{id}/review/messages` sends a message.** Accepts `{ "content": "..." }`, persists the user message, calls the Model Gateway (balanced class) with the full `ReviewContext` as system context plus chat history, persists the assistant response, returns the assistant message. The LLM can answer questions about the changes but cannot modify the pipeline or approve/reject.

9. **`POST /api/tasks/{id}/reject` rejects with reason.** Accepts `{ "rejected_by": "...", "reason": "..." }`. Sends a rejection signal to the Temporal workflow. Resolves the chat thread. Records the rejection in audit. Returns 409 if not in `AWAITING_APPROVAL`.

10. **Existing `POST /api/tasks/{id}/approve` resolves chat.** Enhanced to also resolve the associated chat thread (if one exists) when approval is signaled.

11. **All endpoints require RBAC authentication.** Minimum role: `operator` for approve/reject, `viewer` for GET review context and POST messages.

### Notification Channels

12. **`NotificationChannel` abstract base exists.** `src/approval/channels/base.py` defines methods: `notify_awaiting_approval(context: ReviewContext)`, `notify_approved(taskpacket_id, approved_by, channel)`, `notify_rejected(taskpacket_id, rejected_by, reason, channel)`, `notify_timeout(taskpacket_id)`.

13. **`GitHubChannel` implementation exists.** Enhances the existing GitHub comment posted by `post_approval_request_activity` to include: a link to the review UI, structured summary of intent and QA results, and instructions for the reviewer. The existing comment format is extended, not replaced.

14. **`post_approval_request_activity` uses channels.** The Temporal activity resolves configured channels and calls `notify_awaiting_approval` on each. Channel configuration is in settings.

### Observability and Audit

15. **OpenTelemetry spans cover chat interactions.** Spans for: review context assembly, chat message send, LLM response, approve action, reject action. All spans include `taskpacket_id` and `correlation_id`.

16. **Approval decisions include chat metadata.** The evidence comment (on the PR) includes: "Approved/Rejected by {user} via {channel} after {n} review messages." The audit log records the full decision context.

17. **NATS JetStream signals emitted.** `approval.approved` and `approval.rejected` signals are published for the outcome pipeline, including decision metadata.

### 4b. Top Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| LLM gives incorrect answers about changes, reviewer trusts them | High | High — wrong approval decision | System prompt explicitly states LLM is summarizing existing evidence, not making claims. Disclaimer in UI. ReviewContext is shown alongside LLM responses so reviewer can verify. |
| Review context assembly is slow due to multiple DB queries | Medium | Medium — poor UX on first load | Single optimized query with joins. Cache ReviewContext for active approval sessions. |
| Chat thread grows unbounded, inflating LLM context | Medium | Low — cost increase | Cap at 50 messages per thread. Truncate oldest messages from LLM context window while preserving full persistence. |
| Slack integration requires OAuth and webhook infrastructure | Medium | Medium — deployment complexity | Slack is Story 24.5, explicitly optional. GitHub channel is sufficient for MVP. |
| Rejection signal does not exist in Temporal workflow | Low | High — reject button does nothing | Add `reject_publish` signal to workflow alongside existing `approve_publish`. Mirror the pattern exactly. |
| Reviewer never opens the review UI, approval times out anyway | Medium | Medium — feature unused | Slack notifications (24.5) with action buttons reduce friction. Measure review UI open rate. |

## 5. Constraints & Non-Goals

### Constraints

- **No changes to Temporal workflow orchestration.** The workflow already has `approve_publish` signal handling. This epic adds a `reject_publish` signal using the identical pattern. No other workflow changes.
- **No changes to pipeline steps.** The chat is a UI layer. It does not insert a new step, modify gate behavior, or alter the TaskPacket lifecycle beyond what the approval signal already does.
- **Chat is read-only with respect to pipeline state.** The LLM in the chat cannot trigger actions, modify the TaskPacket, or influence the pipeline. It can only read and explain existing artifacts.
- **One active chat per TaskPacket.** No concurrent chat threads for the same approval. Creating a new chat when one exists returns the existing one.
- **Model Gateway for all LLM calls.** Chat LLM calls route through the Model Gateway with step `approval_chat` and model class `balanced`.
- **RBAC on all endpoints.** No unauthenticated access to review context, chat, or approval actions.
- **Python 3.12+, existing dependencies.** No new frameworks. FastAPI, SQLAlchemy async, Pydantic, existing RBAC — all already in the stack.

### Non-Goals

- **Not building a general-purpose chat system.** The chat is scoped to a specific TaskPacket's approval workflow. It has no threads, no channels, no DMs, no message editing, no reactions.
- **Not building a web frontend.** This epic delivers API endpoints. A frontend (React, HTMX, or otherwise) is a separate epic. The admin UI may get a simple template-based view, but a rich SPA is out of scope.
- **Not implementing Teams, Discord, or email channels.** GitHub is the primary channel. Slack is optional (Story 24.5). Other channels are future work.
- **Not adding chat to non-approval workflows.** The chat is specifically for the approval wait state. Extending conversational interfaces to other pipeline stages is a different epic.
- **Not training or fine-tuning a model for review Q&A.** The chat uses the standard Model Gateway with a well-crafted system prompt. No custom models, no RAG, no embeddings.
- **Not replacing the existing approval API.** `POST /api/tasks/{id}/approve` continues to work exactly as it does today. The chat interface calls the same endpoint. External integrations that use the API directly are unaffected.

## 6. Stakeholders & Roles

| Role | Who | Responsibility |
|------|-----|----------------|
| Epic Owner | Platform Lead (TBD — assign before sprint start) | Accepts epic scope, reviews AC completion |
| Tech Lead | Backend Engineer (TBD — assign before sprint start) | Owns chat API, notification channels, DB schema |
| QA | QA Engineer (TBD — assign before sprint start) | Validates AC, tests approval flows end-to-end |
| Saga | Epic Creator | Authored this epic; available for scope clarification |
| Meridian | VP Success | Reviews this epic before commit; reviews sprint plans |

## 7. Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Review context available | 100% of AWAITING_APPROVAL tasks have ReviewContext | DB query: tasks in AWAITING_APPROVAL with ReviewContext assembled |
| Chat adoption | > 30% of approvals include at least 1 chat message within 30 days of launch | `approval_chat_message` count per resolved chat / total approvals |
| Approval time reduction | Median approval time < 4 hours (from current ~unknown baseline) | Temporal workflow: time between AWAITING_APPROVAL entry and approve signal |
| Timeout rate reduction | < 10% of approval waits expire (7-day timeout) | Temporal workflow: approval_timeout outcomes / total AWAITING_APPROVAL entries |
| Rejection with reason | 100% of rejections include a reason | `approval.rejected` signals with non-empty reason / total rejections |
| Audit completeness | 100% of approval decisions have channel + message count in evidence comment | Evidence comment parsing on published PRs |
| Notification delivery | > 95% of approval requests trigger at least one channel notification | `notify_awaiting_approval` call success rate |

## 8. Context & Assumptions

### Systems Affected

| System | Impact |
|--------|--------|
| `src/approval/review_context.py` | **New file** — ReviewContext model and builder |
| `src/approval/chat_models.py` | **New file** — ApprovalChat, ApprovalChatMessage SQLAlchemy models |
| `src/approval/chat_crud.py` | **New file** — CRUD functions for chat persistence |
| `src/approval/chat_router.py` | **New file** — FastAPI endpoints for review + chat |
| `src/approval/channels/__init__.py` | **New file** — Channel adapter package |
| `src/approval/channels/base.py` | **New file** — Abstract NotificationChannel |
| `src/approval/channels/github.py` | **New file** — GitHub notification channel |
| `src/approval/channels/slack.py` | **New file** — Slack notification channel (optional) |
| `src/api/approval.py` | **Modified** — Enhanced to resolve chat thread on approval |
| `src/workflow/pipeline.py` | **Modified** — Add `reject_publish` signal handler |
| `src/workflow/activities.py` | **Modified** — `post_approval_request_activity` uses channel adapters |
| `src/publisher/evidence_comment.py` | **Modified** — Include approval metadata in evidence comment |
| `src/settings.py` | **Modified** — Add approval chat and channel settings |
| `src/app.py` | **Modified** — Register approval chat router |
| `alembic/versions/` | **New file** — Migration for approval_chat and approval_chat_message tables |

### Assumptions

1. **The Model Gateway supports an `approval_chat` step.** The gateway's `select_model()` accepts arbitrary step strings. If a routing rule does not exist for `approval_chat`, it falls back to the default balanced-class provider. No gateway changes are required.
2. **The reviewer has an authenticated session.** The RBAC system (`get_current_user_id`) works for API calls. The chat endpoints use the same auth mechanism as the existing admin and approval APIs.
3. **The LLM can answer questions about code changes given structured context.** The system prompt provides ReviewContext (intent, QA results, verification results, diff summary). The LLM reasons about this context. It does not have access to the actual repository or file contents beyond the summary.
4. **A rejection signal is straightforward to add.** The Temporal workflow already handles `approve_publish` via `workflow.signal`. Adding `reject_publish` follows the identical pattern — set a flag, unblock `wait_condition`, record the rejector.
5. **Slack Block Kit is sufficient for interactive notifications.** Slack's `actions` block supports buttons that can trigger HTTP callbacks. The approve/reject buttons in Slack call the existing API endpoints via the Slack interactivity webhook.
6. **Chat message volume is low.** Reviewers ask 1-5 questions before deciding. The 50-message cap per thread is generous. If usage patterns differ, the cap is configurable.
7. **PostgreSQL handles chat persistence without a separate store.** Chat messages are small text records. The volume is bounded (one chat per TaskPacket, max 50 messages). No need for Redis, MongoDB, or a dedicated chat database.

### Dependencies

- **Upstream:** Epic 21 (Approval Wait States) — complete. Epic 22 (Execute Tier) — complete. Both provide the `AWAITING_APPROVAL` state and `approve_publish` signal that this epic builds on.
- **Downstream unblocks:** A frontend epic for rich review UI. Additional notification channels (Teams, email). Approval analytics dashboard.

---

## Story Map

Stories are ordered as vertical slices. Story 24.1 and 24.2 are foundational (data model). Story 24.3 delivers the core API. Story 24.4 wires notifications. Story 24.5 is optional (Slack). Story 24.6 adds observability.

### Sprint 1: Foundation + Core API

| # | Story | Size | Value | Files |
|---|-------|------|-------|-------|
| 24.1 | **Approval Review Context Model** | M | Reviewers see everything in one place | `src/approval/review_context.py`, `tests/approval/test_review_context.py` |
| 24.2 | **Approval Chat Thread Persistence** | M | Chat history survives restarts | `src/approval/chat_models.py`, `src/approval/chat_crud.py`, `alembic/versions/xxxx_approval_chat.py`, `tests/approval/test_chat_crud.py` |
| 24.3 | **Approval Chat API Endpoints** | L | Reviewers can interact before approving | `src/approval/chat_router.py`, `src/api/approval.py`, `src/workflow/pipeline.py`, `src/app.py`, `tests/approval/test_chat_router.py` |

### Sprint 2: Channels + Observability

| # | Story | Size | Value | Files |
|---|-------|------|-------|-------|
| 24.4 | **Notification Channel Adapter (Base + GitHub)** | M | Reviewers get structured notifications where they work | `src/approval/channels/base.py`, `src/approval/channels/github.py`, `src/workflow/activities.py`, `tests/approval/test_channels.py` |
| 24.5 | **Slack Notification Channel (Optional)** | M | Slack-native teams can approve without leaving Slack | `src/approval/channels/slack.py`, `src/settings.py`, `tests/approval/test_slack_channel.py` |
| 24.6 | **Approval Chat Observability + Audit** | M | Full audit trail for compliance | `src/approval/chat_router.py`, `src/publisher/evidence_comment.py`, `src/settings.py`, `tests/approval/test_observability.py` |

---

## Meridian Review Status

**Round 1: Conditional Pass (2026-03-16)**

**Verdict:** 5/7 questions PASS, 2 CONDITIONAL. Well-structured epic with strong ACs and non-goals.

| # | Question | Verdict |
|---|----------|---------|
| 1 | Goal specific enough to test? | PASS |
| 2 | AC testable at epic scale? | PASS |
| 3 | Non-goals explicit? | PASS |
| 4 | Dependencies identified with owners/dates? | GAP |
| 5 | Success metrics measurable? | GAP |
| 6 | AI agent can implement without guessing? | PASS |
| 7 | Narrative compelling? | PASS |

**Must fix before commit:**

| # | Issue | Status | Resolution |
|---|-------|--------|------------|
| 1 | No rejection status defined in TaskPacket `ALLOWED_TRANSITIONS`. AC #9 references rejection signal but no `REJECTED` status exists. Must decide: `FAILED` or new `REJECTED` status. | Open | — |
| 2 | Success metrics lack baselines. "Approval time median < 4 hours" set against "~unknown" baseline. "Timeout rate < 10%" has no current measurement. Data exists in Temporal workflow history — measure before setting targets. | Open | — |
| 3 | All stakeholder roles TBD. No named owners or assignment dates. | Open | — |
| 4 | `reject_publish` signal does not exist in `src/workflow/`. Current wait condition is `self._approved` — needs to change to `self._approved or self._rejected`. Should be elevated from risk to explicit AC. | Open | — |
| 5 | Evidence comment edge case: what happens when approval occurs via raw API with no chat thread? AC #16 needs clarification. | Open | — |
