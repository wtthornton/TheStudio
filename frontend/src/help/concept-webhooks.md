# Concept: Webhooks

Webhooks are the entry point for every task TheStudio processes. When a GitHub issue is created, labelled, or updated, GitHub sends an HTTPS POST to TheStudio's webhook endpoint. TheStudio validates the payload, checks eligibility, and — if the issue meets your configured criteria — creates a TaskPacket and starts the pipeline.

## The webhook flow

```
GitHub issue event
       │
       ▼
POST /webhooks/github
       │
  Signature check (HMAC-SHA256)
       │
  Eligibility filter (labels, repos, type)
       │
  TaskPacket created
       │
  Context stage begins
```

## Configuring the webhook on GitHub

1. Go to your repository → **Settings → Webhooks → Add webhook**
2. Set the **Payload URL** to the endpoint shown on your TheStudio Webhook Config screen (e.g. `https://your-studio.example.com/webhooks/github`)
3. Set **Content type** to `application/json`
4. Paste your **webhook secret** — must match the `GITHUB_WEBHOOK_SECRET` environment variable configured in TheStudio
5. Select **Individual events** and enable: *Issues*, *Issue comments* (optional)
6. Save and confirm the green tick appears in GitHub's delivery log

## Signature verification

Every payload is verified with HMAC-SHA256 using your webhook secret. Payloads that fail signature verification are rejected with `401 Unauthorized` and never reach the pipeline. This protects against spoofed events.

## Eligibility filters

Not every GitHub issue should trigger the pipeline. TheStudio applies eligibility checks in order:

| Check | How to configure |
|-------|-----------------|
| **Repository allowlist** | Only repos registered in Repo Settings pass through |
| **Label filter** | Optional: only issues with specific labels (e.g. `studio:ready`) are accepted |
| **Issue type** | Comments, PRs, and other event types are ignored by default |
| **Duplicate guard** | If a TaskPacket already exists for this issue, a new one is not created |

## Delivery retries

GitHub retries failed webhook deliveries up to **3 times** with exponential back-off (5 s, 1 min, 5 min). TheStudio's webhook endpoint is designed to be idempotent: duplicate deliveries for the same event are de-duplicated using the `X-GitHub-Delivery` header so they never create duplicate TaskPackets.

## Manual import

If you miss a webhook event or want to trigger the pipeline for an existing issue, use the **Import Issues** button on the Pipeline Dashboard. This fetches the issue from the GitHub API directly and creates a TaskPacket without a webhook event.

## Troubleshooting

| Symptom | Likely cause |
|---------|-------------|
| GitHub shows red ✗ on delivery | Endpoint unreachable or secret mismatch |
| Issue not appearing in dashboard | Repo not in allowlist, or label filter not matched |
| Duplicate tasks created | Old webhook not removed after reconfiguration |
| `401` in GitHub delivery log | Webhook secret does not match `GITHUB_WEBHOOK_SECRET` |

## See also

- **Webhook Config step** in the Setup Wizard
- **Concept: Pipeline Stages** — what happens after an issue enters the pipeline
- **Concept: Trust Tiers** — how processing behaviour is governed once a task is in-flight
