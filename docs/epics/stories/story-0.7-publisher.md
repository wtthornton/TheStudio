# Story 0.7 -- Publisher: draft PR with evidence comment

<!-- docsmcp:start:user-story -->

> **As a** TheStudio platform, **I want** to create a draft PR on GitHub with an evidence comment (TaskPacket ID, intent summary, verification result) and lifecycle labels, using an idempotency key to prevent duplicates, **so that** every completed task produces exactly one traceable PR

<!-- docsmcp:end:user-story -->

<!-- docsmcp:start:sizing -->
**Points:** 8 | **Size:** L
**Epic:** 0 — Foundation: Prove the Pipe
**Sprint:** 3 (weeks 7-9)
**Depends on:** Story 0.5 (Primary Agent), Story 0.6 (Verification Gate)

<!-- docsmcp:end:sizing -->

---

<!-- docsmcp:start:description -->
## Description

The Publisher is the final step in the Phase 0 pipe. After the Primary Agent implements and the Verification Gate passes, the Publisher creates a draft PR on GitHub with a structured evidence comment and lifecycle labels.

**Publisher responsibilities:**
1. Create a branch from the agent's changes
2. Push the branch to the repo
3. Create a draft PR via GitHub API
4. Add an evidence comment with: TaskPacket ID, intent summary (goal + acceptance criteria), verification result summary
5. Apply lifecycle labels: `agent:in-progress` during creation, then `agent:done` on success
6. Use idempotency key (TaskPacket ID + intent version) to prevent duplicate PRs on retry
7. Update TaskPacket status to "published"

**Idempotency:** Before creating a PR, Publisher checks if a PR with the same idempotency key already exists (via branch name convention or PR body marker). If found, it updates rather than creates.

<!-- docsmcp:end:description -->

---

<!-- docsmcp:start:tasks -->
## Tasks

- [ ] Implement Publisher orchestrator (`src/publisher/publisher.py`)
  - Accept TaskPacket ID + evidence bundle + verification result
  - Orchestrate branch creation, PR creation, evidence comment, labels
  - Handle idempotency check before creating
- [ ] Implement branch management (`src/publisher/branch.py`)
  - Branch naming convention: `agent/taskpacket-{id}`
  - Create branch from agent's working tree
  - Push to remote
- [ ] Implement PR creation (`src/publisher/pr.py`)
  - Create draft PR via GitHub API
  - PR title from intent goal
  - PR body includes idempotency marker: `<!-- taskpacket:{id} intent:{version} -->`
  - Lookup existing PR by branch name before creating
- [ ] Implement evidence comment (`src/publisher/evidence_comment.py`)
  - Structured markdown format:
    - TaskPacket ID + correlation_id
    - Intent summary (goal, acceptance criteria checklist)
    - Verification result (pass/fail per check, loopback count)
  - Add as PR comment via GitHub API
- [ ] Implement lifecycle labels (`src/publisher/labels.py`)
  - Apply `agent:in-progress` on PR creation
  - Update to `agent:done` after evidence comment posted
  - Create labels if they don't exist in the repo
- [ ] Implement idempotency guard (`src/publisher/idempotency.py`)
  - Key: TaskPacket ID + intent version
  - Check: search for existing PR with matching branch or body marker
  - On duplicate: update existing PR instead of creating new one
- [ ] Add OpenTelemetry span (`src/publisher/publisher.py`)
  - Span: `publisher.publish`
  - Attributes: correlation_id, pr_number, is_duplicate, label_applied
- [ ] Write tests (`tests/test_publisher.py`)
  - Unit tests for evidence comment formatting
  - Unit tests for idempotency check
  - Integration test: full publish flow (branch -> PR -> comment -> labels)
  - Integration test: duplicate publish -> update existing PR

<!-- docsmcp:end:tasks -->

---

<!-- docsmcp:start:acceptance-criteria -->
## Acceptance Criteria

- [ ] Draft PR created on GitHub with correct title (from intent goal)
- [ ] Evidence comment contains TaskPacket ID, intent summary, and verification result
- [ ] Lifecycle labels applied: `agent:in-progress` then `agent:done`
- [ ] Idempotency key prevents duplicate PRs on retry
- [ ] Duplicate publish updates existing PR instead of creating new one
- [ ] PR body contains idempotency marker for future lookups
- [ ] TaskPacket status transitions to "published" after successful publish
- [ ] Branch naming follows convention: `agent/taskpacket-{id}`

<!-- docsmcp:end:acceptance-criteria -->

---

<!-- docsmcp:start:definition-of-done -->
## Definition of Done

- [ ] All acceptance criteria pass
- [ ] Unit tests for evidence comment (all 3 sections present, valid markdown)
- [ ] Unit tests for idempotency guard (no existing PR, existing PR found)
- [ ] Integration test: end-to-end publish with mock GitHub API
- [ ] Integration test: duplicate publish -> update path
- [ ] Code passes ruff lint and mypy type check
- [ ] No hardcoded GitHub tokens (from config/env)

<!-- docsmcp:end:definition-of-done -->

---

<!-- docsmcp:start:test-cases -->
## Test Cases

| # | Scenario | Input | Expected Output |
|---|----------|-------|-----------------|
| 1 | First publish | Verified TaskPacket, no existing PR | Draft PR created, evidence comment, labels applied |
| 2 | Duplicate publish | Same TaskPacket ID + intent version | Existing PR updated, no new PR |
| 3 | Evidence comment | TaskPacket + intent + verification result | Formatted markdown with all 3 sections |
| 4 | Label creation | Labels don't exist in repo | Labels created then applied |
| 5 | Label update | PR already has agent:in-progress | Updated to agent:done |
| 6 | Branch exists | Branch already pushed | No error, PR created from existing branch |
| 7 | Status transition | Before publish: verification_passed | After publish: published |
| 8 | GitHub API error | 403 rate limit | Retry with backoff, no partial state |

<!-- docsmcp:end:test-cases -->

---

<!-- docsmcp:start:technical-notes -->
## Technical Notes

- **GitHub API:** Use PyGitHub or httpx for API calls. Authenticate via GitHub App installation token (not PAT).
- **Draft PRs** in Observe tier. Phase 1 Suggest tier may set ready-for-review after QA passes.
- **Evidence comment format** is the minimal Phase 0 version. Phase 1 adds: acceptance criteria checklist, expert coverage, QA result, loopback summary.
- **Single writer to GitHub** is a core architecture principle. Publisher is the only component that writes to GitHub.
- **Architecture references:**
  - System runtime flow: `thestudioarc/15-system-runtime-flow.md` (Step 9: Publish)
  - Overview: `thestudioarc/00-overview.md` (Single writer to GitHub)

<!-- docsmcp:end:technical-notes -->

---

## Files Affected

| File | Action | Description |
|------|--------|-------------|
| `src/publisher/__init__.py` | Create | Package init |
| `src/publisher/publisher.py` | Create | Publisher orchestrator |
| `src/publisher/branch.py` | Create | Branch management |
| `src/publisher/pr.py` | Create | PR creation via GitHub API |
| `src/publisher/evidence_comment.py` | Create | Evidence comment formatting |
| `src/publisher/labels.py` | Create | Lifecycle label management |
| `src/publisher/idempotency.py` | Create | Idempotency guard |
| `tests/test_publisher.py` | Create | Unit and integration tests |

---

<!-- docsmcp:start:dependencies -->
## Dependencies

- **Story 0.5 (Primary Agent):** Produces code changes and evidence bundle
- **Story 0.6 (Verification Gate):** Must pass before Publisher runs
- **External:** GitHub API access (GitHub App installation token)

<!-- docsmcp:end:dependencies -->

---

<!-- docsmcp:start:invest -->
## INVEST Checklist

- [x] **I**ndependent -- Can develop with mock GitHub API
- [x] **N**egotiable -- Comment format, label names, branch convention are flexible
- [x] **V**aluable -- Without Publisher, verified work never reaches GitHub
- [x] **E**stimable -- 8 points, well-understood GitHub API pattern
- [x] **S**mall -- Completable within one sprint
- [x] **T**estable -- 8 test cases with mock-able GitHub API

<!-- docsmcp:end:invest -->

---

*Story created by Saga. Part of Epic 0 — Foundation: Prove the Pipe.*
