---
paths:
  - "src/verification/**"
  - "src/qa/**"
description: "Verification and QA gate rules"
---

# Gate Rules

Verification (deterministic): ruff, pytest, security scan → pass/fail signal
QA (intent validation): acceptance criteria check → pass/defect/rework signal

Gates fail closed. No opinions. No silent skips.
Loopbacks: Verify max 3 retries (45 min), QA max 2 retries (30 min).

Defect taxonomy: intent_gap | implementation_bug | regression
Severity: critical | high | medium | low

All signals flow to Outcome Ingestor → Reputation Engine via NATS JetStream.
