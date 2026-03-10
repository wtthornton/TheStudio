# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added

- **Production deployment hardening:** Docker entrypoint with auto-migration, unified migration runner (15 migrations), user_roles migration (015), readiness probe (`/readyz`), graceful shutdown (30s), production docker-compose with resource limits
- **Security:** UI auth enforcement on all Admin routes, encryption key validation (rejects placeholder in postgres mode), rate limiting (60/min global, 30/min webhook via slowapi), Tailwind CSS CDN fix
- **CI:** Integration test job with PostgreSQL service container, Python version aligned to 3.12
- **Test coverage:** 7 low-coverage files brought to 100% (+155 tests, 1,395 → 1,550 total, 80% → 83% coverage)
- **Ops:** Database backup script with 30-backup rotation, production .env template

- **Epic 12 — Admin Settings & Configuration UI:** Settings page with 5 sections (API Keys, Infrastructure, Feature Flags, Agent Config, Secrets), Fernet encryption at rest, RBAC enforcement, audit logging, hot reload, input validation, key rotation
- **Post-roadmap hardening:** CI pipeline, security fixes, docs sync, quality debt cleanup (`e26ead1`)
- **Epic 11 — Phase 4 Completion:** Gateway enforcement, compliance wiring, roadmap exit (`781def5`)
- **Epic 10 — Phase 4 Maturity:** Quarantine UI, merge mode, model spend dashboard, execution planes, compliance hardening (`d386434`)
- **Epic 9 — Prove the Pipe:** Integration tests, healthz endpoint, docker-compose (`734d898`)
- **Epic 8 Sprint 2:** Real GitHub/LLM adapters, PostgreSQL persistence layer, deployment config (`5b8d849`)
- **Epic 8 Sprint 1:** Test health improvements, e2e smoke test, coverage baseline (`b14856f`)
- **Epic 7 Sprint 2:** Admin UI for Tool Hub, Model Gateway, Compliance, Targets (`7a663f4`)
- **Epic 7 Sprint 1:** Tool Hub catalog, Model Gateway routing, Compliance Scorecard, Operational Targets (`6ac682c`)
- **Epic 6 Sprint 1:** Context packs, expert expansion, success gate — Phase 3 complete (`7570ae4`)
- **Epic 5 Sprint 1:** Eval suite, metrics APIs, admin UI extensions (`8250241`)
- **Epic 4 Sprint 2:** Admin UI frontend — dashboard, repos, workflows, audit views (`cb0c932`)
- **Epic 4 Sprint 1:** Workflow metrics, RBAC, audit log, admin console (`c384355`)
- **Epic 3:** Compliance checker, multi-repo registration, tier promotion gate
- **Epic 2:** Outcome Ingestor hardening, reputation drift/decay, trust tiers, complexity index
- **Epic 1:** Full-flow expert pipeline — recruiter, templates, expert library, router, assembler
- **Epic 0 — Foundation:** Ingress, TaskPacket, Context Manager, Intent Builder, Primary Agent, Verification Gate, Publisher, Repo Profile, Observability

### Fixed

- Update 26 pre-existing tests for schema drift (`841a6fa`)
