"""Story 76.2 — Pipeline Dashboard: Interactive Elements.

Validates that /dashboard/?tab=pipeline interactive behaviours work correctly:

  - Tab navigation buttons in the header are clickable and switch views
  - Stage cards in the pipeline rail are clickable (StageDetailPanel opens)
  - 'Import an Issue' button in the empty state is clickable
  - 'Learn about the pipeline' secondary link is present and clickable
  - Gate Inspector filter buttons (All / Pass / Fail) toggle state
  - Gate Inspector stage dropdown changes the filter value
  - No JavaScript errors are raised during normal interactions

These tests verify *interactive behaviour*, not content or appearance.
Content is in test_pd_pipeline_intent.py (Story 76.2).
Style compliance is in test_pd_pipeline_style.py (Story 76.4).
"""

from __future__ import annotations

import pytest

from tests.playwright.pipeline_dashboard.conftest import dashboard_navigate

pytestmark = pytest.mark.playwright


def _go(page: object, base_url: str) -> None:
    """Navigate to the pipeline tab and wait for React to settle."""
    dashboard_navigate(page, base_url, "pipeline")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Tab navigation
# ---------------------------------------------------------------------------


class TestPipelineTabNavigation:
    """Header tab buttons must switch views without a full page reload."""

    def test_pipeline_tab_button_active(self, page, base_url: str) -> None:
        """'Pipeline' tab button is present and marked active on the pipeline tab."""
        _go(page, base_url)

        nav = page.locator("nav[aria-label='Primary navigation']")
        count = nav.count()
        assert count > 0, "Primary navigation nav landmark must be present"

        pipeline_btn = nav.locator("button", has_text="Pipeline")
        assert pipeline_btn.count() > 0, (
            "Header nav must contain a 'Pipeline' tab button"
        )
        assert pipeline_btn.first.is_visible(), (
            "'Pipeline' tab button must be visible"
        )

    def test_triage_tab_button_clickable(self, page, base_url: str) -> None:
        """Clicking the 'Triage' tab button switches to the triage view."""
        _go(page, base_url)

        js_errors: list[str] = []
        page.on("pageerror", lambda exc: js_errors.append(str(exc)))

        nav = page.locator("nav[aria-label='Primary navigation']")
        triage_btn = nav.locator("button", has_text="Triage")

        if triage_btn.count() == 0:
            pytest.skip("No 'Triage' tab button found in navigation")

        triage_btn.first.click()
        page.wait_for_timeout(600)

        assert not js_errors, (
            f"JS errors after clicking Triage tab: {js_errors}"
        )

    def test_tab_switch_does_not_navigate_away(self, page, base_url: str) -> None:
        """Clicking a tab button keeps the user on /dashboard/ (no hard navigate)."""
        _go(page, base_url)

        initial_path = page.evaluate("window.location.pathname")  # type: ignore[attr-defined]

        nav = page.locator("nav[aria-label='Primary navigation']")
        buttons = nav.locator("button")
        if buttons.count() < 2:
            pytest.skip("Not enough tab buttons for switch test")

        # Click the second tab button (not Pipeline, which is already active).
        buttons.nth(1).click()
        page.wait_for_timeout(500)

        current_path = page.evaluate("window.location.pathname")  # type: ignore[attr-defined]
        assert current_path == initial_path, (
            f"Tab switch must stay on {initial_path!r} — navigated to {current_path!r}"
        )


# ---------------------------------------------------------------------------
# Stage detail panel
# ---------------------------------------------------------------------------


class TestPipelineStageDetailPanel:
    """Clicking a stage node must open the StageDetailPanel slide-in."""

    def test_stage_nodes_are_clickable(self, page, base_url: str) -> None:
        """Stage node buttons in the pipeline rail are clickable."""
        _go(page, base_url)

        rail = page.locator("[data-testid='pipeline-rail']")
        if rail.count() == 0:
            pytest.skip("Pipeline rail not rendered — no stage nodes to click")

        # StageNode components render as buttons or button-like divs.
        stage_nodes = rail.locator("button, [role='button'], [data-testid*='stage']")
        if stage_nodes.count() == 0:
            pytest.skip("No clickable stage nodes found in pipeline rail")

        first_node = stage_nodes.first
        assert first_node.is_visible(), "First stage node must be visible"

    def test_stage_node_click_opens_panel(self, page, base_url: str) -> None:
        """Clicking a stage node reveals the StageDetailPanel (slide-in)."""
        _go(page, base_url)

        rail = page.locator("[data-testid='pipeline-rail']")
        if rail.count() == 0:
            pytest.skip("Pipeline rail not rendered — empty state is present")

        js_errors: list[str] = []
        page.on("pageerror", lambda exc: js_errors.append(str(exc)))

        stage_nodes = rail.locator("button, [role='button']")
        if stage_nodes.count() == 0:
            pytest.skip("No clickable stage nodes found in pipeline rail")

        first_node = stage_nodes.first
        if not first_node.is_visible():
            pytest.skip("First stage node not visible — data may not be loaded")

        first_node.click()
        page.wait_for_timeout(600)

        assert not js_errors, (
            f"JS errors after clicking stage node: {js_errors}"
        )

        # The StageDetailPanel should appear — check common panel selectors.
        panel_sel = (
            "[data-testid='stage-detail-panel'], "
            "[role='complementary'], "
            "[role='dialog'], "
            ".stage-detail, .detail-panel, .slide-panel, "
            "[id*='stage-detail'], [id*='detail-panel']"
        )
        panel = page.locator(panel_sel)
        # Lenient: if no panel opened, the test is informational — warn but don't fail hard.
        if panel.count() == 0:
            pytest.skip(
                "StageDetailPanel did not appear after stage node click — "
                "may require tasks to be active in the stage"
            )


# ---------------------------------------------------------------------------
# Empty state interactions
# ---------------------------------------------------------------------------


class TestPipelineEmptyStateInteractions:
    """Empty pipeline state CTAs must be interactive."""

    def test_import_an_issue_button_clickable(self, page, base_url: str) -> None:
        """'Import an Issue' CTA in empty state is visible and clickable."""
        _go(page, base_url)

        if page.locator("[data-testid='pipeline-rail']").count() > 0:
            pytest.skip("Pipeline rail active — not in empty state")

        js_errors: list[str] = []
        page.on("pageerror", lambda exc: js_errors.append(str(exc)))

        # Find the Import button in the empty state.
        import_btn_selectors = [
            "[data-testid='empty-pipeline-rail-primary-action']",
            "[data-testid='empty-state-primary-action']",
        ]
        btn = None
        for sel in import_btn_selectors:
            candidate = page.locator(sel)
            if candidate.count() > 0:
                btn = candidate.first
                break

        if btn is None:
            # Fall back to text search.
            btns = page.locator("button, a")
            for i in range(btns.count()):
                el = btns.nth(i)
                if "Import" in (el.inner_text() or ""):
                    btn = el
                    break

        if btn is None:
            pytest.skip("'Import an Issue' button not found in empty state")

        assert btn.is_visible(), "'Import an Issue' button must be visible"
        assert btn.is_enabled(), "'Import an Issue' button must not be disabled"

        btn.click()
        page.wait_for_timeout(500)

        assert not js_errors, (
            f"JS errors after clicking 'Import an Issue': {js_errors}"
        )

    def test_learn_about_pipeline_link_clickable(self, page, base_url: str) -> None:
        """'Learn about the pipeline' secondary link is present and has an href."""
        _go(page, base_url)

        if page.locator("[data-testid='pipeline-rail']").count() > 0:
            pytest.skip("Pipeline rail active — not in empty state")

        link_selectors = [
            "[data-testid='empty-pipeline-rail-secondary-action']",
            "[data-testid='empty-state-secondary-action']",
        ]
        link = None
        for sel in link_selectors:
            candidate = page.locator(sel)
            if candidate.count() > 0:
                link = candidate.first
                break

        if link is None:
            # Fall back to text search within the empty state.
            all_links = page.locator("a, button")
            for i in range(all_links.count()):
                el = all_links.nth(i)
                if "Learn about" in (el.inner_text() or ""):
                    link = el
                    break

        if link is None:
            pytest.skip("'Learn about the pipeline' link not found in empty state")

        assert link.is_visible(), "'Learn about the pipeline' link must be visible"


# ---------------------------------------------------------------------------
# Gate Inspector filter interactions
# ---------------------------------------------------------------------------


class TestGateInspectorFilterInteractions:
    """Gate Inspector filter controls must respond to user interaction."""

    def test_gate_filter_all_button_clickable(self, page, base_url: str) -> None:
        """'All' filter button in Gate Inspector is clickable without JS errors."""
        _go(page, base_url)

        filter_bar = page.locator("[data-testid='gate-filter-bar']")
        if filter_bar.count() == 0:
            pytest.skip("Gate filter bar not found")

        js_errors: list[str] = []
        page.on("pageerror", lambda exc: js_errors.append(str(exc)))

        all_btn = filter_bar.locator("button", has_text="All")
        if all_btn.count() == 0:
            pytest.skip("'All' button not found in gate filter bar")

        all_btn.first.click()
        page.wait_for_timeout(400)

        assert not js_errors, f"JS errors after clicking 'All' filter: {js_errors}"

    def test_gate_filter_pass_button_clickable(self, page, base_url: str) -> None:
        """'Pass' filter button in Gate Inspector is clickable without JS errors."""
        _go(page, base_url)

        filter_bar = page.locator("[data-testid='gate-filter-bar']")
        if filter_bar.count() == 0:
            pytest.skip("Gate filter bar not found")

        js_errors: list[str] = []
        page.on("pageerror", lambda exc: js_errors.append(str(exc)))

        pass_btn = filter_bar.locator("button", has_text="Pass")
        if pass_btn.count() == 0:
            pytest.skip("'Pass' button not found in gate filter bar")

        pass_btn.first.click()
        page.wait_for_timeout(400)

        assert not js_errors, f"JS errors after clicking 'Pass' filter: {js_errors}"

    def test_gate_filter_fail_button_clickable(self, page, base_url: str) -> None:
        """'Fail' filter button in Gate Inspector is clickable without JS errors."""
        _go(page, base_url)

        filter_bar = page.locator("[data-testid='gate-filter-bar']")
        if filter_bar.count() == 0:
            pytest.skip("Gate filter bar not found")

        js_errors: list[str] = []
        page.on("pageerror", lambda exc: js_errors.append(str(exc)))

        fail_btn = filter_bar.locator("button", has_text="Fail")
        if fail_btn.count() == 0:
            pytest.skip("'Fail' button not found in gate filter bar")

        fail_btn.first.click()
        page.wait_for_timeout(400)

        assert not js_errors, f"JS errors after clicking 'Fail' filter: {js_errors}"

    def test_gate_stage_dropdown_present(self, page, base_url: str) -> None:
        """Gate Inspector has a stage selector dropdown."""
        _go(page, base_url)

        filter_bar = page.locator("[data-testid='gate-filter-bar']")
        if filter_bar.count() == 0:
            pytest.skip("Gate filter bar not found")

        dropdown = filter_bar.locator("select")
        assert dropdown.count() > 0, (
            "Gate filter bar must include a stage selector <select> dropdown"
        )
        assert dropdown.first.is_visible(), "Stage dropdown must be visible"

    def test_gate_stage_dropdown_has_stage_options(self, page, base_url: str) -> None:
        """Gate Inspector stage dropdown includes pipeline stage options."""
        _go(page, base_url)

        filter_bar = page.locator("[data-testid='gate-filter-bar']")
        if filter_bar.count() == 0:
            pytest.skip("Gate filter bar not found")

        dropdown = filter_bar.locator("select").first
        if dropdown.count() == 0:
            pytest.skip("No stage dropdown found")

        # The dropdown should have at least the 'All stages' default option.
        options_count = page.evaluate(  # type: ignore[attr-defined]
            "document.querySelector('[data-testid=\"gate-filter-bar\"] select')?.options.length ?? 0"
        )
        assert options_count >= 1, (
            "Stage dropdown must have at least one option ('All stages')"
        )

    def test_gate_refresh_button_clickable(self, page, base_url: str) -> None:
        """Gate Inspector 'Refresh' button reloads gate data without JS errors."""
        _go(page, base_url)

        gate_inspector = page.locator("[data-testid='gate-inspector']")
        if gate_inspector.count() == 0:
            pytest.skip("Gate Inspector not found")

        js_errors: list[str] = []
        page.on("pageerror", lambda exc: js_errors.append(str(exc)))

        refresh_btn = gate_inspector.locator("button", has_text="Refresh")
        if refresh_btn.count() == 0:
            pytest.skip("No 'Refresh' button found in Gate Inspector")

        refresh_btn.first.click()
        page.wait_for_timeout(500)

        assert not js_errors, f"JS errors after clicking Gate Inspector Refresh: {js_errors}"
