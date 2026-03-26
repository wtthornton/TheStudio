# Story 76.7 -- Fix Real Accessibility Bugs

<!-- docsmcp:start:user-story -->

> **As a** platform operator using assistive technology, **I want** all admin UI tables and controls to have proper ARIA labels, **so that** the admin UI is accessible to screen readers and keyboard users

<!-- docsmcp:end:user-story -->

<!-- docsmcp:start:sizing -->
**Points:** 3 | **Size:** M

<!-- docsmcp:end:sizing -->

<!-- docsmcp:start:purpose-intent -->
## Purpose & Intent

This story exists so that genuine accessibility defects in the admin UI templates are fixed -- not just test calibration issues. After stories 76.3 and 76.4 fix the test infrastructure, some a11y test failures will remain because the templates themselves are missing table captions, ARIA labels on controls, or landmark annotations. This story addresses those real WCAG 2.2 AA violations.

<!-- docsmcp:end:purpose-intent -->

<!-- docsmcp:start:description -->
## Description

Audit all admin UI templates for accessibility issues that cause genuine axe-core violations or a11y assertion failures. Add `aria-label` or `<caption>` elements to data tables, ensure all form controls have associated labels, and verify that landmark regions are properly annotated. This is the only story in Epic 76 that modifies production template files rather than test code.

See [Epic 76](../../epic-76-playwright-test-calibration.md) for project context and failure baseline.

<!-- docsmcp:end:description -->

<!-- docsmcp:start:files -->
## Files

- `src/admin/templates/partials/audit_list.html`
- `src/admin/templates/partials/dashboard_content.html`
- `src/admin/templates/repos.html` (if tables lack captions)
- `src/admin/templates/workflows.html` (if tables lack captions)
- `src/admin/templates/base.html` (landmark annotations if missing)
- All templates under `src/admin/templates/` and `src/admin/templates/partials/` (audit scope)

<!-- docsmcp:end:files -->

<!-- docsmcp:start:tasks -->
## Tasks

- [ ] Run axe-core audit (via `run_axe_audit()` after Story 76.3 is complete) against each admin page and document genuine violations with their element selectors
- [ ] Add `aria-label` or `<caption>` to the audit log table in `src/admin/templates/partials/audit_list.html`
- [ ] Audit all other templates under `src/admin/templates/` for tables missing `<caption>` or `aria-label` and fix each one
- [ ] Audit all form controls (inputs, selects, textareas, buttons) across templates for missing `<label>` associations or `aria-label` attributes and fix each one
- [ ] Verify that `<nav>`, `<main>`, `<header>` landmarks in `src/admin/templates/base.html` have distinct `aria-label` attributes when duplicated
- [ ] Run all a11y test files and verify no new WCAG violations are introduced and previously-failing genuine a11y tests now pass

<!-- docsmcp:end:tasks -->

<!-- docsmcp:start:acceptance-criteria -->
## Acceptance Criteria

- [ ] All `<table>` elements in admin templates have either an `aria-label` attribute or a `<caption>` child element
- [ ] All form controls (`<input>`, `<select>`, `<textarea>`) have an associated `<label>` element (via `for` attribute) or an `aria-label` attribute
- [ ] All buttons have visible text content or an `aria-label` attribute
- [ ] Duplicate landmark regions (`<nav>`, `<header>`) have distinct `aria-label` attributes
- [ ] No new WCAG 2.2 AA violations are introduced by the template changes
- [ ] Previously-failing genuine a11y tests pass after the fixes

<!-- docsmcp:end:acceptance-criteria -->

<!-- docsmcp:start:definition-of-done -->
## Definition of Done

Definition of Done per [Epic 76](../../epic-76-playwright-test-calibration.md).

<!-- docsmcp:end:definition-of-done -->

<!-- docsmcp:start:test-cases -->
## Test Cases

1. `test_ac1_all_tables_have_aria_label_or_caption` -- Every table element across all admin pages has aria-label or caption
2. `test_ac2_all_form_controls_have_labels` -- Every input, select, and textarea has an associated label or aria-label
3. `test_ac3_all_buttons_have_accessible_names` -- Every button has visible text or aria-label
4. `test_ac4_duplicate_landmarks_have_distinct_labels` -- Duplicate nav/header elements have distinct aria-label values
5. `test_ac5_no_new_wcag_violations` -- axe-core audit produces zero new violations after template changes
6. `test_ac6_genuine_a11y_tests_pass` -- Previously-failing a11y tests for fixed elements now pass

<!-- docsmcp:end:test-cases -->

<!-- docsmcp:start:technical-notes -->
## Technical Notes

- This is the only story in Epic 76 that modifies production templates (all other stories modify test code only).
- Changes should be minimal and targeted -- add `aria-label` attributes and `<caption>` elements without altering layout or visual presentation.
- Use the Jinja2 template structure (blocks, includes, macros) when adding accessibility attributes so they propagate correctly across pages that include shared partials.
- WCAG 2.2 AA requires: all non-decorative images have alt text, all form controls have labels, all tables have captions or aria-labels, focus is visible, and color is not the sole indicator.

<!-- docsmcp:end:technical-notes -->

<!-- docsmcp:start:dependencies -->
## Dependencies

- Story 76.3 (axe-core integration must work before we can distinguish genuine violations from test bugs)
- Story 76.4 (focus-visible helper must work before we can verify focus ring fixes)

<!-- docsmcp:end:dependencies -->

<!-- docsmcp:start:invest -->
## INVEST Checklist

- [x] **I**ndependent -- Template fixes are independent of test calibration changes
- [x] **N**egotiable -- Specific ARIA label text can be refined during implementation
- [x] **V**aluable -- Directly improves accessibility for users of assistive technology
- [x] **E**stimable -- Team can estimate the effort
- [x] **S**mall -- Completable within one sprint/iteration
- [x] **T**estable -- Has clear criteria to verify completion via axe-core and a11y tests

<!-- docsmcp:end:invest -->
