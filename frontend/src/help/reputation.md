# Reputation & Outcomes

The Reputation tab tracks the long-term performance of each expert agent and surfaces quality signals from merged PRs.

## How reputation works

After a PR is merged (or closed), TheStudio ingests outcome signals:

- **Merge without changes** → positive signal
- **PR modified by human before merge** → neutral or negative signal (depending on size of change)
- **PR closed without merge** → negative signal
- **Post-merge CI failures** → strong negative signal

These signals update each expert agent's **reputation score**, which influences future routing decisions.

## Reading the reputation table

| Column | Meaning |
|--------|---------|
| Expert | Agent name and domain |
| Tasks completed | Total PRs published |
| Acceptance rate | % merged without modification |
| Avg quality score | Composite score from QA + outcome signals |
| Trend | 30-day moving average direction |

## Quarantine

Agents whose reputation falls below a threshold are automatically **quarantined** — they are removed from routing until a human reviews their recent output and re-enables them.

## Decay

Reputation scores decay over time so recent performance matters more than historical performance. A quarantined agent that improves after fixes will recover its score within weeks.
