# Repository Settings

The Repos tab lets you register GitHub repositories, configure per-repo settings, and view fleet health across all connected repos.

## Registering a repository

1. Click **Add Repository**
2. Enter the owner, repository name, and GitHub App installation ID
3. Configure the webhook secret to match what you set in GitHub
4. Set the initial trust tier for this repo
5. Save — the repo will appear in the fleet list

## Per-repo settings

Each repository has independent configuration for:

- **Trust tier** — Observe, Suggest, or Execute
- **Label filters** — only process issues with specific labels (e.g., `ai-ready`)
- **Branch target** — default branch for PRs (defaults to `main`)
- **Cost limit** — per-repo spending cap separate from the global budget

## Fleet health

The fleet health panel shows:
- **Webhook status** — whether events are arriving from GitHub
- **Last processed** — timestamp of the most recent issue processed
- **Error rate** — percentage of recent tasks that failed a gate

## Removing a repository

Click the repo row and select **Deregister**. In-flight tasks will complete. The repo's history is retained in Analytics for 90 days.
