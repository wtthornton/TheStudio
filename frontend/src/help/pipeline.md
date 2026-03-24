# Pipeline Dashboard

The Pipeline Dashboard gives you a real-time view of every GitHub issue flowing through TheStudio's 9-stage processing pipeline. Think of it as mission control: you can see exactly where each task is, what happened at each gate, and whether anything needs your attention.

## What you'll see

Each **stage node** shows the current task count and status for that pipeline step — from Intake through to Publish. Active tasks pulse green; failed gates turn amber; idle stages appear gray. The **minimap** at the bottom of the screen lists every in-flight task by ID, letting you quickly locate a specific issue.

## The 9 pipeline stages

| Stage | What happens |
|-------|-------------|
| Intake | Webhook received, eligibility checked |
| Context | Issue enriched with repo history and complexity flags |
| Intent | Intent Specification generated from issue text |
| Router | Expert agents selected based on intent |
| Assembler | Expert outputs merged into a unified plan |
| Implement | Primary Agent writes code changes |
| Verify | Ruff, pytest, and security scan run against the diff |
| QA | QA Agent validates output against intent spec |
| Publish | Draft PR created on GitHub with evidence comment |

## Key concepts

- **TaskPacket** — the durable record that carries a GitHub issue through every stage. It accumulates evidence at each step so nothing is lost.
- **Stage gate** — each stage has a pass/fail gate; gates fail closed to prevent bad output from advancing downstream.
- **Loopback arc** — when the QA Agent rejects a draft PR, the task loops back to the Implement stage with detailed evidence attached so the agent can correct its work.

## Actions available

- Click any stage node to open the **Stage Detail Panel** showing all active tasks in that stage
- Click a task ID in the minimap to open the **Task Timeline** and **Activity Stream** for that task
- Use the **Import Issues** button to pull GitHub issues directly into the pipeline without waiting for a webhook event

## Status indicators

| Colour | Meaning |
|--------|---------|
| Emerald | Stage is active and processing tasks |
| Amber | Gate warning or loopback in progress |
| Gray | Stage idle — no current tasks |
| Red | Hard failure requiring human intervention |

Import your first GitHub issue to see the pipeline come to life.
