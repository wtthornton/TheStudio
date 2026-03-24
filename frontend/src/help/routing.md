# Routing Review

The Routing Review tab shows which specialist agents have been selected to work on a task and why. Reviewing routing decisions helps you catch mismatches early — before the agent spends time and budget on the wrong kind of change.

## How routing works

After the Intent stage, the Router reads the intent specification and assigns one or more **Expert Agents** based on the domains involved. Each expert covers a specific technical area:

- **Backend Developer** — Python, FastAPI, SQLAlchemy, async patterns
- **Frontend Developer** — React, TypeScript, Tailwind CSS, Vite
- **Database Specialist** — schema migrations, query optimisation, PostgreSQL specifics
- **Security Reviewer** — OWASP checks, secret handling, authentication and authorisation flows
- **Test Engineer** — pytest coverage, edge cases, regression tests, fixture design

Complex tasks can involve multiple experts. The Assembler stage merges their outputs before the Primary Agent produces the final implementation.

## Trust tiers and routing

The Router respects the **Trust Tier** you've configured for each repository:

- **Observe** — experts analyse and propose; no code is written or committed
- **Suggest** — experts draft changes; a human must promote the draft PR to ready-for-review
- **Execute** — approved experts can commit and open PRs automatically

## Reviewing a routing decision

1. Select a task from the Pipeline tab
2. The routing panel shows the assigned expert(s) alongside confidence scores and the reasoning behind each assignment
3. You can **override** an assignment by deselecting an expert or adding one from the list
4. Click **Approve routing** to advance the task to the Assembler stage

## When routing goes wrong

Common routing mistakes and how to fix them:

| Problem | Action |
|---------|--------|
| Backend expert assigned to a CSS change | Remove Backend, add Frontend expert |
| Security reviewer missing on an auth task | Add Security Reviewer manually |
| Test Engineer not included for a new API endpoint | Add Test Engineer to ensure coverage |

When you override a routing decision, the system records your correction and adjusts its confidence weights for similar future tasks. Over time this means fewer manual corrections are needed.

## Confidence scores

A confidence score below 0.7 on any assignment is worth inspecting — it usually means the issue is ambiguous or spans an unusual combination of domains.
