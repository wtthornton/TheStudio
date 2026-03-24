# Triage Queue

The Triage Queue is your inbox for newly-imported GitHub issues awaiting a decision before they enter the full pipeline.

## How triage works

When an issue arrives via webhook or manual import, it lands here first. The Intake stage performs basic eligibility checks (size, label filters, duplicate detection) and flags the issue for human review.

## Triage actions

- **Accept** — approve the issue and advance it to the Context stage
- **Reject** — dismiss the issue with a reason (it will not reappear)
- **Defer** — hold the issue for later consideration

## What to look for

- Issues that are too vague for the agent to act on should be rejected with feedback
- Large issues ("add authentication") should be broken down before accepting
- Duplicate or stale issues can be rejected immediately

## Tips

- Use the intent preview panel to see how the system interpreted the issue before deciding
- Accepted issues appear in the Pipeline Dashboard within seconds
- You can re-open a rejected issue from the Backlog board if you change your mind
