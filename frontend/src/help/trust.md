# Trust Tiers

Trust Tiers control how autonomously TheStudio's agents can act on your behalf. Choosing the right tier lets you balance development velocity against the level of human oversight your team needs. You can change tiers at any time, and configure different tiers for different repositories.

## The three tiers

### Observe
The agent analyses issues and proposes changes but **never commits code or opens a PR**. All output is visible in the dashboard as read-only proposals. Use this tier when first setting up TheStudio or when evaluating agent quality on a critical repository. It costs the same as other tiers but gives you complete visibility before granting write access.

### Suggest *(recommended default)*
The agent creates **draft PRs** on GitHub but does not request reviews, add reviewers, or auto-merge. A human must promote the draft to a ready-for-review PR. This tier gives you the productivity benefit of automated implementation while keeping a human in the loop for every merge decision.

### Execute
The agent creates PRs and **auto-merges** those that pass all configured gates (tests, lint, security scan, QA review). Use this tier only for repositories with strong automated test coverage and branch protection rules. It is well-suited to documentation repositories, low-risk tooling, or teams with high confidence in their test suite.

## Per-repo configuration

You can set different trust tiers for different repositories. For example:
- Keep your monorepo on **Suggest** while allowing a docs repository to run on **Execute**
- Keep a new repo on **Observe** while onboarding to TheStudio, then promote to Suggest once you've validated output quality

## Changing tiers

Changes take effect immediately for **new tasks**. Tasks already in-flight continue with the tier that was active when they were triaged — this prevents mid-flight mode changes from disrupting in-progress work.

## Safety mechanisms

Regardless of trust tier, TheStudio's agents will never:
- Push commits directly to `main` or `master` without a PR
- Delete files not mentioned in the intent specification
- Access secrets or credentials beyond those you explicitly configured
- Modify `.github/workflows` or CI configuration without a Security Reviewer expert included in the routing

If an agent encounters a situation that seems to exceed its scope, it stops and creates a human-review flag rather than proceeding.
