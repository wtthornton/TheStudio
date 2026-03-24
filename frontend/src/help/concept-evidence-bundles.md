# Concept: Evidence Bundles

An evidence bundle is the structured record that accompanies every draft PR TheStudio opens. It explains *what* was changed, *why* each decision was made, and *what verification passed* — so human reviewers have the full context they need to make a confident merge decision without re-reading a wall of code.

## Why evidence matters

A PR without context forces reviewers to reconstruct intent from code. TheStudio's agents generate evidence at every pipeline stage so that the final PR review is a confirmation of understood intent rather than a detective exercise.

## What an evidence bundle contains

Every evidence bundle is posted as a structured comment on the draft PR. It includes:

| Section | Contents |
|---------|----------|
| **Intent summary** | The intent specification extracted from the original GitHub issue |
| **Routing rationale** | Which expert agents were selected and why (e.g. "Security Reviewer included because issue touches auth middleware") |
| **Implementation notes** | Key decisions the Primary Agent made, with alternatives considered |
| **Verification results** | Ruff lint, pytest pass/fail counts, security scan summary |
| **QA verdict** | Whether the QA Agent's diff-against-intent check passed, with any flags |
| **Loopback history** | If the task looped back from QA, each loop's reason and fix summary |
| **Provenance chain** | Hash of the intent spec used, commit range, TaskPacket ID |

## The provenance chain

The provenance chain links the PR to the exact intent specification that governed it. This means:

- If the intent spec changes after the task starts, the chain records the spec version that was in effect
- Reviewers can always see *which constraints* the agent was given, not just what it produced
- The chain is cryptographically anchored (SHA-256 hash of the intent spec JSON) so it cannot be silently altered

## Loopback evidence

When the QA Agent rejects a draft, it writes a **loopback signal** containing:
- The specific intent clauses that were not satisfied
- The diff segment that caused the rejection
- The corrective instruction passed back to the Implement stage

Each loopback is appended to the evidence bundle so reviewers can see the full correction history, not just the final output.

## Reading evidence in the Activity Log

The **Activity Log** tab surfaces evidence events in a chronological stream. Each event is stamped with its pipeline stage, agent role, and outcome. You can filter by TaskPacket ID to see the complete evidence trail for a single task.

## Evidence and trust

Evidence bundles are the mechanism that makes **Execute** tier safe. When a PR auto-merges, the evidence bundle is retained as the audit record for the decision. It answers: "What did the agent intend? What did it verify? Who (or what) approved it?"

## Retention

Evidence bundles are stored:
- As GitHub PR comments (permanent, visible to all collaborators)
- In TheStudio's outcome database (queryable via the Activity Log and Analytics tabs)
- Referenced in reputation weight calculations for each expert agent

Evidence is never deleted automatically. It follows the PR lifecycle — if the PR is closed without merge, the evidence bundle remains on the closed PR.

## See also

- **Activity Log tab** — browse evidence events in real time
- **Analytics tab** — aggregate evidence across tasks and time periods
- **Concept: Pipeline Stages** — when evidence is written at each stage
- **Concept: Trust Tiers** — how evidence supports the Execute tier
