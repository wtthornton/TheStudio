# Routing Review

The Routing Review tab shows which specialist agents have been selected to work on a task and why.

## How routing works

After the Intent stage, the Router reads the intent specification and assigns one or more **Expert Agents** to the task. Each expert covers a domain:

- **Backend Developer** — Python/FastAPI implementation
- **Frontend Developer** — React/TypeScript/Tailwind
- **Database Specialist** — SQLAlchemy, migrations, query optimisation
- **Security Reviewer** — OWASP checks, secret handling, auth flows
- **Test Engineer** — pytest coverage, edge cases, regression tests

## Trust tiers and routing

The Router respects the **Trust Tier** you've configured. In **Observe** mode, experts propose changes but nothing is committed. In **Execute** mode, approved experts can commit directly.

## Reviewing a routing decision

1. Select a task from the Pipeline tab
2. The routing panel shows the assigned expert(s) with confidence scores
3. You can **override** an assignment by selecting a different expert
4. Click **Approve routing** to advance the task to the Assembler stage

## When routing goes wrong

If the wrong expert was selected (e.g., a backend expert assigned to a CSS change), override the assignment. The system updates its weights based on corrections to improve future routing.
