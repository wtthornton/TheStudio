# Concept: Trust Tiers

Trust Tiers are the primary safety control in TheStudio. They determine how autonomously agents can act across **every repository** you connect — from reading and proposing changes all the way to merging code without human confirmation.

## Why trust tiers exist

AI agents can write correct, well-tested code and still make decisions that a human reviewer would catch — a refactor that changes public API surface, a dependency bump that introduces a license conflict, or a migration that is safe but poorly timed. Trust Tiers put the human back in the loop at exactly the right moment based on the confidence level you have in the agent's output for a given repository.

## The three tiers at a glance

| Tier | What the agent does | Human touchpoint |
|------|---------------------|-----------------|
| **Observe** | Analyses issues, generates intent specs, proposes code — but never writes to GitHub | Human reviews proposals in the dashboard only |
| **Suggest** | Creates draft PRs on GitHub; does not request reviews or auto-merge | Human promotes draft → ready-for-review before any merge |
| **Execute** | Creates PRs and auto-merges when all gates pass | Human receives merge notification; can revert |

## How tiers interact with the pipeline

Every stage gate in the pipeline checks the current trust tier before writing any output:

1. **Intake → Context → Intent** — runs at all tiers; no external writes happen here
2. **Assembler → Implement** — code is generated at all tiers, but only written to GitHub if tier ≥ Suggest
3. **Verify → QA** — gates run at all tiers; tier drives what happens on pass vs. fail
4. **Publish** — at Observe, output stays in the dashboard; at Suggest, a draft PR is opened; at Execute, the PR is opened and auto-merged if all checks pass

## Changing tiers safely

Changes are **instantaneous for new tasks** — there is no propagation delay. Tasks that are already in-flight complete under the tier that was active when they were triaged. This means:

- Promoting from Observe → Suggest will not automatically publish pending proposals; they need to be re-triaged
- Demoting from Execute → Suggest will not revert already-merged PRs, but future auto-merges stop immediately

## Per-repository granularity

You can mix tiers across repositories. A common pattern:

- **Observe** on your primary monorepo while evaluating quality
- **Suggest** on shared libraries where speed matters but review is required
- **Execute** on documentation repositories, changelogs, or low-risk tooling with 90%+ test coverage

## Safety invariants (always enforced regardless of tier)

- Agents never push directly to `main` or `master` without a PR
- Agents never modify CI/workflow files without a Security Reviewer expert in the routing
- Agents never access credentials beyond those you explicitly configured
- When an agent encounters ambiguity that exceeds its scope, it stops and raises a human-review flag

## See also

- **Trust Tiers tab** — configure per-repo tiers and view the current setting
- **Concept: Pipeline Stages** — how tier gates are applied at each stage
- **Concept: Webhooks** — how issues enter the pipeline in the first place
