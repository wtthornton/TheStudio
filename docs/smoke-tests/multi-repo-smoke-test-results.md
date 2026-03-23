# Multi-Repo Smoke Test Results

> Epic 41, Story 41.13 — Real second repo smoke test documentation.
>
> This document records the results of the manual end-to-end smoke test for multi-repo
> support. A second real GitHub repository was registered, an issue was processed through
> the full pipeline, and the first repo was verified to continue operating correctly.

---

## Test Environment

| Item | Value |
|------|-------|
| Date | TBD — perform before Sprint 3 demo |
| First repo (existing) | `wtthornton/thestudio-production-test-rig` |
| Second repo (new) | TBD — choose from options below |
| Pipeline version | Epic 41 Slice 2 (post-Sprint 2 branch) |
| Dashboard URL | http://localhost:5173 (local) |
| API URL | http://localhost:8000 |

### Second Repo Options

Choose one before running the test:

1. **Self-referential** — `wtthornton/TheStudio` (the platform tests itself)
2. **Dedicated test repo** — Create `wtthornton/thestudio-multi-repo-test` (clean slate)

Recommended: Option 2 (dedicated repo gives cleaner signals; no risk of triggering
    production pipeline changes on the platform's own code during testing).

---

## Pre-Test Checklist

- [ ] Docker Compose stack running (`docker-compose up -d`)
- [ ] First repo (`thestudio-production-test-rig`) already registered and active
- [ ] GitHub App installed on second repo (Settings → GitHub Apps → Install)
- [ ] Second repo has at least one open issue with label `agent:run`
- [ ] `GITHUB_APP_ID`, `GITHUB_PRIVATE_KEY_PATH`, `GITHUB_INSTALLATION_ID` set in `.env`

---

## Step 1: Register Second Repo

```bash
curl -X POST http://localhost:8000/admin/repos \
  -H "Content-Type: application/json" \
  -d '{
    "owner": "wtthornton",
    "repo": "thestudio-multi-repo-test",
    "installation_id": <INSTALLATION_ID>,
    "default_branch": "main"
  }'
```

**Expected response:**
```json
{
  "id": "<uuid>",
  "owner": "wtthornton",
  "repo": "thestudio-multi-repo-test",
  "tier": "OBSERVE",
  "installation_id": <INSTALLATION_ID>,
  "message": "Registered wtthornton/thestudio-multi-repo-test at Observe tier"
}
```

**Actual response:** _(fill in during test)_

---

## Step 2: Configure Webhook

In the second repo's GitHub Settings → Webhooks:
- Payload URL: `https://<tunnel>/webhook` (use ngrok or similar for local dev)
- Content type: `application/json`
- Secret: _(use value from `THESTUDIO_WEBHOOK_SECRET` or repo-specific secret)_
- Events: `Issues`, `Pull requests`

**Webhook delivery test:** _(record delivery ID and status)_

---

## Step 3: Verify Repos Listed Independently

```bash
curl http://localhost:8000/admin/repos | jq '.repos[] | {owner, repo, tier}'
```

**Expected:** Two repos listed — first at its current tier, second at OBSERVE.

**Actual:**

```
_(fill in)_
```

---

## Step 4: Create Test Issue on Second Repo

Create a GitHub issue on the second repo with:
- Title: `[Smoke Test] Add a hello world function`
- Body: `Add a simple hello() function that returns the string "hello, world!".`
- Label: `agent:run`

**Issue URL:** _(fill in)_

---

## Step 5: Verify Webhook Received and TaskPacket Created

```bash
# Wait ~30 seconds for webhook delivery, then check
curl "http://localhost:8000/api/v1/dashboard/tasks?repo=wtthornton/thestudio-multi-repo-test" \
  | jq '.[0] | {id, title, repo, status}'
```

**Expected:** One task with `repo = "wtthornton/thestudio-multi-repo-test"`.

**Actual:**

```
_(fill in)_
```

---

## Step 6: Verify First Repo Unaffected

```bash
curl "http://localhost:8000/api/v1/dashboard/tasks?repo=wtthornton/thestudio-production-test-rig" \
  | jq 'length'
```

**Expected:** Same count as before step 4 (no new tasks created for first repo).

**Actual:** _(fill in)_

---

## Step 7: Monitor Pipeline Stages

In the dashboard, switch the repo selector to `wtthornton/thestudio-multi-repo-test` and
observe the task progressing through pipeline stages.

| Stage | Status | Notes |
|-------|--------|-------|
| Intake | ⬜ | |
| Context | ⬜ | |
| Intent | ⬜ | |
| Router | ⬜ | |
| Assembler | ⬜ | |
| Implement | ⬜ | |
| Verify | ⬜ | |
| QA | ⬜ | |
| Publish | ⬜ | |

Replace ⬜ with ✅ (pass), ❌ (fail), or ⏭ (skipped).

---

## Step 8: Verify Draft PR Created

```bash
# Get the task ID from step 5
curl "http://localhost:8000/api/v1/dashboard/tasks/<task_id>" \
  | jq '{status, pr_url, pr_number}'
```

**Expected:** `status: "published"`, `pr_url` pointing to the second repo's pull requests.

**Actual:**

```
_(fill in)_
```

**PR URL:** _(fill in)_

---

## Step 9: Verify Evidence Comment

Open the draft PR on GitHub. The evidence comment should reference the correct repo:
- `repo: wtthornton/thestudio-multi-repo-test`
- Not the first repo

**Evidence comment screenshot / excerpt:** _(fill in)_

---

## Step 10: Verify Repo Context Switching in Dashboard

1. In the dashboard, select `wtthornton/thestudio-multi-repo-test` from the repo selector
2. Task list shows only second repo's tasks
3. Switch to `wtthornton/thestudio-production-test-rig` — task list shows only first repo's tasks
4. Switch to "All Repos" — both repos' tasks visible

**Result:** _(pass / fail with notes)_

---

## Timing Results

| Step | Time |
|------|------|
| Webhook received → TaskPacket created | _(fill in)_ |
| TaskPacket created → Draft PR created | _(fill in)_ |
| Total pipeline time | _(fill in)_ |
| Time to register a new repo (steps 1–2) | _(fill in)_ |

---

## Issues Encountered

_(List any errors, workarounds, or unexpected behaviours during the smoke test)_

---

## Final Assessment

| Criterion | Result |
|-----------|--------|
| Second repo processes issue end-to-end | ⬜ |
| Draft PR created with correct repo reference | ⬜ |
| Evidence comment references correct repo | ⬜ |
| First repo continues working after test | ⬜ |
| Dashboard repo context switching works | ⬜ |
| Total time < 5 min to register new repo | ⬜ |

Replace ⬜ with ✅ or ❌.

**Overall: PASS / FAIL** _(fill in)_

---

## Sign-Off

| Role | Name | Date |
|------|------|------|
| Developer | | |
| Reviewer | Meridian (post-test review) | |
