# Intent Review

The Intent Review tab lets you inspect and refine the **Intent Specification** that the system generated for a selected task.

## What is an Intent Specification?

An Intent Specification is the definition of correctness for a task. It captures:

- **Goal** — what the implementation should achieve
- **Constraints** — rules the implementation must obey (e.g., no new dependencies, must be backwards-compatible)
- **Acceptance criteria** — measurable tests that determine whether the implementation is correct
- **Scope** — files and modules the agent is expected to touch

## How to use this tab

1. Select a task from the Pipeline tab (it will be highlighted in the minimap)
2. Review the auto-generated intent specification
3. Edit any fields that are inaccurate or incomplete
4. Save the spec — the Routing stage will use the updated intent

## Why this matters

A precise intent spec directly improves agent output quality. Vague intent leads to vague implementation. The QA Agent validates the final PR against the intent spec, so accuracy here reduces loopbacks.

## Tips

- The system infers intent from the GitHub issue title, body, and labels — check its interpretation carefully for complex issues
- Acceptance criteria should be testable statements (e.g., "returns 200 for valid input" not "handles errors")
