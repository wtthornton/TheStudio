# Handoff prompt — Ralph Epic 51 (next agent)

**Copy everything below the line into a new agent thread** (optionally prefix with: *Read `CLAUDE.md` and Epic 51; then execute the following.*)

---

## Handoff: TheStudio — Ralph Epic 51 (post–P0 implementation)

### Context

- **Repo:** TheStudio (`wtthornton/TheStudio` on GitHub, default branch `master`).
- **Recent work:** Epic **51** P0 was **implemented in the vendored SDK** and wired into the Ralph path. Landmark commit: **`51f9726`** — `feat(ralph-sdk): Epic 51 P0 — stall detection, progressive context, files_changed`.
- **Dependency change:** `pyproject.toml` pins **`ralph-sdk @ file:./vendor/ralph-sdk`**. After checkout run **`pip install -e ".[dev]"`** so the environment uses the vendor tree, not an old external SDK path.
- **Planning / review docs:**
  - `docs/ralph-sdk-upgrade-evaluation.md` — full CLI vs SDK gap list and priorities.
  - `docs/epics/epic-51-ralph-vendored-sdk-parity.md` — epic (Meridian **PASS**; see `docs/epics/MERIDIAN-REVIEW-EPIC-51.md`).
  - Upstream umbrella issue: **https://github.com/frankbria/ralph-claude-code/issues/226** — index: `docs/ralph-upstream-issues.md`, body template: `docs/ralph-upstream-issue-body.md`.

### What P0 already delivered (do not redo blindly)

- `vendor/ralph-sdk/ralph_sdk/context_management.py` — progressive `fix_plan` trimming + `estimate_tokens`.
- `vendor/ralph-sdk/ralph_sdk/circuit_breaker.py` — `StallDetector`, `CircuitBreaker.open_circuit`.
- `vendor/ralph-sdk/ralph_sdk/agent.py` — stall evaluation after each iteration; `TaskResult.files_changed` via `git diff --name-only HEAD`; `CircuitBreaker.can_proceed()`; progressive prompt; `RalphStatus.tests_status`.
- `src/agent/ralph_bridge.py` — `ralph_result_to_evidence` prefers non-empty `result.files_changed`, else legacy bullet heuristic.
- Tests: `tests/unit/test_ralph_sdk_context_stall.py`, extended `tests/unit/test_ralph_bridge.py`.

### Suggested next steps (priority order)

1. **P1 from Epic 51 / evaluation** — Stories **51.4–51.6** and P2 items in `docs/ralph-sdk-upgrade-evaluation.md` (decomposition hints, cost tracking, `cancel()` semantics, metrics, etc.). Default path: **`vendor/ralph-sdk/`** unless upstream takes #226.
2. **Legacy Primary Agent path** — `src/agent/primary_agent.py` still uses `_parse_changed_files` for **non-Ralph** mode; decide parity vs document “structured paths = Ralph path only.”
3. **Tests** — Parsing/integration for `TESTS_STATUS: DEFERRED` in realistic CLI-shaped output; optional `git`/non-git edge cases for `files_changed` and fast-trip.
4. **Upstream** — Update **#226** with PR links when contributing; keep `docs/ralph-upstream-issue-body.md` aligned if the ask changes.
5. **CI** — Ensure pipelines install **`ralph-sdk` from `vendor/ralph-sdk`** (same as `pip install -e ".[dev]"` locally).

### Verification (local)

```bash
pip install -e ".[dev]"
pytest tests/unit/test_ralph_sdk_context_stall.py tests/unit/test_ralph_bridge.py tests/unit/test_primary_agent_ralph.py tests/integration/test_ralph_e2e.py -q
ruff check vendor/ralph-sdk/ralph_sdk/ src/agent/ralph_bridge.py tests/unit/test_ralph_sdk_context_stall.py
```

**Note:** Ruff may report pre-existing vendor findings (e.g. `UP042` on `str, Enum`); do not refactor unrelated enums unless in scope.

### Constraints

- Scope to **Epic 51** + **evaluation**; avoid drive-by changes outside Ralph vendor, bridge, and tests.
- **WSL Ralph home:** `scripts/wsl-setup-ralph-home.sh` and `docs/ralph-setup.md` if `~/.ralph` is not a git clone of `frankbria/ralph-claude-code`.

---

*This file lives at `docs/handoffs/ralph-epic-51-next-agent-prompt.md` for version control and sharing.*
