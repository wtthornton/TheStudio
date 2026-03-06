---
name: docs-audit
description: >-
  Audit and validate project documentation using DocsMCP. Checks for drift,
  completeness, freshness, and generates standard docs (README, CHANGELOG, API).
mcp_tools:
  - docs_project_scan
  - docs_check_drift
  - docs_check_completeness
  - docs_check_freshness
  - docs_generate_readme
  - docs_generate_changelog
  - docs_generate_api
  - docs_generate_contributing
  - docs_generate_onboarding
---

Audit and improve project documentation using DocsMCP:

## Audit workflow

1. Call `docs_project_scan` to get the overall documentation state
2. Call `docs_check_completeness` to score coverage and find gaps
3. Call `docs_check_drift` to detect code changes not reflected in docs
4. Call `docs_check_freshness` to find stale documentation

## Fix gaps

Based on audit results, generate missing docs:
- `docs_generate_readme` — README with smart merge
- `docs_generate_changelog` — CHANGELOG from git history
- `docs_generate_api` — API reference documentation
- `docs_generate_contributing` — CONTRIBUTING.md
- `docs_generate_onboarding` — Developer onboarding guide

## Best practices

- Run audit before major releases or after large refactors
- Fix drift issues before freshness issues (accuracy > recency)
- Use `docs_generate_readme` with smart merge to avoid overwriting custom sections
