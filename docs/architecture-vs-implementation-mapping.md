# Architecture vs Implementation Mapping

**Date:** 2026-03-12
**Scope:** 21 of 31 documents in `thestudioarc/` cross-referenced against `src/` implementation and `tests/`
**Methodology:** AI-assisted audit with manual verification against actual file contents. Each claim verified by reading source code.
**Not in scope:** docs `01` (Expert Bench overview), `09` (Service Context Packs detail), `21` (Project Structure), `TOOLS.md`, `EVALS.md`, `SOUL.md`, `AGENTS.md`, `PHASE1-NOTES.md`, `MERIDIAN-ROADMAP-AGGRESSIVE.md`, `README.md`

---

## Legend

| Symbol | Meaning |
|--------|---------|
| THERE | Documented and implemented as described |
| BETTER | Implementation exceeds or improves on the original design |
| NEW | Exists in code but not described in architecture docs |
| MISSING | Described in architecture docs but not yet implemented |

---

## 1. Pipeline Core (9 Stages)

### Stage 1 — Intake (`src/intake/`, doc `00`, `08`)

| Item | Status | Notes |
|------|--------|-------|
| Eligibility evaluation | THERE | `evaluate_eligibility()` pure function with comprehensive rejection logic |
| BaseRole enum (Developer, Architect, Planner) | THERE | Matches doc `08` exactly |
| Overlay enum (8 types) | THERE | Security, Compliance, Billing, Migration, Partner API, Infra, Hotfix, High Risk — matches `08` |
| EffectiveRolePolicy computation | THERE | Mandatory expert classes and strictness levels derived from overlays |
| Label-to-role mapping | THERE | `_select_base_role()` and `_select_overlays()` |
| Admin override of role selection | MISSING | Doc `08` describes admin stage in role selection pipeline; not implemented |

### Stage 2 — Context Manager (`src/context/`, doc `03`)

| Item | Status | Notes |
|------|--------|-------|
| TaskPacket enrichment | THERE | `enrich_taskpacket()` async function |
| Complexity Index | THERE | v1 with 5 dimensions: scope_breadth, risk_flag_count, dependency_count, lines_estimate, expert_coverage |
| Risk flag computation | THERE | Rule-based risk flagger |
| Service Context Pack attachment | THERE | Pack registry, lookup, and attachment |
| Signal emission (pack_used, pack_missing) | BETTER | Signals emitted for observability — doc describes packs but not explicit signal emission at this stage |
| Impacted service identification | THERE | ScopeResult and scope analyzer |
| Open questions / uncertainty recording | MISSING | Doc `03` describes recording uncertainties and dependency gaps; not found in code |

### Stage 3 — Intent Builder (`src/intent/`, doc `11`)

| Item | Status | Notes |
|------|--------|-------|
| Goal statement extraction | THERE | `extract_goal()` regex-based |
| Constraint derivation from risk flags | THERE | Pre-defined mappings from risk flags to constraints |
| Acceptance criteria extraction | THERE | Regex for checkboxes, bullet lists, markdown sections |
| Non-goals extraction | THERE | Pattern matching |
| Intent versioning | THERE | Version tracked in IntentSpecRow |
| Intent refinement loop | THERE | `refinement.py` with update + version increment |
| LLM-based intent extraction | MISSING | Current is Phase 0 rule-based only; doc `11` describes richer semantic extraction |
| Invariant identification | MISSING | Doc `11` lists invariants (what must not change) as a first-class field; not extracted in code |

### Stage 4 — Router (`src/routing/`, doc `05`)

| Item | Status | Notes |
|------|--------|-------|
| Expert subset selection | THERE | `route()` pure function with reputation-weighted scoring |
| Reputation weight consumption | THERE | Injected lookup function from reputation engine |
| Mandatory coverage enforcement | THERE | EffectiveRolePolicy + risk flags drive required classes |
| Budget limits | THERE | Budget enforcement with remaining tracking |
| Recruiter callbacks for gaps | THERE | `RecruiterRequest` dataclass emitted when no candidates match |
| Parallel vs staged consult decisions | MISSING | Doc `05` describes parallel/staged/shadow patterns; code routes all as parallel |
| Shadow consulting | MISSING | Doc `05` describes shadow mode for new experts; not implemented in router |
| Escalation triggers | MISSING | Doc `05` describes escalation for high-risk conflicts; not in router logic |

### Stage 5 — Assembler (`src/assembler/`, doc `07`)

| Item | Status | Notes |
|------|--------|-------|
| Expert output normalization | THERE | Structured ExpertOutput → PlanStep conversion |
| Conflict detection | THERE | `_detect_conflicts()` via assumption comparison |
| Intent-based conflict resolution | THERE | `_resolve_with_intent()` uses constraints as tie-breaker |
| Provenance recording | THERE | ProvenanceRecord with expert identities and decision sources |
| QA handoff mapping | THERE | `_build_qa_handoff()` maps criteria to validation steps |
| Plan generation with checkpoints | THERE | Validation-derived checkpoints inserted into plan |
| Intent refinement request on unresolvable conflicts | THERE | IntentRefinementRequest emitted when needed |
| Escalation of high-risk conflicts per policy | MISSING | Doc `07` says escalate per POLICIES.md; code resolves or requests refinement but doesn't escalate |

### Stage 6 — Primary Agent (`src/agent/`, doc `08`, `15`)

| Item | Status | Notes |
|------|--------|-------|
| Claude Agent SDK integration | THERE | Real integration with `claude_agent_sdk` |
| Evidence bundle production | THERE | EvidenceBundle Pydantic model with full fields |
| Developer system prompt with intent | THERE | Template includes goal, constraints, AC, non-goals |
| Tool allowlist enforcement | THERE | Read, Write, Edit, Glob, Grep, Bash |
| TaskPacket status transition | THERE | RECEIVED → IN_PROGRESS |
| Architect role | MISSING | Only Developer role implemented; doc `08` describes Architect and Planner |
| Planner role | MISSING | Only Developer role; Phase 0 simplification |
| Model budget enforcement per role | MISSING | Doc `08`/`26` describe per-role model budgets; not enforced in agent |

### Stage 7 — Verification Gate (`src/verification/`, doc `13`)

| Item | Status | Notes |
|------|--------|-------|
| Ruff runner | THERE | `runners/ruff_runner.py` async |
| Pytest runner | THERE | `runners/pytest_runner.py` async |
| Fail-closed gate | THERE | Runner errors = verification failure |
| Loopback on failure | THERE | Max 2 per Phase 0 with loopback_count increment |
| Signal emission (pass/fail/exhausted) | THERE | Three distinct signal types |
| Evidence bundle generation | THERE | CheckResult with name, passed, details, duration_ms |
| Flake detection and rerun policy | MISSING | Doc `13` describes max 2 flake reruns per step; not implemented |
| Security scan runner | MISSING | Doc `13` lists security scans as required check; no runner exists |
| Failure categorization system | MISSING | Doc `13` describes categorizing failures; code only has pass/fail |

### Stage 8 — QA Agent (`src/qa/`, doc `14`)

| Item | Status | Notes |
|------|--------|-------|
| Acceptance criteria validation | THERE | Per-criterion results with pass/fail |
| Defect taxonomy (8 categories) | THERE | Matches doc `14` exactly |
| Severity classification (S0-S3) | THERE | Matches doc `14` exactly |
| Intent gap blocking | THERE | intent_gap defects prevent qa_passed |
| Loopback request on failure | THERE | LoopbackRequest dataclass |
| Intent refinement request | THERE | For ambiguous criteria |
| QA expert consultation via Router | MISSING | Doc `14` describes consulting QA experts through Router; not implemented |
| Reopen event handling | MISSING | Doc `14` describes reopen as high-signal outcome; QA agent doesn't consume reopens (outcome module does) |

### Stage 9 — Publisher (`src/publisher/`, doc `15`)

| Item | Status | Notes |
|------|--------|-------|
| Draft PR creation | THERE | Deterministic branch naming from TaskPacket ID + intent version |
| Evidence comment | THERE | EVIDENCE_COMMENT_MARKER for idempotency |
| Tier-based behavior (Observe/Suggest) | THERE | Observe = draft only; Suggest = ready-for-review after gates |
| Label reconciliation | THERE | Tier labels added/removed |
| Idempotency guard | THERE | Branch name + intent version key |
| Execute tier behavior | MISSING | Doc `15`/POLICIES describe Execute tier with auto-merge potential; code only handles Observe and Suggest |
| Projects v2 field reconciliation | MISSING | Doc `15` describes updating GitHub Projects v2 fields; not implemented |
| Reminder cadence for human approval | MISSING | Doc `15` specifies 24h/72h/7d reminders; not implemented |

---

## 2. Cross-Cutting Modules

### TaskPacket Model (`src/models/`, doc `00`, `15`)

| Item | Status | Notes |
|------|--------|-------|
| Durable work record with all enrichments | THERE | Full ORM with scope, risk_flags, complexity, intent ref, loopback_count |
| Status state machine | THERE | ALLOWED_TRANSITIONS dict with explicit valid transitions |
| Idempotent creation (delivery_id + repo) | THERE | ON CONFLICT DO NOTHING |
| Correlation ID | THERE | Generated at creation, flows through pipeline |
| Pydantic read/create models | THERE | TaskPacketCreate, TaskPacketRead |

### Reputation Engine (`src/reputation/`, doc `06`)

| Item | Status | Notes |
|------|--------|-------|
| Weight storage and computation | THERE | In-memory store with sample tracking |
| Confidence calculation (log scaling) | THERE | CONFIDENCE_BASE, CONFIDENCE_MAX parameters |
| Decay with half-life | THERE | DECAY_HALF_LIFE_DAYS constant |
| Drift detection | THERE | DRIFT_WINDOW_SAMPLES parameter |
| Trust tier transitions | THERE | TIER_THRESHOLDS with evidence requirement |
| Router integration | THERE | `get_expert_weights_for_router()` |
| BM25 ranking | MISSING | Doc `06` mentions BM25; not found in code |
| PostgreSQL persistence | MISSING | In-memory only; doc `06` describes DB-backed weights (Phase 2) |
| Attribution principles (intent gap vs expert fault) | MISSING | Doc `06` describes nuanced attribution; outcome ingestor does basic attribution only |

### Outcome Ingestor (`src/outcome/`, doc `12`)

| Item | Status | Notes |
|------|--------|-------|
| Signal ingestion | THERE | `ingest_signal()` async function |
| Complexity normalization | THERE | Normalizes by Complexity Index |
| Provenance-based attribution | THERE | Links signals to expert outputs |
| Quarantine store | THERE | QuarantineStore with reason enums |
| Dead-letter store | THERE | DeadLetterStore for unrecoverable events |
| Replay support | THERE | replay.py module |
| Reopen event handling | THERE | reopen.py module |
| NATS JetStream consumption | MISSING | Outcome ingestor uses in-memory signal store; JetStream not wired for consumption (verification and QA signals do emit to JetStream) |
| Idempotent aggregation | MISSING | Doc `12` describes idempotent replay; code has replay but not idempotent guards |

### Expert Library (`src/experts/`, doc `10`)

| Item | Status | Notes |
|------|--------|-------|
| Expert persistence (ORM) | THERE | ExpertRow with full fields |
| ExpertClass enum (8 types) | THERE | Matches doc taxonomy |
| TrustTier enum (Shadow/Probation/Trusted) | THERE | Matches doc `02`/`04` |
| Lifecycle states (Active/Deprecated/Retired) | THERE | Matches doc `10` |
| Version tracking | THERE | current_version field with update |
| Capability tags for routing | THERE | JSON field for tag-based lookup |
| Seed function for defaults | BETTER | Bootstrap script not described in docs |
| Local expert overlays (repo-scoped) | MISSING | Doc `10` describes global + repo-scoped + service-group-scoped experts; code is global only |
| Deprecation with migration path | MISSING | Lifecycle states exist but no migration workflow |

### Recruiting (`src/recruiting/`, doc `04`)

| Item | Status | Notes |
|------|--------|-------|
| Gap detection | THERE | Triggered by Router when no candidates match |
| Template catalog | THERE | `templates.py` with vetted patterns |
| Expert pack construction | THERE | Scope, procedure, outputs, edge cases, tools |
| Qualification harness | THERE | `qualification.py` with safety checks |
| Trust tier assignment (new recruits) | THERE | COMPLIANCE class forced to shadow; other classes default to template tier (typically probation) |
| Tool policy binding | MISSING | Doc `04` describes minimal tool binding; not formalized in code |
| 8-step recruitment pipeline | MISSING | Doc `04` describes 8 explicit steps; code combines several |

### Observability (`src/observability/`, doc `15`, `20`)

| Item | Status | Notes |
|------|--------|-------|
| OpenTelemetry TracerProvider | THERE | Console and OTLP exporters |
| Correlation middleware | THERE | Request-scoped correlation IDs |
| Span conventions | THERE | Named constants for all pipeline stages |
| Structured logging with correlation_id | THERE | Attribute conventions defined |
| Metrics export | MISSING | Doc `23` describes fleet metrics; no Prometheus/metrics endpoint |

---

## 3. Infrastructure & Governance

### Database & Migrations (`src/db/`)

| Item | Status | Notes |
|------|--------|-------|
| PostgreSQL with asyncpg | THERE | Full async SQLAlchemy setup |
| Custom migration system | BETTER | 18 Python-wrapped SQL migrations (001-018) — docs mention Alembic but project uses custom system that's more controlled |
| pgvector extension | MISSING | Doc `00` mentions pgvector for artifact persistence; not used |

### Workflow Orchestration (`src/workflow/`, doc `15`)

| Item | Status | Notes |
|------|--------|-------|
| Temporal workflow with 9 steps | THERE | Sequential execution with retry policies |
| Step policies (timeout/retry/backoff) | THERE | Matches doc `15` table exactly (2m→60m timeouts) |
| Workflow idempotency key | THERE | TaskPacket ID only (Temporal at-most-once guarantee per workflow ID) |
| Human approval wait states | MISSING | Doc `15`/POLICIES describe 7-day wait with reminders; not implemented |

### Ingress (`src/ingress/`, doc `15`)

| Item | Status | Notes |
|------|--------|-------|
| GitHub webhook receiver | THERE | POST endpoint with HMAC-SHA256 validation |
| Delivery ID deduplication | THERE | Check against database |
| Temporal workflow trigger | THERE | Start workflow on valid webhook |
| Poll scheduler | BETTER | `poll/scheduler.py` for webhook-less environments — not in original docs |

### Admin UI (`src/admin/`, doc `23`)

| Item | Status | Notes |
|------|--------|-------|
| Repo management | THERE | Register, list, update tier, pause |
| Expert management | THERE | List, create, update trust tier |
| Workflow console | THERE | List, rerun, status |
| Health dashboard | THERE | System checks endpoint |
| RBAC with permissions | THERE | `require_permission()` decorator |
| Audit logging | THERE | AuditLogFilter, AuditEventType |
| Settings management (encryption, model config) | THERE | settings_service.py, settings_crypto.py |
| Compliance scorecard | THERE | compliance_scorecard.py |
| HTML templates (45 files) | BETTER | Full server-rendered UI; doc `23` only describes mockups |
| Merge mode configuration | BETTER | merge_mode.py — operational feature not in original design |
| Model spend tracking | BETTER | model_spend.py — operational feature not in docs |
| Expert performance console (weights, drift) | MISSING | Doc `23` describes detailed expert performance views; admin has basic expert management only |
| Policy and guardrails console | MISSING | Doc `23` describes policy violation views; not implemented |
| Quarantine operations UI | THERE | Full quarantine routes (list, detail, replay, delete) in `ui_router.py` with `quarantine.html` + partials |
| Projects v2 drift detection UI | MISSING | Doc `23` describes Projects drift detection; not implemented |
| Execution plane lifecycle controls | THERE | `/planes` routes with register, pause, resume in `ui_router.py` + `planes.html` template |

### Compliance (`src/compliance/`, doc `22`, POLICIES)

| Item | Status | Notes |
|------|--------|-------|
| Compliance checker | THERE | Platform + GitHub-side checks |
| Execution plane checker | THERE | ExecutionPlaneChecker sub-checker |
| Publisher idempotency checker | THERE | PublisherIdempotencyChecker |
| Credential scope checker | THERE | CredentialScopeChecker |
| Tier promotion workflow | THERE | Promotion requires passing compliance |
| Remediation hints | BETTER | Checkers provide actionable fix suggestions — not in original docs |
| Repo compliance scorecard | THERE | Results persisted per POLICIES spec |
| Adversarial input detection | MISSING | POLICIES describes suspicious payload escalation; not implemented |

### Repo Registry (`src/repo/`, doc `15`)

| Item | Status | Notes |
|------|--------|-------|
| Repo profile with tier | THERE | Full ORM with OBSERVE/SUGGEST tiers |
| Status management (Active/Paused/Archived) | THERE | RepoStatus enum |
| Webhook secret encryption | THERE | Encrypted storage and retrieval |
| Tier promotion logic | THERE | tier_promotion.py |
| Execute tier | MISSING | Only OBSERVE and SUGGEST implemented; doc `15`/POLICIES describe EXECUTE |
| Installation ID management | THERE | For GitHub App integration |

---

## 4. Adapter & Integration Layer

### Adapters (`src/adapters/`)

| Item | Status | Notes |
|------|--------|-------|
| GitHub adapter (mock/real) | THERE | Abstract + implementations |
| LLM adapter (mock/real) | THERE | Provider abstraction |
| Model Gateway | THERE | `model_gateway.py` implements ModelRouter with routing rules, fallback chains, budget enforcement, and audit records |

### Model Runtime (doc `26`)

| Item | Status | Notes |
|------|--------|-------|
| Model classes (fast/balanced/strong) | THERE | `ModelClass` enum with FAST, BALANCED, STRONG in `model_gateway.py` |
| Model Gateway with routing rules | THERE | `ModelRouter` class with `DEFAULT_ROUTING_RULES` for 7 pipeline steps |
| Per-step model selection | THERE | Each step has default class + overlay/role/tier overrides via `resolve_class()` |
| Model audit records | THERE | `ModelCallAudit` dataclass + `InMemoryModelAuditStore`; also ModelCallAuditRow in database |
| Fallback chains | THERE | `select_with_fallback()` escalates through model classes when providers exhausted |
| Token/spend caps per task | THERE | `InMemoryBudgetEnforcer` with `per_task_max_spend` and `per_step_token_cap` |
| Claude Code headless as optional provider | MISSING | Not integrated |
| Agent integration with Model Gateway | MISSING | ModelRouter exists but Primary Agent does not call it; agents still use direct LLM adapter |

### Tool Hub / MCP (doc `25`)

| Item | Status | Notes |
|------|--------|-------|
| Tool catalog (DB-backed) | THERE | ToolSuiteRow, ToolEntryRow, ToolProfileRow |
| Tool suite grouping | THERE | Named groups with tool entries |
| Profile-based tool selection | THERE | Profiles select tool subsets |
| MCP integration | MISSING | Doc `25` describes MCP protocol integration; not in code |
| Tool access by EffectiveRolePolicy | MISSING | Tools not gated by role policy at runtime |
| Tool promotion (observe → suggest → execute) | MISSING | No tiered tool access |

### OpenClaw Sidecar (doc `24`)

| Item | Status | Notes |
|------|--------|-------|
| Entire module | MISSING | Optional integration; not started. Expected Phase 3-4 |

---

## 5. Evaluations & Testing

### Evaluation Harness (`src/evals/`)

| Item | Status | Notes |
|------|--------|-------|
| Eval framework | NEW | 7 files including intent_correctness, routing_correctness, qa_defect_mapping |
| Not described in architecture docs | NEW | Emerged from development practice; `EVALS.md` exists but is operational, not architectural |

### Test Infrastructure

| Item | Status | Notes |
|------|--------|-------|
| 1,685 tests across 99 files | BETTER | Doc `21` reported 1,413 tests / 84% coverage; implementation has grown |
| Multi-layer testing (unit/integration/docker/E2E/Playwright) | BETTER | 5 test layers not described in architecture; emerged from engineering |
| Custom test ordering (conftest.py) | NEW | Event-loop pollution prevention — operational concern not in docs |
| Playwright browser tests for Admin UI | NEW | 19 tests for UI rendering — not in architecture docs |

---

## 6. Signal & Event System

| Item | Status | Notes |
|------|--------|-------|
| Signal type constants | THERE | String-based signal types across all pipeline stages |
| In-memory signal store | THERE | Used by outcome ingestor (`_signals` list) and context manager (`_pack_signals` list) |
| NATS JetStream signal emission | THERE | Verification and QA signals emit directly to JetStream via `nats.connect()` |
| NATS JetStream consumption | MISSING | Outcome ingestor consumes from in-memory store, not JetStream; no subscriber wired |
| Event sourcing via JetStream | MISSING | Doc `15` describes JetStream as full event backbone; only partial emission implemented |

---

## 7. Policies & Governance (POLICIES.md)

| Item | Status | Notes |
|------|--------|-------|
| Mandatory coverage triggers | THERE | Enforced through EffectiveRolePolicy → Router |
| Repo tier enforcement (Observe/Suggest) | THERE | Publisher respects tier |
| Execute tier enforcement | MISSING | Third tier not implemented |
| Escalation triggers | MISSING | Doc describes escalation for destructive migrations, privileged access, etc.; not coded |
| Human approval wait states | MISSING | 7-day wait with reminder cadence not implemented |
| Merge policy (human merge default, optional auto-merge) | MISSING | No merge policy enforcement |
| Adversarial input handling | MISSING | No suspicious payload detection |

---

## Summary Counts

| Status | Count | Percentage |
|--------|-------|------------|
| THERE | 98 | 59% |
| BETTER | 11 | 7% |
| NEW | 4 | 2% |
| MISSING | 52 | 32% |
| **Total items** | **165** | **100%** |

---

## Key Takeaways

### What Is There (98 items)
The complete 9-stage pipeline is implemented end-to-end with real logic. Core domain models (TaskPacket, IntentSpec, Expert, RepoProfile), the reputation engine, outcome ingestor, compliance checker, admin UI with RBAC, and workflow orchestration via Temporal all exist and function. The Model Gateway (`model_gateway.py`) provides model class routing, fallback chains, and budget enforcement — though it is not yet wired into the Primary Agent. Verification and QA signals emit to NATS JetStream. The pipeline's key invariant — gates fail closed, loopbacks carry evidence — is enforced.

### What Is Better Than Documented (11 items)
- Admin UI has 45 server-rendered HTML templates; docs only had mockups
- 1,685 tests across 99 files and 5 layers (unit/integration/docker/E2E/Playwright) exceed the documented 1,413
- Custom migration system (18 migrations) is more controlled than the Alembic mentioned in docs
- Poll scheduler enables webhook-less environments (not in original design)
- Compliance checkers provide remediation hints (not in docs)
- Expert seed bootstrap, merge mode config, and model spend tracking are operational improvements

### What Is New (4 items)
- Evaluation harness (`src/evals/`) with intent/routing/QA correctness evals — 2 NEW rows
- Playwright browser test suite for Admin UI
- Custom test ordering to prevent event-loop pollution

Note: Context pack signal emission is classified as BETTER (line 40), not NEW — it extends documented pack behavior with observability signals.

### What Is Missing (52 items) — Triaged

52 line items in the mapping tables are marked MISSING. After deduplication (some gaps span multiple tables), these consolidate into **41 distinct work items** across three priority tiers plus structural items.

**Tier definitions:**
- **CRITICAL** — System violates a POLICIES.md invariant, a documented gate contract, or loses data in its current state
- **VALUABLE** — Improves quality, operability, or capability, but the system functions correctly without it
- **DEFERRED** — Explicitly Phase 2+ by design, or optional integration not on the current roadmap

#### CRITICAL — 8 distinct items (representing 18 raw MISSING entries)

| # | Gap | Size | Done means | MISSING entries | Dependency | Rationale |
|---|-----|------|-----------|----------------|------------|-----------|
| C1 | **Wire Model Gateway into Primary Agent** | M | All agent LLM calls route through `ModelRouter.select_model()`; budget enforcer active per task | Agent integration (line 314) + Model budget per role (line 96) | Standalone | Gateway is built but bypassed — agents ignore routing rules, fallback chains, and budgets |
| C2 | **Execute tier (end-to-end)** | L | EXECUTE enum in RepoTier; Publisher handles Execute behavior; compliance gate enforces Execute policy | Publisher (line 134), Repo Registry (line 288), Policies (line 373) | Depends on C6 (human approval must exist before allowing auto-merge) | 3 entries, 1 gap. Third trust tier is the path to autonomous operation |
| C3 | **JetStream consumption in outcome ingestor** | M | `ingest_signal()` subscribes to JetStream subjects; in-memory store removed as primary path | Outcome JetStream (line 177), Signal consumption (line 362) | JetStream emission already works | Signals are emitted into a void — outcome ingestor reads in-memory only |
| C4 | **Security scan runner** | S | `runners/security_runner.py` exists; gate runs it alongside ruff + pytest | Verification (line 109) | Standalone | Doc `13` lists security scans as required; shipping code without them violates the gate contract |
| C5 | **Escalation triggers** | L | Router and Assembler emit `EscalationRequest` for high-risk conflicts; handler logs + pauses workflow | Router (line 70), Assembler (line 83), Policies (line 374) | Standalone | 3 entries, 1 gap. High-risk conflicts have no escalation path |
| C6 | **Human approval wait states** | L | Temporal workflow has a wait activity after QA; resumes on human signal or 7-day timeout | Workflow (line 235), Policies (line 375) | Standalone (risk: team has not built Temporal timer activities before) | 2 entries, 1 gap. Required by POLICIES for Suggest/Execute tiers |
| C7 | **Reputation PostgreSQL persistence** | M | Reputation weights survive restarts; migration adds weight tables; in-memory store becomes cache layer | Reputation (line 163) | Standalone | Data lost on every restart — correctness problem as soon as system handles real traffic |
| C8 | **Adversarial input detection** | M | Intake rejects or quarantines payloads matching suspicious patterns; compliance checker flags them | Compliance (line 278), Policies (line 377) | Standalone | 2 entries, 1 gap. Suspicious payloads pass through unchecked |

#### VALUABLE — 16 distinct items, ranked by impact (representing 16 raw MISSING entries)

| Rank | # | Gap | MISSING entries | Rationale |
|------|---|-----|----------------|-----------|
| 1 | V1 | **Merge policy enforcement** | Policies (line 376) | No enforcement of human-merge-default; becomes critical once Execute tier (C2) ships |
| 2 | V2 | **Reminder cadence for human approval** | Publisher (line 136) | 24h/72h/7d reminders; operational nicety after C6 ships |
| 3 | V3 | **Event sourcing via JetStream** | Signal system (line 363) | Architectural aspiration; replay already works via replay.py. Depends on C3 |
| 4 | V4 | **Flake detection and rerun policy** | Verification (line 108) | Reduces false failures; max 2 reruns per step |
| 5 | V5 | **Failure categorization system** | Verification (line 110) | Only pass/fail today; no root-cause triage. Note: interacts with C4 (security scan) |
| 6 | V6 | **Attribution principles (nuanced)** | Reputation (line 164) | Intent gap vs expert fault distinction. Depends on C7 (persistence) |
| 7 | V7 | **Invariant identification in intent** | Intent (line 57) | "What must not change" is a first-class field in doc `11`; not extracted |
| 8 | V8 | **Shadow consulting in Router** | Router (line 69) | Allows vetting new experts without affecting outcomes |
| 9 | V9 | **Parallel vs staged consult decisions** | Router (line 68) | All consults run parallel today; staged needed for dependent experts |
| 10 | V10 | **QA expert consultation via Router** | QA (line 122) | QA agent works standalone; could consult domain experts |
| 11 | V11 | **Idempotent aggregation in outcome** | Outcome (line 178) | Replay exists but lacks idempotent guards |
| 12 | V12 | **Expert performance console** | Admin UI (line 261) | Weights, drift, performance views for operators |
| 13 | V13 | **Policy and guardrails console** | Admin UI (line 262) | Policy violation views for operators |
| 14 | V14 | **Projects v2 field reconciliation** | Publisher (line 135) | GitHub Projects v2 field updates |
| 15 | V15 | **Projects v2 drift detection UI** | Admin UI (line 264) | Projects drift detection dashboard |
| 16 | V16 | **Metrics export (Prometheus)** | Observability (line 214) | No fleet metrics endpoint |

#### DEFERRED — Explicitly Phase 2+ or optional by design (10 distinct items)

| # | Gap | MISSING entries | Rationale |
|---|-----|----------------|-----------|
| D1 | **Architect role** | Agent (line 94) | Phase 0 simplification — Developer only |
| D2 | **Planner role** | Agent (line 95) | Phase 0 simplification — Developer only |
| D3 | **LLM-based intent extraction** | Intent (line 56) | Phase 0 is rule-based by design; LLM extraction is Phase 2+ |
| D4 | **Open questions / uncertainty recording** | Context (line 44) | Nice-to-have enrichment; pipeline works without it |
| D5 | **Admin override of role selection** | Intake (line 32) | Label-based selection sufficient for Phase 0 |
| D6 | **Reopen event handling in QA** | QA (line 123) | Outcome module handles reopens; QA doesn't need to consume them directly |
| D7 | **BM25 ranking** | Reputation (line 162) | Mentioned in doc but not core to weight computation |
| D8 | **Local expert overlays (repo-scoped)** | Expert Library (line 191) | Global experts sufficient for Phase 0 |
| D9 | **OpenClaw sidecar** | OpenClaw (line 331) | Optional integration; Phase 3-4 |
| D10 | **Claude Code headless as provider** | Model Runtime (line 313) | Optional provider; not blocking |

#### STRUCTURAL — Process or design gaps, not code (7 items)

- Tool policy binding (Recruiting line 203)
- 8-step recruitment pipeline (Recruiting line 204)
- Deprecation with migration path (Expert Library line 192)
- pgvector extension (Database line 226)
- MCP integration (Tool Hub line 323)
- Tool access by EffectiveRolePolicy (Tool Hub line 324)
- Tool promotion tiers (Tool Hub line 325)

#### Cross-reference: Raw MISSING line → Triage ID

| Lines | Triage ID | Notes |
|-------|-----------|-------|
| 32 | D5 | Admin override |
| 44 | D4 | Open questions |
| 56 | D3 | LLM intent |
| 57 | V7 | Invariants |
| 68 | V9 | Staged consults |
| 69 | V8 | Shadow consulting |
| 70 | C5 | Escalation (Router) |
| 83 | C5 | Escalation (Assembler) |
| 94 | D1 | Architect role |
| 95 | D2 | Planner role |
| 96 | C1 | Model budget per role |
| 108 | V4 | Flake detection |
| 109 | C4 | Security scan |
| 110 | V5 | Failure categorization |
| 122 | V10 | QA expert consultation |
| 123 | D6 | Reopen in QA |
| 134 | C2 | Execute tier (Publisher) |
| 135 | V14 | Projects v2 reconciliation |
| 136 | V2 | Reminder cadence |
| 162 | D7 | BM25 |
| 163 | C7 | Reputation persistence |
| 164 | V6 | Attribution principles |
| 177 | C3 | JetStream consumption (Outcome) |
| 178 | V11 | Idempotent aggregation |
| 191 | D8 | Repo-scoped experts |
| 192 | Structural | Deprecation migration |
| 203 | Structural | Tool policy binding |
| 204 | Structural | 8-step recruitment |
| 214 | V16 | Metrics export |
| 226 | Structural | pgvector |
| 235 | C6 | Human approval (Workflow) |
| 261 | V12 | Expert performance console |
| 262 | V13 | Policy console |
| 264 | V15 | Projects v2 drift UI |
| 278 | C8 | Adversarial input (Compliance) |
| 288 | C2 | Execute tier (Repo Registry) |
| 313 | D10 | Claude Code headless |
| 314 | C1 | Agent-Gateway integration |
| 323 | Structural | MCP integration |
| 324 | Structural | Tool access by role |
| 325 | Structural | Tool promotion |
| 331 | D9 | OpenClaw sidecar |
| 362 | C3 | JetStream consumption (Signal) |
| 363 | V3 | Event sourcing |
| 373 | C2 | Execute tier (Policies) |
| 374 | C5 | Escalation (Policies) |
| 375 | C6 | Human approval (Policies) |
| 376 | V1 | Merge policy |
| 377 | C8 | Adversarial input (Policies) |

**Raw entry count:** 48 lines. Deduplication removes 7 (C2×2, C3×1, C5×2, C6×1, C8×1) = **41 distinct work items**.
Breakdown: 8 Critical + 16 Valuable + 10 Deferred + 7 Structural = **41**.

#### Dependency Graph (Critical items)

```
Arrow means "blocks" (A ──→ B = A must ship before B)

C6 (Human approval) ──→ C2 (Execute tier)
C7 (Reputation persistence) ──→ V6 (Attribution principles)
C3 (JetStream consumption) ──→ V3 (Event sourcing)
C4 (Security scan) ···→ V5 (Failure categorization, nice-to-have interaction)

C1 (Gateway wiring) ← standalone, no blockers
C4 (Security scan) ← standalone, no blockers
C5 (Escalation) ← standalone, no blockers
C7 (Reputation persistence) ← standalone, no blockers
C8 (Adversarial input) ← standalone, no blockers
```

**Recommended build order for Critical tier:**
1. **C1** (Gateway wiring, M) + **C4** (Security scan, S) + **C7** (Reputation persistence, M) — independent, can parallelize
2. **C3** (JetStream consumption, M) + **C5** (Escalation, L) + **C8** (Adversarial input, M) — independent, can parallelize
3. **C6** (Human approval, L) — risk item, Temporal timer activity expertise needed
4. **C2** (Execute tier, L) — depends on C6
