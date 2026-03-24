# Budget Dashboard

The Budget Dashboard shows your LLM API spending across all pipeline stages and lets you set hard cost limits to prevent runaway spend. Understanding where cost originates helps you tune the pipeline for efficiency without sacrificing quality.

## Cost breakdown

Each pipeline stage uses one or more LLM calls. The dashboard shows:

- **Per-stage cost** — average LLM spend per task at each stage
- **Per-repo cost** — total spend broken down by repository so you can spot expensive codebases
- **Running total** — live cost accumulator shown in the header bar for at-a-glance awareness
- **Historical trend** — 30-day chart showing daily spend so you can correlate cost spikes with activity

## Typical cost by stage

| Stage | Typical cost | Why |
|-------|-------------|-----|
| Context | $0.001 | Haiku for metadata extraction |
| Intent Builder | $0.003–0.01 | Sonnet/Opus for nuanced understanding |
| Router | $0.001–0.003 | Classification only |
| Primary Agent | $0.05–0.20 | Long context, multi-turn code generation |
| QA Agent | $0.02–0.05 | Full diff review against intent spec |

The Primary Agent is the dominant cost driver. Loopbacks (when QA rejects and the task returns to Implement) can double or triple the cost of a single task.

## Setting limits

Configure a **monthly budget cap** to prevent unexpected bills. When the cap is reached:
- New tasks will queue but not begin processing
- Tasks already in-flight will complete normally
- You'll receive a dashboard notification at **80% consumption** so you have time to adjust

You can also set **per-repo limits** independently from the global cap, useful for high-volume repositories or experimental repos you want to ring-fence.

## Reducing costs without hurting quality

- **Write clear, specific GitHub issues** — vague intent leads to more clarification rounds and longer agent sessions
- **Use label filters** to prevent trivial or unsuitable issues from entering the pipeline at all
- **Enable the Intake Haiku Filter** to reject obviously unsuitable issues cheaply before they reach the expensive stages
- **Reduce loopback rate** by improving your intent specifications — each QA rejection triggers a full re-run of the Implement and Verify stages
- **Use Observe tier** on experimental work to review proposals before committing budget to full implementation runs
