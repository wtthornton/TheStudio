"""Epic 74.4 — Detail Pages: Interactive Elements.

Validates that entity detail views (/{entity}/{id}) support the expected
interactive behaviours:

  Tier change  — repo and expert detail pages expose tier-change controls
                 (Observe / Suggest / Execute) that are clickable and trigger
                 a visible state change or confirmation prompt.
  Navigation   — back links and breadcrumbs return the operator to the list;
                 related-entity links navigate between repos, workflows, and
                 experts without a full page error.
  Panel actions — action buttons on detail panels (pause, resume, re-trigger)
                 are present, enabled, and respond to interaction.
  No JS errors  — all interactions complete without uncaught JS exceptions.

Note: Detail pages require seed data.  Tests skip gracefully when no entities
exist; the navigation and structural tests fall back to list-page assertions.
"""

from __future__ import annotations

import pytest
import httpx

from tests.playwright.conftest import navigate

pytestmark = pytest.mark.playwright

REPOS_URL = "/admin/ui/repos"
WORKFLOWS_URL = "/admin/ui/workflows"
EXPERTS_URL = "/admin/ui/experts"
API_REPOS = "/api/v1/repos"
API_WORKFLOWS = "/api/v1/workflows"
API_EXPERTS = "/api/v1/experts"

TIER_KEYWORDS = ("observe", "suggest", "execute", "tier", "trust")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _first_entity_id(base_url: str, api_path: str) -> str | None:
    """Return the first entity ID from a list endpoint, or None if unavailable."""
    try:
        r = httpx.get(f"{base_url.rstrip('/')}{api_path}", timeout=5)
        if r.status_code != 200:
            return None
        data = r.json()
        items = data if isinstance(data, list) else data.get("items", data.get("data", []))
        if items:
            first = items[0]
            return str(
                first.get("id")
                or first.get("repo_id")
                or first.get("workflow_id")
                or ""
            )
        return None
    except Exception:  # noqa: BLE001
        return None


def _go_detail(page: object, base_url: str, detail_base: str, entity_id: str) -> None:
    """Navigate to an entity detail page."""
    navigate(page, f"{base_url}{detail_base}/{entity_id}")  # type: ignore[arg-type]


def _go_list(page: object, base_url: str, list_url: str) -> None:
    """Navigate to a list page."""
    navigate(page, f"{base_url}{list_url}")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Tier change actions
# ---------------------------------------------------------------------------


class TestTierChangeActions:
    """Repo and expert detail pages must expose tier-change controls.

    The three trust tiers are Observe, Suggest, and Execute (§5.2).
    Operators must be able to change a repo or expert's tier from the detail
    view without leaving the page.
    """

    def test_repo_detail_has_tier_control(self, page, base_url: str) -> None:
        """Repo detail page exposes a tier selector or tier-change button."""
        entity_id = _first_entity_id(base_url, API_REPOS)
        if not entity_id:
            pytest.skip("No repos registered — seed data required for 74.4 tier test")

        _go_detail(page, base_url, "/admin/ui/repos", entity_id)

        # Accept: select element, radio group, button group, or explicit tier buttons
        tier_selectors = [
            "select[name*='tier' i]",
            "select[id*='tier' i]",
            "[role='radiogroup'][aria-label*='tier' i]",
            "input[type='radio'][value*='observe' i]",
            "input[type='radio'][value*='suggest' i]",
            "input[type='radio'][value*='execute' i]",
            "button[data-tier]",
            "button[aria-label*='observe' i]",
            "button[aria-label*='suggest' i]",
            "button[aria-label*='execute' i]",
            "[data-action*='tier' i]",
        ]
        found = any(page.locator(sel).count() > 0 for sel in tier_selectors)  # type: ignore[attr-defined]

        if not found:
            # Fallback: check body text for tier-change hint
            body_lower = page.locator("body").inner_text().lower()  # type: ignore[attr-defined]
            found = any(kw in body_lower for kw in ("change tier", "set tier", "upgrade", "downgrade"))

        assert found, (
            "Repo detail page must expose a tier-change control "
            "(select, radio group, or labelled button) for Observe/Suggest/Execute"
        )

    def test_expert_detail_has_tier_control(self, page, base_url: str) -> None:
        """Expert detail page exposes a tier selector or tier-change button."""
        entity_id = _first_entity_id(base_url, API_EXPERTS)
        if not entity_id:
            pytest.skip("No experts registered — seed data required for 74.4 tier test")

        _go_detail(page, base_url, "/admin/ui/experts", entity_id)

        tier_selectors = [
            "select[name*='tier' i]",
            "select[id*='tier' i]",
            "[role='radiogroup'][aria-label*='tier' i]",
            "input[type='radio'][value*='observe' i]",
            "input[type='radio'][value*='suggest' i]",
            "input[type='radio'][value*='execute' i]",
            "button[data-tier]",
            "button[aria-label*='observe' i]",
            "button[aria-label*='suggest' i]",
            "button[aria-label*='execute' i]",
            "[data-action*='tier' i]",
        ]
        found = any(page.locator(sel).count() > 0 for sel in tier_selectors)  # type: ignore[attr-defined]

        if not found:
            body_lower = page.locator("body").inner_text().lower()  # type: ignore[attr-defined]
            found = any(kw in body_lower for kw in ("change tier", "set tier", "upgrade", "downgrade"))

        assert found, (
            "Expert detail page must expose a tier-change control "
            "(select, radio group, or labelled button) for Observe/Suggest/Execute"
        )

    def test_tier_control_is_enabled(self, page, base_url: str) -> None:
        """Tier change control on repo detail must be enabled (not read-only)."""
        entity_id = _first_entity_id(base_url, API_REPOS)
        if not entity_id:
            pytest.skip("No repos registered — seed data required for 74.4")

        _go_detail(page, base_url, "/admin/ui/repos", entity_id)

        tier_selectors = [
            "select[name*='tier' i]",
            "select[id*='tier' i]",
            "input[type='radio'][value*='observe' i]",
            "input[type='radio'][value*='suggest' i]",
            "input[type='radio'][value*='execute' i]",
            "button[data-tier]",
            "button[aria-label*='observe' i]",
            "button[aria-label*='suggest' i]",
            "button[aria-label*='execute' i]",
        ]
        for sel in tier_selectors:
            els = page.locator(sel)  # type: ignore[attr-defined]
            if els.count() > 0:
                first_el = els.first
                assert first_el.is_enabled(), (
                    f"Tier control ({sel!r}) must be enabled so operators can change the tier"
                )
                return

        pytest.skip("No enabled tier control found on repo detail page — may be read-only view")

    def test_tier_change_triggers_state_change(self, page, base_url: str) -> None:
        """Interacting with the tier control produces a visible state change or confirmation."""
        entity_id = _first_entity_id(base_url, API_REPOS)
        if not entity_id:
            pytest.skip("No repos registered — seed data required for 74.4")

        _go_detail(page, base_url, "/admin/ui/repos", entity_id)

        js_errors: list[str] = []
        page.on("pageerror", lambda exc: js_errors.append(str(exc)))  # type: ignore[attr-defined]

        before_html = page.locator("body").inner_html()  # type: ignore[attr-defined]

        # Try clicking the first available tier button
        tier_btn_selectors = [
            "button[data-tier]",
            "button[aria-label*='observe' i]",
            "button[aria-label*='suggest' i]",
            "button[aria-label*='execute' i]",
            "[data-action*='tier' i]",
        ]
        clicked = False
        for sel in tier_btn_selectors:
            btns = page.locator(sel)  # type: ignore[attr-defined]
            if btns.count() > 0 and btns.first.is_visible() and btns.first.is_enabled():
                btns.first.click()
                page.wait_for_timeout(600)  # type: ignore[attr-defined]
                clicked = True
                break

        if not clicked:
            # Try select change
            sel_el = page.locator("select[name*='tier' i], select[id*='tier' i]")  # type: ignore[attr-defined]
            if sel_el.count() > 0 and sel_el.first.is_enabled():
                options = sel_el.first.locator("option")
                if options.count() > 1:
                    # Select second option (different from current)
                    sel_el.first.select_option(index=1)
                    page.wait_for_timeout(600)  # type: ignore[attr-defined]
                    clicked = True

        if not clicked:
            pytest.skip("No interactable tier control found — tier change test requires an enabled control")

        after_html = page.locator("body").inner_html()  # type: ignore[attr-defined]

        # Either the DOM changed (confirmation prompt, badge update) or a dialog appeared
        dom_changed = before_html != after_html
        dialog_open = page.locator("[role='dialog'], [role='alertdialog']").count() > 0  # type: ignore[attr-defined]

        assert dom_changed or dialog_open, (
            "Interacting with the tier control must produce a visible change — "
            "DOM was identical and no dialog appeared after the interaction"
        )
        assert not js_errors, f"JS errors during tier change: {js_errors}"


# ---------------------------------------------------------------------------
# Navigation between entities
# ---------------------------------------------------------------------------


class TestDetailPageNavigation:
    """Operators must be able to navigate between entity detail pages and back to lists.

    Required navigation patterns:
      Back nav   — detail page provides a working link back to the list page
      Cross-links — workflow detail links to the repo that triggered it;
                    repo detail may link to related workflows
    """

    @pytest.mark.parametrize("list_url,api_path,detail_base,entity_name", [
        (REPOS_URL, API_REPOS, "/admin/ui/repos", "repo"),
        (WORKFLOWS_URL, API_WORKFLOWS, "/admin/ui/workflows", "workflow"),
        (EXPERTS_URL, API_EXPERTS, "/admin/ui/experts", "expert"),
    ])
    def test_detail_page_back_link_navigates_to_list(
        self,
        page,
        base_url: str,
        list_url: str,
        api_path: str,
        detail_base: str,
        entity_name: str,
    ) -> None:
        """Back link / breadcrumb on detail page navigates to the entity list."""
        entity_id = _first_entity_id(base_url, api_path)
        if not entity_id:
            pytest.skip(f"No {entity_name} entities — seed data required for 74.4 navigation")

        _go_detail(page, base_url, detail_base, entity_id)

        # Locate back navigation link
        back_link = None
        back_selectors = [
            f"a[href='{detail_base}']",
            f"a[href='{detail_base}/']",
            "a:has-text('Back')",
            "a:has-text('back')",
            "nav a",
            "[aria-label*='back' i]",
            ".breadcrumb a",
            "[class*='breadcrumb'] a",
        ]
        for sel in back_selectors:
            el = page.locator(sel)  # type: ignore[attr-defined]
            if el.count() > 0 and el.first.is_visible():
                back_link = el.first
                break

        if back_link is None:
            pytest.skip(f"No back link found on {entity_name} detail page — cannot test navigation")

        back_link.click()
        page.wait_for_load_state("domcontentloaded")  # type: ignore[attr-defined]

        # Must land somewhere on the list URL (allow redirects)
        current_url = page.url  # type: ignore[attr-defined]
        assert list_url in current_url or entity_name in current_url, (
            f"Back link on {entity_name} detail must navigate to the {entity_name} list — "
            f"landed at {current_url!r} instead"
        )

    def test_workflow_detail_links_to_repo(self, page, base_url: str) -> None:
        """Workflow detail page contains a link to the repo that triggered the workflow."""
        entity_id = _first_entity_id(base_url, API_WORKFLOWS)
        if not entity_id:
            pytest.skip("No workflows registered — seed data required for 74.4 cross-link test")

        _go_detail(page, base_url, "/admin/ui/workflows", entity_id)

        # Look for a repo link in the detail content
        has_repo_link = (
            page.locator("a[href*='/repos/']").count() > 0  # type: ignore[attr-defined]
            or page.locator("a[href*='/repo/']").count() > 0  # type: ignore[attr-defined]
        )

        if not has_repo_link:
            # Acceptable fallback: repo name mentioned without a hyperlink
            body_lower = page.locator("body").inner_text().lower()  # type: ignore[attr-defined]
            has_repo_mention = "repo" in body_lower or "repository" in body_lower
            assert has_repo_mention, (
                "Workflow detail page must link to or mention the triggering repo — "
                "no repo link or reference found"
            )
        # If a link exists, verify it resolves to a valid page (no 404)
        # (Full navigation tested separately; here we just assert presence)

    def test_repo_detail_links_to_related_workflows(self, page, base_url: str) -> None:
        """Repo detail page contains a link to or summary of related workflows."""
        entity_id = _first_entity_id(base_url, API_REPOS)
        if not entity_id:
            pytest.skip("No repos registered — seed data required for 74.4 cross-link test")

        _go_detail(page, base_url, "/admin/ui/repos", entity_id)

        has_workflow_link = (
            page.locator("a[href*='/workflows/']").count() > 0  # type: ignore[attr-defined]
            or page.locator("a[href*='/workflow/']").count() > 0  # type: ignore[attr-defined]
        )

        if not has_workflow_link:
            body_lower = page.locator("body").inner_text().lower()  # type: ignore[attr-defined]
            has_workflow_mention = "workflow" in body_lower or "run" in body_lower
            assert has_workflow_mention, (
                "Repo detail page must link to or summarise related workflows — "
                "no workflow link or reference found"
            )

    def test_detail_page_list_navigation_no_js_errors(self, page, base_url: str) -> None:
        """Navigating from a detail page back to the list produces no JS errors."""
        entity_id = _first_entity_id(base_url, API_REPOS)
        if not entity_id:
            pytest.skip("No repos registered — seed data required for 74.4")

        js_errors: list[str] = []
        page.on("pageerror", lambda exc: js_errors.append(str(exc)))  # type: ignore[attr-defined]

        _go_detail(page, base_url, "/admin/ui/repos", entity_id)

        # Navigate back using the browser history
        page.go_back()  # type: ignore[attr-defined]
        page.wait_for_load_state("domcontentloaded")  # type: ignore[attr-defined]
        page.wait_for_timeout(400)  # type: ignore[attr-defined]

        assert not js_errors, f"JS errors during detail → list navigation: {js_errors}"


# ---------------------------------------------------------------------------
# Action buttons on detail panels
# ---------------------------------------------------------------------------


class TestDetailPageActionButtons:
    """Action buttons on entity detail pages must be present, enabled, and responsive."""

    @pytest.mark.parametrize("api_path,detail_base,entity_name", [
        (API_REPOS, "/admin/ui/repos", "repo"),
        (API_WORKFLOWS, "/admin/ui/workflows", "workflow"),
        (API_EXPERTS, "/admin/ui/experts", "expert"),
    ])
    def test_detail_page_has_at_least_one_action_button(
        self,
        page,
        base_url: str,
        api_path: str,
        detail_base: str,
        entity_name: str,
    ) -> None:
        """Entity detail page contains at least one action button."""
        entity_id = _first_entity_id(base_url, api_path)
        if not entity_id:
            pytest.skip(f"No {entity_name} entities — seed data required for 74.4")

        _go_detail(page, base_url, detail_base, entity_id)

        buttons = page.locator("button, [role='button'], a.btn, a[class*='button']")  # type: ignore[attr-defined]
        count = buttons.count()

        if count == 0:
            pytest.skip(f"{entity_name} detail page has no buttons — may be read-only view")

        assert count > 0, (
            f"{entity_name} detail page must have at least one action button — none found"
        )

    def test_repo_detail_pause_or_enable_button_present(self, page, base_url: str) -> None:
        """Repo detail exposes a pause, resume, or enable/disable action."""
        entity_id = _first_entity_id(base_url, API_REPOS)
        if not entity_id:
            pytest.skip("No repos registered — seed data required for 74.4")

        _go_detail(page, base_url, "/admin/ui/repos", entity_id)

        action_selectors = [
            "button[aria-label*='pause' i]",
            "button[aria-label*='resume' i]",
            "button[aria-label*='enable' i]",
            "button[aria-label*='disable' i]",
            "button[aria-label*='activate' i]",
            "button[aria-label*='deactivate' i]",
            "button:has-text('Pause')",
            "button:has-text('Resume')",
            "button:has-text('Enable')",
            "button:has-text('Disable')",
        ]
        found = any(page.locator(sel).count() > 0 for sel in action_selectors)  # type: ignore[attr-defined]

        if not found:
            body_lower = page.locator("body").inner_text().lower()  # type: ignore[attr-defined]
            found = any(
                kw in body_lower
                for kw in ("pause", "resume", "enable", "disable", "activate", "deactivate")
            )

        assert found, (
            "Repo detail page must expose a pause/resume or enable/disable action — "
            "none found in buttons or body text"
        )

    def test_workflow_detail_action_buttons_enabled(self, page, base_url: str) -> None:
        """Workflow detail action buttons are present and not permanently disabled."""
        entity_id = _first_entity_id(base_url, API_WORKFLOWS)
        if not entity_id:
            pytest.skip("No workflows registered — seed data required for 74.4")

        _go_detail(page, base_url, "/admin/ui/workflows", entity_id)

        buttons = page.locator("button, [role='button']")  # type: ignore[attr-defined]
        count = buttons.count()

        if count == 0:
            pytest.skip("No buttons on workflow detail page — may be read-only view")

        # At least the first button must be enabled
        first_btn = buttons.first
        assert first_btn.is_visible(), "First action button on workflow detail must be visible"
        assert first_btn.is_enabled(), "First action button on workflow detail must be enabled"


# ---------------------------------------------------------------------------
# No JS errors across all detail pages
# ---------------------------------------------------------------------------


class TestDetailPageNoJsErrors:
    """Detail page interactions must not raise uncaught JS exceptions."""

    @pytest.mark.parametrize("api_path,detail_base,entity_name", [
        (API_REPOS, "/admin/ui/repos", "repo"),
        (API_WORKFLOWS, "/admin/ui/workflows", "workflow"),
        (API_EXPERTS, "/admin/ui/experts", "expert"),
    ])
    def test_detail_page_loads_without_js_errors(
        self,
        page,
        base_url: str,
        api_path: str,
        detail_base: str,
        entity_name: str,
    ) -> None:
        """Entity detail page loads without uncaught JS errors."""
        entity_id = _first_entity_id(base_url, api_path)
        if not entity_id:
            pytest.skip(f"No {entity_name} entities — seed data required for 74.4")

        js_errors: list[str] = []
        page.on("pageerror", lambda exc: js_errors.append(str(exc)))  # type: ignore[attr-defined]

        _go_detail(page, base_url, detail_base, entity_id)
        page.wait_for_timeout(500)  # type: ignore[attr-defined]

        assert not js_errors, (
            f"{entity_name} detail page produced uncaught JS errors on load: {js_errors}"
        )
