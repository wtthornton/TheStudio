# Story 24.4 — Notification Channel Adapter (Base + GitHub)

> **As a** human reviewer,
> **I want** structured approval notifications on GitHub that include a link to the review interface and a summary of what needs approval,
> **so that** I can quickly assess the request and navigate to the review UI.

**Purpose:** The current `post_approval_request_activity` posts a bare GitHub comment. This story introduces a channel adapter abstraction and a GitHub implementation that posts a richer, structured notification. The abstraction enables Story 24.5 (Slack) and future channels without modifying the workflow activity.

**Intent:** Create an abstract `NotificationChannel` base class, implement `GitHubChannel` that enhances the existing GitHub comment with ReviewContext summary and a review UI link, and wire the channel adapter into `post_approval_request_activity`.

**Points:** 5 | **Size:** M
**Epic:** 24 — Chat Interface for Approval Workflows
**Sprint:** 2 (Stories 24.4-24.6)
**Depends on:** 24.1 (ReviewContext model)

---

## Description

The notification channel is a simple abstraction: given a context (or task ID), produce a notification on a specific platform. The base class defines the interface. The GitHub implementation enhances the existing comment format. Future channels (Slack, Teams) implement the same interface.

The `post_approval_request_activity` currently posts a GitHub comment directly. This story refactors it to resolve configured channels from settings and call each one. The default configuration is `["github"]` — existing behavior is preserved with richer content.

## Tasks

- [ ] Create `src/approval/channels/__init__.py`
- [ ] Create `src/approval/channels/base.py`:
  - `class NotificationChannel(ABC)`:
    - `@abstractmethod async def notify_awaiting_approval(self, context: ReviewContext, review_url: str) -> None`
    - `@abstractmethod async def notify_approved(self, taskpacket_id: str, approved_by: str, channel: str, message_count: int) -> None`
    - `@abstractmethod async def notify_rejected(self, taskpacket_id: str, rejected_by: str, reason: str, channel: str) -> None`
    - `@abstractmethod async def notify_timeout(self, taskpacket_id: str) -> None`
  - `def get_channels(channel_names: list[str]) -> list[NotificationChannel]` — factory function that resolves channel names to instances
- [ ] Create `src/approval/channels/github.py`:
  - `class GitHubChannel(NotificationChannel)`:
    - `notify_awaiting_approval`: Posts a GitHub comment with:
      - Structured summary: intent goal, QA result (pass/fail), verification result (pass/fail), files changed count, trust tier
      - Link to review UI: `{base_url}/api/tasks/{id}/review` (configurable base URL)
      - Call to action: "Review and approve/reject at the link above"
      - Preserves `EVIDENCE_COMMENT_MARKER` for idempotent updates
    - `notify_approved`: Updates the approval comment with "Approved by {user} via {channel}"
    - `notify_rejected`: Updates the approval comment with "Rejected by {user}: {reason}"
    - `notify_timeout`: Updates the approval comment with "Approval timed out after 7 days"
  - Format functions:
    - `format_approval_request_comment(context: ReviewContext, review_url: str) -> str`
    - `format_approval_update_comment(action: str, by: str, detail: str) -> str`
- [ ] Add settings to `src/settings.py`:
  - `approval_notification_channels: list[str] = ["github"]`
  - `approval_review_base_url: str = "http://localhost:8000"` — base URL for review UI links
- [ ] Modify `post_approval_request_activity` in `src/workflow/activities.py`:
  - Build `ReviewContext` (or accept summary data from activity input)
  - Resolve channels via `get_channels(settings.approval_notification_channels)`
  - Call `notify_awaiting_approval` on each channel
  - Existing behavior preserved: if only `["github"]` is configured, same channel fires
- [ ] Write tests in `tests/approval/test_channels.py`:
  - Test `GitHubChannel.notify_awaiting_approval` produces correct comment format
  - Test comment includes intent goal, QA result, verification result
  - Test comment includes review UI link
  - Test `notify_approved` produces update comment
  - Test `notify_rejected` produces update comment with reason
  - Test `notify_timeout` produces timeout comment
  - Test `get_channels` resolves channel names to instances
  - Test `get_channels` with unknown channel name raises ValueError
  - Test `post_approval_request_activity` calls all configured channels

## Acceptance Criteria

- [ ] `NotificationChannel` abstract base defines all four notification methods
- [ ] `GitHubChannel` produces structured approval request comments with review UI link
- [ ] `GitHubChannel` updates comments on approval, rejection, and timeout
- [ ] `post_approval_request_activity` resolves and calls configured channels
- [ ] Default configuration (`["github"]`) preserves existing behavior with richer content
- [ ] Settings include channel list and review base URL
- [ ] Unit tests pass

## Test Cases

| # | Scenario | Input | Expected Output |
|---|----------|-------|-----------------|
| 1 | Approval request comment | ReviewContext + review_url | Markdown comment with summary + link |
| 2 | Approved update | taskpacket_id, user, "web" | "Approved by user via web" comment |
| 3 | Rejected update | taskpacket_id, user, reason | "Rejected by user: reason" comment |
| 4 | Timeout update | taskpacket_id | "Approval timed out" comment |
| 5 | Channel resolution | ["github"] | [GitHubChannel instance] |
| 6 | Unknown channel | ["carrier_pigeon"] | ValueError |

## Files Affected

| File | Action |
|------|--------|
| `src/approval/channels/__init__.py` | Create |
| `src/approval/channels/base.py` | Create |
| `src/approval/channels/github.py` | Create |
| `src/settings.py` | Modify — add channel settings |
| `src/workflow/activities.py` | Modify — use channel adapters |
| `tests/approval/test_channels.py` | Create |

## Technical Notes

- The GitHub comment posting mechanism already exists in `post_approval_request_activity`. The `GitHubChannel` wraps this existing mechanism — it does not implement a new GitHub API client.
- The `EVIDENCE_COMMENT_MARKER` from `src/publisher/evidence_comment.py` should be reused (or a similar `APPROVAL_COMMENT_MARKER`) so the channel can find and update its own comments idempotently.
- The review URL format is `{base_url}/api/tasks/{taskpacket_id}/review`. This is the API endpoint — a future frontend epic may provide a different URL. The base URL is configurable in settings.
- Channel resolution is a simple factory: `"github" -> GitHubChannel()`, `"slack" -> SlackChannel()`. No plugin system, no dynamic loading. Explicit is better than implicit.
