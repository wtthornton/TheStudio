"""Labeled test dataset for agent evaluation.

Epic 30, Story 30.1: 10 realistic GitHub issues spanning bug fix, feature,
security, refactor, documentation, breaking change, multi-file, performance,
dependency update, and API design categories. Each case includes expected
output characteristics for scoring.
"""

from __future__ import annotations

from src.eval.models import EvalCase

INTENT_DATASET: list[EvalCase] = [
    # ---------------------------------------------------------------
    # 1. Simple bug fix
    # ---------------------------------------------------------------
    EvalCase(
        case_id="bug_fix_01",
        category="bug_fix",
        issue_title="Fix: UserProfile.avatar_url returns None for users with default avatars",
        issue_body=(
            "## Description\n\n"
            "When a user hasn't uploaded a custom avatar, `UserProfile.avatar_url` "
            "returns `None` instead of the default Gravatar URL. This causes a "
            "`TypeError` in the template layer when trying to render the avatar.\n\n"
            "## Steps to Reproduce\n"
            "1. Create a new user without uploading an avatar\n"
            "2. Navigate to /profile\n"
            "3. See `TypeError: expected str, got NoneType`\n\n"
            "## Expected Behavior\n"
            "Should return the Gravatar URL based on the user's email hash.\n\n"
            "## Acceptance Criteria\n"
            "- [ ] `avatar_url` returns a valid URL for users without custom avatars\n"
            "- [ ] Gravatar fallback uses the user's email hash\n"
            "- [ ] Existing custom avatars are not affected"
        ),
        labels=["bug", "priority:high"],
        risk_flags={},
        complexity="low",
        expected_goal_keywords=["avatar", "gravatar", "default", "none", "url"],
        expected_constraints=["tests"],
        expected_acs=["avatar_url", "gravatar", "custom avatars"],
        expects_invariants=False,
        expects_non_goals=True,
    ),
    # ---------------------------------------------------------------
    # 2. Feature request
    # ---------------------------------------------------------------
    EvalCase(
        case_id="feature_02",
        category="feature",
        issue_title="Add pagination to /api/v1/tasks endpoint",
        issue_body=(
            "## Description\n\n"
            "The tasks endpoint currently returns all tasks in a single response. "
            "For repos with 1000+ tasks, this is too slow and uses too much memory.\n\n"
            "## Requirements\n"
            "- Add `page` and `per_page` query parameters\n"
            "- Default page size: 50, max: 200\n"
            "- Response should include `total_count`, `page`, `per_page`, "
            "`total_pages` in a wrapper object\n"
            "- Existing filters (`status`, `repo_id`) must continue to work\n"
            "- Empty pages should return an empty `items` list, not 404\n\n"
            "## Out of Scope\n"
            "- Cursor-based pagination (future consideration)\n"
            "- Caching layer"
        ),
        labels=["feature", "api"],
        risk_flags={},
        complexity="medium",
        expected_goal_keywords=["pagination", "tasks", "endpoint", "page"],
        expected_constraints=["tests", "backward"],
        expected_acs=["page", "per_page", "total_count", "filters", "empty"],
        expects_invariants=True,
        expects_non_goals=True,
    ),
    # ---------------------------------------------------------------
    # 3. Security fix
    # ---------------------------------------------------------------
    EvalCase(
        case_id="security_03",
        category="security",
        issue_title="CVE-2026-1234: SQL injection in repo search endpoint",
        issue_body=(
            "## Vulnerability\n\n"
            "The `/api/v1/repos/search` endpoint passes the `q` parameter "
            "directly into a raw SQL query without parameterization. This allows "
            "an attacker to execute arbitrary SQL.\n\n"
            "## Impact\n"
            "Critical — full database read access, potential data exfiltration.\n\n"
            "## Fix\n"
            "Replace the raw SQL query with a parameterized SQLAlchemy query. "
            "Add input validation for the `q` parameter (max length, allowed characters).\n\n"
            "## Acceptance Criteria\n"
            "- [ ] `q` parameter is parameterized, not interpolated\n"
            "- [ ] Input validation rejects queries > 500 chars\n"
            "- [ ] SQL injection payloads return 400, not results\n"
            "- [ ] Search functionality still works for normal queries"
        ),
        labels=["security", "priority:critical"],
        risk_flags={"security": True, "data_access": True},
        complexity="medium",
        expected_goal_keywords=["sql injection", "parameterized", "search", "security"],
        expected_constraints=["security", "parameterized", "validation", "tests"],
        expected_acs=["parameterized", "validation", "injection", "search"],
        expects_invariants=True,
        expects_non_goals=True,
    ),
    # ---------------------------------------------------------------
    # 4. Refactoring
    # ---------------------------------------------------------------
    EvalCase(
        case_id="refactor_04",
        category="refactor",
        issue_title="Refactor: Extract notification logic from TaskPacket into NotificationService",
        issue_body=(
            "## Problem\n\n"
            "TaskPacket has grown to handle email, Slack, and webhook notifications "
            "inline. This violates single responsibility and makes the class harder "
            "to test. Notification logic is duplicated across 3 methods.\n\n"
            "## Proposed Change\n"
            "1. Create `NotificationService` class in `src/notifications/service.py`\n"
            "2. Move email, Slack, and webhook dispatch into the service\n"
            "3. TaskPacket calls `NotificationService.notify()` instead of inline logic\n"
            "4. Add a `NotificationChannel` enum for channel types\n\n"
            "## Constraints\n"
            "- All existing notification behavior must be preserved\n"
            "- No new dependencies\n"
            "- Existing tests must pass without modification"
        ),
        labels=["refactor", "tech-debt"],
        risk_flags={"breaking_change": True},
        complexity="medium",
        expected_goal_keywords=[
            "extract",
            "notification",
            "service",
            "single responsibility",
        ],
        expected_constraints=["existing", "behavior", "preserved", "tests", "no new dependencies"],
        expected_acs=["notification", "service", "taskpacket"],
        expects_invariants=True,
        expects_non_goals=True,
    ),
    # ---------------------------------------------------------------
    # 5. Documentation
    # ---------------------------------------------------------------
    EvalCase(
        case_id="docs_05",
        category="documentation",
        issue_title="Document the webhook retry and dead-letter behavior",
        issue_body=(
            "## Gap\n\n"
            "The webhook retry policy (exponential backoff, max 5 retries, "
            "30-minute window) and dead-letter queue behavior are implemented "
            "but not documented anywhere a developer can find them.\n\n"
            "## Requirements\n"
            "- Add a section to `docs/WEBHOOKS.md` explaining retry behavior\n"
            "- Document the dead-letter queue: when messages go there, "
            "how to inspect, how to replay\n"
            "- Include a sequence diagram showing the retry flow\n"
            "- Add a troubleshooting section for common webhook failures"
        ),
        labels=["documentation"],
        risk_flags={},
        complexity="low",
        expected_goal_keywords=["document", "webhook", "retry", "dead-letter"],
        expected_constraints=["tests"],
        expected_acs=["retry", "dead-letter", "diagram", "troubleshooting"],
        expects_invariants=False,
        expects_non_goals=True,
    ),
    # ---------------------------------------------------------------
    # 6. Breaking change
    # ---------------------------------------------------------------
    EvalCase(
        case_id="breaking_06",
        category="breaking_change",
        issue_title="Migrate TaskPacket.status from string enum to integer status codes",
        issue_body=(
            "## Motivation\n\n"
            "String-based status comparison is error-prone and slow for DB queries. "
            "Moving to integer status codes improves query performance and prevents "
            "typo-based bugs.\n\n"
            "## Migration Plan\n"
            "1. Add `status_code` integer column (nullable)\n"
            "2. Backfill from existing `status` string column\n"
            "3. Switch application code to use `status_code`\n"
            "4. Drop `status` string column in a follow-up migration\n\n"
            "## Breaking Changes\n"
            "- API responses will return integer status codes instead of strings\n"
            "- Webhook payloads will include both during transition period\n"
            "- Admin UI must be updated to display status names from codes\n\n"
            "## Acceptance Criteria\n"
            "- [ ] Migration adds `status_code` column\n"
            "- [ ] Backfill script populates existing rows\n"
            "- [ ] All API endpoints use `status_code`\n"
            "- [ ] Webhook payloads include both `status` and `status_code`\n"
            "- [ ] Admin UI renders status names correctly"
        ),
        labels=["breaking-change", "database", "migration"],
        risk_flags={"breaking_change": True, "data_migration": True},
        complexity="high",
        expected_goal_keywords=["migrate", "status", "integer", "status_code"],
        expected_constraints=[
            "migration",
            "backward",
            "data",
            "tests",
        ],
        expected_acs=["migration", "backfill", "api", "webhook", "admin"],
        expects_invariants=True,
        expects_non_goals=True,
    ),
    # ---------------------------------------------------------------
    # 7. Multi-file change
    # ---------------------------------------------------------------
    EvalCase(
        case_id="multi_file_07",
        category="multi_file",
        issue_title="Add correlation_id propagation to all HTTP middleware and background workers",
        issue_body=(
            "## Problem\n\n"
            "correlation_id is generated at intake but lost when requests pass "
            "through middleware or are picked up by background Temporal workers. "
            "This makes distributed tracing incomplete.\n\n"
            "## Requirements\n"
            "- HTTP middleware extracts `X-Correlation-ID` header or generates a new UUID\n"
            "- correlation_id is set in the async context (contextvars)\n"
            "- All Temporal activities receive correlation_id via activity input\n"
            "- Structured logging automatically includes correlation_id\n"
            "- Outbound HTTP calls include `X-Correlation-ID` header\n\n"
            "## Files Affected\n"
            "- `src/middleware/correlation.py` (new)\n"
            "- `src/workflow/activities.py`\n"
            "- `src/adapters/github.py`\n"
            "- `src/observability/logging.py`\n"
            "- `src/app.py` (register middleware)"
        ),
        labels=["observability", "cross-cutting"],
        risk_flags={"cross_team": True},
        complexity="high",
        expected_goal_keywords=["correlation_id", "propagation", "middleware", "tracing"],
        expected_constraints=["tests", "existing"],
        expected_acs=[
            "correlation_id",
            "header",
            "contextvars",
            "temporal",
            "logging",
        ],
        expects_invariants=True,
        expects_non_goals=True,
    ),
    # ---------------------------------------------------------------
    # 8. Performance issue
    # ---------------------------------------------------------------
    EvalCase(
        case_id="perf_08",
        category="performance",
        issue_title="Optimize: ReputationEngine.get_weights() is O(n²) for repos with many experts",
        issue_body=(
            "## Problem\n\n"
            "`get_weights()` iterates over all experts for every context key, "
            "resulting in O(n*m) complexity where n=experts and m=context_keys. "
            "For repos with 50+ experts and 20+ context keys, this takes >2s.\n\n"
            "## Root Cause\n"
            "The inner loop does a linear scan of `expert_weights` list for each "
            "context key instead of using a dict lookup.\n\n"
            "## Proposed Fix\n"
            "Pre-build a `dict[str, dict[str, float]]` mapping "
            "`(expert_id, context_key) -> weight` during initialization. "
            "Lookups become O(1) per key.\n\n"
            "## Acceptance Criteria\n"
            "- [ ] `get_weights()` runs in < 50ms for 100 experts x 50 context keys\n"
            "- [ ] Weight values are identical before and after optimization\n"
            "- [ ] Memory usage increase is < 10MB for the lookup dict"
        ),
        labels=["performance", "reputation"],
        risk_flags={},
        complexity="medium",
        expected_goal_keywords=["optimize", "get_weights", "performance", "O(1)"],
        expected_constraints=["tests", "identical", "values"],
        expected_acs=["50ms", "identical", "memory"],
        expects_invariants=True,
        expects_non_goals=True,
    ),
    # ---------------------------------------------------------------
    # 9. Dependency update
    # ---------------------------------------------------------------
    EvalCase(
        case_id="dep_update_09",
        category="dependency_update",
        issue_title="Upgrade httpx from 0.25.x to 0.27.x",
        issue_body=(
            "## Motivation\n\n"
            "httpx 0.27 includes HTTP/2 improvements, better timeout handling, "
            "and fixes for connection pool leaks that we've hit in production.\n\n"
            "## Changes Required\n"
            "- Update `httpx` version in `pyproject.toml`\n"
            "- Update `respx` (mock library) to compatible version\n"
            "- Review changelog for breaking changes in 0.26 and 0.27\n"
            "- Verify all HTTP adapter tests pass\n"
            "- Check that `AsyncClient` API usage is still compatible\n\n"
            "## Known Breaking Changes (from changelog)\n"
            "- `httpx.TimeoutException` renamed to `httpx.TimeoutError` in 0.26\n"
            "- `httpx.StreamConsumed` moved to `httpx.StreamClosed` in 0.27"
        ),
        labels=["dependencies", "maintenance"],
        risk_flags={},
        complexity="low",
        expected_goal_keywords=["upgrade", "httpx", "0.27"],
        expected_constraints=["tests", "compatible"],
        expected_acs=["httpx", "respx", "tests", "breaking changes"],
        expects_invariants=True,
        expects_non_goals=True,
    ),
    # ---------------------------------------------------------------
    # 10. API design
    # ---------------------------------------------------------------
    EvalCase(
        case_id="api_design_10",
        category="api_design",
        issue_title="Design and implement /api/v2/evidence endpoint for external consumers",
        issue_body=(
            "## Context\n\n"
            "External CI/CD systems want to query evidence bundles for completed "
            "tasks. Currently evidence is only visible in PR comments.\n\n"
            "## Requirements\n"
            "- GET `/api/v2/evidence/{taskpacket_id}` returns the full evidence bundle\n"
            "- Response includes: verification results, QA results, expert coverage, "
            "loopback history, cost summary\n"
            "- Authenticated via GitHub App installation token\n"
            "- Rate limited: 100 requests/minute per installation\n"
            "- Supports `Accept: application/json` and `Accept: text/markdown`\n\n"
            "## Out of Scope\n"
            "- Write endpoints (evidence is read-only)\n"
            "- Bulk export\n"
            "- Webhook notifications for new evidence"
        ),
        labels=["feature", "api", "v2"],
        risk_flags={"security": True},
        complexity="high",
        expected_goal_keywords=["evidence", "endpoint", "api", "external"],
        expected_constraints=["authentication", "rate limit", "security", "tests"],
        expected_acs=[
            "evidence",
            "taskpacket_id",
            "verification",
            "authentication",
            "rate limit",
        ],
        expects_invariants=False,
        expects_non_goals=True,
    ),
]


def load_intent_dataset() -> list[EvalCase]:
    """Return the labeled intent evaluation dataset."""
    return list(INTENT_DATASET)
