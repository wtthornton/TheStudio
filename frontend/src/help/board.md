# Backlog Board

The Backlog Board gives you a Kanban-style view of all tasks across the pipeline in one place.

## Columns

Each column maps to a pipeline stage:

| Column | Stage |
|--------|-------|
| Triage | Awaiting human review |
| Context | Enrichment in progress |
| Intent | Intent spec being built |
| Routing | Expert selection |
| In Progress | Agent implementing |
| Review | QA checking output |
| Done | PR published to GitHub |

## Using the board

- **Click a card** to open the Task Timeline and Stage Detail Panel for that task
- **Drag a card** to manually advance or roll back a task (requires Suggest or Execute trust tier)
- **Filter by repo** using the repo selector in the header

## Priority and labels

Cards show the GitHub issue labels from the original issue. Priority is inferred from label keywords (`p0`, `p1`, `critical`, `urgent`).

## Archiving

Completed tasks stay in the Done column for 7 days, then archive automatically. Use the Reputation tab to review archived outcomes.
