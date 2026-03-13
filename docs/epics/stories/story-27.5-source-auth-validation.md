# Story 27.5 — Source Auth Validation

> **As a** platform developer,
> **I want** auth validation that supports API key, HMAC-SHA256, bearer token, and pass-through modes,
> **so that** each configured source can use its native authentication scheme without custom code.

**Purpose:** Security is not optional. The generic webhook endpoint must authenticate every request using the scheme the source supports. Without this, the endpoint is an open door into the pipeline. This story provides the multi-scheme auth validator that the endpoint (Story 27.4) calls before any payload processing.

**Intent:** Create `src/ingress/sources/auth.py` with `validate_source_auth(source: SourceConfig, request: Request) -> bool`. Implements four auth strategies: API key header check (timing-safe), HMAC-SHA256 body signature (same pattern as GitHub), bearer token header check (timing-safe), and none (pass-through for trusted internal sources).

**Points:** 5 | **Size:** M
**Epic:** 27 — Webhook Triggers for Non-GitHub Input Sources
**Sprint:** 1 (Stories 27.1, 27.5, 27.3, 27.4)
**Depends on:** Story 27.1 (Source Definition Model)

---

## Description

This module mirrors the security properties of `src/ingress/signature.py` (the existing GitHub HMAC validator) but generalizes to multiple auth schemes. Every comparison is timing-safe. Secrets are read from environment variables at validation time, never stored in config.

### Auth strategies:

1. **API Key (`api_key`).** The source sends a secret value in a configured header (e.g., `X-API-Key: abc123`). The validator reads the expected value from `os.environ[source.auth.secret_env_var]` and does a timing-safe comparison.

2. **HMAC-SHA256 (`hmac_sha256`).** The source signs the request body and puts the signature in a configured header (e.g., `X-Jira-Webhook-Signature: sha256=abc123`). The validator computes `HMAC-SHA256(secret, body)` and does a timing-safe comparison. Handles both `sha256=...` prefixed and raw hex formats.

3. **Bearer Token (`bearer`).** The source sends a token in the `Authorization: Bearer {token}` header. The validator extracts the token and does a timing-safe comparison against the secret.

4. **None (`none`).** Pass-through. Returns True immediately. For internal/trusted sources only. The admin API should warn when creating a source with `auth.type = none`.

### Security invariants:

- All string comparisons use `hmac.compare_digest()` — no `==` for secrets.
- If the configured env var is missing, validation fails (deny by default).
- If the expected header is missing from the request, validation fails.
- Empty secrets are rejected (env var set to empty string = fail).

## Tasks

- [ ] Create `src/ingress/sources/auth.py`:
  - `class AuthValidationError(Exception)` — raised with detail about what failed (for logging, not for the client)
    - `source_name: str`
    - `auth_type: str`
    - `reason: str` (e.g., "missing header", "missing env var", "signature mismatch")
  - `def _get_secret(source: SourceConfig) -> str`
    - Read `os.environ[source.auth.secret_env_var]`
    - Raise `AuthValidationError` if env var is missing or empty
  - `def _validate_api_key(request_headers: dict, header_name: str, expected: str) -> bool`
    - Extract header value
    - Timing-safe compare with expected
  - `def _validate_hmac(body: bytes, header_value: str, secret: str) -> bool`
    - Compute HMAC-SHA256 of body with secret
    - Handle `sha256=` prefix (strip if present)
    - Timing-safe compare
  - `def _validate_bearer(request_headers: dict, expected: str) -> bool`
    - Extract `Authorization` header
    - Strip `Bearer ` prefix
    - Timing-safe compare
  - `async def validate_source_auth(source: SourceConfig, request: Request) -> bool`
    - Dispatch to the correct validator based on `source.auth.type`
    - For `none`: return True immediately
    - For others: read secret, extract header, validate
    - On any failure: log the reason (structured logging with source_name), return False
    - Note: `request.body()` must be called for HMAC. The caller (endpoint) should pass pre-read body bytes to avoid double-read issues.
  - Alternative signature for testability: `validate_source_auth(source: SourceConfig, headers: dict, body: bytes) -> bool` (avoids coupling to FastAPI Request in tests)
- [ ] Write tests in `tests/ingress/sources/test_auth.py`:
  - API key: valid key, invalid key, missing header, missing env var
  - HMAC: valid signature (with prefix), valid (without prefix), invalid signature, missing header, missing env var
  - Bearer: valid token, invalid token, missing Authorization header, missing env var
  - None: always passes
  - Empty secret env var: fails
  - Timing-safe comparison: verify `hmac.compare_digest` is used (mock and assert)

## Acceptance Criteria

- [ ] `validate_source_auth()` returns True for valid API key
- [ ] `validate_source_auth()` returns True for valid HMAC-SHA256 signature
- [ ] `validate_source_auth()` returns True for valid bearer token
- [ ] `validate_source_auth()` returns True for auth type `none`
- [ ] All invalid credentials return False (not an exception to the caller)
- [ ] Missing env var returns False and logs a warning
- [ ] Missing header returns False
- [ ] Empty secret returns False
- [ ] All comparisons use `hmac.compare_digest()` (timing-safe)
- [ ] All tests pass

## Test Cases

| # | Scenario | Input | Expected Output |
|---|----------|-------|-----------------|
| 1 | Valid API key | Header matches env var secret | True |
| 2 | Invalid API key | Header does not match | False |
| 3 | Missing API key header | Header absent | False |
| 4 | Valid HMAC (prefixed) | `sha256=<valid_sig>` in header | True |
| 5 | Valid HMAC (raw hex) | `<valid_sig>` in header (no prefix) | True |
| 6 | Invalid HMAC | Wrong signature | False |
| 7 | Valid bearer | `Authorization: Bearer <valid>` | True |
| 8 | Invalid bearer | Wrong token | False |
| 9 | Missing Authorization | No Authorization header | False |
| 10 | Auth type none | Any headers | True |
| 11 | Missing env var | `secret_env_var` not in os.environ | False, warning logged |
| 12 | Empty env var | `secret_env_var = ""` | False |

## Files Affected

| File | Action |
|------|--------|
| `src/ingress/sources/auth.py` | Create |
| `tests/ingress/sources/test_auth.py` | Create |

## Technical Notes

- Reuse the pattern from `src/ingress/signature.py` for HMAC validation. That module uses `hmac.new()` and `hmac.compare_digest()` — the same approach applies here.
- For the function signature, prefer `(source: SourceConfig, headers: dict[str, str], body: bytes)` over `(source, request: Request)`. This decouples auth logic from FastAPI and makes testing trivial (no need to construct mock Request objects). The endpoint extracts headers and body before calling.
- The `none` auth type should emit a structured log at `INFO` level noting that an unauthenticated request was accepted. This creates an audit trail for security review.
- HMAC computation must use the raw body bytes, not re-serialized JSON. JSON serialization is not deterministic (key order, whitespace), so computing HMAC on `json.dumps(payload)` instead of the original bytes will fail.
