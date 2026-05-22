# TheStudio — Phase 1 Implementation Plan

**Companion:** [Phase1-Operating-Architecture.pdf](../../code/NLTlabsPE/docs/Phase1-Operating-Architecture.pdf)
**Sibling plans:** [NLTlabsPE](../../code/NLTlabsPE/docs/PHASE-1-IMPLEMENTATION.md) · [AgentForge](../../code/AgentForge/docs/PHASE-1-IMPLEMENTATION.md)
**Issued:** 2026-05-22
**Phase 1 goal:** one portfolio company live end-to-end with zero manual scaffolding between products

## TheStudio's Phase 1 lane

TheStudio owns **build + maintain** for *every* portfolio company — the engineering function. The product is already mature in its own lane (GitHub Issue → reviewed Draft PR with Intent Specs + Saga/Meridian/Helm persona-gated planning + container-isolated production). The Phase 1 work is the **edges** — accepting AF-issued GitHub issues, deploying on PR merge, reporting trust-tier back to AF, and standardizing the per-portfolio repo conventions.

TheStudio is **the smallest Phase 1 surface area** of the three products because the core engine doesn't need to change. Resist the urge to refactor anything that isn't directly load-bearing for the AF↔TheStudio handoff.

## Epics

### EPIC-TS-1 — AF-issued GitHub issue intake

**Sprint:** 2 · **Owner:** TheStudio

**Why this matters.** When AgentForge's `gh-issue-creator` files an issue, TheStudio needs to recognize it, parse the `nlt-trace-id` reference, and carry that ID through TaskPacket → Intent → PR. Without this, every AF-filed issue gets manually retagged.

#### Stories

**STORY-TS-1.1 — Parse AF-issued issue body conventions**
- Extend `src/intake/parser.py` to recognize the AF issue body schema (defined in AF EPIC-AF-3).
- Required fields parsed out of the issue body: `nlt-trace-id`, `portfolio_id`, `customer_event_type`, `severity`.
- Unrecognized issue formats fall through to the existing parser unchanged (don't regress non-AF intake).
- Acceptance:
  - [ ] AF-issued test issue produces a `TaskPacket` with `nlt_trace_id` populated.
  - [ ] Hand-filed issue (no AF metadata) still produces a valid TaskPacket.

**STORY-TS-1.2 — Propagate `nlt-trace-id` through Intent + PR**
- `TaskPacket.nlt_trace_id` (new optional field) flows into Intent Specification and surfaces in the final PR body as `Trace: <nlt-trace-id>`.
- Acceptance:
  - [ ] One round-trip from AF event → issue → PR shows the same trace-id end-to-end (verifiable in OTel).

---

### EPIC-TS-2 — Post-merge deploy hook

**Sprint:** 2 · **Owner:** TheStudio

**Why this matters.** PR merged ≠ portfolio company updated. Today TheStudio stops at "Draft PR with Evidence." For Phase 1, merge → deploy is what closes the operate loop (stage 12 in the walkthrough).

#### Stories

**STORY-TS-2.1 — Deploy-hook configuration per repo**
- New `thestudio_deploy:` block in repo registration (per-portfolio).
- Supported targets v1: `vercel`, `fly`, `render`, `manual-webhook` (POSTs to an arbitrary URL on merge).
- Acceptance:
  - [ ] One test portfolio repo registers with `thestudio_deploy.target=vercel` and PR merge triggers a Vercel deploy.

**STORY-TS-2.2 — Deploy-status feedback to AF**
- After deploy completes (or fails), TheStudio posts a `DeployComplete` event to AF: `POST /tenants/{p}/events` with `event_type=deploy_complete`.
- AF can then trigger operate-agent post-deploy verification (e.g., `finance-monitor` confirms billing still works, `customer-support` confirms response templates load).
- Acceptance:
  - [ ] Successful deploy generates a `deploy_complete` event observable in AF.
  - [ ] Failed deploy generates `deploy_failed` with the failure reason.

---

### EPIC-TS-3 — Trust-tier extension to portfolio repos

**Sprint:** 3 · **Owner:** TheStudio

**Why this matters.** TheStudio's per-repo Trust Tiers (Observe → Suggest → Execute) already exist. Phase 1 extends them so AF can read the tier and decide whether to **auto-merge** (high trust) or **route for human review** (low trust). This is the lever that lets the operate loop run unattended over time.

#### Stories

**STORY-TS-3.1 — Trust-tier API endpoint**
- New `GET /repos/{owner}/{repo}/trust-tier` returning `{ tier: "Observe"|"Suggest"|"Execute", since: <timestamp>, last_promotion_reason: <str> }`.
- Acceptance:
  - [ ] AF can query the tier and gets a JSON response in < 500ms.

**STORY-TS-3.2 — Promotion criteria for portfolio repos**
- Document promotion rules in `thestudioarc/26-trust-tier-promotion.md`.
- Phase 1 rules: repo starts at **Observe**. Promotes to **Suggest** after 2 consecutive Verification + QA gates pass without human override. Promotes to **Execute** after 10 consecutive merges without revert + 90 days of operation.
- Acceptance:
  - [ ] Document blessed by Meridian persona before Sprint 3 starts.
  - [ ] Automated promotion test: simulating 2 clean cycles flips Observe → Suggest.

**STORY-TS-3.3 — Demotion on revert / production incident**
- If a merged PR is reverted within 7 days OR a production incident is filed referencing the PR, demote one tier.
- Acceptance:
  - [ ] Synthetic revert demotes the test repo by one tier.

---

### EPIC-TS-4 — Portfolio-repo conventions (AGENTS.md / SOUL.md templates)

**Sprint:** 1 · **Owner:** TheStudio

**Why this matters.** Each portfolio company's repo needs an `AGENTS.md` (declaring the agents that touch it) and a `SOUL.md` (brand voice + product principles) for TheStudio's persona chain to have a home. Standardize the templates so portfolio #2 onwards is copy-paste.

#### Stories

**STORY-TS-4.1 — Portfolio repo template**
- New `templates/portfolio-repo/` directory with: `AGENTS.md`, `SOUL.md`, `USER.md` (initially empty), `.github/workflows/thestudio-deploy.yml`, `README.md` with the contract.
- Variables: `${PORTFOLIO_NAME}`, `${VERTICAL}`, `${BRAND_VOICE}`, `${DEPLOY_TARGET}`.
- Acceptance:
  - [ ] `scripts/init-portfolio-repo.sh permitly vertical=permits brand_voice=trustworthy` produces a working repo skeleton in one command.

**STORY-TS-4.2 — `AGENTS.md` declares both AF and TheStudio agents**
- The template lists: AF operate-agents that touch the repo (customer-support, billing-ops, finance-monitor) AND TheStudio agents (Primary Agent in container mode, the 5 experts, the persona chain).
- This is the single-source-of-truth for "who is allowed to touch this codebase."
- Acceptance:
  - [ ] Template `AGENTS.md` passes `tapps_validate_changed` for the portfolio repo.

---

### EPIC-TS-5 — Shared substrate adoption

**Sprint:** 1–2 · **Owner:** TheStudio (mostly already done; verification only)

**Why this matters.** TheStudio already vendors Ralph SDK and already runs container-isolated agents. Phase 1's work here is **verification + telemetry alignment**, not new code.

#### Stories

**STORY-TS-5.1 — Emit to the shared OTel collector**
- Existing spans already use OTel; point them at the shared collector hosted by AF (EPIC-AF-6).
- Adopt the common `nlt.*` attribute schema (EPIC-AF-6 STORY-AF-6.2): `nlt.portfolio_id`, `nlt.trace_id`.
- Acceptance:
  - [ ] One TheStudio task produces spans visible in AF's OTel store.

**STORY-TS-5.2 — Confirm Ralph SDK version floor**
- TheStudio's `Dockerfile` vendors Ralph SDK from `/path/to/ralph-claude-code/sdk/`. Pin floor to v2.15+ (matches AF's adoption target in EPIC-AF-8).
- Acceptance:
  - [ ] CI test ensures the vendored SDK version is ≥ v2.15.

---

## Out of scope (do NOT build in Phase 1)

- **Reputation engine v2.** The current per-expert reputation is good enough for Phase 1. Don't rebuild the decay model or drift detection yet — wait for cross-portfolio data to drive the design.
- **Service Context Pack expansion.** The 5 existing experts + Service Context Pack pattern is correct. Don't add experts speculatively. Wait until 3+ portfolios are live and the long tail is visible.
- **Marketplace of expert templates.** Phase 3+.
- **OpenClaw sidecar.** Existing design holds; no Phase 1 work needed.
- **Admin UI rebuild.** The current HTMX admin console is sufficient for one studio operator running 1–2 portfolios. Don't rebuild it yet.
- **Multi-vendor LLM in the Primary Agent.** Phase 2 alongside AF's multi-vendor work.

## Cross-product dependencies

| What TheStudio depends on | From which product | When needed |
|---|---|---|
| GitHub issue body schema (with `nlt-trace-id` convention) | AgentForge (EPIC-AF-3) | Sprint 2 mid |
| Shared OTel collector receiving spans | AgentForge (EPIC-AF-6) | Sprint 1 end |
| AF endpoint accepting deploy-complete events | AgentForge (EPIC-AF-1) | Sprint 2 end |
| Ralph SDK v2.15+ | Ralph (already shipped) | Sprint 1 |

## Definition of Phase 1 done — for TheStudio

- AF-issued GitHub issue produces a TaskPacket with `nlt-trace-id` populated.
- Merge of one PR in the test portfolio repo triggers a real deploy via the configured target (Vercel/Fly/Render).
- AF can query `/repos/.../trust-tier` and get a JSON response that drives auto-merge vs human-review routing.
- One portfolio repo bootstrapped from the template in under 5 minutes.
- TheStudio spans visible in AF's OTel collector with the common `nlt.*` attribute schema.

## ADRs implied by this plan

- **ADR-015** — TheStudio trust-tier promotion criteria for portfolio repos. *Sprint 3.*

(All other Phase 1 ADRs are owned by AF or NLTlabsPE.)
