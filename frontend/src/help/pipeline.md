# Pipeline Dashboard

The Pipeline Dashboard gives you a real-time view of every GitHub issue flowing through TheStudio's 9-stage processing pipeline.

## What you'll see

Each **stage node** shows the current task count and status for that pipeline step — from Intake through to Publish. Active tasks pulse green; failed gates turn amber.

## Key concepts

- **TaskPacket** — the durable record that carries a GitHub issue through every stage
- **Stage gate** — each stage has a pass/fail gate; gates fail closed to prevent bad output from advancing
- **Loopback arc** — when the QA Agent rejects a draft PR, the task loops back to the Implement stage with evidence attached

## Actions available

- Click any stage node to open the **Stage Detail Panel** showing active tasks in that stage
- Click a task ID in the minimap to open the **Task Timeline** and **Activity Stream**
- Use the **Import Issues** button to pull GitHub issues directly into the pipeline

## Status indicators

| Colour | Meaning |
|--------|---------|
| Emerald | Stage is active and processing tasks |
| Amber | Gate warning or loopback in progress |
| Gray | Stage idle (no current tasks) |

Import your first GitHub issue to see the pipeline come to life.
