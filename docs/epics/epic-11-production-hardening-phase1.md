# Epic 11 — Production Release & Hardening Phase 1

**Author:** Saga
**Date:** 2026-03-10
**Status:** Implementation Complete — All stories delivered, compose validated

---

## 1. Title

Safe to Run Real Workloads — Harden TheStudio's deployed stack with TLS, locked-down ports, proper secrets management, automated database backups, and production-grade Temporal so the platform can process real GitHub issues without operational risk.

## 2. Narrative

TheStudio's application code is tested, the Docker Compose stack starts, smoke tests pass, and the test rig proves the deployed artifacts work. But the gap between "the stack boots" and "the stack is safe to run real workloads" is wide open.

Right now, every service port is published to the host network — PostgreSQL on 5434, Temporal on 7233, NATS on 4222, Temporal UI on 8088. An attacker or misconfigured firewall rule gives direct access to the database, the workflow engine, and the message bus. Secrets are hardcoded in Compose files or stored in a `.env` file with no rotation story. The backup script exists but must be run manually; there is no schedule, no retention validation, and no restore test. Temporal uses `auto-setup:latest` in dev and a pinned `1.25` in prod — neither is production-grade (auto-setup recreates the schema on every restart). There is no TLS anywhere: the app serves plain HTTP, and inter-service communication is unencrypted on the Docker network.

This matters now because Epics 8-10 closed the "does it work" gap. The next workload will be a real GitHub repository with real code, real API keys, and real user expectations. Running that workload on the current infrastructure is an operational liability. One exposed port, one leaked secret, or one lost database is enough to undermine trust before the platform proves its value.

**Roadmap linkage:** This epic is a prerequisite for the aggressive roadmap's Phase 2 ("real repo end-to-end"). Phase 2 requires real API keys, real GitHub webhooks, and real data — none of which can be safely used on the current unhardened stack. Until this epic completes, all real-repo testing is blocked or must happen behind a VPN with accepted risk. This epic directly advances the OKR: "TheStudio processes a real GitHub issue end-to-end with evidence-backed output."

This epic does the minimum required to safely run real workloads. Not Kubernetes. Not multi-region. Not zero-downtime deploys. Just: TLS on the front door, ports locked to the Docker network, secrets out of plaintext, backups that run themselves, and a Temporal deployment that survives restarts.

## 3. References

- Production Compose (current): `infra/docker-compose.prod.yml`
- Dev Compose: `docker-compose.dev.yml`
- Existing backup script: `infra/backup-db.sh`
- Environment template: `infra/.env.example`
- Temporal init SQL: `infra/init-temporal-db.sql`
- Dockerfile: `Dockerfile`
- Epic 8 (Production Readiness): `docs/epics/epic-8-production-readiness.md`
- Epic 9 (Docker Test Rig): `docs/epics/epic-9-docker-test-rig.md`
- Epic 10 (Test Rig Hardening): `docs/epics/epic-10-docker-test-hardening.md`
- Architecture overview: `thestudioarc/00-overview.md`
- Aggressive roadmap: `thestudioarc/MERIDIAN-ROADMAP-AGGRESSIVE.md`
- Pipeline stage mapping: `.claude/rules/pipeline-stages.md`

## 4. Acceptance Criteria

**AC-1: Only HTTP/HTTPS ports are published to the host network.**
`infra/docker-compose.prod.yml` exposes only ports 80 (HTTP redirect) and 443 (HTTPS) on the host via the Caddy reverse proxy. PostgreSQL (5432), Temporal (7233), NATS (4222), and Temporal UI (8080) are accessible only within the Docker network. Services communicate over the internal `thestudio` bridge network. A test from outside the Docker network confirms that connection attempts to PostgreSQL, Temporal, and NATS on their mapped ports are refused.

**AC-2: TLS terminates at the app or a reverse proxy in front of it.**
HTTPS is served on the published port using a valid TLS certificate. For initial deployment, this can be a self-signed certificate with documented instructions for replacing it with a Let's Encrypt or CA-issued certificate. The app rejects plain HTTP connections on the published port (or redirects HTTP to HTTPS). The TLS configuration supports TLS 1.2+ only, with no known-weak cipher suites.

**AC-3: No secrets appear in Compose files, Dockerfiles, or version-controlled files.**
All secrets (database password, encryption key, API keys, webhook secret, TLS private key) are read from environment variables or Docker secrets. The `.env.example` file documents every required secret with generation instructions but contains no real values. The production `.env` file is in `.gitignore`. A `grep -r` for known test secrets (e.g., `thestudio_dev`, `test-webhook-secret`, `hWaGRA3AtIn5jP9TYc3Vu56PS9JQHkFpcekh9PWg7Ac=`) in `infra/docker-compose.prod.yml` returns zero matches.

**AC-4: Database backups run on an automated schedule with verified retention.**
A cron job, Docker healthcheck sidecar, or Compose-native mechanism runs `pg_dump` at least daily. Backups are compressed and stored in a persistent volume or host-mounted directory. Retention policy removes backups older than 30 days. A restore test script (`infra/restore-db.sh` or equivalent) exists and has been run at least once against a fresh PostgreSQL container to verify backup integrity.

**AC-5: Temporal runs in production-grade configuration.**
Temporal uses a pinned, stable image version (not `auto-setup`, not `latest`). Schema migrations are handled explicitly (via `temporal-sql-tool` or init container), not by auto-setup on every restart. Temporal persists its state to PostgreSQL across container restarts. The Temporal UI is either removed from the production Compose file or restricted to internal network access only (not published to host).

**AC-6: All services survive a full `docker compose down && docker compose up` cycle.**
After a clean restart of the entire stack: PostgreSQL data persists (named volume), Temporal workflows are recoverable, NATS JetStream data persists (named volume), and the app reconnects to all dependencies and passes its health check. A test script verifies this cycle.

**AC-7: Production deployment is documented and repeatable.**
A deployment guide (`infra/README.md` or `docs/deployment.md`) covers: prerequisites, secret generation, first-time setup, starting the stack, verifying health, running a backup, restoring from backup, rotating secrets, and common troubleshooting. A new operator can deploy the stack by following the guide without asking questions.

## 4b. Top Risks

1. **TLS complexity scope creep.** Adding a reverse proxy (nginx/Caddy/Traefik) introduces a new service to configure and maintain. Mitigation: use Caddy (zero-config TLS with Let's Encrypt, single binary) or add TLS directly to uvicorn if the deployment is single-node. Keep the proxy configuration minimal — TLS termination and forwarding only.

2. **Temporal migration from auto-setup is non-trivial.** The `auto-setup` image handles schema creation automatically. Moving to a standard Temporal server image requires explicit schema management. Mitigation: use `temporalio/server` with an init container that runs `temporal-sql-tool` for schema setup. Test the migration path on a copy of the dev database before applying to production.

3. **Backup automation on Docker Compose (no native cron).** Docker Compose does not have a built-in scheduler. Mitigation: use a lightweight sidecar container (e.g., `ofelia` scheduler or a simple `alpine` container with crond) or document host-level cron as the backup trigger. Keep it simple.

4. **Port lockdown breaks existing developer workflows.** Developers currently connect to PostgreSQL on `localhost:5434` for debugging. Mitigation: port lockdown applies only to `infra/docker-compose.prod.yml`. The dev Compose file (`docker-compose.dev.yml`) retains published ports for development convenience. Document the distinction clearly.

## 5. Constraints & Non-Goals

### Constraints
- All changes are to infrastructure files (`infra/`, `Dockerfile`, deployment docs). No application code changes unless required for TLS support (e.g., uvicorn TLS flags).
- The dev Compose file (`docker-compose.dev.yml`) must remain unchanged. Developers keep their current local workflow. Production hardening applies only to `infra/docker-compose.prod.yml`.
- No new cloud provider dependencies. The stack must run on any Linux host with Docker and Docker Compose. No AWS/GCP/Azure-specific services.
- TLS certificate provisioning for Let's Encrypt requires a public domain and DNS. Self-signed certificates are acceptable for initial deployment with a documented upgrade path.

### Non-Goals
- **No Kubernetes, Helm, or container orchestration.** Docker Compose on a single host is the target.
- **No multi-node or high-availability deployment.** Single instance of each service.
- **No zero-downtime deployment or blue-green strategy.** Restart-based deployment is acceptable.
- **No centralized logging or log aggregation.** Console/file logging via Docker is sufficient.
- **No network policies or firewall rule management.** Port lockdown is at the Compose level; host firewall is the operator's responsibility (documented).
- **No automated secret rotation.** Rotation is documented as a manual procedure. Automated rotation is future work.
- **No load testing, performance tuning, or resource optimization.** Resource limits in the existing prod Compose file are sufficient for now.
- **No changes to the application's authentication or authorization model.** RBAC stays as-is.
- **No monitoring/alerting stack (Prometheus, Grafana, PagerDuty).** That is a separate epic.

## 6. Stakeholders & Roles

| Role | Who | Responsibility |
|------|-----|----------------|
| **Epic Owner** | Engineering Lead | Scope decisions, priority calls, deployment approval |
| **Tech Lead** | Backend Engineer | Infrastructure changes, Compose hardening, TLS setup |
| **QA** | Meridian (review) | Acceptance criteria validation, security review |
| **DevOps** | Backend Engineer | Backup automation, Temporal migration, deployment guide |
| **Reviewer** | Meridian | Epic and plan review before commit |
| **Operator** | Engineering Lead | First production deployment, guide validation |

## 7. Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Exposed host ports** | Exactly 2 (80 redirect + 443 HTTPS) in prod Compose | `docker compose -f infra/docker-compose.prod.yml config` inspection |
| **TLS grade** | TLS 1.2+ only, no weak ciphers, valid certificate chain | `openssl s_client` or `testssl.sh` scan against deployed instance |
| **Secrets in version control** | Zero real secrets in any tracked file | `git grep` for known secret patterns across the repo |
| **Backup success rate** | 100% of scheduled backups complete without error for 7 consecutive days (trailing indicator — measured post-deployment, not a close gate) | Backup log file or sidecar health check |
| **Restore verification** | At least 1 successful restore test documented before first production workload | Restore script output + verification query results |
| **Temporal restart survival** | Workflows recoverable after `docker compose restart temporal` | Manual or scripted verification: start workflow, restart Temporal, confirm workflow resumes |
| **Full stack restart survival** | All data persists and all services healthy after `docker compose down && up` | Scripted verification with data assertions |
| **Deployment guide usability** | A second engineer deploys the stack from the guide without assistance | Walkthrough by a team member who did not write the guide |

## 8. Context & Assumptions

### Assumptions
- The deployment target is a single Linux host (VPS, EC2 instance, bare metal) with Docker and Docker Compose v2 installed. The host has a public IP address and optionally a domain name.
- The existing `infra/docker-compose.prod.yml` is the starting point. It already has resource limits, restart policies, env var references for secrets, and persistent volumes for PostgreSQL. This epic hardens it further.
- The existing `infra/backup-db.sh` script works correctly for manual backups. This epic wraps it in automation and adds a restore counterpart.
- Temporal `auto-setup` images are not suitable for production because they re-run schema setup on every container start, which can cause issues with existing data. The migration to `temporalio/server` + explicit schema management is a known best practice from Temporal's documentation.
- Self-signed TLS certificates are acceptable for the initial deployment. The team controls the client environment (internal use) and can trust a self-signed cert. The guide must document the upgrade path to Let's Encrypt or CA-issued certificates.
- NATS JetStream persistence via a named volume (`natsdata`) is already configured in the base Compose file. No additional NATS hardening is needed for Phase 1 beyond port lockdown.
- The `infra/.env` file is already in `.gitignore`. This epic verifies and documents this.

### Dependencies
- **Epic 8 (Status: Complete).** Production Compose file, Dockerfile, health checks exist. No blockers.
- **Epic 9 (Status: Complete).** Docker test rig validates the stack boots and serves traffic. No blockers.
- **Epic 10 (Status: In Progress).** Compose dependency ordering fixes. This epic does not conflict — it modifies only `infra/docker-compose.prod.yml`, not `docker-compose.dev.yml`. Proceed in parallel; no file overlap. If Epic 10 introduces changes to the base `infra/docker-compose.yml`, Story 11.1 will rebase on top.
- **Temporal documentation.** Migration from `auto-setup` to `temporalio/server` requires referencing Temporal's official deployment guide for PostgreSQL-backed persistence. **Pre-requisite spike:** Before Story 11.5 begins, confirm that `temporal-sql-tool` works with PostgreSQL 16 and the current `init-temporal-db.sql` schema. Owner: Tech Lead. Estimated spike: 2-4 hours.
- **Domain name and DNS (optional).** Required for Let's Encrypt TLS. Not required for self-signed deployment. Owner: Engineering Lead.
- **`scripts/wait-for-stack.sh` (from Epic 9).** Story 11.6 depends on this script. If not yet delivered by Epic 9, Story 11.6 scope includes creating a prod-specific readiness check script (`infra/wait-for-stack.sh`).

### Systems Affected
- `infra/docker-compose.prod.yml` — port lockdown, TLS proxy, Temporal migration, backup sidecar
- `infra/.env.example` — updated with all required secrets and generation instructions
- `infra/backup-db.sh` — minor updates for automation integration
- `infra/restore-db.sh` — new file, restore and verify script
- `infra/README.md` or `docs/deployment.md` — new file, deployment guide
- `Dockerfile` — possible minor changes for TLS support (if using uvicorn TLS directly)
- `.gitignore` — verify `infra/.env` and TLS private keys are excluded

---

## Story Map

Stories are ordered as vertical slices. Each delivers independently testable hardening. Story 11.1 locks down the network (highest risk reduction). Story 11.2 adds TLS (the public-facing security boundary). Story 11.3 secures secrets. Story 11.4 automates backups. Story 11.5 hardens Temporal. Story 11.6 verifies restart resilience. Story 11.7 documents everything for repeatable deployment.

### Story 11.1: Lock Down Service Ports to Docker Network Only

**As a** platform operator,
**I want** only the HTTPS port exposed to the host,
**so that** PostgreSQL, Temporal, NATS, and Temporal UI are not directly accessible from outside the Docker network.

**Details:**
- In `infra/docker-compose.prod.yml`, remove `ports` mappings from all services except the app (or TLS proxy). For services that currently expose ports (PostgreSQL 5434, Temporal 7233, NATS 4222/8222, Temporal UI 8088), remove the `ports` block entirely or bind only to `127.0.0.1` if host-local access is needed for debugging.
- Define an explicit Docker bridge network (`thestudio-net`) and attach all services to it. Services communicate using their service names as hostnames (already the case with default Compose networking, but explicit is better for production).
- Remove the Temporal UI service from prod Compose entirely, or keep it but without a published port (accessible only via `docker exec` or SSH tunnel if needed).
- Do NOT modify `docker-compose.dev.yml`. Developer workflows are unchanged.

**Acceptance Criteria:**
- `docker compose -f infra/docker-compose.prod.yml config` shows only two published ports: 80 (HTTP redirect) and 443 (HTTPS), both on the Caddy service.
- From the host, `nc -z localhost 5434` (PostgreSQL), `nc -z localhost 7233` (Temporal), and `nc -z localhost 4222` (NATS) all fail with connection refused.
- Services within the Docker network can still communicate (app connects to postgres:5432, temporal:7233, nats:4222).
- `docker-compose.dev.yml` is unchanged.

**Files to modify:**
- `infra/docker-compose.prod.yml` — remove/restrict port mappings, add explicit network

---

### Story 11.2: Add TLS Termination via Reverse Proxy

**As a** platform operator,
**I want** HTTPS on the public-facing port,
**so that** all traffic to TheStudio is encrypted in transit.

**Details:**
- Add a Caddy reverse proxy service to `infra/docker-compose.prod.yml`. Caddy is chosen for zero-config TLS (automatic Let's Encrypt) and minimal configuration.
- Caddy listens on host ports 80 (HTTP redirect) and 443 (HTTPS) and proxies to `app:8000` on the internal network.
- Create `infra/Caddyfile` with reverse proxy configuration. For self-signed/local deployment, use `tls internal`. For production with a domain, use `tls {email}` for automatic Let's Encrypt.
- The app service no longer publishes port 8000 to the host — only Caddy is exposed.
- Add a Caddy data volume for certificate persistence across restarts.
- Document TLS configuration options (self-signed vs. Let's Encrypt) in the deployment guide (Story 11.7).

**Acceptance Criteria:**
- `curl -k https://localhost/healthz` returns 200 with `{"status": "ok"}` (self-signed cert).
- `curl http://localhost/healthz` returns a 301/308 redirect to HTTPS.
- `openssl s_client -connect localhost:443` shows TLS 1.2 or 1.3 negotiation.
- The app service has no host-published ports.
- Caddy data volume persists certificates across `docker compose restart caddy`.

**Files to create/modify:**
- `infra/docker-compose.prod.yml` — add Caddy service, remove app port mapping
- `infra/Caddyfile` — new file, reverse proxy + TLS configuration

---

### Story 11.3: Remove Secrets from Version Control and Enforce .env

**As a** platform operator,
**I want** all secrets managed through environment variables with no real values in tracked files,
**so that** credentials are not leaked through version control.

**Details:**
- Audit `infra/docker-compose.prod.yml` — it already uses `${VARIABLE:?message}` syntax for most secrets. Verify every secret reference is present and has a descriptive error message.
- Update `infra/.env.example` with complete documentation: every required variable, generation commands for each secret type, and clear "REQUIRED" vs "OPTIONAL" labels.
- Verify `infra/.env` is in `.gitignore`. Add `infra/*.pem`, `infra/*.key`, and `infra/*.crt` to `.gitignore` for TLS private keys.
- Add a pre-flight validation script (`infra/check-env.sh`) that reads `.env` (or environment) and verifies: all required variables are set, no variable has a known-insecure default (e.g., `thestudio_dev`), encryption key is valid base64, and PostgreSQL password meets a minimum length (12+ characters).
- Document secret rotation procedure in the deployment guide (Story 11.7).

**Acceptance Criteria:**
- `grep -rn 'thestudio_dev\|test-webhook-secret\|hWaGRA3AtIn5jP9TYc3Vu56PS9JQHkFpcekh9PWg7Ac' infra/docker-compose.prod.yml` returns zero matches.
- `infra/.env.example` documents every secret with generation instructions.
- `.gitignore` contains entries for `infra/.env`, `infra/*.pem`, `infra/*.key`, `infra/*.crt`.
- `infra/check-env.sh` exits 0 with a valid `.env` and exits 1 with clear error messages when secrets are missing or insecure.
- The pre-flight script can be run before `docker compose up` and is referenced in the deployment guide.

**Files to create/modify:**
- `infra/.env.example` — complete documentation
- `infra/check-env.sh` — new file, pre-flight validation
- `infra/docker-compose.prod.yml` — verify/fix secret references
- `.gitignore` — add TLS key patterns

---

### Story 11.4: Automate Database Backups with Retention and Restore Verification

**As a** platform operator,
**I want** daily automated database backups with verified retention and a tested restore procedure,
**so that** I can recover from data loss without manual intervention.

**Details:**
- Add a backup sidecar container to `infra/docker-compose.prod.yml`. Options: a lightweight Alpine container running crond, or the `ofelia` Docker job scheduler. The sidecar runs `pg_dump` against the PostgreSQL container daily, compresses the output, and stores it in a host-mounted backup directory.
- The backup file naming includes a timestamp: `thestudio_YYYYMMDD_HHMMSS.sql.gz`.
- Retention: delete backups older than 30 days (the existing `backup-db.sh` already does count-based retention; switch to date-based for clarity).
- Create `infra/restore-db.sh` that takes a backup file path, restores it to a fresh or existing PostgreSQL container, and runs a verification query (e.g., `SELECT count(*) FROM task_packets`) to confirm data integrity.
- The restore script must work against both a running stack (restore into existing container) and a fresh container (for disaster recovery testing).
- Update the existing `infra/backup-db.sh` to be callable by the sidecar and by operators manually.

**Acceptance Criteria:**
- A backup sidecar runs in the prod Compose stack and produces a `.sql.gz` backup file daily without manual intervention.
- Backups older than 30 days are automatically removed.
- `infra/restore-db.sh <backup_file>` successfully restores data and outputs a verification summary.
- At least one backup-restore cycle has been tested: create data, back up, destroy database volume, restore, verify data exists.
- The backup sidecar logs success/failure to stdout (visible via `docker compose logs backup`).

**Files to create/modify:**
- `infra/docker-compose.prod.yml` — add backup sidecar service
- `infra/backup-db.sh` — minor updates for sidecar compatibility
- `infra/restore-db.sh` — new file, restore and verify script

---

### Story 11.5: Migrate Temporal to Production-Grade Configuration

**As a** platform operator,
**I want** Temporal to run on a stable, production-ready image with explicit schema management,
**so that** workflow state survives restarts and the schema is not recreated on every container start.

**Details:**
- Replace `temporalio/auto-setup:1.25` with `temporalio/server:1.25` (or the latest stable 1.x) in `infra/docker-compose.prod.yml`.
- Add a one-time init container or script that runs `temporal-sql-tool` to set up or migrate the Temporal schema in PostgreSQL. This runs before the Temporal server starts on first deployment.
- Create `infra/temporal-schema-setup.sh` that: checks if the Temporal database schema exists, runs `temporal-sql-tool setup-schema` if it does not, and runs `temporal-sql-tool update-schema` if it does (for future version upgrades).
- Pin the Temporal server version explicitly (no `latest` tag).
- Add a healthcheck to the Temporal service in the prod Compose file (currently missing — only the dev Compose has one via `tctl`).
- The Temporal UI service should be removed from the prod Compose file or made opt-in (commented out with instructions for enabling via SSH tunnel).

**Acceptance Criteria:**
- `infra/docker-compose.prod.yml` uses `temporalio/server:<pinned_version>`, not `auto-setup` or `latest`.
- Temporal schema is created by an explicit script/init container, not by auto-setup on every restart.
- After `docker compose down && docker compose up`, Temporal connects to its existing database without schema errors.
- `infra/temporal-schema-setup.sh` is idempotent: running it multiple times does not corrupt the schema.
- Temporal UI is either removed from prod Compose or has no published host port.

**Files to create/modify:**
- `infra/docker-compose.prod.yml` — replace Temporal image, add init container or script
- `infra/temporal-schema-setup.sh` — new file, schema management script

---

### Story 11.6: Full Stack Restart Resilience Verification

**As a** platform operator,
**I want** a script that proves the entire stack survives a clean restart with all data intact,
**so that** I have confidence that restarts (planned or unplanned) do not cause data loss.

**Details:**
- Create `infra/verify-restart.sh` that: starts the prod stack, creates a known data record (e.g., registers a repo via the admin API), runs a backup, stops the stack (`docker compose down`), starts the stack again (`docker compose up -d`), waits for all services to be healthy, and verifies the data record still exists via the admin API.
- The script uses `scripts/wait-for-stack.sh` if it exists (from Epic 9), or creates `infra/wait-for-stack.sh` as a prod-specific readiness check. This script polls service health endpoints until all services report healthy or a timeout is reached.
- The script tests: PostgreSQL data persistence (named volume), NATS JetStream persistence (named volume), and app reconnection to all dependencies.
- Exit 0 on success, exit 1 with diagnostic output on failure.

**Acceptance Criteria:**
- `infra/verify-restart.sh` runs against the prod Compose stack and exits 0 when data persists across restart.
- The script creates and then verifies at least one data record across the restart boundary.
- The script outputs per-service status (healthy/unhealthy) after restart.
- The script completes in under 5 minutes on a healthy system.
- The script is referenced in the deployment guide as a post-deployment verification step.

**Files to create/modify:**
- `infra/verify-restart.sh` — new file, restart resilience verification

---

### Story 11.7: Production Deployment Guide

**As a** platform operator deploying TheStudio for the first time,
**I want** a step-by-step deployment guide,
**so that** I can set up the production stack without guessing or asking the team.

**Details:**
- Create `docs/deployment.md` (or `infra/README.md`) covering:
  1. **Prerequisites:** Linux host, Docker, Docker Compose v2, domain name (optional), firewall configuration.
  2. **Secret generation:** Step-by-step commands for every secret (PostgreSQL password, encryption key, webhook secret, API keys). Reference `infra/.env.example`.
  3. **First-time setup:** Copy `.env.example` to `.env`, fill in secrets, run `infra/check-env.sh`, run Temporal schema setup (`infra/temporal-schema-setup.sh`), start the stack.
  4. **TLS configuration:** Self-signed (default) vs. Let's Encrypt (requires domain + DNS).
  5. **Verification:** Health check URLs, `infra/verify-restart.sh`, viewing logs.
  6. **Backups:** How backups work (automated via sidecar), how to run a manual backup, how to restore (`infra/restore-db.sh`).
  7. **Secret rotation:** Procedure for rotating each secret type without downtime.
  8. **Troubleshooting:** Common failure modes and diagnostic commands.
- The guide must be followable by someone who has never seen the codebase.

**Acceptance Criteria:**
- The deployment guide exists and covers all 8 sections listed above.
- A team member who did not author the guide can deploy the stack by following it without assistance.
- All scripts referenced in the guide (`check-env.sh`, `temporal-schema-setup.sh`, `backup-db.sh`, `restore-db.sh`, `verify-restart.sh`) exist and are executable.
- The guide includes the expected output of each verification step so the operator knows what "success" looks like.

**Files to create:**
- `docs/deployment.md` — production deployment guide

---

## Meridian Review Status

### Round 1: Complete (2026-03-10)

**Verdict: Not Ready to Commit** — 5 issues identified.

| # | Issue | Resolution |
|---|-------|------------|
| 1 | AC-1 said "exactly 1 port" but Story 11.2 publishes 80+443 | Fixed: AC-1 updated to "ports 80 and 443 only" |
| 2 | No dependency dates; Temporal migration feasibility unconfirmed | Fixed: Added parallel-execution decision for Epic 10, added Temporal spike pre-requisite |
| 3 | `scripts/wait-for-stack.sh` referenced but doesn't exist | Fixed: Story 11.6 now creates `infra/wait-for-stack.sh` if Epic 9 script is absent |
| 4 | No link to OKR or roadmap milestone | Fixed: Added roadmap linkage paragraph to narrative |
| 5 | 7-day backup metric ambiguous (close gate vs trailing) | Fixed: Marked as trailing indicator in success metrics |

### Round 2: Pass (2026-03-10)

**Verdict: Ready to Commit.** All 5 Round 1 fixes verified. Full 7-question checklist passes. Zero red flags.

**Minor observations (not blocking):**
1. If Temporal UI is kept as opt-in, pin the image tag (don't leave `latest`).
2. `infra/.env` is already covered by root `.gitignore` `.env` pattern — explicit entry would be clearer but not required.
3. Backup retention: count-based vs date-based produces near-identical results at daily frequency — story is internally consistent.

**Next step:** Proceed to Helm for sprint planning.
