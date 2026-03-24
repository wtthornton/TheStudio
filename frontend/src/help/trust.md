# Trust Tiers

Trust Tiers control how autonomously TheStudio's agents can act on your behalf. Configure the level that matches your team's comfort with AI-driven changes.

## The three tiers

### Observe
The agent analyses issues and proposes changes but **never commits or opens a PR**. All output is read-only. Use this tier when first setting up TheStudio or evaluating agent quality.

### Suggest
The agent creates **draft PRs** on GitHub but does not request reviews or auto-merge. A human must promote the draft to a ready-for-review PR. This is the recommended default tier.

### Execute
The agent creates and **auto-merges PRs** that pass all configured gates. Use this tier only for repositories with strong test coverage and branch protection rules.

## Per-repo configuration

You can set different trust tiers for different repositories. For example, keep a monorepo on **Suggest** while allowing a docs repository to run on **Execute**.

## Changing tiers

Changes take effect immediately for new tasks. Tasks already in-flight continue with the tier that was active when they were triaged.

## Safety mechanisms

Regardless of tier, the agent will never:
- Push to `main` or `master` directly
- Delete files not mentioned in the intent specification
- Access secrets beyond those configured in your environment
