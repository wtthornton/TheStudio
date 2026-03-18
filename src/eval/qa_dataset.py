"""Labeled QA evaluation dataset — synthetic evidence bundles.

Epic 30, Story 30.3: 10 synthetic evidence bundles (7 with planted defects,
3 clean) for validating the QA agent's defect detection and classification.
Each bundle includes acceptance criteria, evidence, and expected outcomes.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class QAEvalCase:
    """A labeled test case for QA agent evaluation.

    Extends the concept of EvalCase with evidence bundles and expected
    defect characteristics for QA-specific scoring.
    """

    case_id: str
    category: str  # "planted_defect" or "clean"
    description: str

    # Intent inputs
    acceptance_criteria: list[str] = field(default_factory=list)

    # Evidence bundle (what the primary agent produced)
    agent_summary: str = ""
    test_results: str = ""
    lint_results: str = ""
    file_changes: list[str] = field(default_factory=list)

    # Expected QA outcomes
    expects_defects: bool = True
    expected_defect_count: int = 0
    expected_defect_categories: list[str] = field(default_factory=list)
    expected_severity_floor: str = ""  # minimum severity expected (e.g. "S1_high")
    is_clean: bool = False


QA_DATASET: list[QAEvalCase] = [
    # ---------------------------------------------------------------
    # 1. Intent gap — ambiguous acceptance criterion
    # ---------------------------------------------------------------
    QAEvalCase(
        case_id="qa_intent_gap_01",
        category="planted_defect",
        description="Ambiguous acceptance criterion: 'system should be fast'",
        acceptance_criteria=[
            "API response time should be fast",
            "Error messages should be user-friendly",
            "Pagination returns correct page counts",
        ],
        agent_summary=(
            "Implemented pagination for the tasks endpoint. Added page and "
            "per_page query parameters with defaults of 50 and max of 200. "
            "Response includes total_count, page, per_page, total_pages."
        ),
        test_results="12 tests passed, 0 failed. Coverage: 89%.",
        lint_results="ruff: 0 errors, 0 warnings.",
        file_changes=["src/api/tasks.py", "tests/api/test_tasks.py"],
        expects_defects=True,
        expected_defect_count=1,
        expected_defect_categories=["intent_gap"],
        expected_severity_floor="S1_high",
    ),
    # ---------------------------------------------------------------
    # 2. Missing test coverage
    # ---------------------------------------------------------------
    QAEvalCase(
        case_id="qa_missing_tests_02",
        category="planted_defect",
        description="Feature added but no new tests written",
        acceptance_criteria=[
            "New /api/v2/export endpoint returns CSV data",
            "Endpoint requires authentication",
            "Large exports are streamed, not buffered",
        ],
        agent_summary=(
            "Added /api/v2/export endpoint that returns CSV data. "
            "Added authentication check using the existing auth middleware. "
            "Implemented streaming response for large datasets."
        ),
        test_results="0 new tests. Existing tests: 45 passed, 0 failed.",
        lint_results="ruff: 0 errors.",
        file_changes=["src/api/export.py"],
        expects_defects=True,
        expected_defect_count=1,
        expected_defect_categories=["implementation_bug"],
        expected_severity_floor="S1_high",
    ),
    # ---------------------------------------------------------------
    # 3. Security vulnerability — hardcoded secret
    # ---------------------------------------------------------------
    QAEvalCase(
        case_id="qa_security_03",
        category="planted_defect",
        description="Hardcoded API key in source code",
        acceptance_criteria=[
            "Webhook notifications are sent to Slack on task completion",
            "Slack webhook URL is configurable via environment variable",
            "Failed notifications are logged but don't block the pipeline",
        ],
        agent_summary=(
            "Implemented Slack notification on task completion. "
            "Configured webhook URL. Added error handling for failed sends."
        ),
        test_results="5 tests passed, 0 failed.",
        lint_results=(
            "ruff: 0 errors. bandit: 1 HIGH — hardcoded password "
            "(B105) in src/notifications/slack.py:12."
        ),
        file_changes=["src/notifications/slack.py", "tests/test_slack.py"],
        expects_defects=True,
        expected_defect_count=1,
        expected_defect_categories=["security"],
        expected_severity_floor="S0_critical",
    ),
    # ---------------------------------------------------------------
    # 4. Regression — broken existing test
    # ---------------------------------------------------------------
    QAEvalCase(
        case_id="qa_regression_04",
        category="planted_defect",
        description="Existing test now fails after refactor",
        acceptance_criteria=[
            "Extract notification logic into NotificationService",
            "All existing notification behavior is preserved",
            "No new dependencies added",
        ],
        agent_summary=(
            "Extracted email, Slack, and webhook notification logic into "
            "NotificationService class. TaskPacket now calls the service "
            "instead of inline logic. Removed duplicate code."
        ),
        test_results=(
            "New tests: 8 passed, 0 failed. "
            "Existing tests: 42 passed, 2 FAILED. "
            "FAILED tests/notifications/test_email.py::test_send_on_completion — "
            "AttributeError: 'TaskPacket' has no attribute 'send_email'. "
            "FAILED tests/notifications/test_webhook.py::test_retry_on_failure — "
            "ImportError: cannot import name 'send_webhook' from 'src.models.taskpacket'."
        ),
        lint_results="ruff: 0 errors.",
        file_changes=[
            "src/notifications/service.py",
            "src/models/taskpacket.py",
            "tests/notifications/test_service.py",
        ],
        expects_defects=True,
        expected_defect_count=2,
        expected_defect_categories=["regression"],
        expected_severity_floor="S1_high",
    ),
    # ---------------------------------------------------------------
    # 5. Implementation bug — wrong return type
    # ---------------------------------------------------------------
    QAEvalCase(
        case_id="qa_impl_bug_05",
        category="planted_defect",
        description="Function returns string instead of expected dict",
        acceptance_criteria=[
            "get_weights() returns a dict mapping expert_id to weight float",
            "Performance: get_weights() runs in < 50ms for 100 experts",
            "Weight values are identical before and after optimization",
        ],
        agent_summary=(
            "Optimized get_weights() by pre-building a lookup dictionary. "
            "Changed return type to use the pre-built dict for O(1) lookups. "
            "Benchmark shows 5ms for 100 experts x 50 context keys."
        ),
        test_results=(
            "4 passed, 1 FAILED. "
            "FAILED tests/reputation/test_weights.py::test_return_type — "
            "AssertionError: expected dict, got str. "
            "get_weights() returns JSON string instead of dict."
        ),
        lint_results=(
            "ruff: 0 errors. mypy: 1 error — "
            "src/reputation/engine.py:45: Incompatible return type "
            "(got str, expected dict[str, float])."
        ),
        file_changes=["src/reputation/engine.py", "tests/reputation/test_weights.py"],
        expects_defects=True,
        expected_defect_count=1,
        expected_defect_categories=["implementation_bug"],
        expected_severity_floor="S1_high",
    ),
    # ---------------------------------------------------------------
    # 6. Performance issue — O(n^2) in hot path
    # ---------------------------------------------------------------
    QAEvalCase(
        case_id="qa_perf_06",
        category="planted_defect",
        description="Nested loop creates O(n^2) in frequently called method",
        acceptance_criteria=[
            "Search endpoint returns results in < 200ms for 10k records",
            "Results are ranked by relevance score",
            "Search supports wildcard queries",
        ],
        agent_summary=(
            "Implemented full-text search with relevance scoring. "
            "Added wildcard support via LIKE queries. "
            "Results are sorted by score descending."
        ),
        test_results="8 passed, 0 failed.",
        lint_results=(
            "ruff: 0 errors. radon cc: src/search/engine.py:search — "
            "Cyclomatic complexity: C (15). Contains nested loop: "
            "for each query term, iterates all 10k records with string matching."
        ),
        file_changes=["src/search/engine.py", "tests/search/test_search.py"],
        expects_defects=True,
        expected_defect_count=1,
        expected_defect_categories=["performance"],
        expected_severity_floor="S2_medium",
    ),
    # ---------------------------------------------------------------
    # 7. Compliance gap — missing audit logging
    # ---------------------------------------------------------------
    QAEvalCase(
        case_id="qa_compliance_07",
        category="planted_defect",
        description="Admin action handler missing audit log entries",
        acceptance_criteria=[
            "Admin can pause/resume repos via the Admin UI",
            "All admin actions are recorded in the audit log",
            "Paused repos stop processing new issues immediately",
        ],
        agent_summary=(
            "Added pause/resume toggle to Admin UI. Repos with paused=True "
            "skip intake processing. UI shows current status with toggle button."
        ),
        test_results="6 passed, 0 failed.",
        lint_results="ruff: 0 errors.",
        file_changes=[
            "src/admin/repo_management.py",
            "src/admin/templates/repo_detail.html",
            "tests/admin/test_repo_management.py",
        ],
        expects_defects=True,
        expected_defect_count=1,
        expected_defect_categories=["compliance", "operability"],
        expected_severity_floor="S2_medium",
    ),
    # ---------------------------------------------------------------
    # 8. CLEAN — all criteria genuinely met
    # ---------------------------------------------------------------
    QAEvalCase(
        case_id="qa_clean_08",
        category="clean",
        description="All acceptance criteria fully satisfied with evidence",
        acceptance_criteria=[
            "avatar_url returns a valid URL for users without custom avatars",
            "Gravatar fallback uses the user's email hash",
            "Existing custom avatars are not affected",
        ],
        agent_summary=(
            "Fixed UserProfile.avatar_url to return a Gravatar URL when no "
            "custom avatar is set. The URL is computed from an MD5 hash of "
            "the user's lowercase email address. Added a unit test for the "
            "fallback path and a test confirming custom avatars are unchanged."
        ),
        test_results=(
            "14 passed, 0 failed. New tests: test_avatar_default, "
            "test_avatar_custom_unchanged. Coverage: 92%."
        ),
        lint_results="ruff: 0 errors. bandit: 0 findings. mypy: 0 errors.",
        file_changes=[
            "src/models/user_profile.py",
            "tests/models/test_user_profile.py",
        ],
        expects_defects=False,
        expected_defect_count=0,
        expected_defect_categories=[],
        is_clean=True,
    ),
    # ---------------------------------------------------------------
    # 9. CLEAN — refactor with full test coverage
    # ---------------------------------------------------------------
    QAEvalCase(
        case_id="qa_clean_09",
        category="clean",
        description="Clean refactor with comprehensive tests and no regressions",
        acceptance_criteria=[
            "TaskPacket.notify() delegates to NotificationService",
            "Email, Slack, and webhook channels all work correctly",
            "No new pip dependencies introduced",
            "All existing tests pass without modification",
        ],
        agent_summary=(
            "Created NotificationService in src/notifications/service.py. "
            "Moved email dispatch, Slack webhook, and HTTP webhook logic "
            "from TaskPacket into the service. TaskPacket.notify() now calls "
            "NotificationService.send(). Added NotificationChannel enum. "
            "All 3 channel types have dedicated tests."
        ),
        test_results=(
            "New tests: 12 passed, 0 failed. "
            "Existing tests: 45 passed, 0 failed. "
            "Total: 57 passed, 0 failed. Coverage: 91%."
        ),
        lint_results="ruff: 0 errors. mypy: 0 errors. bandit: 0 findings.",
        file_changes=[
            "src/notifications/service.py",
            "src/notifications/__init__.py",
            "src/models/taskpacket.py",
            "tests/notifications/test_service.py",
        ],
        expects_defects=False,
        expected_defect_count=0,
        expected_defect_categories=[],
        is_clean=True,
    ),
    # ---------------------------------------------------------------
    # 10. CLEAN — dependency update with verified compatibility
    # ---------------------------------------------------------------
    QAEvalCase(
        case_id="qa_clean_10",
        category="clean",
        description="Dependency upgrade with verified compatibility",
        acceptance_criteria=[
            "httpx upgraded from 0.25.x to 0.27.x",
            "All HTTP adapter tests pass",
            "Breaking change from 0.26 (TimeoutException → TimeoutError) handled",
            "Connection pool leak fix confirmed by test",
        ],
        agent_summary=(
            "Updated httpx to 0.27.2 and respx to 0.22.0 in pyproject.toml. "
            "Renamed TimeoutException to TimeoutError in 3 files. "
            "Added connection pool leak regression test. "
            "Verified all 28 adapter tests pass."
        ),
        test_results="28 passed, 0 failed. New test: test_connection_pool_no_leak.",
        lint_results="ruff: 0 errors. pip-audit: 0 vulnerabilities.",
        file_changes=[
            "pyproject.toml",
            "src/adapters/github.py",
            "src/adapters/llm.py",
            "src/adapters/http_client.py",
            "tests/adapters/test_github.py",
            "tests/adapters/test_pool_leak.py",
        ],
        expects_defects=False,
        expected_defect_count=0,
        expected_defect_categories=[],
        is_clean=True,
    ),
]


def load_qa_dataset() -> list[QAEvalCase]:
    """Return the labeled QA evaluation dataset."""
    return list(QA_DATASET)
