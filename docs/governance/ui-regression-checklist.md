# UI Modernization Regression Checklist

> **Scope:** All UI modernization waves (Epics 53-57)
> **Canonical style guide:** `docs/design/07-THESTUDIO-UI-UX-STYLE-GUIDE.md`
> **Owner story:** Story 57.2
> **Last updated:** 2026-03-24

This checklist must pass before any UI modernization wave ships. Each item has a clear pass/fail criterion. Mark items as they are verified.

---

## 1. Accessibility (SG 6.1-6.5)

- [ ] **Focus-visible on all interactive elements** -- Every button, link, input, and control has a visible `:focus-visible` ring. No interactive element lacks keyboard focus indication.
- [ ] **Keyboard navigation complete** -- All primary workflows are completable using keyboard only (Tab, Shift+Tab, Enter, Escape). Modal dialogs trap focus and return it on close.
- [ ] **Aria-labels on dynamic content** -- Dynamically loaded content (HTMX partials, React async components) has appropriate `aria-label`, `aria-labelledby`, or `aria-describedby` attributes.
- [ ] **Non-color status cues** -- No status is communicated by color alone. Icons, text labels, or patterns accompany every color-coded status indicator.
- [ ] **Screen reader semantics** -- Correct `role` attributes on interactive regions. `aria-live="polite"` on regions that update dynamically. `role="alert"` on error messages.

## 2. Semantic Consistency (SG 3.1-3.3)

- [ ] **Status colors match SG 3.1** -- success (green), warning (amber), error (red), info (blue), neutral (gray) are used consistently. No semantic drift (e.g., using red for non-error states).
- [ ] **Trust tiers match SG 3.2** -- EXECUTE, SUGGEST, and OBSERVE tiers use their defined color tokens and labels consistently across both surfaces.
- [ ] **Role badges match SG 3.3** -- Agent role badges use the canonical badge recipe. Admin and dashboard surfaces show consistent role representations.
- [ ] **Cross-surface semantics aligned** -- The same concept (e.g., "error", "pending", "active") uses the same color and label on both Admin Console and Pipeline Dashboard.

## 3. Prompt-First Compliance (SG 8.1-8.6)

- [ ] **AI flows use 5-step sequence (SG 8.1)** -- Every AI-assisted flow follows: prompt -> preview -> confirm -> execute -> feedback. No AI action fires without user confirmation.
- [ ] **Prompt object fields present (SG 8.2)** -- Prompt surfaces expose the required fields (intent, context, constraints) per the prompt object contract.
- [ ] **Evidence and trust signals shown (SG 8.4)** -- AI outputs display confidence, evidence source, timestamp, and ownership. Trust signals are not hidden or truncated.
- [ ] **AI outputs labeled (SG 8.6)** -- All AI-generated content is visually labeled as AI-produced. Users can distinguish human-authored from AI-generated content.

## 4. State Handling (SG 5.1-5.3)

- [ ] **Explicit loading states** -- Every async operation shows a named loading indicator with `role="status"` and `aria-live="polite"`. No blank screens during data fetch.
- [ ] **Empty states with guidance** -- Empty lists, tables, and dashboards show a helpful message and a primary action CTA. No blank containers without explanation.
- [ ] **Error states with recovery actions** -- Errors display a clear message, the error category, and at least one recovery action (retry, navigate back, contact support). `role="alert"` is present.

## 5. Responsive and i18n (SG 9.3C, 9.3D)

- [ ] **Tablet layout functional** -- All primary views render correctly at 768px width. No horizontal overflow, no overlapping elements, no hidden critical controls.
- [ ] **No hard-coded text widths** -- Text containers use relative or max-width sizing. Long text wraps or truncates gracefully. No fixed pixel widths on text-heavy elements.
- [ ] **Locale-aware formatting** -- Dates, numbers, and currencies use locale-aware formatters (or are structured to accept them). No hard-coded date formats like "MM/DD/YYYY".

## 6. Deferred Pattern Guard (SG 9.4)

- [ ] **No AR/VR patterns** -- No augmented reality, virtual reality, or spatial UI patterns are introduced. These remain explicitly deferred.
- [ ] **No unbounded customization** -- User customization is constrained to predefined options with a reset-to-default mechanism. No free-form theme or layout editors.

---

**This checklist is required for Epic 57.3 wave gates.** Each wave must complete all applicable items before shipping. Items not applicable to a specific wave should be marked N/A with justification.
