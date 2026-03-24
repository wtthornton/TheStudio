# Handoff prompt — Ralph Epic 51 (next agent)

**Copy everything below the line into a new agent thread** (optionally prefix with: *Read `CLAUDE.md` and Epic 51; then execute the following.*)

---

## Handoff: TheStudio — Ralph Epic 51 (post–P0 / post–P1 slice)

### Context

- **Repo:** TheStudio (`wtthornton/TheStudio` on GitHub, default branch `master`).
- **Dependency:** `pyproject.toml` pins **`ralph-sdk @ file:./vendor/ralph-sdk`**. After checkout or when new SDK modules appear, refresh the install so Python does not load a stale copy from user `site-packages`:
  - **`pip install -e ".[dev]"`** and, if imports fail for new submodules, **`pip install --force-reinstall --no-cache-dir "./vendor/ralph-sdk"`** (or **`pip install -e "./vendor/ralph-sdk"`**).
  - **Wheel cache pitfall:** Pip may install an **older built wheel** for the path dependency (same version `2.0.2`) that omits newly added `.py` files. If you see `ModuleNotFoundError: ralph_sdk.decomposition` (etc.) after a normal install, run **`pip install --no-cache-dir -e ".[dev]"`** (or `pip cache remove ralph-sdk` then reinstall) so the wheel is rebuilt from the current `vendor/ralph-sdk` tree.
- **Planning / review docs:**
  - `docs/ralph-sdk-upgrade-evaluation.md` — full CLI vs SDK gap list and priorities.
  - `docs/epics/epic-51-ralph-vendored-sdk-parity.md` — epic (Meridian **PASS**; see `docs/epics/MERIDIAN-REVIEW-EPIC-51.md`).
  - Upstream umbrella: **https://github.com/frankbria/ralph-claude-code/issues/226** — index: `docs/ralph-upstream-issues.md`, body template: `docs/ralph-upstream-issue-body.md`.

### What P0 delivered (do not redo blindly)

- `vendor/ralph-sdk/ralph_sdk/context_management.py` — progressive `fix_plan` trimming + `estimate_tokens`.
- `vendor/ralph-sdk/ralph_sdk/circuit_breaker.py` — `StallDetector`, `CircuitBreaker.open_circuit`.
- `vendor/ralph-sdk/ralph_sdk/agent.py` — stall evaluation after each iteration; `TaskResult.files_changed` via `git diff --name-only HEAD`; progressive prompt; `RalphStatus.tests_status`.
- `src/agent/ralph_bridge.py` — `ralph_result_to_evidence` prefers non-empty `result.files_changed`, else legacy bullet heuristic.
- Tests: `tests/unit/test_ralph_sdk_context_stall.py`, extended `tests/unit/test_ralph_bridge.py`.

### What P1 slice delivered (recent; verify in tree before redoing)

- **51.4 — Decomposition:** `vendor/ralph-sdk/ralph_sdk/decomposition.py` (`detect_decomposition_needed`, `DecompositionContext`, `DecompositionHint`); config thresholds; `TaskInput.complexity_band`; loop logging + `TaskResult.decomposition_hint`; tests: `tests/unit/test_ralph_decomposition.py`.
- **51.5 — Cost tracking:** `vendor/ralph-sdk/ralph_sdk/cost_tracking.py` (`CostTracker`, `BudgetCheckResult`, `BudgetLevel`); `RalphConfig` cost fields; per-iteration recording + `TaskResult.session_cost_usd`; `primary_agent._implement_ralph` prefers numeric `session_cost_usd > 0` over heuristic (guards against `MagicMock`); tests: `tests/unit/test_ralph_cost_tracking.py`.
- **51.6 — `cancel()`:** `CancelResult` on `RalphAgent.cancel()`; active CLI child tracked; **`terminate()`** (SIGTERM semantics); `src/workflow/activities.py` logs cancel outcome; tests: `tests/unit/test_ralph_agent_cancel_completion.py`.
- **Evaluation §1.6 — Completion decay:** `should_exit` clears `_completion_indicators` when there is progress without `exit_signal` (files changed or `completed_task`).
- **DEFERRED parsing tests:** `tests/unit/test_ralph_parsing_tests_status.py`.
- **Primary agent docs:** module + `_parse_changed_files` document Ralph vs legacy changed-files behavior.

**Exports:** `vendor/ralph-sdk/ralph_sdk/__init__.py` includes decomposition, cost, `CancelResult`, etc.

### Suggested next steps (priority order)

1. **Evaluation gaps still open (mostly P1/P2)** — See `docs/ralph-sdk-upgrade-evaluation.md`: **dynamic model routing** (§1.5), **prompt cache split** (§1.8), **metrics JSONL** (§1.9), **session lifecycle / Continue-As-New** (§1.10), **error categorization** (§1.7 P2), **ProgressSnapshot / heartbeat** (§2.3 P2).
2. **Cancel hardening (evaluation §2.2)** — `CancelResult.partial_output` (stream or buffer stdout), optional **grace wait** inside SDK; today partial output is explicitly **not** captured; Temporal still uses a **10 s** sleep after `cancel()`.
3. **`git` / non-git edge cases** — `files_changed` and stall fast-trip when `git` missing or repo dirty; extra unit tests if not already covered.
4. **Epic hygiene** — Mark stories **51.4–51.6** and epic AC in `docs/epics/epic-51-ralph-vendored-sdk-parity.md` / `EPIC-STATUS-TRACKER.md` if your process requires it; **upstream #226** + `docs/ralph-upstream-issue-body.md` when contributing patches.
5. **CI** — `uv sync --dev` already installs from `./vendor/ralph-sdk` via `pyproject.toml`; no change required unless lockfile or path regressions appear.

### Verification (local)

```bash
pip install -e ".[dev]"
# If ModuleNotFoundError for new ralph_sdk submodules:
pip install --force-reinstall --no-cache-dir "./vendor/ralph-sdk"

pytest tests/unit/test_ralph_sdk_context_stall.py \
  tests/unit/test_ralph_bridge.py \
  tests/unit/test_ralph_decomposition.py \
  tests/unit/test_ralph_cost_tracking.py \
  tests/unit/test_ralph_parsing_tests_status.py \
  tests/unit/test_ralph_agent_cancel_completion.py \
  tests/unit/test_primary_agent_ralph.py \
  tests/unit/test_ralph_cost_and_heartbeat.py \
  tests/integration/test_ralph_e2e.py -q

ruff check vendor/ralph-sdk/ralph_sdk/ src/agent/ralph_bridge.py src/agent/primary_agent.py src/workflow/activities.py \
  tests/unit/test_ralph_*.py
```

**Note:** Ruff may report pre-existing vendor findings (e.g. `UP042` on `str, Enum`, `S110` on timeout kill); do not refactor unless in scope.

### Constraints

- Scope to **Epic 51** + **evaluation**; avoid drive-by changes outside Ralph vendor, bridge, activities, primary agent Ralph path, and tests.
- **WSL Ralph home:** `scripts/wsl-setup-ralph-home.sh` and `docs/ralph-setup.md` if `~/.ralph` is not a git clone of `frankbria/ralph-claude-code`.

### Execution checklist (any agent — before “done”)

1. Run the **Verification (local)** `pytest` + `ruff` block above; fix failures in scope.
2. Re-read **`docs/ralph-sdk-upgrade-evaluation.md`** for the gap you are closing; note the section id (e.g. §1.9) in the commit or PR.
3. If you changed **`vendor/ralph-sdk`**, reinstall per **Dependency** (wheel cache pitfall) before tests.
4. Update **`docs/epics/epic-51-ralph-vendored-sdk-parity.md`** / **`EPIC-STATUS-TRACKER.md`** only if your team process requires it for the slice you shipped.
5. Optional upstream: **`docs/ralph-upstream-issues.md`** / issue **#226** when contributing patches outward.

---

*This file lives at `docs/handoffs/ralph-epic-51-next-agent-prompt.md` for version control and sharing.*
