# Story 24.3 — Approval Chat API Endpoints

> **As a** human reviewer,
> **I want** API endpoints to view review context, ask questions about changes, and approve or reject,
> **so that** I can complete the approval workflow through a structured interface.

**Purpose:** This is the core value delivery of the epic. Without these endpoints, the review context model (24.1) and chat persistence (24.2) are infrastructure with no surface. This story connects the data layer to HTTP, adds the LLM-powered Q&A capability, adds the rejection endpoint, and enhances the existing approval endpoint to resolve chat threads.

**Intent:** Create FastAPI endpoints for review context retrieval, chat message exchange (with LLM response), rejection with reason, and enhance the existing approval endpoint. All endpoints are RBAC-protected.

**Points:** 8 | **Size:** L
**Epic:** 24 — Chat Interface for Approval Workflows
**Sprint:** 1 (Stories 24.1-24.3)
**Depends on:** 24.1 (ReviewContext), 24.2 (Chat persistence)

---

## Description

Four endpoints, one enhancement, and one workflow signal addition.

The chat message endpoint is the most complex: it persists the user message, builds an LLM prompt with the full ReviewContext as system context plus the chat history as conversation context, calls the Model Gateway for a balanced-class response, persists the assistant response, and returns it. The LLM is explicitly instructed that it cannot take actions — it can only explain, summarize, and answer questions about the existing evidence.

The rejection endpoint is new. The Temporal workflow needs a `reject_publish` signal (mirroring `approve_publish`). When received, the workflow unblocks from `wait_condition`, records the rejection, and returns failure with `rejection_reason = "rejected"`.

## Tasks

- [ ] Add `reject_publish` signal to `TheStudioPipelineWorkflow` in `src/workflow/pipeline.py`:
  - `self._rejected = False`, `self._rejected_by: str | None = None`, `self._rejection_reason: str | None = None`
  - `@workflow.signal async def reject_publish(self, rejected_by: str, reason: str, source: str) -> None`
  - Update `wait_condition` lambda: `lambda: self._approved or self._rejected`
  - After `wait_condition` unblocks, check `self._rejected` — if True, set `output.rejection_reason = "rejected"` and return
- [ ] Create `src/approval/chat_router.py`:
  - `router = APIRouter(prefix="/api/tasks", tags=["approval-chat"])`
  - **`GET /{taskpacket_id}/review`**:
    - Depends: `get_current_user_id` (RBAC — minimum viewer), `get_session`
    - Call `build_review_context(session, taskpacket_id)`
    - If None, return 404 (not found) or 409 (wrong status)
    - Call `get_chat_by_taskpacket(session, taskpacket_id)` or `create_chat(session, taskpacket_id, user_id)` if none exists
    - Call `get_messages(session, chat.id)`
    - Return `ReviewResponse(context=review_context, messages=messages, chat_id=chat.id)`
  - **`POST /{taskpacket_id}/review/messages`**:
    - Depends: `get_current_user_id` (RBAC — minimum viewer), `get_session`
    - Request body: `ChatMessageRequest(content: str)` — max 2000 chars
    - Validate TaskPacket is in AWAITING_APPROVAL
    - Get or create active chat
    - Check message count — if >= 50, return 429 (thread limit reached)
    - Persist user message via `add_message(session, chat.id, "user", content)`
    - Build LLM messages:
      - System: ReviewContext.to_prompt_context() + instructions ("You are a review assistant. Answer questions about the proposed changes using only the context provided. You cannot take actions, modify code, or approve/reject. Be precise and cite evidence.")
      - History: all chat messages as user/assistant turns
    - Call Model Gateway: `select_model(step="approval_chat", model_class="balanced", ...)`
    - Call LLM with messages
    - Persist assistant response via `add_message(session, chat.id, "assistant", response)`
    - Return `ChatMessageResponse(role="assistant", content=response, created_at=now)`
  - **`POST /{taskpacket_id}/reject`**:
    - Depends: `get_current_user_id` (RBAC — minimum operator), `get_session`
    - Request body: `RejectionRequest(rejected_by: str, reason: str)` — reason required, min 10 chars
    - Validate TaskPacket is in AWAITING_APPROVAL (same pattern as approve)
    - Send `reject_publish` signal to Temporal workflow
    - Resolve active chat thread if one exists
    - Log rejection
    - Return `RejectionResponse(status="rejected", taskpacket_id=..., reason=...)`
- [ ] Enhance `approve_task()` in `src/api/approval.py`:
  - After successful signal, resolve the active chat thread if one exists:
    ```python
    chat = await get_chat_by_taskpacket(session, task_uuid)
    if chat:
        await resolve_chat(session, chat.id)
    ```
- [ ] Register the chat router in `src/app.py`:
  - `from src.approval.chat_router import router as chat_router`
  - `app.include_router(chat_router)`
- [ ] Create response models in `src/approval/chat_router.py`:
  - `ReviewResponse`: context (ReviewContext), messages (list), chat_id (str)
  - `ChatMessageRequest`: content (str, max_length=2000)
  - `ChatMessageResponse`: role (str), content (str), created_at (datetime)
  - `RejectionRequest`: rejected_by (str), reason (str, min_length=10)
  - `RejectionResponse`: status (str), taskpacket_id (str), reason (str)
- [ ] Write tests in `tests/approval/test_chat_router.py`:
  - Test GET /review returns context + empty messages for new chat
  - Test GET /review returns existing chat + messages
  - Test GET /review returns 404 for missing TaskPacket
  - Test GET /review returns 409 for non-AWAITING_APPROVAL task
  - Test POST /messages persists user message and returns assistant response
  - Test POST /messages returns 429 when thread limit reached
  - Test POST /messages returns 409 for non-AWAITING_APPROVAL task
  - Test POST /reject sends signal and resolves chat
  - Test POST /reject requires reason (min 10 chars)
  - Test POST /reject returns 409 for non-AWAITING_APPROVAL task
  - Test approve_task resolves chat thread
  - Test reject_publish signal unblocks workflow
  - Mock LLM responses for message endpoint tests

## Acceptance Criteria

- [ ] GET /review returns ReviewContext + chat history
- [ ] POST /messages persists both user and assistant messages
- [ ] POST /messages calls Model Gateway with balanced class
- [ ] POST /messages enforces 50-message thread limit
- [ ] POST /reject requires reason and sends rejection signal
- [ ] reject_publish signal unblocks Temporal wait_condition
- [ ] Approval resolves chat thread
- [ ] Rejection resolves chat thread
- [ ] All endpoints enforce RBAC (viewer for read, operator for actions)
- [ ] Unit tests pass with mocked LLM and mocked Temporal

## Test Cases

| # | Scenario | Input | Expected Output |
|---|----------|-------|-----------------|
| 1 | First review access | GET /api/tasks/{id}/review | 200 with context + empty messages |
| 2 | Chat exchange | POST /api/tasks/{id}/review/messages with "Why this file?" | 200 with assistant response |
| 3 | Thread limit | POST message when 50 messages exist | 429 |
| 4 | Reject with reason | POST /api/tasks/{id}/reject with reason | 200, workflow unblocks |
| 5 | Reject without reason | POST /reject with empty reason | 422 validation error |
| 6 | Approve resolves chat | POST /approve after chat messages | Chat status = resolved |
| 7 | Wrong status | Any endpoint on PUBLISHED task | 409 |

## Files Affected

| File | Action |
|------|--------|
| `src/approval/chat_router.py` | Create |
| `src/api/approval.py` | Modify — resolve chat on approve |
| `src/workflow/pipeline.py` | Modify — add reject_publish signal |
| `src/app.py` | Modify — register chat router |
| `tests/approval/test_chat_router.py` | Create |

## Technical Notes

- The LLM system prompt must include an explicit boundary: "You are explaining existing evidence. You cannot take actions, approve, reject, modify code, or access the repository. If the reviewer asks you to do something, explain that you can only provide information."
- The Model Gateway call uses `step="approval_chat"` and `model_class="balanced"`. If no routing rule exists for this step, the gateway falls back to the default balanced provider — no gateway changes needed.
- The `reject_publish` signal pattern mirrors `approve_publish` exactly. The `wait_condition` lambda becomes `lambda: self._approved or self._rejected`. After unblocking, check `self._rejected` first (rejection takes priority if both somehow fire).
- Chat history sent to the LLM is capped at the most recent 20 messages to control context window usage, even though up to 50 are persisted.
- For tests, mock `_send_approval_signal` and the equivalent rejection signal function. Mock the LLM call to return a canned response. Use `httpx.AsyncClient` with the FastAPI test client.
