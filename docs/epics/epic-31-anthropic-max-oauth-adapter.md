# Epic 31: Anthropic Max OAuth Token Support for Pipeline API Calls

> **Status:** Planned (Research Complete, Implementation Blocked — See Risk R3)
> **Epic Owner:** Primary Developer
> **Duration:** 1 sprint (~1 week) once unblocked
> **Created:** 2026-03-18
> **Meridian Review:** Round 1: Pending

---

## 1. Title

**Use Claude Max Subscription for Pipeline API Calls by Supporting OAuth Token Authentication**

---

## 2. Narrative

### The Cost Problem

Epic 30 Sprint 1 validated the intent agent against real Claude (Story 30.2). The results exposed a critical cost concern for 24/7 pipeline operations:

| Metric | Measured (Intent Agent Only) | Projected (Full Pipeline) |
|--------|------------------------------|---------------------------|
| Cost per issue (intent agent) | $0.023 actual | — |
| Cost per issue (all 9 agents) | — | $2-8 estimated |
| 10 issues/day | — | $600-2,400/month |
| 50 issues/day | — | $3,000-12,000/month |
| 100 issues/day | — | $6,000-24,000/month |

**Note on cost estimation accuracy:** The `AgentRunner` reported $0.13 for 10 intent cases; Anthropic's billing dashboard showed $2.08 for the full test session (80+ API calls across 8 integration tests, each running all 10 cases). Internal cost tracking underestimates actual spend by ~16x due to stale `cost_per_1k_tokens` values in `ProviderConfig`. This must be fixed regardless of auth mode (see Story 31.0 recommendations).

Meanwhile, the $200/month Claude Max subscription that already covers Claude Code usage sits at **3% Sonnet weekly usage** and **20% all-models weekly usage** while running 3-5 coding agents continuously. The subscription has massive unused capacity.

### The Technical Gap

TheStudio's `AnthropicAdapter` in `src/adapters/llm.py` hardcodes `x-api-key` as its only auth header. Claude Max subscription OAuth tokens (prefix `sk-ant-oat01-...`) require `Authorization: Bearer` and an `anthropic-beta: oauth-2025-04-20` header instead. Plugging an OAuth token into the current adapter returns 401.

### The Complication

Research (Story 31.0) revealed that Anthropic is **actively restricting OAuth usage in third-party applications**:

- Anthropic has sent legal requests to third-party tools (OpenClaw, OpenCode) removing OAuth support
- The `oauth-2025-04-20` beta header can return 400 errors ("Unexpected value")
- OAuth tokens have 8-hour expiration requiring refresh token rotation
- Using OAuth tokens outside of first-party tools (Claude Code, Claude Desktop) may violate Anthropic's TOS
- 1M context window is unavailable with OAuth tokens

**However:** Claude Code itself uses OAuth tokens to hit `api.anthropic.com/v1/messages` with `Authorization: Bearer` headers. TheStudio's agents running under Claude Code would be a first-party usage pattern — but running as a standalone server would not be.

### Why This Epic Exists

Even if OAuth proves legally or technically untenable for the standalone pipeline, this research must be documented so the team understands:
1. Why the Max subscription cannot simply replace API keys
2. What the actual cost model is for production operations
3. What alternatives exist (model routing optimization, Haiku for cheap agents, budget caps)

**Why now:** Epic 30 is flipping `llm_provider` from `mock` to `anthropic` for the first time. Cost model clarity is prerequisite to any production deployment planning.

---

## 3. References

| Artifact | Location |
|----------|----------|
| AnthropicAdapter (current) | `src/adapters/llm.py` lines 80-134 |
| Settings (anthropic_api_key) | `src/settings.py` line 24 |
| Unit tests for adapter | `tests/unit/test_llm_adapter.py` |
| Integration contract tests | `tests/integration/test_adapter_contracts.py` |
| Epic 30 (real provider flip) | `docs/epics/epic-30-real-provider-integration.md` |
| Sprint 1 intent eval results | `docs/eval-results/sprint1-intent.md` |
| LLMAdapterProtocol | `src/adapters/llm.py` lines 43-50 |
| Claude Code auth docs | `https://code.claude.com/docs/en/authentication` |
| LiteLLM Max subscription guide | `https://docs.litellm.ai/docs/tutorials/claude_code_max_subscription` |
| OAuth beta header issue | `https://github.com/BerriAI/litellm/issues/22398` |
| Anthropic legal stance on OAuth | `https://daveswift.com/claude-oauth-update/` |
| Claude Code OAuth issue #6536 | `https://github.com/anthropics/claude-code/issues/6536` |

---

## 4. Acceptance Criteria

### AC 1: Research Documented (Story 31.0) — COMPLETE
OAuth token mechanics, required headers, token lifecycle, legal/TOS implications, and rate limits are documented with sources. Decision on whether to proceed with implementation is recorded.

### AC 2: OAuth Token Auto-Detection
When `THESTUDIO_ANTHROPIC_API_KEY` contains a token with prefix `sk-ant-oat01-`, the `AnthropicAdapter` sends it as `Authorization: Bearer <token>` with `anthropic-beta: oauth-2025-04-20` instead of `x-api-key: <token>`. No configuration change beyond the key value itself is required.

### AC 3: Standard API Key Backward Compatibility
When `THESTUDIO_ANTHROPIC_API_KEY` contains a standard key with prefix `sk-ant-api03-`, the adapter continues to use the `x-api-key` header exactly as it does today. All existing tests pass without modification.

### AC 4: Token Refresh Handling
The adapter handles 8-hour token expiration gracefully. When a 401 is received with an OAuth token, the adapter attempts to refresh using the stored refresh token before falling back to error. Refresh token (`sk-ant-ort01-...`) and client ID are stored in settings.

### AC 5: Explicit Auth Mode Override
A new optional setting `THESTUDIO_ANTHROPIC_AUTH_MODE` (values: `auto`, `api_key`, `oauth`) allows operators to force a specific authentication mode. Default is `auto` (prefix-based detection).

### AC 6: Test Coverage for Both Auth Paths
Unit tests verify that (a) an `sk-ant-oat01-` key produces Bearer + beta headers, (b) an `sk-ant-api03-` key produces an `x-api-key` header, (c) the explicit override takes precedence, (d) token refresh on 401, and (e) an unrecognized prefix falls back to `x-api-key` with warning.

### AC 7: Cost Estimation Fix
`ProviderConfig` cost rates updated to match actual Anthropic pricing. `AgentRunner` cost estimates within 20% of actual billing.

---

### 4b. Top Risks

| # | Risk | Likelihood | Impact | Mitigation |
|---|------|-----------|--------|------------|
| R1 | Anthropic changes OAuth token prefix format | Low | Medium | Explicit `auth_mode` override bypasses prefix detection |
| R2 | OAuth tokens have different rate limits or model access | Medium | Medium | Document observed differences; no 1M context with OAuth |
| R3 | **Using OAuth tokens in a standalone server violates Anthropic TOS** | **High** | **High** | **Do not deploy OAuth for standalone pipeline server. Only use if pipeline runs within Claude Code context. Research alternative: Claude Code as the execution runtime.** |
| R4 | Token refresh adds complexity and failure modes | Medium | Medium | Refresh token rotation with retry; fall back to error on refresh failure |
| R5 | `anthropic-beta: oauth-2025-04-20` header conflicts with other beta features | Medium | Low | Merge beta headers rather than overwrite |

---

## 5. Constraints & Non-Goals

### Constraints
- The `LLMAdapterProtocol` interface must not change
- No new pip dependencies
- **Must not violate Anthropic TOS** — if OAuth is restricted to first-party tools, implementation must be gated behind a clear disclaimer and only enabled for development/testing use
- OAuth token refresh adds a new failure mode that must be handled gracefully

### Non-Goals
- **Token procurement automation.** Getting the OAuth token is manual (`claude login` + token extraction)
- **Per-agent auth mode.** All agents share one adapter instance and one key
- **Production deployment with OAuth.** Until Anthropic's position on third-party OAuth is clarified, this is for development cost savings only
- **Anthropic SDK migration.** The adapter uses raw `httpx`
- **Cost tracking dashboard.** Epic 30's cost model covers that

---

## 6. Stakeholders & Roles

| Role | Who | Responsibility |
|------|-----|----------------|
| Epic Owner | Primary Developer | Implementation, testing, docs |
| Tech Lead | Primary Developer | TOS compliance decision |
| QA | Automated (pytest) | Unit + integration tests |
| Reviewer | Meridian (persona) | Epic review before commit |

---

## 7. Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Research documented | All OAuth mechanics and risks captured | Story 31.0 complete |
| Auth mode works for dev/test | OAuth token produces 200 responses | Manual validation |
| Zero regression | All existing tests pass unchanged | CI |
| Cost estimation accuracy | Within 20% of actual billing | Compare AgentRunner estimates to Anthropic dashboard |
| Test coverage | >= 8 new test cases | pytest count |

---

## 8. Context & Assumptions

### Research Findings (Story 31.0)

#### How OAuth Authentication Works

1. **Token format:** Access tokens use prefix `sk-ant-oat01-`, refresh tokens use `sk-ant-ort01-`
2. **Auth header:** `Authorization: Bearer sk-ant-oat01-...` (NOT `x-api-key`)
3. **Required beta header:** `anthropic-beta: oauth-2025-04-20` (must be merged with other beta values, not overwrite)
4. **API endpoint:** Same `https://api.anthropic.com/v1/messages` — no endpoint change
5. **`anthropic-version` header:** Still required (`2023-06-01`)
6. **Token expiration:** Access token expires in 8 hours (`expires_in: 28800`)
7. **Token refresh:** `POST https://console.anthropic.com/api/oauth/token` with `grant_type=refresh_token`, `refresh_token=sk-ant-ort01-...`, `client_id=9d1c250a-e61b-44d9-88ed-5944d1962f5e`
8. **Usage billing:** Counted against subscription quota, not per-token billing
9. **Context window:** 1M context unavailable with OAuth tokens (200k max)

#### How to Obtain Tokens

Option A (official): `claude setup-token` CLI command
Option B (manual): Intercept OAuth flow via mitmproxy during `claude login`

#### TOS and Legal Status

- **First-party use (Claude Code, Claude Desktop):** Supported, OAuth is the default auth
- **Third-party use (standalone servers, custom apps):** Anthropic has sent legal requests removing OAuth from third-party integrations (OpenClaw, OpenCode confirmed)
- **Gray area:** TheStudio running as a Claude Code extension or plugin vs. standalone server
- **Recommendation:** Use OAuth for development/testing only. Use standard API keys for production. Monitor Anthropic's official API docs for any sanctioned third-party OAuth path.

#### Claude Code Auth Precedence (from official docs)

1. Cloud provider credentials (Bedrock, Vertex, Foundry)
2. `ANTHROPIC_AUTH_TOKEN` env var → `Authorization: Bearer` header
3. `ANTHROPIC_API_KEY` env var → `X-Api-Key` header
4. `apiKeyHelper` script output
5. Subscription OAuth credentials from `/login`

**Key insight:** Claude Code itself uses `ANTHROPIC_AUTH_TOKEN` with Bearer headers. This is the officially documented path for bearer token auth.

### Cost Model Reality

| Source | Intent Agent (10 cases) | Notes |
|--------|-------------------------|-------|
| AgentRunner estimate | $0.13 | Stale `cost_per_1k_tokens` in ProviderConfig |
| Anthropic billing (full test session) | $2.08 | 80+ API calls (8 tests x 10 cases each) |
| Per-call actual | ~$0.023 | $2.08 / ~90 calls |

**The internal cost tracker underreports by ~16x.** This must be fixed in ProviderConfig regardless of auth mode decision.

### Dependencies
- **Epic 30 Sprint 1** is the first consumer
- No infrastructure dependencies for the adapter change
- Token refresh requires network access to `console.anthropic.com`

### Systems Affected
- `src/adapters/llm.py` — auth header logic, beta header, token refresh
- `src/settings.py` — new `anthropic_auth_mode`, `anthropic_refresh_token`, `anthropic_oauth_client_id` settings
- `tests/unit/test_llm_adapter.py` — new test cases
- `src/admin/model_gateway.py` — fix `cost_per_1k_tokens` values

---

## Story Map

### Story 31.0: Research & Document OAuth Token Mechanics (COMPLETE)

**Status: COMPLETE (2026-03-18)**

Research the Anthropic OAuth token authentication flow, document findings, and make a go/no-go recommendation for implementation.

**Findings documented in this epic's Section 8.**

**Key decision:** Proceed with implementation for development/testing use. Do NOT use OAuth tokens for production standalone server until Anthropic provides an official third-party API OAuth path. Use standard API keys ($2.08 per full test session is acceptable for development).

---

### Story 31.1: Fix Cost Estimation in ProviderConfig

**As a** developer monitoring pipeline costs,
**I want** accurate cost estimates from AgentRunner,
**so that** budget caps and cost tracking reflect actual Anthropic billing.

**Details:**
- Update `cost_per_1k_tokens` in `ProviderConfig` defaults to match actual Sonnet 4.6 pricing ($3/M input, $15/M output → split rate)
- Add separate `cost_per_1k_input` and `cost_per_1k_output` fields to `ProviderConfig`
- Update `AgentRunner` cost calculation to use split input/output rates
- Validate estimates are within 20% of actual billing

**Files to modify:** `src/admin/model_gateway.py`, `src/agent/framework.py`
**Estimate:** 2 points

---

### Story 31.2: Add Auth Mode Detection and Dual-Header Support

**As a** developer using a Claude Max subscription,
**I want** the AnthropicAdapter to auto-detect OAuth tokens and use the correct auth headers,
**so that** I can use my subscription for development pipeline runs.

**Details:**
- Detect key prefix in `AnthropicAdapter.__init__`
- Add `anthropic_auth_mode` setting to `src/settings.py` (values: `auto`, `api_key`, `oauth`; default `auto`)
- OAuth path: `Authorization: Bearer` + merge `oauth-2025-04-20` into `anthropic-beta` header
- API key path: `x-api-key` header (unchanged)
- Structured log on mode selection (prefix + mode, no secrets)
- Add disclaimer comment: OAuth for development/testing only

**Files to modify:** `src/adapters/llm.py`, `src/settings.py`
**Estimate:** 3 points

---

### Story 31.3: Token Refresh on Expiration

**As a** developer running long eval sessions,
**I want** the adapter to refresh expired OAuth tokens automatically,
**so that** 8-hour token expiration doesn't break multi-hour test runs.

**Details:**
- Add `anthropic_refresh_token` and `anthropic_oauth_client_id` settings
- On 401 response with OAuth mode, attempt token refresh via `POST https://console.anthropic.com/api/oauth/token`
- Cache refreshed access token for subsequent calls
- If refresh fails, raise clear error (not silent fallback)
- Log token refresh events at INFO level

**Files to modify:** `src/adapters/llm.py`, `src/settings.py`
**Estimate:** 3 points

---

### Story 31.4: Unit Tests for Both Auth Paths

**As a** developer maintaining the adapter,
**I want** comprehensive tests for both auth modes,
**so that** changes don't break either path.

**Details:**
- Test OAuth prefix → Bearer + beta headers
- Test API key prefix → x-api-key header
- Test explicit override takes precedence
- Test unrecognized prefix falls back to x-api-key with warning
- Test token refresh on 401 (mock HTTP)
- Test beta header merging (oauth + other betas)
- No regression on existing tests

**Files to modify:** `tests/unit/test_llm_adapter.py`
**Estimate:** 2 points

---

### Story 31.5: Live Validation with Real OAuth Token

**As a** developer validating the adapter,
**I want** to confirm OAuth tokens work against the real Anthropic API,
**so that** we have confidence before recommending this for development use.

**Details:**
- Obtain OAuth token via `claude setup-token` or mitmproxy
- Run intent eval (3 cases) with OAuth token
- Compare response shape, latency, and model access to standard API key
- Document any differences in rate limits or model availability
- Document 200k context window limitation

**Files to create:** Results appended to `docs/eval-results/sprint1-intent.md`
**Estimate:** 1 point

---

### Story 31.6: Documentation Update

**As a** developer deploying TheStudio,
**I want** deployment docs that explain both auth modes,
**so that** I can make an informed choice.

**Details:**
- Document `THESTUDIO_ANTHROPIC_AUTH_MODE` env var
- Document Claude Max OAuth token usage pattern (development only)
- Document token refresh configuration
- Document TOS limitations and production recommendation (use API keys)
- Add cost comparison table

**Files to modify:** `docs/DEPLOYMENT.md`
**Estimate:** 1 point

---

## Alternative Cost Strategies (If OAuth Is Not Viable for Production)

If OAuth remains restricted to first-party tools, these strategies reduce production API costs:

1. **Model routing by agent complexity:**
   - Intake, context, router → Haiku ($0.25/M input vs $3/M = 12x cheaper)
   - Intent, QA → Sonnet (current, good quality)
   - Primary agent → Sonnet with budget cap
   - Estimated savings: 40-60% on pipeline cost

2. **Aggressive budget caps:** Current $5/issue cap is rarely hit. Tighten to $2 for Observe tier.

3. **Caching:** Cache intent specs for duplicate/similar issues. Cache context enrichment.

4. **Batching:** Batch low-priority issues for off-peak processing.

5. **Claude Code as runtime:** Run TheStudio's pipeline within Claude Code itself (uses subscription). This is architecturally different but would be a legitimate first-party usage pattern.

---

## Meridian Review Status

### Round 1: Pending

*This epic requires Meridian review before commit. Key questions:*
1. Is the TOS risk assessment (R3) accurately scoped?
2. Should implementation proceed given the legal uncertainty, or should we defer to cost optimization strategies?
3. Is the cost estimation fix (Story 31.1) correctly scoped as part of this epic vs. a separate fix?
4. Is the "development only" stance on OAuth sufficient, or should we avoid OAuth entirely?
