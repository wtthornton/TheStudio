# Pipeline Walkthrough: Feature with Loopback

> Scenario: "Add correlation_id to all structured log entries in the context module"
> This example demonstrates Verification failure, loopback with evidence, QA rejection,
> and the full retry cycle. Gates fail closed. Loopbacks carry evidence. Retries are bounded.

---

## 1. Intake

A GitHub issue is created with labels `["agent:run", "type:feature"]`. The intake webhook
receives the `issues.labeled` event.

`evaluate_eligibility` passes: repository is registered, issue has the `agent:run` trigger label,
and no exclusion labels are present. `_select_base_role` maps `type:feature` to `BaseRole.DEVELOPER`.
Context flags `risk:observability` from the issue body mentioning "logging" and "correlation_id",
which adds the overlay — but since there's no dedicated observability overlay, it stays clean.

```json
{
  "id": "tp-f1a2b3...",
  "repo": "acme/platform",
  "issue_id": 587,
  "correlation_id": "corr-c4d5e6...",
  "status": "received",
  "effective_role": { "base_role": "developer", "overlays": ["security"] }
}
```

The `security` overlay is added because the Context stage (next) flags that logging changes
can accidentally leak sensitive data.

---

## 2. Context

Context Manager scans the repository and identifies affected files in `src/context/`.
Complexity: **medium** (multiple files, cross-cutting concern). Risk flags: `security: true`
(logging changes may expose PII if correlation_id includes user data).

```json
{
  "status": "enriched",
  "scope": {
    "files_touched": [
      "src/context/enrichment.py",
      "src/context/complexity.py",
      "src/context/risk_flags.py"
    ]
  },
  "risk_flags": { "auth": false, "migration": false, "security": true },
  "complexity_index": { "score": 4, "band": "medium" }
}
```

---

## 3. Intent

Intent Builder produces the specification. Note the explicit non-goals and constraints
that will be validated by QA later.

```json
{
  "id": "intent-b7c8d9...",
  "taskpacket_id": "tp-f1a2b3...",
  "version": 1,
  "goal": "Add correlation_id parameter to all structured log calls in src/context/ modules, using the TaskPacket's correlation_id from the current span.",
  "constraints": [
    "correlation_id must come from TaskPacket, not generated fresh",
    "Must not log PII or sensitive fields alongside correlation_id",
    "All log calls must use structlog bound loggers, not stdlib logging"
  ],
  "acceptance_criteria": [
    "Every logger.info/warning/error call in src/context/*.py includes correlation_id as a bound field",
    "No log statement includes fields from: email, password, token, api_key, secret",
    "All logging uses structlog, not stdlib logging module"
  ],
  "non_goals": [
    "Do not add correlation_id to modules outside src/context/",
    "Do not refactor existing log message text"
  ]
}
```

TaskPacket status advances to `intent_built`.

---

## 4. Router

The security overlay from Intake triggers the Router to include a Security expert consult.
Reputation-weighted scoring selects the security expert with highest confidence for
logging/observability context.

```json
{
  "experts_consulted": ["security-logging-v3"],
  "service_context_packs": ["context-module-v2"],
  "mandatory_classes_satisfied": true,
  "publishing_posture": "ready_after_gate"
}
```

---

## 5. Assembler

Assembler merges the security expert guidance (e.g., "ensure no PII fields are bound to
structured loggers") with the service context pack for `src/context/`. Single expert,
so no conflict resolution needed.

```json
{
  "plan_id": "plan-g2h3i4...",
  "decision": "In each file under src/context/, bind correlation_id to the structlog logger at function entry. Use TaskPacket.correlation_id, never generate a new UUID. Exclude any user-identifiable fields from log bindings.",
  "provenance": [
    { "source": "security-logging-v3", "scope": "expert" },
    { "source": "context-module-v2", "scope": "service_context_pack" }
  ]
}
```

---

## 6. Implement (Attempt 1)

Primary Agent (Developer role + Security overlay) edits the three files.
However, the agent accidentally uses `import logging` in one file instead of `structlog`.

```json
{
  "taskpacket_id": "tp-f1a2b3...",
  "intent_version": 1,
  "files_changed": [
    "src/context/enrichment.py",
    "src/context/complexity.py",
    "src/context/risk_flags.py"
  ],
  "agent_summary": "Added correlation_id binding to all log calls across 3 files in src/context/.",
  "loopback_attempt": 0
}
```

TaskPacket status: `in_progress`.

---

## 7. Verify (Attempt 1 -- FAILS)

Verification Gate runs the repo profile checks: `ruff` and `pytest`.

**Ruff fails** with a lint error: `src/context/risk_flags.py` has an unused `import logging`
(the agent imported stdlib logging but used structlog).

```json
{
  "event": "verification_failed",
  "taskpacket_id": "tp-f1a2b3...",
  "correlation_id": "corr-c4d5e6...",
  "loopback_count": 1,
  "checks": [
    {
      "name": "ruff",
      "result": "failed",
      "details": "src/context/risk_flags.py:3:1 F401 `logging` imported but unused",
      "duration_ms": 280
    },
    {
      "name": "pytest",
      "result": "passed",
      "details": "142 passed, 0 failed",
      "duration_ms": 6200
    }
  ]
}
```

**Gate fails closed.** The verification signal includes the specific error, file location,
and rule code. This evidence is attached to the loopback signal sent back to the Primary Agent.

---

## 6. Implement (Attempt 2 -- After Loopback)

Primary Agent receives the loopback signal with evidence:
- File: `src/context/risk_flags.py`
- Error: `F401 logging imported but unused`
- Action: Remove the unused `import logging` statement

The agent fixes the issue, removing the unused import.

```json
{
  "taskpacket_id": "tp-f1a2b3...",
  "intent_version": 1,
  "files_changed": ["src/context/risk_flags.py"],
  "agent_summary": "Removed unused `import logging` from risk_flags.py (ruff F401). structlog is the correct import.",
  "loopback_attempt": 1
}
```

---

## 7. Verify (Attempt 2 -- PASSES)

Both checks pass on retry.

```json
{
  "event": "verification_passed",
  "taskpacket_id": "tp-f1a2b3...",
  "correlation_id": "corr-c4d5e6...",
  "loopback_count": 1,
  "checks": [
    { "name": "ruff", "result": "passed", "details": "0 violations", "duration_ms": 290 },
    { "name": "pytest", "result": "passed", "details": "142 passed, 0 failed", "duration_ms": 6100 }
  ]
}
```

TaskPacket status: `verification_passed`.

---

## 8. QA (Attempt 1 -- FAILS)

QA Agent validates each acceptance criterion against the code changes.

Criterion 1 passes: all log calls in `src/context/*.py` include `correlation_id`.
Criterion 3 passes: all logging uses `structlog`.

**Criterion 2 FAILS**: QA Agent detects that `src/context/enrichment.py` logs a
`repo_config` object that includes an `api_key` field. The intent constraint says
"Must not log PII or sensitive fields alongside correlation_id."

```json
{
  "passed": false,
  "defect_count": 1,
  "criteria_results": [
    {
      "criterion": "Every logger call in src/context/*.py includes correlation_id",
      "passed": true
    },
    {
      "criterion": "No log statement includes fields from: email, password, token, api_key, secret",
      "passed": false,
      "defects": [
        {
          "category": "security",
          "severity": "S1",
          "description": "src/context/enrichment.py:45 logs repo_config which contains api_key field",
          "acceptance_criterion": "No log statement includes fields from: email, password, token, api_key, secret",
          "evidence": "structlog.get_logger().info('enrichment_complete', repo_config=repo_config, correlation_id=correlation_id)"
        }
      ]
    },
    {
      "criterion": "All logging uses structlog, not stdlib logging module",
      "passed": true
    }
  ],
  "has_intent_gap": false
}
```

**QA gate fails closed.** The defect is classified as `security` / `S1` (high severity --
logging sensitive data). The loopback signal carries the exact file, line, and what must change.

---

## 6. Implement (Attempt 3 -- After QA Loopback)

Primary Agent receives the QA loopback with evidence:
- Defect: `security` / `S1`
- File: `src/context/enrichment.py:45`
- Problem: `repo_config` object contains `api_key`, must not be logged
- Fix: Log only safe fields, or exclude sensitive keys

The agent updates the log call to exclude sensitive fields:

```json
{
  "taskpacket_id": "tp-f1a2b3...",
  "intent_version": 1,
  "files_changed": ["src/context/enrichment.py"],
  "agent_summary": "Replaced `repo_config=repo_config` in log binding with safe subset: `repo_name=repo_config.name, complexity=repo_config.complexity`. Excluded api_key and other sensitive fields.",
  "loopback_attempt": 2
}
```

---

## 7. Verify (Attempt 3 -- PASSES)

```json
{
  "event": "verification_passed",
  "taskpacket_id": "tp-f1a2b3...",
  "correlation_id": "corr-c4d5e6...",
  "loopback_count": 2,
  "checks": [
    { "name": "ruff", "result": "passed", "details": "0 violations", "duration_ms": 310 },
    { "name": "pytest", "result": "passed", "details": "142 passed, 0 failed", "duration_ms": 6050 }
  ]
}
```

---

## 8. QA (Attempt 2 -- PASSES)

All three criteria now pass. The sensitive field is no longer logged.

```json
{
  "passed": true,
  "defect_count": 0,
  "criteria_results": [
    { "criterion": "Every logger call in src/context/*.py includes correlation_id", "passed": true },
    { "criterion": "No log statement includes fields from: email, password, token, api_key, secret", "passed": true },
    { "criterion": "All logging uses structlog, not stdlib logging module", "passed": true }
  ],
  "has_intent_gap": false
}
```

TaskPacket status: `qa_passed`.

---

## 9. Publish

Publisher creates a draft PR on the working branch, posts the evidence comment with
full loopback history, and applies lifecycle labels.

```
<!-- thestudio-evidence -->
## TheStudio Evidence

| Field              | Value              |
|--------------------|--------------------|
| TaskPacket ID      | tp-f1a2b3...       |
| Correlation ID     | corr-c4d5e6...     |
| Intent Version     | v1                 |
| Verification       | PASSED (attempt 3) |
| QA                 | PASSED (attempt 2) |

**Goal:** Add correlation_id parameter to all structured log calls in src/context/
modules, using the TaskPacket's correlation_id from the current span.

### Loopback Summary
- Verification loops: 1
  - Loop 1: `ruff F401` — unused `import logging` in risk_flags.py (fixed: removed import)
- QA loops: 1
  - Loop 1: `security/S1` — repo_config with api_key logged in enrichment.py:45 (fixed: log safe subset only)

### Files Changed
- `src/context/enrichment.py` — Added correlation_id binding, removed sensitive field logging
- `src/context/complexity.py` — Added correlation_id binding
- `src/context/risk_flags.py` — Added correlation_id binding, removed unused import

### Expert Coverage
- Security expert (security-logging-v3): logging PII prevention guidance
```

Labels applied: `verification:passed`, `qa:passed`, `agent:human-review`.
TaskPacket status: `published`.

---

## Key Takeaways

1. **Gates fail closed.** Both Verification and QA rejected the change and sent it back
   with specific evidence — not just "failed."

2. **Loopbacks carry evidence.** The Primary Agent didn't guess what was wrong. Each
   loopback included the exact file, line, error code/defect category, and what to fix.

3. **Retries are bounded.** The system allows a maximum number of loopbacks (configured
   per repo profile, default: 2 for verification, 2 for QA). If exceeded, the TaskPacket
   is escalated to human review.

4. **The evidence comment records history.** The PR reviewer can see every loopback,
   what failed, and how it was fixed. No information is lost.

5. **Security overlay influenced routing.** The security risk flag caused the Router to
   include a security expert, whose guidance was validated by QA catching the PII logging issue.
