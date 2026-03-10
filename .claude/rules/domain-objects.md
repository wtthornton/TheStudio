---
paths:
  - "src/**/*.py"
description: "TheStudio core domain objects"
---

# Domain Objects

**TaskPacket** — Durable work record for a GitHub issue. Fields: repo_id, issue_id, correlation_id, status, risk_flags, complexity_index, role + overlays, timeline. Never create a new one outside src/intake/.

**Intent Specification** — Definition of correctness. Fields: goal, constraints, invariants, acceptance_criteria, non_goals, assumptions, version. Versioned on refinement. Created in src/intent/ only.

**EffectiveRolePolicy** — Runtime policy = base role (Developer|Architect|Planner) + overlays (Security|Compliance|Billing|Migration|Hotfix|HighRisk) + repo profile. Computed, not stored.

**Evidence Bundle** — Test results, lint output, security findings, QA defects. Attached to TaskPacket. Never fabricated.

All cross-module communication via artifacts and signals, never conversational state.
