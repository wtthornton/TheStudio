# Lessons Learned — TheStudio

Maintained by **Helm** (Planner & Dev Manager). Updated at each sprint retro.
Actions from this log feed into the next sprint plan.

---

## Sprint 1 — Epic 0: Prove the Pipe (2026-03-05)

### What worked

| # | Observation | Evidence |
|---|-------------|----------|
| 1 | Unit test coverage was strong from the start | 42/42 tests pass; every story has dedicated test file |
| 2 | Ruff lint clean on first run | Zero warnings across all src/ |
| 3 | Planning artifacts (epic, stories, sprint plan) were comprehensive and async-readable | Meridian review passed before commit |
| 4 | Tooling scaffolding (CI workflows, CODEOWNERS, dependabot, TAPPS pipeline) landed alongside code | No "set up CI later" debt |

### What didn't work

| # | Observation | Impact | Root cause |
|---|-------------|--------|------------|
| 1 | Mypy shipped with 5 type errors | Sprint DoD item #5 not met | Type narrowing not addressed during implementation; no pre-commit mypy hook |
| 2 | Docker infrastructure never stood up | Integration tests blocked; Sprint 1 DoD items #3, #4, #6 not fully validated | Infra setup was "parallel work" with no owner or deadline — treated as implicit |
| 3 | Single 148-file, ~9,800-line commit | Violates SOUL.md "prefer small diffs"; hard to review/bisect | All stories implemented in one pass without intermediate commits |

### Actions taken

| # | Action | Sprint applied | Status |
|---|--------|---------------|--------|
| A1 | Fix 5 mypy errors | Sprint 1 (patch) | Done — 5 type errors fixed, mypy clean |
| A2 | Stand up Docker infra before Sprint 2 stories start | Sprint 2 prerequisite | Done — 4 fixes: (1) temporalio/ui:2.31 → :latest, (2) DB=postgresql → postgres12, (3) port 5432→5434 (native PG conflict), (4) pgdata volume recreated |
| A3 | Run integration tests against real services | Sprint 2 prerequisite | Done — 8/8 integration tests pass against live PostgreSQL |
| A5 | Fix TaskPacket ORM model missing UniqueConstraint | Sprint 1 (patch) | Done — `__table_args__` was missing `UniqueConstraint("delivery_id", "repo")` needed by ON CONFLICT |
| A6 | Fix asyncpg multi-statement migration bug | Sprint 1 (patch) | Done — asyncpg rejects multiple statements in one execute(); split SQL_UP into statement lists |
| A4 | One commit per story minimum going forward | Sprint 2+ process | Adopted |

### Patterns to carry forward

- **Estimate infra setup as a real story with DoD, not "parallel work."** If it doesn't have an owner and acceptance criteria, it won't get done.
- **Run mypy in the edit loop, not just at the end.** Add to pre-commit or use `tapps_quick_check` after each file edit.
- **Commit per story.** Small diffs, clear evidence, easier bisect.
- **Sprint DoD is the bar.** If the DoD says "mypy clean," it must be clean before declaring done. No partial credit (per Helm's own constraint).
- **Pin Docker image tags to verified versions.** Speculative tags (e.g. temporalio/ui:2.31) break `docker compose up`. Verify tags exist before committing compose files.
- **Use correct Temporal DB driver names.** Valid drivers: mysql8, postgres12, postgres12_pgx, cassandra. Not "postgresql".
- **Check host port conflicts before defining compose ports.** Other projects (e.g. homeiq) and native PostgreSQL installs may hold standard ports. Use `netstat` to verify before choosing host ports.
- **asyncpg cannot execute multiple SQL statements in one call.** Split migration SQL into individual statements. This is a fundamental asyncpg limitation (unlike psycopg2).
- **ORM model constraints must match CRUD queries.** If CRUD uses `ON CONFLICT (col_a, col_b)`, the ORM model must have `UniqueConstraint("col_a", "col_b")` in `__table_args__`. Run integration tests against real DB to catch this — unit tests with mocks won't.
- **Always run integration tests before declaring a data-layer story done.** Unit tests with mocked sessions hide constraint, type, and driver-level bugs.

---

*Updated by Helm after Sprint 1 retro. Next update: Sprint 2 retro.*
