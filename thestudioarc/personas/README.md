# TheStudio Personas

Personas that represent best-in-class roles for epic creation, planning/dev management, and success accountability. Designed for a team using **Cursor** and **Claude** (2026 tools and features) and aligned with TheStudio architecture.

---

## Reset & train

- **Reset (start here):** [TEAM.md](TEAM.md) — canonical index, chain, checklist.
- **Train the team:** [TRAINING.md](TRAINING.md) — when to use which persona, how to invoke in Cursor/Claude, how to run a Meridian review.
- **Cursor rules:** `.cursor/rules/persona-saga.mdc`, `persona-helm.mdc`, `persona-meridian.mdc` — Agent applies the right persona when you work on epics, plans, or reviews.

---

## Personas

| Name  | Role                      | File |
|-------|---------------------------|------|
| **Saga** | Best at creating epics   | [saga-epic-creator.md](saga-epic-creator.md) |
| **Helm** | Best planner & dev manager | [helm-planner-dev-manager.md](helm-planner-dev-manager.md) |
| **Meridian** | VP Success — reviewer & challenger of Saga and Helm | [meridian-vp-success.md](meridian-vp-success.md) |

**Relationship:** Saga produces epics; Helm produces plans and sprint goals. **Meridian** reviews and challenges both. She is dedicated to success (quality, performance, time to market), has 20+ years of experience, sniffs out bullshit, and understands AI teams—so she holds epics and plans to a clear, evidence-based bar.

**Chain:** Strategy/OKRs → **Saga** (epic) → **Meridian** (epic review) → **Helm** (plan, sprint goal, order of work) → **Meridian** (plan review) → execution (Primary Agent + Cursor/Claude using TheStudio flow). Execution follows the epic and plan; Verification and QA gates fail closed. Outcome data (single-pass success, loopbacks, reopen rate) should feed back into how Saga and Helm refine.

**Review checklist:** [meridian-review-checklist.md](meridian-review-checklist.md) — run this before treating an epic or plan as committed.

## How to use

- **In Cursor:** Rules in `.cursor/rules/` (persona-saga, persona-helm, persona-meridian) load the right persona when you work on epics, plans, or reviews. Use @persona-saga, @persona-helm, or @persona-meridian to invoke explicitly, or say "Run the Meridian checklist on this epic/plan."
- **With Claude:** Use the persona text as context when asking for epic drafts (Saga), planning artifacts and sprint goals (Helm), or a VP-style review of an epic or plan (Meridian). Use Artifacts for epic/plan documents and extended thinking for complex scope or dependencies.
- **TheStudio alignment:** Saga feeds the Intent Layer and Planner role; Helm’s outputs support the Planner, Context Manager, and runtime flow (docs 08, 11, 15). Meridian’s review bar aligns with Intent, Verification, QA, evidence, and outcome metrics (docs 11, 12, 13, 14, 15).

## Research basis

- 2026 best practices: epic creation (Parallel, Asana, Monday.com, Atlassian), planning and dev management (Easy Agile, Monday.com, DORA).
- Cursor: Agent overview, Rules, AGENTS.md, context injection, checkpoints, export.
- Claude: extended thinking, Artifacts, long context, API/agent capabilities (2026).
