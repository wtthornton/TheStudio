# Epic 9 MCP Tool Review — TappsMCP & docs-mcp Effectiveness

**Date:** 2026-03-10
**Scope:** Review of TappsMCP and docs-mcp tool calls made during Meridian Round 3 review of Epic 9 (Docker Deployed Stack Test Rig)

---

## 1. Tool Call Audit

| # | Tool | Domain/Args | Latency | Confidence | Useful? |
|---|------|-------------|---------|------------|---------|
| 1 | `tapps_session_start(quick=True)` | — | 60.9s | N/A | Yes — confirmed 6 checkers available |
| 2 | `tapps_consult_expert` | testing-strategies | 68ms | 0.3 | No — zero RAG chunks, generic fallback |
| 3 | `tapps_consult_expert` | cloud-infrastructure | 2ms | 0.3 | No — zero RAG chunks, generic fallback |
| 4 | `docs_check_drift` | docs/epics | 618ms | N/A | Partially — confirmed no endpoint drift, but 57KB JSON blob hard to parse |
| 5 | `tapps_research` | testing-strategies + pytest | 1.2s | 0.3 | No — no knowledge, docs lookup returned nothing |
| 6 | `tapps_research` | cloud-infrastructure + docker | 1.9s | 0.3 | No — Context7 returned generic Docker docs index, not CI-specific |
| 7 | `docs_check_links` | epic-9 file | 0ms | N/A | No — returned 0 links (epic uses backtick refs, not markdown links) |
| 8 | `tapps_checklist` | review | 0ms | N/A | Yes — confirmed pipeline completion |

**Total calls:** 8
**Useful calls:** 3 out of 8 (37.5%)

---

## 2. What Worked Well

### `tapps_session_start`
- Fast initialization confirmed all 6 quality checkers (ruff, mypy, bandit, radon, vulture, pip-audit) are available.
- Pipeline progress tracking correctly showed prior session state.

### `docs_check_drift`
- Returned 188 drift items across the codebase, useful for cross-referencing that no endpoints cited in the epic had been renamed or removed.
- Confirmed all epic-referenced paths (`/webhook/github`, `/admin/health`, `/admin/workflows`, `/admin/repos`, `/healthz`) still exist in source.

### `tapps_checklist`
- Properly tracked that all required pipeline tools had been called during the session.
- Identified `tapps_dead_code` as a recommended (not required) missing tool — appropriate for a review task where no code was changed.

### Meridian agent (non-MCP)
- The Meridian reviewer agent was the most valuable tool in this session — it found 3 must-fix and 4 should-fix issues by cross-referencing epic text against actual source code. This was done via direct file reads and grep, not MCP tools.

---

## 3. What Did Not Work

### `tapps_consult_expert` — zero domain knowledge for Docker/CI
- Both testing-strategies and cloud-infrastructure domains returned confidence 0.3 with zero RAG chunks.
- The questions were well-scoped (Docker Compose integration testing, GitHub Actions CI patterns) but the knowledge bases had no indexed content for these topics.
- **Root cause:** TappsMCP expert knowledge bases are not populated with Docker, CI/CD, or infrastructure testing patterns.

### `tapps_research` — Context7 fallback unhelpful
- The Docker docs fallback returned only a generic table-of-contents (build images, multi-stage builds, Dockerfile writing) — nothing about GitHub Actions, CI integration, or `docker compose` testing patterns.
- pytest docs lookup returned nothing at all.
- **Root cause:** Context7 library docs are oriented toward API reference, not operational patterns like CI pipeline design.

### `docs_check_links` — wrong tool for this document
- Returned 0 links because the epic uses backtick code formatting (`` `docker-compose.dev.yml` ``) for file references, not markdown link syntax (`[text](url)`).
- The tool is designed for markdown links only — it cannot validate backtick-style file references against the filesystem.
- **Root cause:** Architectural mismatch — epic documents use backtick formatting by convention, but the link checker only parses markdown links.

### `docs_check_drift` — output format unusable
- Returned 57KB of JSON in a single line, requiring grep filtering to find relevant entries.
- No filtering parameters available (e.g., filter by specific source files or endpoint names).
- **Root cause:** The tool is designed for broad project-level drift detection, not targeted validation of specific file references in a document.

---

## 4. Recommendations

### For TappsMCP improvements

1. **Populate expert knowledge bases for infrastructure topics.** The testing-strategies and cloud-infrastructure domains need indexed content covering:
   - Docker Compose integration testing patterns
   - GitHub Actions CI job design (caching, artifact upload, concurrency groups, service containers)
   - pytest markers and fixture patterns for container-based tests
   - httpx usage for smoke testing live services

2. **Add a `tapps_validate_epic` or `tapps_review_doc` tool.** Current tools are Python-file-oriented. A document-focused tool that cross-references file paths and endpoint names in markdown against the actual codebase would be highly valuable for epic reviews.

3. **Context7 library resolution needs CI/ops coverage.** The `docker` library resolved to generic Docker documentation. Consider adding `docker-compose`, `github-actions`, or `ci-cd-patterns` as resolvable library targets.

### For docs-mcp improvements

4. **`docs_check_links` should support backtick file references.** Scan for backtick-wrapped paths (`` `src/foo/bar.py` ``) and validate they exist on disk. This is the most common reference style in epic documents.

5. **`docs_check_drift` needs filtering.** Add parameters like `source_files` or `search_names` to filter the output to specific modules or public names, rather than returning the full project drift report.

### For the review workflow

6. **Lead with the Meridian agent, use MCP tools as supplements.** The Meridian agent (direct file reads + grep + domain reasoning) found all actionable issues. MCP tools added confirmation but no new findings. For epic reviews, the optimal workflow is:
   - Meridian agent first (finds issues)
   - `docs_check_drift` to confirm no stale code references (supplemental)
   - `tapps_checklist` to close out (procedural)
   - Skip `tapps_consult_expert` and `tapps_research` for infrastructure/CI topics until knowledge bases are populated

7. **Don't call `docs_check_links` on epic files.** It adds no value when documents use backtick formatting. Reserve it for README files and guides that use actual markdown links.

---

## 5. Summary

| Category | Score | Notes |
|----------|-------|-------|
| MCP tool usefulness | 3/8 calls useful | 37.5% hit rate |
| Issues found by MCP | 0 new issues | All issues found by Meridian agent |
| Issues confirmed by MCP | 2 confirmations | Drift check confirmed endpoint stability; checklist confirmed pipeline |
| Time spent on MCP calls | ~66s total | Dominated by session_start (61s) |
| Recommendation | Use MCP tools selectively | Meridian agent is the primary review tool; MCP supplements for validation |
