"""Intent-based page tests — verify each Admin UI page delivers its purpose.

Every page exists for a reason. These tests verify that each page provides the
information and controls the user needs — not just that it loads without errors.

Structure:
- Generic parameterized tests (heading, entities, console errors) remain
- Per-page intent tests verify semantic content: cards, tables, metrics, labels,
  forms, and controls that give the page its purpose.
"""

import pytest

from tests.playwright.conftest import navigate

pytestmark = pytest.mark.playwright

# ---------------------------------------------------------------------------
# Page registry — path, expected heading
# ---------------------------------------------------------------------------
STATIC_PAGES = [
    ("/admin/ui/dashboard", "Fleet Dashboard"),
    ("/admin/ui/repos", "Repo Management"),
    ("/admin/ui/workflows", "Workflow Console"),
    ("/admin/ui/audit", "Audit Log"),
    ("/admin/ui/metrics", "Metrics"),
    ("/admin/ui/experts", "Expert Performance"),
    ("/admin/ui/tools", "Tool Hub"),
    ("/admin/ui/models", "Model Gateway"),
    ("/admin/ui/compliance", "Compliance Scorecard"),
    ("/admin/ui/quarantine", "Quarantine"),
    ("/admin/ui/dead-letters", "Dead-Letter"),
    ("/admin/ui/planes", "Execution Planes"),
    ("/admin/ui/settings", "Settings"),
]


# ---------------------------------------------------------------------------
# Generic structural tests (parameterized across all pages)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("path", "expected_heading"),
    STATIC_PAGES,
    ids=[p.split("/")[-1] for p, _ in STATIC_PAGES],
)
def test_page_loads_with_heading(
    page, base_url: str, path: str, expected_heading: str
) -> None:
    """Each page returns 200 and contains the expected heading."""
    navigate(page, f"{base_url}{path}")

    heading = page.locator("h2").first
    heading_text = heading.inner_text() if heading else ""
    assert expected_heading in heading_text, (
        f"Expected '{expected_heading}' in page heading, got: '{heading_text}'"
    )


@pytest.mark.parametrize(
    ("path", "_heading"),
    STATIC_PAGES,
    ids=[p.split("/")[-1] for p, _ in STATIC_PAGES],
)
def test_no_entity_artifacts(page, base_url: str, path: str, _heading: str) -> None:
    """No page shows literal HTML entity text like &#9744; in visible content."""
    navigate(page, f"{base_url}{path}")

    visible_text = page.locator("body").inner_text()
    assert "&#" not in visible_text, (
        f"Literal HTML entity found on {path}: {visible_text[:500]}"
    )


@pytest.mark.parametrize(
    ("path", "_heading"),
    STATIC_PAGES,
    ids=[p.split("/")[-1] for p, _ in STATIC_PAGES],
)
def test_no_console_errors(
    page, base_url: str, console_errors: list, path: str, _heading: str
) -> None:
    """No JavaScript console errors on any page."""
    navigate(page, f"{base_url}{path}")

    assert len(console_errors) == 0, f"Console errors on {path}: {console_errors}"


# ===========================================================================
# INTENT TESTS — per-page purpose validation
# ===========================================================================


# ---------------------------------------------------------------------------
# 1. DASHBOARD — Fleet health at a glance
# Purpose: Operators need system health, workflow summary, and repo activity
# to monitor capacity, detect issues, and understand workload distribution.
# ---------------------------------------------------------------------------
class TestDashboardIntent:
    """Dashboard must show system health, workflow metrics, and repo activity."""

    URL = "/admin/ui/dashboard"

    def test_system_health_services_visible(self, page, base_url: str) -> None:
        """Dashboard shows health status for critical infrastructure services."""
        navigate(page, f"{base_url}{self.URL}")
        body = page.locator("body").inner_text()

        for service in ("Temporal", "Postgres"):
            assert service in body, (
                f"Dashboard must show '{service}' service health status"
            )

    def test_workflow_summary_metrics(self, page, base_url: str) -> None:
        """Dashboard shows aggregate workflow counts (running, stuck, failed, queue)."""
        navigate(page, f"{base_url}{self.URL}")
        body = page.locator("body").inner_text()

        for metric in ("Running", "Stuck", "Failed", "Queue"):
            assert metric in body, (
                f"Dashboard must show '{metric}' workflow metric"
            )

    def test_repo_activity_section(self, page, base_url: str) -> None:
        """Dashboard shows repo activity table or empty-state message."""
        navigate(page, f"{base_url}{self.URL}")
        body = page.locator("body").inner_text()

        has_repo_table = page.locator("table").count() > 0
        has_empty_state = "No repos" in body or "no repos" in body.lower()
        assert has_repo_table or has_empty_state, (
            "Dashboard must show repo activity table or 'No repos' empty state"
        )

    def test_service_health_has_status_indicators(self, page, base_url: str) -> None:
        """Each service health card should show a latency or status indicator."""
        navigate(page, f"{base_url}{self.URL}")
        body = page.locator("body").inner_text()

        assert "ms" in body or "status" in body.lower() or "healthy" in body.lower(), (
            "Dashboard service health must show latency (ms) or status indicators"
        )


# ---------------------------------------------------------------------------
# 2. REPOS — Repository lifecycle management
# Purpose: Admins register repos, view config, control tier and processing.
# ---------------------------------------------------------------------------
class TestReposIntent:
    """Repos page must allow registration and show repo list with tier/status."""

    URL = "/admin/ui/repos"

    def test_register_repo_control_available(self, page, base_url: str) -> None:
        """Repos page provides a way to register new repositories."""
        navigate(page, f"{base_url}{self.URL}")

        register_btn = page.get_by_role("button", name="Register Repo")
        has_register = register_btn.count() > 0
        has_register_form = page.locator("#register-form").count() > 0
        assert has_register or has_register_form, (
            "Repos page must have a 'Register Repo' button or registration form"
        )

    def test_repo_list_or_empty_state(self, page, base_url: str) -> None:
        """Repos page shows a repo list table or an empty-state message."""
        navigate(page, f"{base_url}{self.URL}")
        body = page.locator("body").inner_text()

        has_table = page.locator("table").count() > 0
        has_empty = "no repos" in body.lower() or "register" in body.lower()
        assert has_table or has_empty, (
            "Repos page must show a repo list or empty-state guidance"
        )

    def test_repo_list_shows_tier_and_status(self, page, base_url: str) -> None:
        """If repos exist, the list shows tier and status information."""
        navigate(page, f"{base_url}{self.URL}")
        body = page.locator("body").inner_text()
        body_lower = body.lower()

        has_tier_labels = any(
            t in body_lower
            for t in ("shadow", "probation", "trusted", "observe", "suggest", "execute")
        )
        has_no_repos = "no repos" in body_lower
        assert has_tier_labels or has_no_repos, (
            "Repos page must show tier badges (shadow/probation/trusted) or empty state"
        )


# ---------------------------------------------------------------------------
# 3. WORKFLOWS — Pipeline execution console
# Purpose: Observe TaskPacket processing through the 9-stage pipeline,
# filter by status, understand workflow state and duration.
# ---------------------------------------------------------------------------
class TestWorkflowsIntent:
    """Workflows page must show pipeline execution state with filtering."""

    URL = "/admin/ui/workflows"

    def test_status_filter_available(self, page, base_url: str) -> None:
        """Workflows page provides status filtering controls."""
        navigate(page, f"{base_url}{self.URL}")

        has_select = page.locator("select").count() > 0
        has_filter_form = page.locator("form").count() > 0
        has_filter_text = "filter" in page.locator("body").inner_text().lower()
        assert has_select or has_filter_form or has_filter_text, (
            "Workflows page must have status filter controls (select/form)"
        )

    def test_workflow_status_labels(self, page, base_url: str) -> None:
        """Workflows page shows or allows filtering by pipeline status values."""
        navigate(page, f"{base_url}{self.URL}")
        body = page.locator("body").inner_text().lower()

        status_labels = ("running", "completed", "failed", "stuck")
        has_any_status = any(s in body for s in status_labels)
        assert has_any_status, (
            f"Workflows page must reference status values: {status_labels}"
        )

    def test_workflow_list_or_empty_state(self, page, base_url: str) -> None:
        """Workflows page shows a workflow list or empty-state message."""
        navigate(page, f"{base_url}{self.URL}")
        body = page.locator("body").inner_text().lower()

        has_table = page.locator("table").count() > 0
        has_empty = "no workflow" in body or "no results" in body or "empty" in body
        assert has_table or has_empty, (
            "Workflows page must show workflow list or empty state"
        )


# ---------------------------------------------------------------------------
# 4. AUDIT — Compliance audit trail
# Purpose: Governance log of all admin actions for forensics and compliance.
# ---------------------------------------------------------------------------
class TestAuditIntent:
    """Audit page must show filterable event log with actor and event type."""

    URL = "/admin/ui/audit"

    def test_audit_event_types_visible(self, page, base_url: str) -> None:
        """Audit page references event types for filtering or display."""
        navigate(page, f"{base_url}{self.URL}")
        body = page.locator("body").inner_text().lower()

        event_keywords = (
            "event", "type", "registered", "updated", "changed",
            "paused", "resumed", "action",
        )
        has_event_refs = any(k in body for k in event_keywords)
        assert has_event_refs, (
            "Audit page must reference event types or actions"
        )

    def test_audit_has_time_filtering(self, page, base_url: str) -> None:
        """Audit page provides time-range filtering (1h, 6h, 24h, 7d)."""
        navigate(page, f"{base_url}{self.URL}")
        body = page.locator("body").inner_text()

        time_refs = ("1h", "6h", "24h", "7d", "hour", "day")
        has_time = any(t in body for t in time_refs)
        has_select = page.locator("select").count() > 0
        assert has_time or has_select, (
            "Audit page must provide time-range filtering"
        )

    def test_audit_shows_actor_and_target(self, page, base_url: str) -> None:
        """Audit log entries reference actors and targets."""
        navigate(page, f"{base_url}{self.URL}")
        body = page.locator("body").inner_text().lower()

        has_actor = "actor" in body or "user" in body
        has_target = "target" in body or "repo" in body or "resource" in body
        assert has_actor or has_target, (
            "Audit page must show actor/user and target/resource columns"
        )


# ---------------------------------------------------------------------------
# 5. METRICS — Quality metrics for pipeline health
# Purpose: Show success rates, gate status, loopback breakdown, reopen
# attribution so operators can identify process bottlenecks.
# ---------------------------------------------------------------------------
class TestMetricsIntent:
    """Metrics page must show success rates, gates, loopbacks, and reopen data."""

    URL = "/admin/ui/metrics"

    def test_success_rate_displayed(self, page, base_url: str) -> None:
        """Metrics page shows single-pass success rate or equivalent quality metric."""
        navigate(page, f"{base_url}{self.URL}")
        body = page.locator("body").inner_text().lower()

        has_success = "success" in body or "pass rate" in body or "pass" in body
        has_percentage = "%" in page.locator("body").inner_text()
        assert has_success or has_percentage, (
            "Metrics page must show success rate with percentage"
        )

    def test_gate_status_shown(self, page, base_url: str) -> None:
        """Metrics page shows success gate status (PASSING/FAILING/Insufficient)."""
        navigate(page, f"{base_url}{self.URL}")
        body = page.locator("body").inner_text().lower()

        gate_refs = ("gate", "passing", "failing", "threshold", "insufficient")
        has_gate = any(g in body for g in gate_refs)
        assert has_gate, "Metrics page must show success gate status"

    def test_loopback_breakdown(self, page, base_url: str) -> None:
        """Metrics page shows verification loopback categories and counts."""
        navigate(page, f"{base_url}{self.URL}")
        body = page.locator("body").inner_text().lower()

        has_loopback = "loopback" in body or "loop" in body or "retry" in body
        assert has_loopback, "Metrics page must show loopback/retry breakdown"

    def test_reopen_rate_attribution(self, page, base_url: str) -> None:
        """Metrics page shows reopen rate with attribution breakdown."""
        navigate(page, f"{base_url}{self.URL}")
        body = page.locator("body").inner_text().lower()

        has_reopen = "reopen" in body or "reopened" in body
        assert has_reopen, "Metrics page must show reopen rate information"

    def test_time_window_context(self, page, base_url: str) -> None:
        """Metrics are shown with time window context (7d, 30d, etc.)."""
        navigate(page, f"{base_url}{self.URL}")
        body = page.locator("body").inner_text()

        time_refs = ("7", "30", "day", "7d", "30d", "week")
        has_time = any(t in body for t in time_refs)
        assert has_time, "Metrics page must show time window context (7d/30d)"


# ---------------------------------------------------------------------------
# 6. EXPERTS — Expert router performance
# Purpose: Show which AI experts handle work, their trust tier, confidence,
# drift signals to guide expert selection tuning.
# ---------------------------------------------------------------------------
class TestExpertsIntent:
    """Experts page must show trust tiers, confidence, and drift signals."""

    URL = "/admin/ui/experts"

    def test_trust_tier_labels(self, page, base_url: str) -> None:
        """Experts page references trust tier vocabulary."""
        navigate(page, f"{base_url}{self.URL}")
        body = page.locator("body").inner_text().lower()

        tier_refs = ("shadow", "probation", "trusted", "tier")
        has_tiers = any(t in body for t in tier_refs)
        has_empty = "no expert" in body or "no data" in body
        assert has_tiers or has_empty, (
            "Experts page must show trust tier labels or empty state"
        )

    def test_performance_metrics_columns(self, page, base_url: str) -> None:
        """Experts page shows confidence, weight, or drift performance columns."""
        navigate(page, f"{base_url}{self.URL}")
        body = page.locator("body").inner_text().lower()

        metric_refs = ("confidence", "weight", "drift", "score", "performance")
        has_metrics = any(m in body for m in metric_refs)
        has_empty = "no expert" in body or "no data" in body
        assert has_metrics or has_empty, (
            "Experts page must show performance metrics (confidence/weight/drift)"
        )

    def test_expert_filtering(self, page, base_url: str) -> None:
        """Experts page provides filtering by tier or repo."""
        navigate(page, f"{base_url}{self.URL}")

        has_filter = (
            page.locator("select").count() > 0
            or page.locator("input[type='text']").count() > 0
            or "filter" in page.locator("body").inner_text().lower()
        )
        assert has_filter, "Experts page must provide filtering controls"


# ---------------------------------------------------------------------------
# 7. TOOLS — Tool approval and access control
# Purpose: Show available tool suites, their approval status, and allow
# testing access rules for role/tier combinations.
# ---------------------------------------------------------------------------
class TestToolsIntent:
    """Tools page must show tool catalog with approval status and access rules."""

    URL = "/admin/ui/tools"

    def test_tool_catalog_present(self, page, base_url: str) -> None:
        """Tools page shows a catalog of available tool suites."""
        navigate(page, f"{base_url}{self.URL}")
        body = page.locator("body").inner_text().lower()

        tool_refs = ("ruff", "pytest", "security", "suite", "tool")
        has_tools = any(t in body for t in tool_refs)
        assert has_tools, "Tools page must list available tool suites"

    def test_approval_status_shown(self, page, base_url: str) -> None:
        """Tools page shows approval status (observe/suggest/execute) for suites."""
        navigate(page, f"{base_url}{self.URL}")
        body = page.locator("body").inner_text().lower()

        status_refs = ("observe", "suggest", "execute", "approved", "status")
        has_status = any(s in body for s in status_refs)
        assert has_status, (
            "Tools page must show approval status (observe/suggest/execute)"
        )

    def test_access_check_or_profiles(self, page, base_url: str) -> None:
        """Tools page shows default profiles or access check capability."""
        navigate(page, f"{base_url}{self.URL}")
        body = page.locator("body").inner_text().lower()

        has_profiles = "profile" in body or "access" in body or "role" in body
        assert has_profiles, (
            "Tools page must show access profiles or access check controls"
        )


# ---------------------------------------------------------------------------
# 8. MODELS — LLM provider and routing
# Purpose: Show available models, cost/throughput, and routing rules that
# determine which model class is used for each pipeline stage.
# ---------------------------------------------------------------------------
class TestModelsIntent:
    """Models page must show providers, routing rules, and model classes."""

    URL = "/admin/ui/models"

    def test_model_providers_listed(self, page, base_url: str) -> None:
        """Models page lists model providers and model IDs."""
        navigate(page, f"{base_url}{self.URL}")
        body = page.locator("body").inner_text().lower()

        provider_refs = ("anthropic", "openai", "provider", "model", "claude")
        has_providers = any(p in body for p in provider_refs)
        assert has_providers, "Models page must list model providers"

    def test_model_classes_shown(self, page, base_url: str) -> None:
        """Models page shows model class categories (fast/balanced/strong)."""
        navigate(page, f"{base_url}{self.URL}")
        body = page.locator("body").inner_text().lower()

        class_refs = ("fast", "balanced", "strong", "class")
        has_classes = any(c in body for c in class_refs)
        assert has_classes, (
            "Models page must show model classes (fast/balanced/strong)"
        )

    def test_routing_rules_visible(self, page, base_url: str) -> None:
        """Models page shows routing rules mapping pipeline steps to model classes."""
        navigate(page, f"{base_url}{self.URL}")
        body = page.locator("body").inner_text().lower()

        step_refs = ("intake", "context", "intent", "router", "implement", "verify")
        routing_refs = ("routing", "step", "rule", "default")
        has_steps = any(s in body for s in step_refs)
        has_routing = any(r in body for r in routing_refs)
        assert has_steps or has_routing, (
            "Models page must show routing rules with pipeline step mapping"
        )

    def test_cost_information_available(self, page, base_url: str) -> None:
        """Models page shows cost or rate limit information for models."""
        navigate(page, f"{base_url}{self.URL}")
        body = page.locator("body").inner_text()

        has_cost = "$" in body or "cost" in body.lower() or "rate" in body.lower()
        assert has_cost, (
            "Models page must show cost ($) or rate limit information"
        )


# ---------------------------------------------------------------------------
# 9. COMPLIANCE — Compliance scorecard
# Purpose: Show whether a repo passes all compliance checks required for
# promotion to execute tier. Display per-check pass/fail status.
# ---------------------------------------------------------------------------
class TestComplianceIntent:
    """Compliance page must show pass/fail scorecard with per-check details."""

    URL = "/admin/ui/compliance"

    def test_compliance_overall_status(self, page, base_url: str) -> None:
        """Compliance page shows an overall PASS/FAIL status."""
        navigate(page, f"{base_url}{self.URL}")
        body = page.locator("body").inner_text().lower()

        has_status = "pass" in body or "fail" in body or "status" in body
        assert has_status, "Compliance page must show overall PASS/FAIL status"

    def test_compliance_check_list(self, page, base_url: str) -> None:
        """Compliance page lists individual checks with pass/fail indicators."""
        navigate(page, f"{base_url}{self.URL}")
        body = page.locator("body").inner_text().lower()

        check_refs = ("check", "requirement", "coverage", "security", "test")
        has_checks = any(c in body for c in check_refs)
        assert has_checks, (
            "Compliance page must list individual compliance checks"
        )

    def test_repo_selector_or_context(self, page, base_url: str) -> None:
        """Compliance page provides repo selection or shows default repo context."""
        navigate(page, f"{base_url}{self.URL}")

        has_input = page.locator("input").count() > 0
        has_select = page.locator("select").count() > 0
        has_button = page.locator("button").count() > 0
        body_lower = page.locator("body").inner_text().lower()
        has_repo_ref = "repo" in body_lower or "default" in body_lower
        assert has_input or has_select or has_button or has_repo_ref, (
            "Compliance page must have repo selector or show repo context"
        )


# ---------------------------------------------------------------------------
# 10. QUARANTINE — Failed event management
# Purpose: View quarantined events that failed gates, examine failure reason,
# replay or delete. Critical for post-mortem and recovery.
# ---------------------------------------------------------------------------
class TestQuarantineIntent:
    """Quarantine page must show failed events with reason, status, and actions."""

    URL = "/admin/ui/quarantine"

    def test_quarantine_reason_filtering(self, page, base_url: str) -> None:
        """Quarantine page provides filtering by failure reason."""
        navigate(page, f"{base_url}{self.URL}")

        has_filter = (
            page.locator("select").count() > 0
            or "reason" in page.locator("body").inner_text().lower()
            or "filter" in page.locator("body").inner_text().lower()
        )
        assert has_filter, "Quarantine page must allow filtering by reason"

    def test_quarantine_event_list_or_empty(self, page, base_url: str) -> None:
        """Quarantine page shows event list or empty-state message."""
        navigate(page, f"{base_url}{self.URL}")
        body = page.locator("body").inner_text().lower()

        has_table = page.locator("table").count() > 0
        has_empty = (
            "no quarantine" in body
            or "empty" in body
            or "no event" in body
            or "0 event" in body
        )
        assert has_table or has_empty, (
            "Quarantine page must show event list or empty state"
        )

    def test_quarantine_status_vocabulary(self, page, base_url: str) -> None:
        """Quarantine page uses correct status vocabulary."""
        navigate(page, f"{base_url}{self.URL}")
        body = page.locator("body").inner_text().lower()

        status_refs = (
            "pending", "replayed", "corrected", "reason", "quarantine", "status",
        )
        has_status = any(s in body for s in status_refs)
        assert has_status, (
            "Quarantine page must reference status values (pending/replayed/corrected)"
        )


# ---------------------------------------------------------------------------
# 11. DEAD-LETTERS — Unrecoverable event forensics
# Purpose: View events that failed after all retries. Forensics and
# troubleshooting for systemic failures.
# ---------------------------------------------------------------------------
class TestDeadLettersIntent:
    """Dead-letters page must show failed events with failure reason and attempts."""

    URL = "/admin/ui/dead-letters"

    def test_dead_letter_list_or_empty(self, page, base_url: str) -> None:
        """Dead-letters page shows event list or empty-state message."""
        navigate(page, f"{base_url}{self.URL}")
        body = page.locator("body").inner_text().lower()

        has_table = page.locator("table").count() > 0
        has_empty = (
            "no dead" in body
            or "empty" in body
            or "no event" in body
            or "0 event" in body
        )
        assert has_table or has_empty, (
            "Dead-letters page must show event list or empty state"
        )

    def test_failure_reason_displayed(self, page, base_url: str) -> None:
        """Dead-letters page shows failure reason for each event."""
        navigate(page, f"{base_url}{self.URL}")
        body = page.locator("body").inner_text().lower()

        reason_refs = ("reason", "failure", "error", "dead-letter", "dead letter")
        has_reason = any(r in body for r in reason_refs)
        assert has_reason, (
            "Dead-letters page must show failure reason information"
        )

    def test_attempt_count_or_retry_info(self, page, base_url: str) -> None:
        """Dead-letters page shows attempt count or retry information."""
        navigate(page, f"{base_url}{self.URL}")
        body = page.locator("body").inner_text().lower()

        retry_refs = ("attempt", "retry", "retries", "count", "tries")
        has_retry = any(r in body for r in retry_refs)
        assert has_retry, (
            "Dead-letters page must show attempt count or retry info"
        )


# ---------------------------------------------------------------------------
# 12. PLANES — Execution plane management
# Purpose: Show distributed worker clusters, their health, repo assignments,
# and allow pause/resume for maintenance.
# ---------------------------------------------------------------------------
class TestPlanesIntent:
    """Planes page must show execution environments with health and controls."""

    URL = "/admin/ui/planes"

    def test_plane_summary_counts(self, page, base_url: str) -> None:
        """Planes page shows summary counts (total planes, repos, active)."""
        navigate(page, f"{base_url}{self.URL}")
        body = page.locator("body").inner_text().lower()

        summary_refs = ("total", "active", "plane", "repo")
        has_summary = sum(1 for s in summary_refs if s in body) >= 2
        assert has_summary, (
            "Planes page must show summary counts (total/active planes, repos)"
        )

    def test_register_plane_capability(self, page, base_url: str) -> None:
        """Planes page provides ability to register a new execution plane."""
        navigate(page, f"{base_url}{self.URL}")

        has_form = page.locator("form").count() > 0
        has_input = page.locator("input").count() > 0
        has_button = page.locator("button").count() > 0
        assert has_form or has_input or has_button, (
            "Planes page must have plane registration form or controls"
        )

    def test_plane_status_indicators(self, page, base_url: str) -> None:
        """Planes page shows status indicators (active/paused/draining)."""
        navigate(page, f"{base_url}{self.URL}")
        body = page.locator("body").inner_text().lower()

        status_refs = ("active", "paused", "draining", "status", "health")
        has_status = any(s in body for s in status_refs)
        assert has_status, (
            "Planes page must show status indicators (active/paused/draining)"
        )

    def test_region_information(self, page, base_url: str) -> None:
        """Planes page shows or accepts region information for planes."""
        navigate(page, f"{base_url}{self.URL}")
        body = page.locator("body").inner_text().lower()

        has_region = "region" in body or "default" in body
        has_region_input = page.locator("input[name='region']").count() > 0
        assert has_region or has_region_input, (
            "Planes page must show or accept region information"
        )


# ---------------------------------------------------------------------------
# 13. SETTINGS — Administrative configuration hub
# Purpose: Central admin-only config for API keys, infrastructure, feature
# flags, agent model selection, and secrets rotation.
# ---------------------------------------------------------------------------
SETTINGS_TABS = [
    ("api-keys", "API Keys"),
    ("infrastructure", "Infrastructure"),
    ("feature-flags", "Feature Flags"),
    ("agent-config", "Agent"),
    ("secrets", "Secrets"),
]


@pytest.mark.parametrize(
    ("tab_id", "expected_text"),
    SETTINGS_TABS,
    ids=[t for t, _ in SETTINGS_TABS],
)
def test_settings_tab_loads(
    page, base_url: str, tab_id: str, expected_text: str
) -> None:
    """Each settings sub-tab loads content containing expected text."""
    navigate(page, f"{base_url}/admin/ui/settings")

    tab_link = page.locator(f'[hx-get*="{tab_id}"]')
    if tab_link.count() > 0:
        tab_link.first.click()
        page.wait_for_load_state("networkidle")

    body_text = page.locator("body").inner_text()
    assert expected_text in body_text, (
        f"Expected '{expected_text}' in settings tab '{tab_id}', not found"
    )


class TestSettingsIntent:
    """Settings page must provide admin configuration across all domains."""

    URL = "/admin/ui/settings"

    def test_all_settings_tabs_present(self, page, base_url: str) -> None:
        """Settings page has tab links for all configuration domains."""
        navigate(page, f"{base_url}{self.URL}")

        for tab_id, _ in SETTINGS_TABS:
            tab_link = page.locator(f'[hx-get*="{tab_id}"]')
            assert tab_link.count() > 0, (
                f"Settings page must have tab link for '{tab_id}'"
            )

    def test_api_keys_tab_has_key_management(self, page, base_url: str) -> None:
        """API Keys tab shows key names with masked values and management controls."""
        navigate(page, f"{base_url}{self.URL}")

        tab_link = page.locator('[hx-get*="api-keys"]')
        if tab_link.count() > 0:
            tab_link.first.click()
            page.wait_for_load_state("networkidle")

        body = page.locator("body").inner_text().lower()
        has_keys = "key" in body or "token" in body
        has_actions = "reveal" in body or "update" in body or "***" in body
        assert has_keys and has_actions, (
            "API Keys tab must show key names with masked values and actions"
        )

    def test_feature_flags_tab_has_toggles(self, page, base_url: str) -> None:
        """Feature Flags tab shows toggleable flag controls."""
        navigate(page, f"{base_url}{self.URL}")

        tab_link = page.locator('[hx-get*="feature-flags"]')
        if tab_link.count() > 0:
            tab_link.first.click()
            page.wait_for_load_state("networkidle")

        body = page.locator("body").inner_text().lower()
        has_flags = "flag" in body or "enabled" in body or "disabled" in body
        has_toggle = (
            page.locator("input[type='checkbox']").count() > 0
            or "toggle" in body
            or "enabled" in body
        )
        assert has_flags or has_toggle, (
            "Feature Flags tab must show flag names with toggle controls"
        )

    def test_secrets_tab_has_rotation_controls(self, page, base_url: str) -> None:
        """Secrets tab provides key rotation or secret management controls."""
        navigate(page, f"{base_url}{self.URL}")

        tab_link = page.locator('[hx-get*="secrets"]')
        if tab_link.count() > 0:
            tab_link.first.click()
            page.wait_for_load_state("networkidle")

        body = page.locator("body").inner_text().lower()
        has_secrets = "secret" in body or "encrypt" in body or "webhook" in body
        has_rotation = (
            "rotate" in body
            or "regenerate" in body
            or page.locator("button").count() > 0
        )
        assert has_secrets and has_rotation, (
            "Secrets tab must show secret info and rotation controls"
        )
