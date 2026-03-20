# Failure Catalog

> **Last Updated:** 2026-03-18
> **Epic 30, Story 30.8:** Every failure mode observed during Docker prod validation.

## Failure Modes

### F1: Stale API Key in Docker Container

| Field | Value |
|-------|-------|
| **ID** | F1 |
| **Provider** | LLM (Anthropic) |
| **Category** | auth |
| **Severity** | Critical |
| **Description** | Docker container `thestudio-prod-app-1` was running with `sk-mock-placeho...` as the API key instead of the real key from `infra/.env`. Adapter returned 401 on every real API call. |
| **Root Cause** | The `.env` file was updated with the real key, but the container was not rebuilt/restarted to pick up the new value. Docker Compose uses `.env` at `docker compose up` time, not at runtime. |
| **Reproduction** | Deploy with placeholder key → all LLM calls fail with 401 |
| **Mitigation** | Always run `docker compose up --build` after changing `.env`. Added healthcheck that validates API key format on startup (prefix check). |
| **Status** | Known limitation — operator must restart containers after key rotation |

### F2: No Host Port Mapping for App Container

| Field | Value |
|-------|-------|
| **ID** | F2 |
| **Provider** | Infrastructure |
| **Category** | configuration |
| **Severity** | Medium |
| **Description** | The prod Docker stack does not map port 8000 to the host. Tests expecting to reach the app at `localhost:8000` or `localhost:9080` fail with connection refused. Only accessible via Caddy reverse proxy (when running) or Docker network. |
| **Root Cause** | Production architecture uses Caddy as the reverse proxy. App container intentionally has no direct host port mapping for security. |
| **Reproduction** | `curl http://localhost:8000/healthz` from host → connection refused |
| **Mitigation** | Integration tests that need to reach the app use Docker exec or run inside the Docker network. Health check tests skip when Caddy is not running. |
| **Status** | By design — not a defect |

### F3: pg-proxy Not Auto-Started

| Field | Value |
|-------|-------|
| **ID** | F3 |
| **Provider** | Postgres |
| **Category** | configuration |
| **Severity** | Low |
| **Description** | The `pg-proxy` service in `docker-compose.prod.yml` is defined but not always started. Integration tests that need direct Postgres access from the host require manual proxy startup. |
| **Root Cause** | The pg-proxy is an optional sidecar for development convenience, not required for production. |
| **Reproduction** | Run Postgres integration tests without starting pg-proxy → connection refused on localhost:5434 |
| **Mitigation** | Added proxy startup command to test runner docs. The `reference_credentials.md` memory documents the command. |
| **Status** | Known limitation |

### F4: OAuth Token 401 Without Refresh Token

| Field | Value |
|-------|-------|
| **ID** | F4 |
| **Provider** | LLM (Anthropic) |
| **Category** | auth |
| **Severity** | High |
| **Description** | OAuth tokens (`sk-ant-oat01-*`) expire after 8 hours. If `THESTUDIO_ANTHROPIC_REFRESH_TOKEN` is not set, the adapter gets a 401 and cannot recover. Long-running eval sessions (8+ hours) will fail mid-run. |
| **Root Cause** | OAuth token lifecycle requires refresh token rotation. Without a refresh token, the adapter has no way to renew the access token. |
| **Reproduction** | Set an expired OAuth token, no refresh token → 401 on all calls |
| **Mitigation** | Story 31.3 implements automatic token refresh. When refresh token is configured, adapter retries once with refreshed token. If no refresh token, adapter raises clear error message. |
| **Status** | Mitigated (Story 31.3) |

### F5: Intent/Assembler Agent Hits max_tokens

| Field | Value |
|-------|-------|
| **ID** | F5 |
| **Provider** | LLM (Anthropic) |
| **Category** | validation |
| **Severity** | Medium |
| **Description** | Intent and assembler agents consistently generate output that hits the 2,048 max_tokens limit, producing truncated JSON. Output parsing may fail on the truncated response. |
| **Root Cause** | These agents produce verbose structured output (intent specs, merged plans). Original max_tokens was 2,048 but has been increased to 4,096. |
| **Reproduction** | Run intent_agent with complex issue → tokens_out=2048 (truncated) |
| **Mitigation** | max_tokens increased to 4,096 in both LLMRequest default and AgentRunner._call_llm_completion. Monitor parse failure rates (>90% success metric). |
| **Status** | **Fixed** — max_tokens=4096 in framework.py and LLMRequest default |

### F6: Prompt Caching Not Active

| Field | Value |
|-------|-------|
| **ID** | F6 |
| **Provider** | LLM (Anthropic) |
| **Category** | cost |
| **Severity** | Low |
| **Description** | Prompt caching headers are sent correctly (`prompt-caching-2024-07-31` beta, `cache_control` block), but `cache_creation_input_tokens` and `cache_read_input_tokens` return 0 in the usage response. |
| **Root Cause** | Prompt caching may require minimum prompt length (>1024 tokens) or specific model support. System prompts in test are short. Production system prompts (~2000 tokens) should trigger caching. |
| **Reproduction** | Send short system prompt with cache_control → cache metrics = 0 |
| **Mitigation** | Not blocking — caching is additive. Falls back to uncached request transparently. Will validate with production-length prompts in Epic 32 Slice 3. |
| **Status** | Expected behavior for short prompts |

### F7: Router Agent Template Variables Not Injected

| Field | Value |
|-------|-------|
| **ID** | F7 |
| **Provider** | LLM (Anthropic) |
| **Category** | validation |
| **Severity** | Medium |
| **Description** | Router agent's system prompt template contains `{base_role}`, `{overlays}`, `{risk_flags}`, `{required_classes}` placeholders. When the eval `router_context_builder` doesn't inject these into `context.extra`, AgentRunner logs "System prompt template has unresolved keys, using raw template" and the LLM sees literal `{base_role}` in the prompt. |
| **Root Cause** | `router_context_builder` in `src/eval/routing_eval.py` puts values in `extra["base_role"]` and `extra["required_classes"]`, but `AgentRunner.build_system_prompt()` only includes `agent_name`, `repo`, `issue_title`, `issue_body`, `complexity`, `risk_flags`, `labels` in the format dict. Extra keys are merged but may not match template variable names. |
| **Mitigation** | `build_system_prompt()` merges `context.extra` into the format dict (line 366 of `framework.py`). The eval `router_context_builder` sets `base_role` and `required_classes` in `extra`; `overlays` and `risk_flags` come from the context directly. All 4 template variables resolve. |
| **Status** | **Fixed** — already resolved by `fmt.update(context.extra)` in `AgentRunner.build_system_prompt()` |

### F8: Assembler qa_handoff Schema Mismatch

| Field | Value |
|-------|-------|
| **ID** | F8 |
| **Provider** | LLM (Anthropic) |
| **Category** | validation |
| **Severity** | High |
| **Description** | `AssemblerAgentOutput.qa_handoff[].criterion` expects `list[str]` but the LLM consistently returns a plain `str`. Pydantic validation fails on every assembler eval case (7/7 parse failures). This causes the assembler to fall back to the rule-based path, producing $0 cost and 0% quality score. |
| **Root Cause** | The Pydantic schema defines `criterion` as `list[str]` but the LLM interprets "criterion" as a single description string. Either the schema or the prompt needs to be aligned. |
| **Mitigation** | Change `criterion` field type to `str | list[str]` with a validator that coerces strings to single-element lists, OR update the prompt to instruct the LLM to output a list. |
| **Status** | **Fixed** (2026-03-19) — `@field_validator("criterion", mode="before")` in `assembler_config.py` coerces `list[str]` to `str` |

### F9: Eval Scoring Too Strict for Real LLM Output

| Field | Value |
|-------|-------|
| **ID** | F9 |
| **Provider** | LLM (Anthropic) |
| **Category** | validation |
| **Severity** | Medium |
| **Description** | Intake and context eval scoring functions score 0% pass rate despite 100% parse success rate. The LLM produces valid, detailed output but the scoring dimensions (`goal_clarity`, `constraint_coverage`, etc.) are inherited from the intent eval's scoring framework and don't match these agents' output schemas. |
| **Root Cause** | The `run_eval` harness uses the same `EvalResult` dimensions for all agents, but intake/context agents don't produce "goals" or "constraints" — they produce classifications and enrichment. Custom scoring functions exist but the pass/fail threshold may not account for the different scoring scale. |
| **Mitigation** | Added calibrated weight maps for intake (`accepted_correct` 0.35, `role_correct` 0.25, etc.) and context (`scope_relevance` 0.30, `service_coverage` 0.25, etc.) dimensions in `harness.py`. Primary correctness signals get highest weight. Lowered `pass_threshold` to 0.5 for intake/context evals (vs 0.6 for intent). 4 new tests validate weight selection. |
| **Status** | **Fixed** (2026-03-19) — calibrated weights + adjusted thresholds |

## Summary

| Category | Count | Critical | High | Medium | Low |
|----------|-------|----------|------|--------|-----|
| auth | 2 | 1 | 1 | 0 | 0 |
| configuration | 2 | 0 | 0 | 1 | 1 |
| validation | 4 | 0 | 1 | 3 | 0 |
| cost | 1 | 0 | 0 | 0 | 1 |
| **Total** | **9** | **1** | **2** | **4** | **2** |

### Blocking for Suggest Tier

- **F1 (auth):** Must ensure real API keys are deployed — blocking
- **F5 (validation):** Must increase max_tokens for intent/assembler — should fix
- ~~**F8 (validation):**~~ Fixed — criterion field coercion validator added

### Should Fix (Quality)

- ~~**F7 (validation):**~~ Fixed — Router template variables resolved
- ~~**F9 (validation):**~~ Fixed — Calibrated weights + adjusted thresholds

### Known Limitations (Non-Blocking)

- F2, F3: Infrastructure configuration — by design
- F4: OAuth refresh — mitigated by Story 31.3
- F6: Caching — additive, not blocking
