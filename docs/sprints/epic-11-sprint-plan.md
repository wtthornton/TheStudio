# Sprint Plan: Epic 11 — Production Release & Hardening Phase 1

**Planned by:** Helm
**Date:** 2026-03-10
**Status:** APPROVED — Meridian review passed (2026-03-10)
**Epic:** `docs/epics/epic-11-production-hardening-phase1.md`
**Capacity:** Single developer, 1-week sprint (5 working days, ~6 productive hours/day = 30 hours)

---

## Sprint Goal (Testable Format)

**Objective:** Harden the production Docker Compose stack so that only HTTPS is externally accessible, all secrets are out of version control, backups run automatically, Temporal survives restarts without schema re-creation, and a new operator can deploy from documentation alone.

**Test:** After all stories are complete:
1. `docker compose -f infra/docker-compose.prod.yml config` shows exactly 2 published ports (80, 443) on the Caddy service.
2. `curl -k https://localhost/healthz` returns 200; `nc -z localhost 5434` / `nc -z localhost 7233` / `nc -z localhost 4222` all fail.
3. `grep -rn 'thestudio_dev\|test-webhook-secret' infra/docker-compose.prod.yml` returns zero matches.
4. `infra/verify-restart.sh` exits 0 (data persists across full stack restart).
5. A second person deploys the stack using only `docs/deployment.md` without asking questions.

**Constraint:** 5 working days. Infrastructure files only (`infra/`, docs, `.gitignore`). No application code changes. No cloud provider dependencies. Dev Compose file (`docker-compose.dev.yml`) is not modified.

---

## Ordered Backlog

### Pre-Sprint: Temporal Spike (2-4 hours) — MUST COMPLETE BEFORE SPRINT DAY 3

**What:** Confirm that `temporal-sql-tool` works with PostgreSQL 16 and the current `init-temporal-db.sql` schema. Pull `temporalio/server:1.25.2` (or latest stable 1.25.x), attempt schema setup against a local PG16 container, document the exact commands that work.

**Why before sprint:** Story 11.5 depends on this. If the spike reveals that `temporal-sql-tool` does not work cleanly with PG16, we need time to adjust scope (e.g., use a different schema management approach, or pin a different Temporal version). A 2-hour spike that saves a potential 4-hour dead end is good risk management.

**Output:** A short write-up in `docs/spikes/temporal-pg16-spike.md` with: image version confirmed, exact schema setup commands, any gotchas.

---

### Day 1 (Stories 11.1 + 11.2 + Temporal Spike) — ~7 hours

#### Story 11.1: Lock Down Service Ports (Est: 1.5 hours)

**Sequence rationale:** Highest risk reduction per effort. Every other story builds on top of the hardened Compose file. Do this first so all subsequent changes are made to the locked-down baseline.

**Work:**
- Remove `ports` from postgres, temporal, temporal-ui, nats in `infra/docker-compose.prod.yml`
- Add explicit `thestudio-net` bridge network, attach all services
- Remove temporal-ui service from prod (or comment out with SSH tunnel instructions)
- Retain only Caddy ports (added in 11.2)

**Unknowns:** None significant. Straightforward Compose editing.
**Estimate reasoning:** Small, well-scoped file change. 1 hour of work + 30 min verification (spin up stack, test `nc -z` from host, confirm inter-service communication works).

#### Story 11.2: TLS Termination via Caddy (Est: 2.5 hours)

**Sequence rationale:** Must follow 11.1 because 11.1 removes the app's host port. Caddy replaces it as the only externally published service. Together 11.1+11.2 establish the network perimeter that all other stories assume.

**Work:**
- Add Caddy service to prod Compose (ports 80, 443)
- Create `infra/Caddyfile` with `tls internal` for self-signed, reverse proxy to `app:8000`
- Add `caddy_data` and `caddy_config` volumes
- Remove `ports` from app service
- Verify HTTP-to-HTTPS redirect, TLS negotiation

**Unknowns:**
- Caddy image version to pin (minor — check Docker Hub for latest stable `caddy:2.x-alpine`)
- Whether the app's healthcheck path needs adjustment behind the proxy (likely not — Caddy proxies transparently)

**Estimate reasoning:** New service addition to Compose + new config file. 1.5 hours of work + 1 hour of testing (TLS handshake, redirect behavior, certificate persistence across restart).

#### Temporal Spike (Est: 2-4 hours, parallel with 11.1/11.2 testing)

Start the spike during 11.1/11.2 verification downtime. Pull images, test schema tool.

---

### Day 2 (Story 11.3 + 11.4) — ~6 hours

#### Story 11.3: Secrets Hardening (Est: 2.5 hours)

**Sequence rationale:** With the network perimeter established (11.1+11.2), the next highest-value hardening is removing secrets from tracked files. This is prerequisite to the deployment guide (11.7) which documents secret generation.

**Work:**
- Audit prod Compose for any remaining hardcoded secrets
- Expand `infra/.env.example` with full documentation, generation commands, REQUIRED/OPTIONAL labels
- Create `infra/check-env.sh` — validates all required vars set, no insecure defaults, encryption key is valid base64, PG password >= 12 chars
- Update `.gitignore` with `infra/*.pem`, `infra/*.key`, `infra/*.crt`
- Note: `.env.example` currently has `POSTGRES_PASSWORD=thestudio_dev` as a default — this must be changed to empty with a generation instruction

**Unknowns:**
- Full list of secrets that need generation instructions (need to cross-reference all `${VAR:?msg}` in prod Compose)

**Estimate reasoning:** Audit is fast (grep the Compose file). The `check-env.sh` script is the bulk of the work — validation logic, error messages, edge cases. 1.5 hours scripting + 1 hour testing.

#### Story 11.4: Automated Backups with Restore (Est: 3.5 hours)

**Sequence rationale:** Backups are independent of TLS/secrets but must come before the restart verification (11.6) which exercises the backup. Also needed before the deployment guide (11.7) which documents backup/restore procedures.

**Work:**
- Add backup sidecar to prod Compose (Alpine + crond, runs `pg_dump` daily)
- Update `infra/backup-db.sh` for sidecar compatibility (date-based retention, 30-day cutoff)
- Create `infra/restore-db.sh` — takes backup file, restores to PG, runs verification query
- Test full cycle: create data, backup, destroy volume, restore, verify

**Unknowns:**
- Sidecar approach: Alpine+crond vs. ofelia. Alpine+crond is simpler and has no extra dependency — prefer this.
- Whether `pg_dump` from inside the sidecar needs network access to the PG container (yes, via Docker network — sidecar must be on `thestudio-net`)
- The verification query (`SELECT count(*) FROM task_packets`) assumes the table exists — need to handle fresh databases gracefully in the restore script

**Estimate reasoning:** This is the most complex story per-line-of-code because it involves a sidecar container, cron scheduling, two scripts, and a full backup-restore cycle test. 2 hours of scripting + 1.5 hours of testing the full cycle.

---

### Day 3 (Story 11.5) — ~4 hours

#### Story 11.5: Temporal Production Migration (Est: 4 hours)

**Sequence rationale:** Depends on the Temporal spike completing successfully. Must come after 11.1 (which removes Temporal's host port) and before 11.6 (which verifies restart resilience including Temporal).

**Work:**
- Replace `temporalio/auto-setup:1.25` with `temporalio/server:<pinned_version>` (version confirmed by spike)
- Create `infra/temporal-schema-setup.sh` — idempotent schema creation/migration using `temporal-sql-tool`
- Add init container or entrypoint wrapper to run schema setup before Temporal starts
- Add healthcheck to Temporal service in prod Compose
- Pin temporal-ui image tag if kept as opt-in

**Unknowns (to be resolved by spike):**
- Exact `temporal-sql-tool` commands for PG16
- Whether schema setup needs a separate Docker image (`temporalio/admin-tools`) or can run from the server image
- Init container vs. entrypoint script — Compose does not natively support init containers; likely need an entrypoint wrapper or a `depends_on` with a one-shot schema container

**Estimate reasoning:** Highest uncertainty story. The spike de-risks the core question but integration into Compose (init container pattern, healthcheck, restart behavior) takes careful work. 2.5 hours of implementation + 1.5 hours of testing (restart cycle, schema idempotency).

---

### Day 4 (Story 11.6) — ~3 hours

#### Story 11.6: Full Stack Restart Resilience Verification (Est: 3 hours)

**Sequence rationale:** This is the integration test for everything in 11.1-11.5. Must come after all infrastructure changes are in place. Cannot verify restart resilience of Temporal if 11.5 is not done.

**Work:**
- Create `infra/verify-restart.sh` — starts prod stack, creates test data via admin API, backs up, runs `docker compose down && up`, waits for health, verifies data persists
- Use existing `scripts/wait_for_stack.py` (Python, underscores) as reference. Note: the epic references `scripts/wait-for-stack.sh` (shell, hyphens) which does not exist — the actual file is `scripts/wait_for_stack.py`. Create a new shell-based `infra/wait-for-stack.sh` for prod (no Python dependency on the host — only Docker and bash required)
- Test PostgreSQL data persistence, NATS JetStream persistence, Temporal workflow recovery, app reconnection

**Unknowns:**
- Admin API endpoint for creating test data — need to check what's available on the running prod stack
- Whether `scripts/wait_for_stack.py` can be adapted or if a fresh shell script is cleaner (likely fresh shell script — prod hosts should not require Python)

**Estimate reasoning:** Scripting the happy path is 1.5 hours. The tricky part is handling timing (how long to wait for services, race conditions on startup). 1.5 hours of testing and edge-case handling.

---

### Day 5 (Story 11.7 + buffer) — ~4 hours work + 2 hours buffer

#### Story 11.7: Production Deployment Guide (Est: 4 hours)

**Sequence rationale:** Last because it documents everything built in 11.1-11.6. Writing docs before the implementation is stable leads to rework. The guide references every script created in earlier stories.

**Work:**
- Create `docs/deployment.md` covering all 8 sections from the story
- Include expected output for each verification step
- Cross-reference all scripts: `check-env.sh`, `temporal-schema-setup.sh`, `backup-db.sh`, `restore-db.sh`, `verify-restart.sh`
- Document self-signed vs. Let's Encrypt TLS paths
- Document secret rotation (manual procedure)
- Document common troubleshooting scenarios

**Unknowns:**
- Troubleshooting section depends on issues encountered during Days 1-4 — capture notes as you go

**Estimate reasoning:** Documentation for 6 prior stories covering 8 required sections. Not trivial — this is operator-facing and must be self-contained. 3 hours of writing + 1 hour of review and cross-checking against actual scripts.

---

## Dependency Map

| Dependency | Owner | Status | Blocks |
|---|---|---|---|
| Epic 8 (Production Readiness) — prod Compose, Dockerfile, healthchecks | Complete | Done | Nothing blocked |
| Epic 9 (Docker Test Rig) — stack boots, smoke tests pass | Complete | Done | Nothing blocked |
| Epic 10 (Test Rig Hardening) — Compose dependency ordering | In Progress | Parallel, no file overlap | Low risk — only touches `docker-compose.dev.yml` |
| `scripts/wait_for_stack.py` (from Epic 9) | Exists | Available | 11.6 will create shell equivalent for prod |
| Temporal spike (PG16 + temporal-sql-tool) | Sprint developer (single-person sprint) | NOT STARTED | Blocks 11.5 |
| Domain name + DNS (optional) | Eng Lead | Not required for self-signed | Does not block sprint |
| `infra/docker-compose.prod.yml` baseline | Exists | Available | Starting point for 11.1 |
| `infra/backup-db.sh` | Exists | Available | Starting point for 11.4 |
| `infra/.env.example` | Exists | Available | Starting point for 11.3 |

### Internal Story Dependencies (Sequence Constraints)

```
Temporal Spike ---------> 11.5
11.1 --> 11.2 ----------> 11.5 --> 11.6 --> 11.7
              \-> 11.3 --------/
              \-> 11.4 --------/
```

- 11.1 must precede 11.2 (Caddy replaces app's host port)
- 11.3 and 11.4 can run in parallel after 11.1+11.2
- 11.5 requires the Temporal spike AND 11.1 (port lockdown)
- 11.6 requires 11.1-11.5 all complete (integration test)
- 11.7 requires 11.1-11.6 all complete (documents everything)

---

## Estimation Summary

| Story | Estimate | Confidence | Key Risk |
|---|---|---|---|
| Temporal Spike | 2-4 hrs | Medium | PG16 compatibility unknown |
| 11.1 Port Lockdown | 1.5 hrs | High | Low risk — Compose edits only |
| 11.2 TLS/Caddy | 2.5 hrs | High | Caddy is well-documented; self-signed path is simple |
| 11.3 Secrets | 2.5 hrs | High | `check-env.sh` validation logic is the bulk |
| 11.4 Backups | 3.5 hrs | Medium | Sidecar cron + restore cycle testing |
| 11.5 Temporal Migration | 4 hrs | Medium-Low | Highest uncertainty — depends on spike outcome |
| 11.6 Restart Verification | 3 hrs | Medium | Timing/race conditions in startup sequence |
| 11.7 Deployment Guide | 4 hrs | Medium | Time-consuming; also the overflow absorber, so effective confidence is conditional |
| **Total** | **23-25 hrs** | | |

### Big Estimates = Big Unknowns

- **11.5 (4 hrs, Medium-Low confidence):** The Temporal migration is the riskiest story. The `auto-setup` to `temporalio/server` migration path is documented by Temporal but not battle-tested in our stack. The spike is the mitigation. If the spike reveals major issues, we have two options: (a) descope to keeping auto-setup with a documented migration plan for Phase 2, or (b) extend the sprint by 1 day.
- **11.4 (3.5 hrs, Medium confidence):** Backup automation sounds simple but the full cycle test (create data, backup, destroy, restore, verify) touches multiple moving parts. The restore script must handle both fresh and existing databases.

---

## Capacity Allocation

| Category | Hours | % of 30-hour sprint |
|---|---|---|
| Planned story work | 23-25 | 77-83% |
| Buffer for unknowns | 5-7 | 17-23% |
| **Total** | **30** | **100%** |

Buffer is allocated primarily to:
1. Temporal spike overrun (if PG16 has issues) — up to 2 hours
2. Story 11.5 integration surprises — up to 2 hours
3. General testing/debugging across all stories — up to 3 hours

**If we run over:** Story 11.7 (Deployment Guide) is the most compressible. We can ship a minimal guide covering prerequisites + secret generation + first-time setup and defer the troubleshooting and secret rotation sections to a fast follow-up.

**What won't fit this sprint:** Automated Let's Encrypt certificate provisioning (requires domain + DNS setup). The sprint delivers self-signed TLS with documented upgrade path. Let's Encrypt is a follow-up task when a domain is available.

---

## Daily Plan Summary

| Day | Stories | Hours | Cumulative |
|---|---|---|---|
| 1 | 11.1 + 11.2 + Temporal Spike (start) | ~7 (intentional front-load, 1hr from buffer) | 7 |
| 2 | 11.3 + 11.4 + Temporal Spike (finish) | ~6-8 | 13-15 |
| 3 | 11.5 | ~4 | 17-19 |
| 4 | 11.6 | ~3 | 20-22 |
| 5 | 11.7 + buffer overflow | ~4+buffer | 24-28 |

---

## Meridian Review

### Review: Pass (2026-03-10)

**Verdict: Ready to Commit.** Zero auto-reject red flags. 5 non-blocking items addressed:

| # | Item | Resolution |
|---|------|------------|
| 1 | No lessons from prior sprints | Added "Lessons from Prior Sprints" section |
| 2 | Temporal spike ownership unclear | Clarified as sprint developer (single-person sprint) |
| 3 | Day 1 exceeds 6-hour capacity | Acknowledged as intentional front-load, 1hr from buffer |
| 4 | `wait-for-stack` naming discrepancy | Added explicit note in Story 11.6 about `.py` vs `.sh` |
| 5 | Story 11.7 confidence mismatch | Reframed from "High" to "Medium" given overflow absorber role |

**Next action:** Begin execution. Start with Temporal spike + Story 11.1.

---

## Lessons from Prior Sprints

No formal retrospectives were conducted for Epics 8-10. Observed patterns:
- **Compose-related stories estimate well** — file edits are predictable, testing catches issues quickly.
- **Script creation is routinely underestimated** — backup, restore, and verification scripts require edge-case handling that adds 30-50% to initial estimates. Estimates for 11.4 and 11.6 include this padding.
- **Documentation stories compress** — when time is short, docs get cut first. This sprint explicitly designates 11.7 as the compressible story to make that trade-off intentional rather than accidental.

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Temporal `temporal-sql-tool` does not work with PG16 | Low-Medium | High (blocks 11.5) | Spike before Day 3; fallback to keeping auto-setup with documented plan |
| Caddy configuration issues with internal TLS | Low | Medium (delays 11.2) | Caddy docs are excellent; self-signed is the simplest path |
| Backup sidecar cron fails silently | Medium | Medium (11.4 appears done but is not) | Sidecar logs to stdout; verify with `docker compose logs backup` |
| Epic 10 changes conflict with prod Compose | Low | Low (different files) | Epic 10 targets dev Compose only; no overlap |
| Restart verification script has timing issues | Medium | Low (debugging cost) | Build in generous wait times; use healthcheck polling, not sleep |
