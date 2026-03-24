# Reputation & Outcomes

The Reputation tab tracks the long-term performance of each expert agent and surfaces quality signals from merged PRs. It closes the feedback loop between what the agent produces and what actually gets merged — giving you an honest picture of agent quality over time.

## How reputation works

After a PR is merged (or closed), TheStudio ingests **outcome signals** from GitHub:

| Outcome | Signal |
|---------|--------|
| Merged without modification | Strong positive |
| Merged after minor human edits | Neutral (depends on edit size) |
| Merged after significant human edits | Negative |
| PR closed without merge | Negative |
| Post-merge CI failures | Strong negative |
| PR reverted after merge | Very strong negative |

These signals update each expert agent's **reputation score**, a weighted composite that influences future routing decisions. Agents with higher reputation scores are selected more often for tasks in their domain.

## Reading the reputation table

| Column | Meaning |
|--------|---------|
| Expert | Agent name and technical domain |
| Tasks completed | Total PRs published to date |
| Acceptance rate | Percentage merged without significant modification |
| Avg quality score | Composite from QA gate scores + outcome signals |
| Trend | 30-day moving average — up, flat, or down |
| Status | Active, Watched, or Quarantined |

## Quarantine

Agents whose reputation falls below a configured threshold are automatically **quarantined** — removed from routing until a human reviews their recent output and explicitly re-enables them. A quarantine event generates an Activity Log entry with the triggering evidence so you can understand what went wrong.

To re-enable a quarantined agent, review the recent outputs listed in its detail panel, satisfy yourself that the issue is understood, and click **Restore to routing**. You can optionally adjust the agent's domain scope before restoring.

## Decay

Reputation scores apply **time decay** so that recent performance matters more than historical performance. An agent that had a poor month a year ago but has performed well recently will have a healthy score. Equally, an agent with a historically good reputation that suddenly degrades will surface in the Watched tier quickly — typically within 1–2 weeks of consistent underperformance.

## Using reputation to improve the pipeline

Low acceptance rates for a specific expert usually mean one of two things: the routing is sending it tasks outside its competency, or a recent model or prompt change degraded its output. Compare the reputation trend against your deployment history in the Activity Log to diagnose the cause.
