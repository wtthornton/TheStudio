# Budget Dashboard

The Budget Dashboard shows your LLM API spending across all pipeline stages and lets you set hard cost limits.

## Cost breakdown

Each pipeline stage uses one or more LLM calls. The dashboard shows:

- **Per-stage cost** — how much each stage spends on average per task
- **Per-repo cost** — total spend broken down by repository
- **Running total** — live cost accumulator shown in the header bar

## Setting limits

Configure a **monthly budget cap** to prevent runaway spend. When the cap is reached:
- New tasks will queue but not start processing
- In-progress tasks will complete
- You'll receive a notification when 80% of the budget is consumed

## Cost drivers

| Stage | Typical cost | Why expensive? |
|-------|-------------|----------------|
| Intent Builder | $0.003–0.01 | Sonnet/Opus for nuanced understanding |
| Primary Agent | $0.05–0.20 | Long context, multi-turn reasoning |
| QA Agent | $0.02–0.05 | Full diff review |
| Context | $0.001 | Haiku for metadata extraction |

## Reducing costs

- Use **Observe** or **Suggest** tier to avoid re-runs from loopbacks
- Write clear, specific GitHub issues to reduce intent clarification rounds
- Enable the **Intake Haiku Filter** to reject unsuitable issues early
