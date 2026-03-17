# P1: Does the Claude Agent SDK Support Completion-Only Mode?

**Epic 23 Sprint 1 — Pre-Sprint Investigation P1**
**Date:** 2026-03-16
**Author:** tapps-researcher

---

## Question

Can the Claude Agent SDK (`claude_agent_sdk`) be used for single-turn, no-tools LLM calls, or do the 7 non-agent pipeline nodes (Intake, Context, Intent, Router, Recruiter, Assembler, QA) need a different mechanism?

---

## Findings

### 1. What the Claude Agent SDK Actually Is

The `claude_agent_sdk` package (version `>=0.1.40`, installed at `.venv/Lib/site-packages/claude_agent_sdk/`) is **not a direct API client**. Its `SubprocessCLITransport` (see `_internal/transport/subprocess_cli.py`, line 34) spawns the `claude` CLI binary as a child process and communicates over its stdio control protocol.

Every call to `query()` launches a `claude` subprocess. This has concrete consequences for pipeline nodes:

- **Startup overhead:** Each invocation forks a new Node.js process (the Claude CLI) — hundreds of milliseconds per call.
- **CLI dependency:** Requires `claude` binary installed and on `PATH`. Not suitable for Docker-based pipeline workers without that dependency.
- **Streaming control protocol:** The SDK sends an `initialize` control request, manages hooks, permissions, and tool-loop state even for calls that never use tools.
- **No direct HTTP:** There is no code path that calls the Anthropic Messages API directly. It always goes through the CLI.

The `query()` function's own docstring (`query.py`, lines 22–37) frames it as "one-shot or unidirectional streaming interactions" and "fire-and-forget". This sounds appealing, but the subprocess mechanism still applies.

### 2. Can You Use It Without Tools?

Technically yes. `ClaudeAgentOptions` has:
- `allowed_tools: list[str] = field(default_factory=list)` — defaults to empty
- `disallowed_tools: list[str] = field(default_factory=list)` — can be populated
- `max_turns: int | None = None` — can be set to `1`

You could call:

```python
options = ClaudeAgentOptions(
    system_prompt="...",
    model="claude-sonnet-4-5",
    max_turns=1,
    allowed_tools=[],          # no tools offered
    permission_mode="bypassPermissions",
)
async for message in query(prompt=user_prompt, options=options):
    if isinstance(message, ResultMessage):
        text = message.result
```

This would produce a single-turn response with no tool calls. But it still:
1. Spawns a subprocess
2. Runs the full CLI initialization and hook protocol
3. Requires the `claude` binary present at runtime
4. Carries all the overhead of the agentic loop infrastructure

For 7 pipeline nodes each processing potentially dozens of TaskPackets concurrently, this is the wrong tool.

### 3. The Project Already Has the Right Tool

`src/adapters/llm.py` (Story 8.5) already provides exactly what Epic 23 needs:

**`AnthropicAdapter`** — calls the Anthropic Messages API directly via `httpx`:
- No subprocess, no CLI dependency
- Full async (`httpx.AsyncClient`)
- Returns `LLMResponse` with `content`, `tokens_in`, `tokens_out`, `model`, `stop_reason`
- Supports `system` prompt, `messages`, `max_tokens`, `temperature`
- Already wired to `settings.anthropic_api_key`

**`MockLLMAdapter`** — canned responses for tests (already used project-wide)

**`get_llm_adapter()`** — factory that switches on `settings.llm_provider` (`"mock"` or `"anthropic"`)

```python
# src/adapters/llm.py — already exists, no new code needed

adapter = get_llm_adapter()   # returns AnthropicAdapter or MockLLMAdapter

request = LLMRequest(
    system="You are the Intake agent...",
    messages=[{"role": "user", "content": json.dumps(payload)}],
    max_tokens=2048,
    temperature=0.0,
)
response: LLMResponse = await adapter.complete(provider, request)
structured = json.loads(response.content)
```

The `ProviderConfig` argument to `complete()` comes from the Model Gateway (`get_model_router().select_model(step="intake", ...)`), which is already wired up for budget enforcement and audit.

---

## Recommendation

**Option B: Use the Anthropic Messages API (via `src/adapters/llm.py`) for non-tool agents. Abstract behind a shared `_call_llm()` helper.**

Do **not** use `claude_agent_sdk` for Intake, Context, Intent, Router, Recruiter, Assembler, or QA nodes. Reserve the SDK exclusively for the Primary Agent (Implement step), where the full agentic tool loop — file edits, bash commands, multi-turn reasoning — is genuinely required.

### Implementation Pattern for Epic 23

Each pipeline node should follow this pattern:

```python
# Pattern: single-turn LLM completion for pipeline nodes

from src.adapters.llm import LLMRequest, get_llm_adapter
from src.admin.model_gateway import get_model_router

async def _call_llm(
    step: str,
    system_prompt: str,
    user_content: str,
    *,
    max_tokens: int = 2048,
    temperature: float = 0.0,
) -> str:
    """Single-turn LLM completion. Returns response text."""
    adapter = get_llm_adapter()
    router = get_model_router()
    provider = router.select_model(step=step, role="planner")

    request = LLMRequest(
        system=system_prompt,
        messages=[{"role": "user", "content": user_content}],
        max_tokens=max_tokens,
        temperature=temperature,
    )
    response = await adapter.complete(provider, request)
    return response.content


# Example: Intake node
async def classify_issue(raw_issue: dict) -> IntakeResult:
    text = await _call_llm(
        step="intake",
        system_prompt=INTAKE_SYSTEM_PROMPT,
        user_content=json.dumps(raw_issue),
    )
    return IntakeResult.model_validate_json(text)
```

This helper can live in a new `src/agent/llm_helpers.py` or inline in each node module.

### Structured Output

For nodes that return structured JSON (all 7 nodes), pass a JSON schema instruction in the system prompt and parse with Pydantic:

```python
system_prompt = """
You are the Context Enrichment agent.
Respond ONLY with valid JSON matching this schema:
{
  "complexity_index": float,    // 0.0–1.0
  "risk_flags": list[str],
  "estimated_effort_hours": int
}
Do not include any text outside the JSON object.
"""

response_text = await _call_llm("context", system_prompt, issue_text)
result = ContextResult.model_validate_json(response_text)
```

If structured output reliability becomes a concern, the `ClaudeAgentOptions.output_format` field (a JSON schema dict) exists in the SDK — but since we are using `AnthropicAdapter` directly, the equivalent is the Anthropic API's `tool_use` or `text` response with a well-constrained prompt.

---

## Decision Table

| Node | Needs Tool Loop | SDK or Messages API | Reason |
|------|----------------|---------------------|--------|
| Intake | No | Messages API | Classify + eligibility, single JSON output |
| Context | No | Messages API | Enrichment, single JSON output |
| Intent | No | Messages API | Intent spec construction, single JSON output |
| Router | No | Messages API | Expert selection, single JSON output |
| Recruiter | No | Messages API | Role assignment, single JSON output |
| Assembler | No | Messages API | Merge + provenance, single JSON output |
| QA | No | Messages API | Defect analysis, single JSON output |
| Primary Agent (Implement) | **Yes** | **Claude Agent SDK** | Multi-turn, file edits, bash, loopbacks |

---

## Evidence

- **SDK transport source:** `c:\cursor\TheStudio\.venv\Lib\site-packages\claude_agent_sdk\_internal\transport\subprocess_cli.py` — confirms subprocess-only design
- **SDK types source:** `c:\cursor\TheStudio\.venv\Lib\site-packages\claude_agent_sdk\types.py` — `ClaudeAgentOptions` confirmed; no direct HTTP client
- **Existing adapter:** `c:\cursor\TheStudio\src\adapters\llm.py` — `AnthropicAdapter` and `MockLLMAdapter` already implemented
- **Settings:** `c:\cursor\TheStudio\src\settings.py` — `anthropic_api_key`, `llm_provider` feature flag already wired
- **Current SDK usage:** `c:\cursor\TheStudio\src\agent\primary_agent.py` — confirms SDK is correct for the Primary Agent (tool loop, multi-turn, `cwd`-bound)

---

## No Action Required on Existing Code

`src/adapters/llm.py` requires no changes. Epic 23 nodes should import `get_llm_adapter`, `LLMRequest`, and `LLMResponse` directly. The `MockLLMAdapter` means all 7 new nodes get test coverage without any API keys, consistent with the project's existing testing strategy.
