# Pipeline Walkthrough: Persona Chain to Pipeline Execution

**Story:** 14.4 — Persona-to-pipeline walkthrough (the "Rosetta Stone")
**Scenario:** Add a `/health` endpoint to the verification service so monitoring can detect when the gate is down.
**Persona chain:** Saga (epic) → Meridian (review) → Helm (plan) → Meridian (review) → GitHub issue → Intake
**Outcome:** Approved sprint work becomes a GitHub issue; the pipeline processes it end-to-end.

---

## How the Two Layers Connect

```
PERSONA LAYER (strategic planning)          AGENT LAYER (automated execution)
─────────────────────────────────           ──────────────────────────────────

  Saga creates epic
       ↓
  Meridian reviews epic
       ↓
  Helm creates sprint plan
       ↓
  Meridian reviews plan
       ↓
  Approved work → GitHub issue  ──────→  [1. Intake] → [2. Context] → …
                                              ↓
                                         [3. Intent] → [4. Router] → …
                                              ↓
                                         [5. Assembler] → [6. Implement] → …
                                              ↓
                                         [7. Verify] → [8. QA] → [9. Publish]
                                              ↓
                                         Draft PR with evidence comment
```

The persona layer produces **intent and constraints**. The pipeline consumes them.
Everything above the arrow is human-paced strategy. Everything below is machine-paced execution.

---

## Handoff 1 — Saga Creates an Epic

Saga receives a strategic directive: "production monitoring must detect service outages within 60 seconds." She produces an epic using the 8-part structure, condensed here to the fields that matter for downstream consumption.

**Epic 15 (abbreviated):**

```markdown
# Epic 15 — Observability Foundation: Health Checks and Uptime Monitoring

## 1. Title
Every service exposes a `/health` endpoint so monitoring can detect
outages within 60 seconds and page on-call before users notice.

## 2. Narrative
TheStudio runs five services (app, Temporal, PostgreSQL, NATS, Caddy).
Today, the only way to know one is down is to watch logs or wait for
a user report. Docker healthchecks exist but are not surfaced to
external monitoring. A single `/health` endpoint per service, with
a standard response schema, gives monitoring a pull target and gives
the Docker healthcheck a real liveness signal.

## 4. Acceptance Criteria
- AC-1: Each Python service exposes GET /health returning
  {"status": "ok", "service": "<name>", "timestamp": "<iso>"}
  with a 200 when healthy, 503 when degraded.
- AC-2: Docker healthcheck for each service calls /health
  with a 10s interval and 3 retries.
- AC-3: A monitoring integration (or script) queries all
  endpoints and alerts if any returns non-200 for >60s.

## 5. Constraints & Non-Goals
- Constraints: No new dependencies. Response < 50ms. No auth on /health.
- Non-goals: Distributed tracing, APM dashboards, metric aggregation.

## 7. Success Metrics
- MTTD (mean time to detect) for service outage drops from
  "whenever someone notices" to < 60 seconds.
```

**What Saga hands off:** A structured epic with testable acceptance criteria, explicit non-goals, and a measurable success metric. This is the raw material for both Meridian's review and Helm's planning.

---

## Handoff 2 — Meridian Reviews the Epic

Meridian applies her standard checklist (from `meridian-vp-success.md`) to the epic draft. She scores each question Pass or Gap and provides a one-line rationale.

**Meridian's Epic Review:**

| # | Question | Verdict | Note |
|---|----------|---------|------|
| 1 | Is there one measurable success metric? | **Pass** | MTTD < 60s is measurable and readable in production. |
| 2 | Are acceptance criteria testable by script? | **Pass** | AC-1 is a curl + JSON assertion. AC-2 is a `docker inspect` check. AC-3 needs a concrete alert threshold — add the 60s SLA to AC-3 explicitly. |
| 3 | Are non-goals written down? | **Pass** | Distributed tracing, APM, and metric aggregation are explicitly excluded. |
| 4 | If Cursor/Claude implement from this epic alone, do they know what "done" means? | **Gap** | The response schema is specified but the error/degraded behavior is not. Define what "degraded" means (e.g., DB unreachable = 503 with `{"status": "degraded", "reason": "..."}`). |

**Meridian's verdict:** Conditionally approved. Saga must add the degraded-response schema before Helm plans against it.

> "AC-2 is good. AC-3 needs the 60s number stated as a pass/fail threshold, not just a narrative claim. And define what 'degraded' looks like in the response body — the agent will guess if you don't."

Saga updates the epic. Meridian re-reads and confirms. The epic is now approved for planning.

---

## Handoff 3 — Helm Creates a Sprint Plan

Helm takes the approved epic and decomposes it into sprint-sized work. He writes a testable sprint goal (Objective + Test + Constraint) and orders the backlog.

**Sprint Goal (Sprint 22):**

```
Objective: The verification service exposes a /health endpoint that
           returns structured JSON and is checked by Docker healthcheck.

Test:      curl http://localhost:8000/health returns 200 with
           {"status": "ok", "service": "verification", ...} AND
           docker inspect shows the container health as "healthy"
           after 30 seconds of uptime.

Constraint: No new pip dependencies. Endpoint responds in < 50ms.
            Must not break existing /webhook or /api routes.
```

**Ordered Backlog:**

| Order | Story | Points | Dependency | Notes |
|-------|-------|--------|------------|-------|
| 1 | 15.1: Add `/health` route to verification service | 2 | None | Vertical slice: route + handler + response model |
| 2 | 15.2: Add Docker healthcheck to verification container | 1 | 15.1 | Compose change + interval config |
| 3 | 15.3: Add `/health` to remaining services (app, context, intent) | 3 | 15.1 (pattern established) | Repeat the pattern; batch for efficiency |
| 4 | 15.4: Monitoring script that queries all endpoints | 2 | 15.1, 15.3 | Shell script or Python; alert on non-200 > 60s |

**Capacity note:** 8 points committed against 10-point capacity (80% commitment, 20% buffer for unknowns and interrupt work).

**What Helm hands off:** A testable sprint goal, an ordered backlog with dependencies visible, and a capacity check. This is what Meridian reviews next.

---

## Handoff 4 — Meridian Reviews the Plan

Meridian applies her planning checklist (from `meridian-vp-success.md`, Helm section) to the sprint plan.

**Meridian's Plan Review:**

| # | Question | Verdict | Note |
|---|----------|---------|------|
| 1 | Is the sprint goal testable (objective + test)? | **Pass** | Curl command and docker inspect are concrete, scriptable verifications. |
| 2 | Is there a single order of work? | **Pass** | 15.1 → 15.2 → 15.3 → 15.4 is sequential with dependencies marked. |
| 3 | Are dependencies confirmed? | **Pass** | All dependencies are internal (no cross-team). 15.3 depends on the pattern from 15.1 — acceptable. |
| 4 | Is capacity realistic with buffer? | **Pass** | 8/10 points = 80%. Buffer is stated. No red flags. |

**Meridian's verdict:** Approved. No gaps.

> "Clean plan. Order makes sense — establish the pattern in one service, then replicate. The 80% commitment is honest. Ship it."

The plan is now approved. Story 15.1 is the first item to execute.

---

## Handoff 5 — Approved Work Becomes a GitHub Issue

Helm (or automation) creates a GitHub issue from the top-priority story in the approved plan. The issue body carries the intent, acceptance criteria, and constraints forward from the persona layer into the agent layer.

**GitHub Issue `acme/thestudio#87`:**

```markdown
## Add /health endpoint to verification service

**Epic:** 15 — Observability Foundation
**Sprint:** 22
**Story:** 15.1

### Goal

Add a GET /health endpoint to the verification service that returns
structured JSON indicating service health. This is the foundation
pattern that other services will replicate.

### Acceptance Criteria

- [ ] GET /health returns 200 with JSON body:
      `{"status": "ok", "service": "verification", "timestamp": "<ISO 8601>"}`
- [ ] When the database is unreachable, returns 503 with:
      `{"status": "degraded", "service": "verification", "reason": "db_unreachable"}`
- [ ] Endpoint responds in < 50ms under normal conditions
- [ ] No new pip dependencies added
- [ ] Existing /webhook and /api routes are unaffected

### Constraints

- No authentication on /health (it must be callable by Docker healthcheck)
- Response schema must match the standard defined in Epic 15

### Labels

`type:feature`, `epic:15`, `agent:run`
```

**What crosses the boundary:** The `agent:run` label is the trigger. When this issue is labeled, the persona layer's work is done. The pipeline takes over.

---

## Handoff 6 — Intake Processes the Issue

The `agent:run` label fires a GitHub `issues.labeled` webhook. The Intake stage receives it, validates the HMAC signature, checks eligibility gates, and creates a TaskPacket. From here, the pipeline operates exactly as described in the other walkthroughs.

**Eligibility gates (all pass):**

- `agent:run` label present
- Repo registered
- Repo not paused
- No active workflow for this issue

**Role mapping:** `type:feature` → `BaseRole.DEVELOPER`. No risk labels → `overlays=[]`.

**TaskPacket at end of Intake:**

```json
{
  "id": "tp-f1a2b3c4-d5e6-7890-abcd-1234567890ab",
  "repo": "acme/thestudio",
  "issue_id": 87,
  "correlation_id": "corr-a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "received",
  "effective_role": {
    "base_role": "developer",
    "overlays": [],
    "mandatory_expert_classes": [],
    "verification_strictness": "standard",
    "publishing_posture": "ready_after_gate"
  }
}
```

**What happens next:** The TaskPacket flows through Context (enrichment, complexity scoring), Intent (IntentSpec built from the issue's acceptance criteria), Router, Assembler, Implement, Verify, QA, and Publish. For the full stage-by-stage detail, see:

- [Simple bugfix walkthrough](walkthrough-simple-bugfix.md) — happy path, no loopbacks
- [Feature with loopback walkthrough](walkthrough-feature-with-loopback.md) — verification failure and retry

The key point: **the acceptance criteria and constraints written by Saga, stress-tested by Meridian, and planned by Helm are the same criteria the Intent Builder uses to define correctness and the QA Agent uses to validate the implementation.** Nothing is invented by the pipeline. Intent flows from strategy through planning into automated execution.

---

## Where Intent Lives at Each Handoff

| Handoff | Artifact | Intent carrier |
|---------|----------|----------------|
| 1. Saga → Meridian | Epic doc | Acceptance criteria, success metrics, non-goals |
| 2. Meridian → Saga | Review checklist | Gaps and refinements feed back into epic |
| 3. Helm → Meridian | Sprint plan | Testable goal, ordered backlog, constraints |
| 4. Meridian → Helm | Review checklist | Confirmation or gaps feed back into plan |
| 5. Helm → GitHub | Issue body | AC, constraints, and labels (the `agent:run` trigger) |
| 6. GitHub → Pipeline | TaskPacket | Issue content becomes IntentSpec via Intent Builder |

**The invariant:** Intent is defined by humans in the persona layer. The pipeline consumes it, enforces it (gates fail closed), and produces evidence against it. The pipeline never invents scope.

---

## Key Takeaways

1. **Epics are not tasks.** Saga's epic defines the "what" and "why." Helm breaks it into executable stories. The pipeline executes one story at a time.

2. **Meridian is a gate, not a bottleneck.** Her reviews are checklist-driven and async. She catches gaps that would cause the pipeline to guess or loop.

3. **The GitHub issue is the contract boundary.** Everything above it is strategic planning. Everything below it is automated execution. The `agent:run` label is the handoff signal.

4. **Acceptance criteria are the thread.** The same criteria appear in the epic (Saga), survive review (Meridian), enter the sprint plan (Helm), populate the issue body, become the IntentSpec, and are validated by the QA Agent. This traceability is what makes the system accountable.

5. **Gates fail closed.** If Meridian finds a gap, the epic goes back to Saga. If the QA Agent finds a criterion unmet, the implementation loops back. No stage silently passes incomplete work forward.
