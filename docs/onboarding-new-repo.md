# Onboarding a New Repository to TheStudio

> **Epic 41 — Story 41.1**
> This guide walks through every step required to register a second (or third, or Nth) GitHub
> repository with TheStudio so it can receive webhooks, have its issues triaged, and run
> full pipeline workflows.

---

## Prerequisites

Before starting, confirm that:

- [ ] TheStudio is running (Docker Compose or native).
- [ ] The GitHub App ("TheStudio App") is installed on **your target repo** — see §2 below.
- [ ] You have the App's **Installation ID** for the target repo (visible in GitHub App settings).
- [ ] You have admin credentials (bearer token) for the TheStudio API, or `dashboard_token` is
      empty (dev mode).

---

## 1. Identify Your Target Repository

Choose the repository you want to onboard. Good candidates:

| Option | Pros | Cons |
|--------|------|------|
| A new dedicated test repo (`org/thestudio-test`) | Clean slate, no real issues at risk | Requires creating a new repo |
| TheStudio's own repo (`wtthornton/TheStudio`) | Self-referential — dogfood your own pipeline | PRs from the pipeline are visible to all contributors |
| A production repo you own | Real-world validation | Higher stakes |

Record the **full name** (`owner/repo-name`), e.g., `wtthornton/thestudio-multi-repo-test`.

---

## 2. Install the GitHub App on the Target Repository

1. Go to **https://github.com/apps/thestudio-app** (replace with your App's slug).
2. Click **Configure** next to your organization or personal account.
3. Under **Repository access**, add your target repository.
4. Save. GitHub will redirect you to the App's installation page.
5. Note the **Installation ID** from the URL: `https://github.com/settings/installations/**123456**`.

> **Tip:** The Installation ID is also visible via the GitHub API:
> ```
> GET https://api.github.com/app/installations
> Authorization: Bearer <App JWT>
> ```

---

## 3. Configure the Webhook in GitHub

1. Go to `https://github.com/<owner>/<repo>/settings/hooks`.
2. Click **Add webhook**.
3. Set the following:
   - **Payload URL:** `https://<your-thestudio-host>/webhook/github`
   - **Content type:** `application/json`
   - **Secret:** Generate a strong random secret (e.g., `openssl rand -hex 32`). Record it — you
     will pass it to the admin API in §4.
   - **Events:** Select **Issues** and **Issue comments** at minimum. Add any other events you
     want bridged to the NATS pipeline.
4. Click **Add webhook**.

> **Security:** Each repository **must have a unique webhook secret**. Shared secrets allow
> cross-repo HMAC forgery — this is a security invariant.

---

## 4. Register the Repository via the Admin API

Use `POST /admin/repos` to register the new repository:

```bash
curl -s -X POST http://localhost:8000/admin/repos \
  -H "Authorization: Bearer <admin-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "owner": "wtthornton",
    "repo": "thestudio-multi-repo-test",
    "installation_id": 123456,
    "default_branch": "main",
    "webhook_secret": "<secret-you-set-in-step-3>"
  }'
```

**Expected response (201 Created):**

```json
{
  "id": "uuid-...",
  "owner": "wtthornton",
  "repo": "thestudio-multi-repo-test",
  "tier": "OBSERVE",
  "installation_id": 123456,
  "message": "Registered wtthornton/thestudio-multi-repo-test at Observe tier"
}
```

**Error cases:**
- `409 Conflict` — repository already registered (safe to ignore if re-running).
- `403 Forbidden` — your bearer token lacks `REGISTER_REPO` permission.

> **Note:** New repositories always start at `OBSERVE` tier. They will not create PRs until
> promoted to `SUGGEST` or `EXECUTE`. This is a safety invariant.

---

## 5. Verify the Registration

Confirm the repo is listed:

```bash
curl -s http://localhost:8000/admin/repos \
  -H "Authorization: Bearer <admin-token>" | jq '.repos[] | select(.owner=="wtthornton")'
```

You should see your new repo with `"tier": "OBSERVE"` and `"status": "ACTIVE"`.

---

## 6. Test the Webhook

Send a test webhook from GitHub:

1. Go to `https://github.com/<owner>/<repo>/settings/hooks`.
2. Click the webhook you created.
3. Scroll to **Recent Deliveries** and click **Redeliver** on any delivery, or use
   **Send test delivery**.

Expected server log:

```
INFO ingress.webhook_handler - accepted delivery_id=... repo=wtthornton/thestudio-multi-repo-test
```

If you see `404 Repository not registered`, the `owner/repo` in the payload does not match what
you registered. Verify the `full_name` field in the webhook payload.

If you see `401 Invalid signature`, the secret in GitHub does not match the one stored in
TheStudio. Update the webhook in GitHub or re-register the repo with the correct secret.

---

## 7. Create a Test Issue

1. Open the target repository on GitHub.
2. Create a new issue with the label `agent:run` (required for the pipeline to pick it up).
3. Add a descriptive title and body with clear acceptance criteria.
4. Submit the issue.

Within seconds you should see a new TaskPacket appear in the TheStudio dashboard under the
**Triage** column (if triage mode is enabled) or **Planning** (if skip_triage is configured).

---

## 8. Dashboard Repo Selector

Once the second repo is registered, the dashboard **Repo Selector** dropdown (top-right of the
header) will list both repos. Select your new repo to filter the task list, triage queue, and
gate inspector to show only its tasks.

Select **All Repos** to see the combined view.

---

## 9. Verification Checklist

After completing the above steps:

- [ ] `GET /admin/repos` returns the new repo with `status: "ACTIVE"`.
- [ ] A test webhook delivery shows `200 OK` in GitHub's **Recent Deliveries**.
- [ ] A test issue with `agent:run` label creates a TaskPacket visible in the dashboard.
- [ ] The Repo Selector dropdown shows the new repo.
- [ ] The existing first repo still processes issues correctly (no regression).
- [ ] The new repo's TaskPackets show `repo="<owner>/<repo>"` in the task detail view.

---

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| `404 Repository not registered` | `full_name` mismatch | Confirm `owner/repo` exactly matches GitHub's `repository.full_name` |
| `401 Invalid signature` | Wrong webhook secret | Re-configure the GitHub webhook secret to match the one stored in TheStudio |
| TaskPacket created but workflow not started | Repo is at OBSERVE tier | Expected — OBSERVE repos create TaskPackets but don't start workflows |
| No TaskPacket created | Issue missing `agent:run` label | Add the label, or configure the intake eligibility rules |
| Duplicate blocked | Issue already exists in DB | Normal — re-delivering the same GitHub event is idempotent |

---

## Next Steps

- **Promote to SUGGEST tier:** `PATCH /admin/repos/{repo_id}/tier` with `{"tier": "SUGGEST"}`.
  This enables the pipeline to create draft PRs in review mode.
- **Enable auto-merge (EXECUTE tier):** Requires Epic 42 (Auto-Merge with Human Gates).
- **Per-repo trust tier rules:** See `docs/per-repo-trust-tier-rules.md` for scoping trust
  rules to a specific repository.
- **Fleet health view:** `GET /admin/repos/health` for a summary of all registered repos.
