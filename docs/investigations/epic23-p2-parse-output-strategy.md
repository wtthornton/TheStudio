# Investigation: `_parse_output()` Strategy for `AgentRunner`

**Epic:** 23 — Unified Agent Framework
**Story:** Pre-Sprint P2 (referenced by Story 1.5)
**Date:** 2026-03-16
**Author:** tapps-researcher
**Status:** Complete — Decision: Option B (native Pydantic)

---

## Question

Should `AgentRunner._parse_output()` use the `instructor` library or native Pydantic
`model_validate_json()` for structured output parsing?

---

## Evidence Gathered

### Dependency Audit

`instructor` is **not present** in `pyproject.toml` (production or dev) and is not installed
in `.venv`. Adding it would introduce new transitive dependencies: `tenacity`, `rich`, `typer`,
`docstring-parser`. Current relevant deps: `pydantic>=2.10.0`, `claude-agent-sdk>=0.1.40`.

### What `instructor` Provides

- Wraps the Anthropic client object (`instructor.from_anthropic(client)`)
- Uses `Mode.TOOLS` by default: encodes the Pydantic model as a tool definition, forces the
  model to "call" it — the most reliable structured-output path Anthropic exposes
- Auto-retry on `ValidationError` via `tenacity` (default 3 retries, feeds error back to LLM)
- Alternative `Mode.JSON` for non-tool use (JSON in system prompt — same approach as native)
- Breaks `mypy --strict`: patched client returns dynamically typed object without stubs

### What Native Pydantic `model_validate_json()` Provides

- Parses a JSON string against the Pydantic model's schema
- Raises `ValidationError` on schema mismatch; `ValueError`/`json.JSONDecodeError` on malformed JSON
- Zero new dependencies (Pydantic already in production deps, `pydantic.mypy` plugin active)
- No retry logic — caller implements retry or fallback
- Common failure modes (markdown fences, preamble text) are recoverable via extraction helper (~15 lines)

### Epic Constraints (Section 5 of epic-23-unified-agent-framework.md)

- "No new dependencies except potentially `instructor`" — permits but does not require it
- Risk register explicitly names mitigation: "Use Pydantic with `model_validate_json()`; include
  explicit JSON format instructions in system prompts; log parse failures for prompt tuning"
- AC 38: parse failure triggers `fallback_fn` with `used_fallback=True` — not a crash
- Section 7 success metric: >90% parse success rate per agent

### Execution Mode Compatibility

Epic AC 6 defines two modes:
- **Completion mode** (7 non-Primary agents): single LLM call returning text
- **Agentic mode** (Primary Agent): `claude_agent_sdk.query()` with tool loop

`instructor` `Mode.TOOLS` is incompatible with completion mode (tool definitions not applicable).
In `Mode.JSON`, instructor is a retry wrapper around the same JSON parsing Pydantic already does.
For agentic mode, instructor conflicts with the SDK's own tool management.

---

## Evaluation Matrix

| Criterion | `instructor` | Native Pydantic |
|---|---|---|
| New dependency | Yes — tenacity, rich, typer, docstring-parser | No |
| Reliability (structured output) | High with Mode.TOOLS (Anthropic-native) | Medium — prompt-dependent; fences need stripping |
| Retry on parse failure | Built-in (3 retries before fallback fires) | Manual — one attempt, then fallback_fn |
| Compatibility with completion mode | Poor — Mode.TOOLS not applicable | Excellent — natural fit |
| Compatibility with agentic mode | Conflicts with SDK tool management | Not applicable (agentic mode doesn't use _parse_output) |
| Compatibility with fallback_fn pattern | Redundant — retry fires before fallback; ordering unclear | Clean — fail once, trigger fallback |
| mypy --strict compliance | Fails — patched client breaks strict typing | Full compliance via pydantic.mypy plugin |
| Test complexity | Higher — patched client adds mock indirection | Simple — mock return value, assert model |
| Operational transparency | Retry loop is opaque in traces | Every attempt explicit; used_fallback visible |
| Epic alignment | Diverges from documented risk mitigation | Directly cited in AC 38 and risk section |

---

## Decision

**Option B: Native Pydantic `model_validate_json()` with JSON extraction helper.**

Do not add `instructor` to `pyproject.toml`.

### Rationale

1. **The fallback_fn pattern already handles parse failures.** AC 35 + 38 establish that parse
   failure triggers rule-based fallback with `used_fallback=True`. Instructor's 3-retry loop adds
   latency and cost (3 extra LLM calls at $0.10-$0.50 each) before fallback fires. Native Pydantic
   fails immediately, engaging fallback on the first bad parse. With per-agent budgets of $0.10-$0.50,
   retries are expensive relative to just falling back.

2. **Completion mode doesn't benefit from instructor's tool-calling path.** All 7 non-Primary agents
   use completion mode. Instructor's reliability advantage is `Mode.TOOLS` (Anthropic-native), which
   requires tool definitions — incompatible with completion mode. In `Mode.JSON`, instructor is just
   a retry wrapper around native parsing with added overhead.

3. **`mypy --strict` is in force.** The project runs `mypy --strict` with `pydantic.mypy`. Instructor's
   patched client breaks strict mode without type ignores or stubs. Every agent instantiation becomes
   a source of type noise.

4. **Dependency weight not justified.** Instructor adds tenacity, rich, typer, docstring-parser. These
   serve no other purpose in the project and add surface area for `pip-audit` security scanning.

5. **Epic documentation explicitly names native Pydantic.** The risk register names this as the
   mitigation. Choosing instructor diverges from the documented decision.

6. **A JSON extraction helper closes the reliability gap.** The main weakness of native parsing
   (fences, preamble text) is addressed by ~15 lines of extraction logic before `model_validate_json()`.

---

## Recommended Implementation (Story 1.5)

### `_extract_json_block()` helper

```python
def _extract_json_block(raw: str) -> str:
    """Extract JSON object or array from raw LLM output.

    Handles three common Claude response patterns:
    1. Raw JSON (ideal):       {"key": "value"}
    2. Fenced JSON:            ```json\n{"key": "value"}\n```
    3. JSON after preamble:    "Here is the output:\n{...}"
    """
    # Pattern 1: fenced code block
    fence_match = re.search(r"```(?:json)?\s*(\{[\s\S]*?\}|\[[\s\S]*?\])\s*```", raw)
    if fence_match:
        return fence_match.group(1).strip()

    # Pattern 2: first { ... last } or [ ... ]
    for start_char, end_char in (("{", "}"), ("[", "]")):
        start = raw.find(start_char)
        end = raw.rfind(end_char)
        if start != -1 and end > start:
            candidate = raw[start : end + 1]
            try:
                json.loads(candidate)
                return candidate
            except json.JSONDecodeError:
                continue

    return raw  # pass through; let downstream produce the right error
```

### `_parse_output()` method

```python
def _parse_output(self, raw: str) -> BaseModel | None:
    """Parse agent output against output_schema.

    Returns:
        Parsed Pydantic model on success.
        None on parse failure (signals run() to invoke fallback_fn).

    Emits agent.parse_success / agent.parse_failure span attributes and
    structured log fields for the >90% parse rate metric (Section 7).
    """
    if self.config.output_schema is None:
        return None  # caller uses raw string directly

    agent_name = self.config.agent_name
    json_str = _extract_json_block(raw)

    try:
        parsed = self.config.output_schema.model_validate_json(json_str)
        logger.debug(
            "Structured output parsed",
            extra={"agent": agent_name, "parse_success": True},
        )
        self._current_span.set_attribute("agent.parse_result", "success")
        return parsed

    except (ValidationError, ValueError) as exc:
        logger.warning(
            "Parse failed for agent %s: %s | raw_preview=%r",
            agent_name,
            exc,
            raw[:200],
            extra={"agent": agent_name, "parse_success": False},
        )
        self._current_span.set_attribute("agent.parse_result", "failure")
        return None
```

### Calling pattern in `run()`

```python
# Step h in AC 5 lifecycle
parsed = self._parse_output(raw_output)

if parsed is None and self.config.output_schema is not None:
    # Parse failure — engage fallback
    fallback_result = (
        self.config.fallback_fn(context) if self.config.fallback_fn else None
    )
    return AgentResult(
        agent_name=self.config.agent_name,
        raw_output=raw_output,
        parsed_output=fallback_result,
        model_used=provider.model_id,
        tokens_estimated=tokens,
        cost_estimated=cost,
        duration_ms=duration,
        used_fallback=True,
        operational_notes=[],
        threat_flags=threat_flags,
    )
```

### System Prompt Instruction Block (all completion-mode agents)

Include in every agent's system prompt template to minimize parse failures:

```
Return your response as a single JSON object with no additional text, explanation,
or markdown formatting. The JSON must conform to the schema described above.
Do not wrap the JSON in code fences. Do not add commentary before or after the JSON.
```

---

## Upgrade Path

If parse rates fall below 90% for a specific agent after prompt tuning:

1. First action: refine the system prompt JSON instruction block for that agent
2. Second action: add `model_config = ConfigDict(extra="ignore")` to output schemas
   (already the Pydantic v2 default, but explicit is safer)
3. Last resort: add `instructor` to `pyproject.toml` and use `Mode.JSON` for that
   specific agent only — not a global change. Note: this still does not give
   `Mode.TOOLS` reliability for completion-mode agents.

---

## Source References

- Epic 23 Section 4b (Top Risks): `docs/epics/epic-23-unified-agent-framework.md`
- Epic 23 Section 5 (Constraints): same file
- Epic 23 AC 38 (structured output validation): same file
- Epic 23 Section 7 (>90% parse success metric): same file
- Story 1.5 description: same file (Sprint 1 story map)
- `pyproject.toml`: project root (no instructor dependency present)
- Pydantic v2 docs: `BaseModel.model_validate_json()` classmethod, `ValidationError`
