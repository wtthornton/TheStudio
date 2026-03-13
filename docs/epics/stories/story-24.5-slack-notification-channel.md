# Story 24.5 — Slack Notification Channel (Optional)

> **As a** reviewer who works primarily in Slack,
> **I want** approval notifications with interactive buttons delivered to a Slack channel,
> **so that** I can review, approve, or reject without leaving Slack.

**Purpose:** GitHub comments are invisible to reviewers who live in Slack. This story delivers a Slack notification channel that posts structured approval requests with interactive buttons (Approve / Review / Reject). The Approve and Reject buttons call the existing API endpoints directly via Slack interactivity. The Review button links to the web review UI.

**Intent:** Implement `SlackChannel` using Slack Block Kit for rich messages with interactive buttons. Add a Slack interactivity webhook endpoint that handles button presses. Configure via environment variables.

**Points:** 5 | **Size:** M
**Epic:** 24 — Chat Interface for Approval Workflows
**Sprint:** 2 (Stories 24.4-24.6)
**Depends on:** 24.4 (NotificationChannel base)

---

## Description

The Slack channel posts messages using the Slack Web API (`chat.postMessage`) with Block Kit layouts. The message includes a summary of the approval request (intent goal, QA status, verification status, files changed, trust tier) and three buttons: Approve (green, calls approve API), Review (neutral, links to review UI), Reject (red, opens a modal for reason input).

Interactive buttons require a Slack interactivity webhook. When a reviewer clicks Approve or Reject, Slack sends a POST to our webhook endpoint. The endpoint validates the Slack signature, extracts the action, and calls the appropriate internal API function.

This story is explicitly optional. It requires Slack infrastructure (bot token, signing secret, channel ID) that may not be available in all deployments. The feature is gated by the `approval_notification_channels` setting — if `"slack"` is not in the list, no Slack code runs.

## Tasks

- [ ] Create `src/approval/channels/slack.py`:
  - `class SlackChannel(NotificationChannel)`:
    - `__init__`: Reads `THESTUDIO_SLACK_BOT_TOKEN`, `THESTUDIO_SLACK_CHANNEL`, `THESTUDIO_SLACK_SIGNING_SECRET` from settings
    - `notify_awaiting_approval(context, review_url)`:
      - Build Block Kit message with sections:
        - Header: "Approval Required: {intent_goal[:80]}"
        - Section: repo, tier, QA status, verification status
        - Section: files changed summary
        - Actions: Approve button (style=primary), Review button (url=review_url), Reject button (style=danger)
      - Call `chat.postMessage` with blocks
      - Store message timestamp for future updates
    - `notify_approved(taskpacket_id, approved_by, channel, message_count)`:
      - Call `chat.update` on the original message
      - Replace action buttons with "Approved by {user} via {channel} ({n} review messages)"
    - `notify_rejected(taskpacket_id, rejected_by, reason, channel)`:
      - Call `chat.update` on the original message
      - Replace action buttons with "Rejected by {user}: {reason}"
    - `notify_timeout(taskpacket_id)`:
      - Call `chat.update` on the original message
      - Replace action buttons with "Approval timed out"
  - Block Kit builder functions:
    - `build_approval_blocks(context: ReviewContext, review_url: str) -> list[dict]`
    - `build_resolved_blocks(action: str, by: str, detail: str) -> list[dict]`
- [ ] Create Slack interactivity webhook in `src/approval/channels/slack_webhook.py`:
  - `router = APIRouter(prefix="/api/webhooks/slack", tags=["slack"])`
  - `POST /interactivity`:
    - Validate Slack signature using signing secret
    - Parse action payload
    - If action = "approve": call `_send_approval_signal(taskpacket_id, user_name)`
    - If action = "reject": open modal for reason input (Slack `views.open`)
    - If action = "reject_submit" (modal submission): call `_send_rejection_signal(taskpacket_id, user_name, reason)`
    - Return 200 (Slack requires fast response)
  - Signature validation: verify `X-Slack-Signature` header using HMAC-SHA256 with signing secret
- [ ] Add settings to `src/settings.py`:
  - `slack_bot_token: str = ""` — Slack bot OAuth token
  - `slack_channel: str = ""` — channel ID for approval notifications
  - `slack_signing_secret: str = ""` — for webhook signature validation
- [ ] Register Slack webhook router in `src/app.py` (conditionally, only if slack_bot_token is configured)
- [ ] Update `get_channels()` in `src/approval/channels/base.py`:
  - Add `"slack"` -> `SlackChannel()` mapping
  - Raise `ValueError` if `"slack"` requested but `slack_bot_token` is not configured
- [ ] Write tests in `tests/approval/test_slack_channel.py`:
  - Test `build_approval_blocks` produces valid Block Kit structure
  - Test blocks include Approve, Review, and Reject buttons
  - Test `notify_awaiting_approval` calls chat.postMessage with correct blocks
  - Test `notify_approved` calls chat.update with resolved blocks
  - Test Slack webhook validates signature correctly
  - Test Slack webhook rejects invalid signature
  - Test Slack webhook handles approve action
  - Test Slack webhook handles reject modal submission
  - Test `get_channels(["slack"])` raises when token not configured

## Acceptance Criteria

- [ ] `SlackChannel` posts Block Kit messages with approval summary and action buttons
- [ ] Approve button triggers approval signal via webhook
- [ ] Reject button opens modal for reason, then triggers rejection signal
- [ ] Review button links to web review UI
- [ ] Messages are updated on resolution (approved/rejected/timeout)
- [ ] Webhook validates Slack signature before processing
- [ ] Feature is gated by configuration — no Slack code runs unless configured
- [ ] Unit tests pass with mocked Slack API

## Test Cases

| # | Scenario | Input | Expected Output |
|---|----------|-------|-----------------|
| 1 | Approval request blocks | ReviewContext | Valid Block Kit JSON with 3 buttons |
| 2 | Approve via Slack | Approve button click payload | Approval signal sent, message updated |
| 3 | Reject via Slack | Reject button + modal reason | Rejection signal sent, message updated |
| 4 | Invalid signature | Bad X-Slack-Signature | 401 Unauthorized |
| 5 | Unconfigured Slack | get_channels(["slack"]) without token | ValueError |
| 6 | Timeout update | notify_timeout(taskpacket_id) | Message updated with timeout text |

## Files Affected

| File | Action |
|------|--------|
| `src/approval/channels/slack.py` | Create |
| `src/approval/channels/slack_webhook.py` | Create |
| `src/approval/channels/base.py` | Modify — add slack to factory |
| `src/settings.py` | Modify — add Slack settings |
| `src/app.py` | Modify — conditionally register Slack webhook |
| `tests/approval/test_slack_channel.py` | Create |

## Technical Notes

- Use `httpx` for Slack API calls (already in the dependency tree). Do not add `slack_sdk` as a dependency — the API is simple enough to call directly.
- Slack Block Kit reference: https://api.slack.com/reference/block-kit
- Slack interactivity webhook: https://api.slack.com/interactivity/handling
- Slack signature validation: https://api.slack.com/authentication/verifying-requests-from-slack
- The message timestamp (`ts`) returned by `chat.postMessage` is needed for `chat.update`. Store it in the `ApprovalChat` model (add an optional `slack_message_ts: str | None` column) or in a lightweight in-memory cache keyed by taskpacket_id.
- Slack requires webhook responses within 3 seconds. For approve/reject actions that call Temporal, do the signal send in a background task and return 200 immediately.
- For the reject flow: Slack modals require `trigger_id` from the original interaction payload. The reject button opens a modal (views.open) where the user enters the reason. The modal submission is a separate webhook callback.
