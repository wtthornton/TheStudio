# Intent Review

The Intent Review tab lets you inspect and refine the **Intent Specification** that the system generated for a selected task. Improving intent quality here is one of the highest-leverage actions you can take — it directly determines how well the agent performs downstream.

## What is an Intent Specification?

An Intent Specification is the system's definition of correctness for a task. It is generated automatically from the GitHub issue title, body, labels, and the repository's recent history. The specification captures:

- **Goal** — what the implementation should achieve in plain language
- **Constraints** — rules the implementation must obey (e.g., no new dependencies, must be backwards-compatible, must preserve existing API contracts)
- **Acceptance criteria** — measurable, testable statements that determine whether the implementation is correct
- **Scope** — files and modules the agent is expected to touch, and files it must not touch

## How to use this tab

1. Select a task from the Pipeline tab — it will be highlighted in the minimap
2. Review the auto-generated intent specification field by field
3. Edit any fields that are inaccurate, incomplete, or too vague
4. Save the spec — the Router stage will use the updated intent when selecting experts

## Why this matters

A precise intent spec directly improves agent output quality. Vague intent leads to vague implementation. The QA Agent validates the final PR *against the intent spec*, so accuracy here reduces loopbacks and cuts cost. Research across similar systems suggests that improving intent quality reduces loopback rate by 30–50%.

## Writing good acceptance criteria

Acceptance criteria should be concrete and testable. Compare:

| Poor | Good |
|------|------|
| "handles errors" | "returns HTTP 422 with a structured error body when required fields are missing" |
| "is fast" | "responds in under 200ms at the 99th percentile under normal load" |
| "looks good" | "passes WCAG AA colour contrast check on the new button" |

## Tips

- The system infers intent from the GitHub issue — check its interpretation carefully for complex or ambiguous issues
- If the scope list is empty, add the files you know the implementation will touch; this prevents the agent from modifying unrelated code
- Constraints are as important as the goal — be explicit about what must *not* change
- You can re-edit the spec after routing if you notice a gap before the Implement stage begins
