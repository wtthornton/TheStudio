# Meridian — Review of thestudioarc & Aggressive Roadmap

**I am not in charge of delivery.** I reviewed the architecture documents and set a **very high, aggressive roadmap** so the bar is visible. Leadership owns resourcing and go/no-go. This is the bar I hold the build to.

---

## Review of thestudioarc

### What’s strong

- **Intent in. Proof out.** The north star is right: explicit intent before implementation, evidence at the end, gates fail closed. No hand-waving.
- **Two planes.** Agent Plane (judgment, synthesis) vs Platform Plane (durability, enforcement, signals) is the right split. Conversation is not source of truth; artifacts and signals are.
- **Single writer to GitHub.** Publisher-only writes. Idempotency, evidence comment, label taxonomy, Projects v2—all specified. That’s how we avoid chaos.
- **Hybrid runtime.** Global control plane vs per-repo execution plane, credential isolation, no repo secrets in the control plane. Scalable and safe.
- **Operational contract.** Retry/timeout/backoff per step, quarantine and dead-letter, flake policy, provenance minimum record, adversarial input policy, compliance gate before Execute. The docs don’t assume “we’ll fix it in prod.”
- **Expert strategy.** Service Context Packs for the long tail; promote Service Experts only when high-change/high-risk. That keeps expert sprawl under control.
- **Key metrics are named.** Single-pass success, verification/QA loopbacks, reopen rate, lead time, cycle time, expert precision, coverage compliance. We can measure.

### What I’m watching

- **Complexity Index** is referenced but not formally defined (formula, dimensions, schema). Without it, normalization and fair attribution are fuzzy. Roadmap forces a defined, measurable Complexity Index by the end of Phase 1.
- **Intake Agent** is in the flow but has no dedicated doc. Behavior and contract (eligibility, TaskPacket creation, dedupe) must be explicit so we don’t under-spec at the door.
- **Evals** (EVALS.md) are high-level. Roadmap commits to a first eval suite (intent correctness, routing correctness, verification friction, QA defect mapping) and a target single-pass rate by Phase 3.
- **Assets** (diagrams) are referenced; many live in `assets/`. Ensure they exist and stay in sync with the numbered docs. No “see diagram” with a broken or stale asset.

### Verdict

The arc is **buildable and measurable**. It’s enough to set an aggressive roadmap. The roadmap below assumes the doc set is the source of truth and pushes for early end-to-end value, then scale and learning.

---

## Aggressive Roadmap — Overview

| Phase | Focus | Target outcome | Timebox (aggressive) |
|-------|--------|-----------------|------------------------|
| **0** | Foundation | One repo, Observe tier, issue → draft PR with evidence; no experts yet. | 8–10 weeks |
| **1** | Full flow + experts | Intent → Router/Assembler → Primary Agent → Verify → QA → Publish; 2 expert classes; Suggest tier; signal stream. | 10–12 weeks |
| **2** | Learning + multi-repo | Outcome Ingestor, Reputation Engine; 3+ repos; Execute tier for 1 repo; Admin UI core (fleet, repo, task console). | 10–12 weeks |
| **3** | Scale + quality bar | Complexity Index defined; 5+ expert classes; Service Context Packs in use; first eval suite; single-pass success target ≥60% (normalized). | 8–10 weeks |
| **4** | Platform maturity | Tool Hub + Model Gateway in production; compliance checker; full Admin UI; 10+ repos or 2+ execution planes; reopen rate & lead time targets. | 10–14 weeks |

**Total aggressive horizon:** ~40–50 weeks to Phase 4 done. No slack in the timeboxes; if we slip, we cut scope per phase, we don’t move the date and pretend scope is the same.

---

## Phase 0 — Foundation (8–10 weeks)

**Goal:** One registered repo, Observe tier. Issue → TaskPacket → Context → Intent → Primary Agent (single role) → Verification → Publisher → draft PR with minimal evidence comment. No expert bench yet; no QA Agent (manual check). Prove the pipe.

**Deliverables**

- Ingress: webhook receive, signature validation, dedupe (delivery id + repo), idempotent TaskPacket create, Temporal workflow start (correlation id).
- TaskPacket: minimal schema (repo, issue id, correlation_id, status, created/updated).
- Context Manager: enrich TaskPacket (scope, risk flags); attach 0..n Service Context Packs (stub or one real pack); compute Complexity Index v0 (e.g. low/medium/high from scope + risk).
- Intent Builder: produce Intent Specification (goal, constraints, acceptance criteria, non-goals); persist; no expert consult yet.
- Primary Agent: single base role (Developer); implement from intent; produce evidence bundle (test/lint summary); no Router/Assembler.
- Verification Gate: run repo-profile checks (e.g. ruff, pytest); emit verification_passed / verification_failed to JetStream; loopback to Primary Agent on failure (max 2 loopbacks for Phase 0).
- Publisher: draft PR only; one evidence comment (TaskPacket id, intent summary, verification result); lifecycle labels (agent:in-progress, then agent:queued or done); idempotency key TaskPacket id + intent version.
- Repo Profile: one repo registered; tier = Observe; required checks and tool allowlist defined.
- Observability: OpenTelemetry traces for flow; correlation_id on all spans.

**Success criteria (Meridian bar)**

- 100% of test issues that meet eligibility result in exactly one TaskPacket and one workflow run (no duplicate workflows).
- 100% of published PRs have evidence comment and correct lifecycle labels.
- Verification failure causes a loopback with evidence; no silent skip.
- One runnable diagram or doc that matches the as-built flow (Intake → Context → Intent → Primary Agent → Verification → Publisher).

**Risks**

- Ingress dedupe wrong → duplicate TaskPackets or workflows. Mitigation: tests with replay of same delivery id; idempotency tests.
- Publisher creates duplicate PRs on retry. Mitigation: idempotency key and lookup-before-create in place before first publish.

---

## Phase 1 — Full flow + experts (10–12 weeks)

**Goal:** Full runtime steps 1–9. Router, Recruiter, Assembler; at least 2 expert classes (e.g. Technical + QA/Validation). Suggest tier: draft PR after verification and QA pass. Signal stream consumed by a stub Outcome Ingestor (no reputation yet). Intent and plan with provenance.

**Deliverables**

- Intake Agent: documented contract (eligibility rules, TaskPacket creation, when to reject); link to Repo Profile and tier.
- Router: select expert subset from intent + risk flags; at least 2 classes (e.g. technical, QA); mandatory coverage rules for risk labels; output consult plan (parallel).
- Recruiter: create expert from template when Router reports gap; qualification harness; register in Expert Library; shadow/probation tier only for new experts.
- Expert Library: persistence and versioning; search by class and capability; at least 2 vetted templates (e.g. Security review, QA validation).
- Assembler: merge expert outputs; resolve conflicts with intent as tie-breaker; produce plan + provenance + QA handoff; trigger intent refinement when needed.
- QA Agent: validate against intent and acceptance criteria; defect taxonomy (intent_gap, implementation_bug, regression, severity); emit qa_passed / qa_defect / qa_rework; loopback to Primary Agent on failure.
- Outcome Ingestor (stub): consume verification and QA signals from JetStream; correlate to TaskPacket; persist for analytics; no reputation update yet (Phase 2).
- Evidence comment: full format (TaskPacket id, intent summary, acceptance criteria checklist, what changed, verification summary, QA result, expert coverage summary, loopback summary).
- Repo: same repo promoted to Suggest tier; draft PR only; ready-for-review only after verification + QA pass.
- Provenance: minimum record fields present on plan and in evidence; traceable to experts and intent version.

**Success criteria (Meridian bar)**

- Every committed workflow uses Intent Specification and at least one expert class when risk flags require it.
- Every PR has provenance and expert coverage in the evidence comment.
- QA defects are classified (category + severity); intent_gap blocks qa_passed.
- Signals for verification and QA are in JetStream and consumable by Outcome Ingestor stub.
- No epic or plan committed without Meridian checklist (personas); no PR without evidence comment.

**Risks**

- Assembler conflict resolution under-specified → inconsistent plans. Mitigation: explicit conflict rules in 07; test with conflicting expert outputs.
- QA taxonomy not enforced → noisy signals. Mitigation: defect category and severity required in qa_defect; schema validation.

---

## Phase 2 — Learning + multi-repo (10–12 weeks)

**Goal:** Outcome Ingestor normalizes by Complexity Index; Reputation Engine updates weights; Router uses weights. Three or more repos registered; at least one repo in Execute tier (full workflow, compliance checker passed). Admin UI core: fleet dashboard, repo management, task/workflow console. Learning loop closed.

**Deliverables**

- Outcome Ingestor: full normalization by Complexity Index (v1); attribution using provenance; produce indicators for Reputation Engine; quarantine and dead-letter handling; reopen event handling.
- Reputation Engine: store weights by expert and context key; compute confidence; trust tier transitions (shadow → probation → trusted); expose weights to Router.
- Router: consume reputation weights and confidence; use in expert selection; mandatory coverage unchanged.
- Complexity Index v1: defined dimensions (e.g. scope breadth, risk flags, dependency count); formula or rubric; stored on TaskPacket; used in normalization and reporting.
- Compliance checker: run before Execute tier promotion; rulesets, required reviewers for sensitive paths, evidence comment format, idempotency guard; results persisted; promotion blocked until pass.
- Execute tier: one repo promoted; full workflow; compliance checker passed; human merge default.
- Admin UI (core): Fleet Dashboard (health, queue, workflows by repo); Repo Management (register, tier, pause, disable writes); Task and Workflow Console (timeline, evidence, safe rerun). RBAC and audit log for actions.
- Multi-repo: at least 3 repos registered; at least 2 in Suggest or Execute; per-repo execution plane or shared plane with repo-scoped credentials.

**Success criteria (Meridian bar)**

- Reputation weights update after each completed task (verification + QA outcomes); Router uses them for next selection.
- Single-pass success rate and verification/QA loopback counts visible in Admin UI (by repo).
- Execute tier repo has passed compliance checker; no promotion without it.
- Quarantined signals have drill-down and replay path; no silent drop.
- Complexity Index is documented and used in at least one report or normalization path.

**Risks**

- Attribution wrong → reputation punishes wrong expert. Mitigation: provenance minimum record; intent_gap vs implementation_bug attribution rules in 06 and 12.
- Compliance checker too loose or too strict → block Execute or allow unsafe repos. Mitigation: checklist from 23 and POLICIES; manual review of first few promotions.

---

## Phase 3 — Scale + quality bar (8–10 weeks)

**Goal:** Complexity Index stable and documented. Five or more expert classes in use. Service Context Packs in use for at least 2 services. First eval suite: intent correctness, routing correctness, verification friction, QA defect mapping. **Single-pass success rate ≥60%** (normalized by complexity, rolling 4-week window). Reopen rate tracked and visible.

**Deliverables**

- Complexity Index: stable schema and rubric; used in Outcome Ingestor, Reputation, and reporting; documented in thestudioarc or ADR.
- Expert classes: at least 5 (e.g. Technical, Business, QA/Validation, Security, Compliance or Partner API); Expert Library and taxonomy updated.
- Service Context Packs: at least 2 packs in use; Context Manager attaches them; pack_missing_detected and pack_used_by_task signals.
- Evals: first suite (intent correctness, routing correctness, verification friction, QA defect mapping); runnable; results in dashboard or report.
- Single-pass success target: ≥60% (verification + QA pass on first attempt, normalized by complexity); tracked in Admin UI or metrics; retro if below.
- Reopen rate: defined (e.g. issue reopened within 30 days of merge); tracked; linked to TaskPacket where possible; attribution (intent_gap vs implementation_bug vs regression).
- Admin UI: Expert Performance Console (weights, confidence, drift by repo/context); Metrics and Trends (single-pass, loopbacks, QA defects, reopen rate).

**Success criteria (Meridian bar)**

- Single-pass success ≥60% for 4 consecutive weeks (or root-cause and remediation plan if not).
- Evals run at least weekly; results visible; at least one improvement action per quarter from eval findings.
- Reopen rate and attribution visible; no “we don’t know why it reopened.”
- At least 2 Service Context Packs in production use; Context Manager uses them in TaskPacket enrichment.

**Risks**

- 60% single-pass is aggressive; may require iteration on intent quality, expert selection, or verification/QA. Mitigation: track by category (lint vs test vs security vs QA); focus improvement on highest-fail categories.
- Evals underpowered → no signal. Mitigation: start with small labeled set; define pass/fail per eval; review false positives/negatives.

---

## Phase 4 — Platform maturity (10–14 weeks)

**Goal:** Tool Hub (MCP) and Model Gateway in production. Compliance checker and Execute tier promotion process stable. Admin UI full (policy/guardrails console, metrics/trends, quarantine, model spend, merge mode). **10+ repos** or **2+ execution planes**. **Reopen rate target** (e.g. &lt;5% within 30 days) and **lead time target** (e.g. P95 from intake to PR opened &lt;X hours) set and tracked. OpenClaw optional and documented if in scope.

**Deliverables**

- Tool Hub: MCP Gateway or equivalent; tool suites and profiles; approved catalog; repo-tier scoping (observe/suggest/execute); tools used by Context Manager and/or Primary Agent in at least one flow.
- Model Gateway: all LLM calls routed through gateway; routing by step, role, tier, complexity; budgets and fallbacks; provider credentials only in gateway; audit record (correlation_id, step, provider, model, tokens, latency, error class).
- Compliance checker: required for Execute promotion; run on schedule or on-demand; results in Admin UI with remediation; no Execute without pass.
- Admin UI: Policy and Guardrails Console; Quarantine operations (view, replay); Model spend and reliability (by repo, step, provider); Ingress dedupe visibility; Merge mode controls; Repo compliance scorecard.
- Scale: 10+ repos registered or 2+ execution planes; at least one plane with 5+ repos.
- Targets: reopen rate (e.g. &lt;5% within 30 days); lead time P95 (intake to PR opened); cycle time P95 (PR opened to merge-ready). Tracked and reviewed monthly.
- OpenClaw: optional; if in scope, sidecar integration per 24; no workflow state or GitHub writes in OpenClaw.

**Success criteria (Meridian bar)**

- No direct provider calls from agents; Model Gateway is the only path; audit record for every call.
- Tool Hub in use for at least one agent (Context or Primary); tool access governed by role and tier.
- Reopen rate and lead/cycle time targets met or remediation plan in place with owner.
- Admin UI supports fleet, repo, task, expert, policy, metrics, quarantine, and model spend without DB access.

**Risks**

- Model Gateway becomes bottleneck or single point of failure. Mitigation: fallbacks and circuit breakers; rate limits and budgets.
- Scale (10+ repos) stresses execution planes or global plane. Mitigation: health checks, backpressure, and capacity planning before hitting 10.

---

## Roadmap discipline (Meridian)

- **No phase exit without success criteria met.** If we can’t measure it, we don’t claim it.
- **Scope cut before date slip.** If the timebox is fixed, we reduce scope for the phase and document what moved to the next phase. We don’t extend the date and keep the same scope without explicit leadership approval.
- **Every phase ships something usable.** Phase 0 = one repo, one flow. Phase 1 = full flow + experts. Phase 2 = learning + multi-repo + Admin UI core. Phase 3 = scale + quality bar + evals. Phase 4 = platform maturity + targets. No “big bang.”
- **thestudioarc is the source of truth.** Build to the docs. When the build diverges, update the docs or fix the build. No “the doc is aspirational.”
- **Personas and checklist.** Saga, Helm, Meridian. No epic or plan committed without the Meridian checklist. No PR without evidence. That’s non-negotiable.

---

## Summary

- **Review:** thestudioarc is buildable and measurable. Complexity Index, Intake contract, and evals need to be made explicit; assets must exist and be current.
- **Roadmap:** Five phases, ~40–50 weeks aggressive. Phase 0 proves the pipe; Phase 1 adds experts and full flow; Phase 2 closes the learning loop and adds multi-repo + Admin UI core; Phase 3 sets the quality bar (60% single-pass, evals, reopen rate); Phase 4 reaches platform maturity (Tool Hub, Model Gateway, 10+ repos or 2+ planes, reopen and lead time targets).
- **Bar:** Success criteria per phase are the bar. I don’t run the build; I hold the build to this bar.

---

*Meridian — VP Success. Reviewer and challenger. Not in charge. Bar set high.*
