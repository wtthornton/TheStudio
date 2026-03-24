# Triage Queue

The Triage Queue is your inbox for newly-imported GitHub issues awaiting a decision before they enter the full pipeline. Acting as a human-in-the-loop checkpoint, triage ensures that only well-formed, actionable issues consume pipeline resources.

## How triage works

When an issue arrives via webhook or manual import, it lands here first. The Intake stage performs basic eligibility checks — size, label filters, duplicate detection — and flags the issue for human review. You'll see a card for each issue showing its title, labels, estimated complexity, and a short AI-generated summary.

## Triage actions

- **Accept** — approve the issue and advance it to the Context stage where it will be enriched and processed
- **Reject** — dismiss the issue with a reason; it will not reappear in triage but remains visible in the Backlog for reference
- **Defer** — hold the issue for later consideration; it stays in the queue without consuming pipeline resources

## What to look for

- **Vague issues** ("fix the bug") should be rejected with constructive feedback so the original author can improve them
- **Oversized issues** ("add authentication") should be broken down into smaller tasks before accepting — the agent performs best with focused, single-concern issues
- **Duplicate or stale issues** can be rejected immediately; the system will flag known duplicates automatically
- **Blocked issues** that depend on unreleased work should be deferred until the dependency is resolved

## Using the intent preview

Before deciding, expand the card to see the **intent preview panel** — this shows how the system has interpreted the issue. If the intent looks wrong or incomplete, that's a signal the issue needs more detail before it's ready for the pipeline. Rejecting with a note is far cheaper than letting a poorly-specified task run through all 9 stages.

## Tips

- Accepted issues appear in the Pipeline Dashboard within seconds of your decision
- You can re-open a rejected issue from the Backlog board if you change your mind
- Bulk-accept is available when you've imported a batch of well-formed issues (hold Shift to select multiple cards)
- High-priority issues labelled `p0` or `critical` are automatically surfaced at the top of the queue
