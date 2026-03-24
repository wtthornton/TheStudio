# Backlog Board

The Backlog Board gives you a Kanban-style view of all tasks across the pipeline in one place. Where the Pipeline Dashboard focuses on stage throughput, the Backlog Board focuses on individual task progress — useful for planning, prioritisation, and stakeholder updates.

## Columns

Each column maps to a pipeline stage:

| Column | Stage | What it means |
|--------|-------|---------------|
| Triage | Intake | Awaiting your accept/reject decision |
| Context | Context | Being enriched with repo history |
| Intent | Intent | Intent specification being generated or edited |
| Routing | Router | Expert agents being selected |
| In Progress | Implement | Primary Agent writing code |
| Review | QA | QA Agent validating output against intent |
| Done | Publish | Draft PR published to GitHub |

## Using the board

- **Click a card** to open the Task Timeline and Stage Detail Panel for that task — see the full event history, gate results, and evidence bundle
- **Drag a card** to manually advance or roll back a task to a different stage; this requires **Suggest** or **Execute** trust tier and leaves an audit trail entry
- **Filter by repo** using the repo selector in the header to focus on a single repository's work
- **Search by issue title or ID** using the search bar to quickly find a specific task

## Card details

Each card displays:
- GitHub issue title and number
- Repository name
- Priority inferred from labels (`p0`, `p1`, `critical`, `urgent`)
- Time in current stage
- Assignee (the expert agent currently working on it, if applicable)
- A colour-coded status indicator showing gate pass/fail

## Priority and labels

Cards show the GitHub issue labels from the original issue. Priority is automatically inferred from label keywords — `p0` and `critical` labels surface cards at the top of their column. You can manually set priority using the card context menu if the label inference is incorrect.

## Archiving

Completed tasks stay in the Done column for 7 days, then archive automatically. Archived tasks are still visible in Analytics and the Activity Log. Use the Reputation tab to review long-term outcomes from archived tasks and see whether merged PRs remained clean after merge.
