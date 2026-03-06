# 20 — Coding Standards (Python, AI-Coded Projects)

## Purpose

Define consistent coding standards that allow humans and agents to produce maintainable code with predictable quality. These standards reduce review friction and ensure verification and QA gates can be deterministic.

## Intent

The intent is to make the Primary Agent’s output:
- consistent across services and contributors
- readable under time pressure
- safe by default (security and dependency hygiene)
- testable and observable (traceable correlation IDs)

These standards are written for AI-coded projects where changes must be scoped, evidence-backed, and easy to review.

---

## Tooling Baseline

Formatting and linting
- Ruff lint and Ruff formatter as the default (single tool surface). See Ruff docs: https://docs.astral.sh/ruff/ and Ruff formatter: https://docs.astral.sh/ruff/formatter/

Package and project management
- uv for fast, reproducible environments and dependency management: https://docs.astral.sh/uv/

Pre-commit hooks
- pre-commit for consistent local enforcement: https://pre-commit.com/ and hook catalog: https://pre-commit.com/hooks.html

Testing
- pytest as baseline: https://docs.pytest.org/

Observability
- OpenTelemetry for traces, metrics, logs where applicable: https://opentelemetry.io/docs/languages/python/

Security scanning (OSS)
- pip-audit for dependency vulnerability scanning: https://pypi.org/project/pip-audit/
- gitleaks for secret scanning: https://github.com/gitleaks/gitleaks

---

## Python Style Standards

General
- prefer clarity over cleverness
- avoid global mutable state
- keep functions small and single-purpose
- avoid hidden side effects

Typing
- public interfaces must be type-annotated
- use explicit types for return values on public methods
- avoid Any in new code unless there is a clear reason

Errors
- raise explicit exceptions
- avoid broad except blocks
- include context in errors so failures are debuggable

Logging
- structured logs
- include correlation_id from the TaskPacket in logs and spans

Async
- async only when needed
- avoid mixing async and sync in the same control path without clear boundaries

---

## Security and Data Handling

- never commit secrets
- validate external inputs at boundaries
- parameterize SQL queries
- avoid unsafe deserialization
- avoid dynamic code execution

---

## Testing Standards

- tests must map to acceptance criteria when acceptance criteria exist
- include negative tests for critical invariants
- prefer fast unit tests; add integration tests when behavior crosses process boundaries
- mark slow or integration tests and document marker usage per pytest guidance

---

## Review Hygiene for AI-Coded Changes

- keep diffs small and focused
- avoid large refactors unless explicitly requested in intent
- every change must be explainable in the PR summary, tied to intent and evidence
- do not change unrelated files “for cleanup”

---

## Verification Gate Expectations

Verification should enforce:
- formatting and linting checks
- tests and minimal coverage rules for critical areas
- secret scanning and dependency audit for dependency changes

## Enforcement

These standards are enforced by:
- pre-commit hooks for local consistency
- Verification Gate for deterministic enforcement
- QA Agent for intent-aligned validation where style impacts correctness

Agents must reference these standards when writing code and when summarizing PR changes.
