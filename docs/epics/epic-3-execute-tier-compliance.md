# Epic 3 — Execute Tier + Compliance Checker

**Persona:** Saga (Epic Creator)
**Date:** 2026-03-06
**Phase:** 2 (per `thestudioarc/MERIDIAN-ROADMAP-AGGRESSIVE.md`)
**Status:** Complete — Compliance checker, promotion API, tier transitions implemented
**Predecessor:** Epic 2 — Learning + Multi-Repo (complete: learning loop closed — Complexity Index, Outcome Ingestor full, Reputation Engine with tiers/decay/drift, Router uses weights; 98 new tests)
**Timebox:** 4–6 weeks (focused)

---

## 1. Title

Execute Tier + Compliance Checker — Prove Production Readiness with Governance

---

## 2. Narrative

Epic 2 closed the learning loop: the system now learns from outcomes, updates expert reputation, and uses those weights in routing. But no repo has reached Execute tier — the production-ready state where the full workflow runs with real writes, human merge gating, and compliance governance. Without Execute tier, the platform remains a prototype.

Epic 3 delivers Execute tier promotion with a compliance checker gate. The compliance checker validates that a repo meets governance requirements before it can be promoted: rulesets configured, required reviewers for sensitive paths, branch protections, evidence comment format, Publisher idempotency guard, and execution plane health. Only repos that pass compliance can reach Execute tier. This ensures the platform doesn't scale recklessly — every Execute-tier repo is provably safe.

Additionally, Epic 3 expands multi-repo support from 1 to 3+ repos, proving the architecture works beyond a single codebase. At least two repos must reach Suggest or Execute tier.

**The business value:** Execute tier is the Phase 2 headline. It proves the platform can run full production workflows under governance. Without it, the learning loop and reputation system are academic — impressive infrastructure with no production use. Multi-repo proves scale: the platform isn't a single-repo toy.

**Why now:** The learning loop works. Reputation updates. The Router uses weights. The foundation is solid. What's missing is the final gate: compliance-checked production promotion. Every sprint without Execute tier is a sprint where the platform remains a prototype. The aggressive roadmap demands "one repo in Execute with compliance passed" by Phase 2 end.

---

## 3. References

| Reference | Path |
|-----------|------|
| Aggressive Roadmap — Phase 2 | `thestudioarc/MERIDIAN-ROADMAP-AGGRESSIVE.md` lines 108–135 |
| Admin Control UI — Compliance | `thestudioarc/23-admin-control-ui.md` (Repo Compliance Scorecard, Execute Tier Compliance Gate, Repo Compliance Checker sections) |
| Architecture Guardrails | `thestudioarc/22-architecture-guardrails.md` |
| System Runtime Flow | `thestudioarc/15-system-runtime-flow.md` |
| Agent Roles — Compliance overlay | `thestudioarc/08-agent-roles.md` lines 284–294 |
| Repo Profile | `thestudioarc/04-repo-profile.md` |
| Publisher | `thestudioarc/16-publisher-github-app.md` |
| Epic 2 Complete | `docs/epics/epic-2-learning-multi-repo.md` |

---

## 4. Acceptance Criteria (High Level)

### AC-1: Compliance Checker Implementation

- [ ] Compliance checker runs as a platform job (not an agent).
- [ ] Checks include:
  - Rulesets configured with required status checks for the repo
  - Required reviewer rules for sensitive paths (auth, billing, exports, infra) where applicable
  - Branch protections enabled for default branch
  - Standard labels and Projects v2 fields exist
  - Evidence comment format validated (at least one sample PR)
  - Publisher idempotency guard operational
  - Execution plane health OK (workspace, workers, verification runner)
  - Credentials scoped correctly (no over-permissioned tokens)
- [ ] Results are persisted with pass/fail per check, failure reasons, and remediation hints.
- [ ] Compliance checker is idempotent — rerunning produces same result for same repo state.

### AC-2: Execute Tier Promotion Gate

- [ ] Promotion to Execute tier is blocked until compliance checker passes.
- [ ] Promotion workflow records: who triggered, when, compliance score, all check results.
- [ ] Promotion is reversible: Execute tier can be revoked if compliance drifts or issues emerge.
- [ ] Tier transition emits audit event: `tier_changed` with actor, from_tier, to_tier, compliance_score, timestamp.

### AC-3: Execute Tier Behavior

- [ ] Execute tier repos run full workflow: Intake → Context → Intent → Router → Assembler → Implement → Verify → QA → Publish.
- [ ] Publisher has full write credentials for Execute tier (draft PR, ready-for-review, labels, Projects v2).
- [ ] Human merge default: Publisher creates PR and posts evidence, but merge requires human approval. No auto-merge.
- [ ] Execute tier is revocable: if compliance drifts below threshold, repo can be demoted to Suggest.

### AC-4: First Repo Promoted to Execute

- [ ] At least one repo passes compliance checker and is promoted to Execute tier.
- [ ] Promotion is documented with compliance results and audit trail.
- [ ] Full workflow runs successfully on at least one test issue in the Execute-tier repo.
- [ ] Evidence: workflow completes, PR created with evidence comment, awaiting human merge.

### AC-5: Multi-Repo — 3+ Repos Registered

- [ ] At least 3 repos registered with the platform.
- [ ] At least 2 repos in Suggest or Execute tier (not just Observe).
- [ ] Per-repo credential scoping: repo secrets never leak across repos.
- [ ] Repo Profile for each repo includes: language, build commands, required checks, risk paths.

### AC-6: Compliance Visibility (Minimal UI)

- [ ] Compliance results queryable via API (CLI or script can check compliance status).
- [ ] Compliance check failures include remediation hints (what to fix, where).
- [ ] Tier promotion blocked programmatically — not just documented, but enforced in code.

---

## 5. Constraints & Non-Goals

### Constraints

- **Architecture:** Build to `thestudioarc/` docs. When the build diverges, update the docs or fix the build.
- **Compliance checker is a platform job:** Not an agent. Runs on demand or via promotion workflow.
- **Gates fail closed:** Compliance checker failures block promotion. No bypass.
- **Small diffs:** One commit per story. Prefer focused changes.
- **Observability:** Compliance checker emits OpenTelemetry spans with correlation_id.
- **Mypy in the edit loop:** Run mypy during implementation, not just at the end.
- **Human merge default:** No auto-merge even in Execute tier. Human approves and merges.

### Non-Goals

- **Full Admin UI:** Admin UI is Epic 4. This epic provides API/CLI visibility, not a web dashboard.
- **Auto-merge:** Execute tier still requires human merge. Auto-merge is a later enhancement.
- **Compliance drift monitoring:** Continuous compliance monitoring is Phase 4. This epic checks at promotion time.
- **Expert Performance Console:** No expert performance UI. That's Phase 3/4.
- **Model Gateway:** Agents call LLMs directly. Model Gateway is Phase 4.
- **Tool Hub (MCP):** No centralized tool gateway. Phase 4.
- **Second execution plane:** Multi-repo uses shared execution plane. Dedicated per-repo planes are Phase 4.

---

## 6. Stakeholders & Roles

| Role | Responsibility |
|------|----------------|
| **Saga** | Epic definition (this document) |
| **Meridian** | Epic review and plan review |
| **Helm** | Sprint planning and order of work |
| **Developer(s)** | Implementation per stories |
| **thestudioarc/** | Source of truth for architecture |

---

## 7. Success Metrics

| Metric | Target | How measured |
|--------|--------|-------------|
| **One repo in Execute tier** | 1 repo promoted with compliance passed | Repo Profile query + compliance results |
| **Compliance checker blocks invalid promotion** | 100% of promotion attempts without passing compliance are rejected | Audit log review |
| **Multi-repo registered** | ≥3 repos registered | Repo Profile query |
| **Multi-repo in higher tiers** | ≥2 repos in Suggest or Execute | Repo Profile query |
| **Full workflow completes in Execute tier** | At least 1 test issue → PR with evidence | Workflow completion log |
| **Compliance results have remediation hints** | 100% of failures include fix guidance | Compliance result inspection |

---

## 8. Context & Assumptions

### Dependencies

| Dependency | Status | Owner |
|------------|--------|-------|
| Epic 2 codebase (learning loop, 98 tests) | Complete | — |
| PostgreSQL, Temporal, NATS JetStream | Running | Infra (Epic 0/1) |
| Repo Profile with Observe/Suggest tiers | Complete (Epic 1) | — |
| Publisher with draft PR, labels, Projects v2 | Complete (Epic 1) | — |
| Outcome Ingestor full (signals, quarantine) | Complete (Epic 2) | — |
| Reputation Engine (weights, tiers, decay) | Complete (Epic 2) | — |
| Router with reputation-aware selection | Complete (Epic 2) | — |
| thestudioarc/ docs (04, 22, 23) | Published | — |

### Assumptions

- The compliance checker can query GitHub API for rulesets, branch protections, and required reviewers.
- The execution plane health check can verify workspace, workers, and verification runner status via internal APIs.
- The 3+ repos for multi-repo can be test repos or forks; they don't need to be production repos.
- Execute tier "human merge default" means Publisher creates the PR and posts evidence, but a human must approve and merge.
- Compliance check runs synchronously and completes within a reasonable timeout (< 60 seconds).

### Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Compliance checker too strict → no repos reach Execute in timebox | Medium | Start with essential checks (rulesets, required reviewers); add nice-to-have checks incrementally |
| Compliance checker too loose → unsafe repos promoted | High | Follow checklist from `23-admin-control-ui.md`; manual review of first promotions |
| GitHub API rate limits during compliance check | Medium | Cache ruleset/protection queries; batch API calls |
| Multi-repo credential isolation complex | Medium | Use shared execution plane with repo-scoped tokens; verify token scope on registration |
| First Execute-tier repo has unexpected issues | Medium | Choose a well-tested repo (e.g. TheStudio itself or a fork); run full workflow manually first |

---

## Story Decomposition (Preliminary)

Stories should be broken into vertical slices that deliver testable value. Helm will refine ordering, sizing, and sprint boundaries.

**Requirement (Meridian):** Before any story enters a sprint, Helm must define a per-story Definition of Done with testable criteria that references the specific thestudioarc doc. No story is sprint-ready without this.

| Story ID | Title | Dependencies | Size Estimate |
|----------|-------|-------------|---------------|
| 3.1 | Compliance Checker — core checks (rulesets, required reviewers, branch protections) | Repo Profile, GitHub API | L |
| 3.2 | Compliance Checker — execution plane health, Publisher idempotency guard | 3.1, Execution plane APIs | M |
| 3.3 | Execute Tier Promotion — gate, workflow, audit trail | 3.1, 3.2 | M |
| 3.4 | First Repo Promotion — promote one repo to Execute, full workflow test | 3.3 | M |
| 3.5 | Multi-Repo — register 2 additional repos with Repo Profiles | Repo Profile | M |
| 3.6 | Multi-Repo — promote at least 1 additional repo to Suggest/Execute | 3.3, 3.5 | S |

**Total:** 6 stories, ~1 sprint (4–6 weeks focused)

---

## Sprint Recommendation

Given the focused scope (6 stories, no Admin UI), this epic can be completed in a single sprint:

**Sprint 1: Execute Tier + Compliance**
- 3.1: Compliance Checker core
- 3.2: Compliance Checker execution plane
- 3.3: Execute Tier Promotion gate
- 3.4: First repo promoted
- 3.5: Multi-repo registration
- 3.6: Multi-repo tier promotion

**Sprint Goal (testable):** One repo passes compliance checker and is promoted to Execute tier; full workflow completes on a test issue; 3+ repos registered with at least 2 in Suggest or Execute.

---

*Epic created by Saga. Awaiting Meridian review before commit.*
