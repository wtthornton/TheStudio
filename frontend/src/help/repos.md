# Repository Settings

The Repos tab lets you register GitHub repositories with TheStudio, configure per-repository settings, and monitor fleet health across all connected repos. Each repository is an independent unit of configuration — you can tune trust tiers, label filters, and cost limits independently for each one.

## Registering a repository

1. Click **Add Repository**
2. Enter the GitHub owner (organisation or username) and repository name
3. Provide the **GitHub App installation ID** — find this in your GitHub App's settings under "Installed apps"
4. Configure the **webhook secret** to match the secret you set when configuring the webhook in GitHub's repository settings
5. Set the initial **trust tier** for this repo (Observe is a safe default for new registrations)
6. Save — the repo will appear in the fleet list and begin accepting webhook events

The webhook must be configured in GitHub to send `issues` and `pull_request` events to your TheStudio instance's `/webhook` endpoint.

## Per-repo settings

Each repository has independent configuration:

| Setting | Description |
|---------|-------------|
| Trust tier | Observe, Suggest, or Execute |
| Label filters | Only process issues carrying specific labels (e.g., `ai-ready`, `needs-implementation`) |
| Branch target | Default base branch for PRs — defaults to `main` |
| Cost limit | Per-repo spending cap, independent of the global budget |
| Complexity threshold | Skip issues above a configured complexity score |

Label filters are a powerful cost control: by requiring an `ai-ready` label you ensure a human has pre-screened each issue before TheStudio processes it.

## Fleet health

The fleet health panel shows at-a-glance status for every registered repository:

- **Webhook status** — green if events are arriving from GitHub, amber if no events in the last 24 hours
- **Last processed** — timestamp of the most recently completed task for this repo
- **Error rate** — percentage of recent tasks that failed a gate or required human intervention
- **Queue depth** — number of issues currently awaiting triage

An amber webhook status often means the webhook URL is misconfigured or the secret doesn't match. Check the Activity Log filtered to `webhook` category for the specific error.

## Removing a repository

Click the repo row and select **Deregister**. In-flight tasks will complete before the repo is removed from routing. The repository's history is retained in Analytics and the Activity Log for 90 days after deregistration, then permanently deleted.
