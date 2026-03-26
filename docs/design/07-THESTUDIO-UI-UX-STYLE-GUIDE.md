# TheStudio UI/UX Style Guide

**Status:** Active Standard
**Scope:** All frontend surfaces of TheStudio (Admin Console, Pipeline Dashboard, and any future surface)
**Compliance baseline:** WCAG 2.2 AA
**Last updated:** 2026-03-24
**Owners:** Product + Frontend

---

## 1. Purpose and Scope

This document is the single source of truth for all visual, interaction, and
accessibility standards across every frontend surface of TheStudio. It governs
the Admin Console, the Pipeline Dashboard, and any surface added in the future.

### 1.1 Source-of-Truth Contract

1. If any other document, component library, or template conflicts with this
   guide, **this guide wins**.
2. New frontend work must reference this guide before introducing patterns.
3. Changes to visual or interaction patterns must update this guide in the
   same PR.
4. No surface is exempt. Surfaces may have documented **conformance
   expectations** (see Section 3) but never blanket exemptions.

### 1.2 Design Philosophy

TheStudio is an AI-augmented software delivery platform. Its interfaces serve
operators who need fast, trustworthy, keyboard-driven workflows. The guide is
informed by Linear (keyboard-first, opinionated defaults), Stripe (clean
hierarchy, documentation as product), Apple HIG (progressive disclosure,
consistency), and IBM Carbon for AI (transparency, explainability).

---

## 2. Design Principles

These principles apply to every surface and every PR.

### 2.1 Keyboard-first, mouse-optional

Every interactive element is reachable and operable via keyboard. Mouse and
touch are enhancement layers, not requirements. Power users should never need
to reach for a mouse.

### 2.2 Dark mode is a first-class experience

Both light and dark themes are fully designed and tested. Dark mode is not a
filter or afterthought. Semantic tokens resolve to curated values for each
theme. Surfaces that currently lack a dark toggle must still define dark-ready
tokens.

### 2.3 Overview first, details on demand

Top-level views expose key KPIs and status immediately. Detail is one click or
keyboard action away, never buried behind multiple navigations. Progressive
disclosure, not progressive hiding.

### 2.4 Every action has a shortcut

Frequently used actions have keyboard shortcuts. The command palette
(Ctrl/Cmd+K) is the universal entry point. Discoverability: shortcuts appear
in tooltips, menus, and the palette itself.

### 2.5 AI transparency by default

AI-generated or AI-influenced content is always labeled. Confidence,
provenance, and recency are visible. Users are never surprised by autonomous
action. Human override is always available.

### 2.6 Consistency over novelty

Reuse existing patterns before inventing new ones. Cross-surface consistency is
achieved through shared tokens and shared semantics, not by forcing identical
components onto different tech stacks.

### 2.7 Accessibility is not optional

WCAG 2.2 AA is the compliance floor. Accessibility is tested in every PR, not
bolted on at the end. Semantic HTML is the default. ARIA is the fallback when
semantics alone are insufficient.

### 2.8 Performance is a feature

Skeleton screens over spinners. Optimistic UI where safe. No animation blocks
interaction. Perceived latency matters as much as actual latency.

---

## 3. Surface Registry

Every frontend surface is registered here with its stack, theme model,
navigation pattern, and conformance expectations.

| Surface | Path | Stack | Theme | Primary Nav | Conformance |
|---------|------|-------|-------|-------------|-------------|
| Admin Console | `/admin/ui/*` | Jinja2 + HTMX + Tailwind CDN | Light content + dark sidebar | Vertical sidebar | Full: all sections |
| Pipeline Dashboard | `/dashboard/*` | React SPA + Tailwind build | Dark-first operational | Horizontal tabs (migrating to sidebar) | Full: all sections |
| API Reference | `/dashboard/?tab=api` | React (Scalar embed) | Inherits dashboard theme | Tab within dashboard | Sections 4-6, 11-12 |
| Setup Wizard | Overlay in dashboard | React | Dark overlay | Step progression | Sections 5, 11, 15, 16 |

### 3.1 Cross-Surface Invariants

These rules apply to every surface without exception:

- Status color semantics are universal (Section 5).
- Loading, empty, and error states are always explicit (Section 10).
- Keyboard navigation and visible focus are always required (Section 11).
- No surface may rely on color alone to convey state.
- AI-generated content is always labeled (Section 13).
- The command palette is available on every surface (Section 14).

### 3.2 Reference Implementation

The **Admin Console** is the reference implementation for this guide. Its
patterns (shell layout, sidebar navigation, card surfaces, status badges, empty
states) represent the gold standard. When building a new surface or migrating
an existing one, start from Admin Console patterns and adapt only where the
surface's constraints require it.

### 3.3 Navigation Unification

All surfaces must adopt the **sidebar navigation** pattern as their primary
navigation. Horizontal tabs and bars serve as secondary navigation within a
surface, not as the primary navigation shell.

The Pipeline Dashboard currently uses horizontal tabs as primary navigation.
This is a documented conformance gap. Migration to sidebar navigation is
tracked in the epic backlog.

---

## 4. Design Token Architecture

TheStudio uses a three-tier token system: **primitive**, **semantic**, and
**component**. Tokens are defined as CSS custom properties and integrated with
Tailwind via `theme.extend`.

### 4.1 Primitive Tokens (Tier 1)

Raw values with no implied meaning. These are the palette.

```css
:root {
  /* Grays */
  --primitive-gray-50:  #f9fafb;
  --primitive-gray-100: #f3f4f6;
  --primitive-gray-200: #e5e7eb;
  --primitive-gray-300: #d1d5db;
  --primitive-gray-400: #9ca3af;
  --primitive-gray-500: #6b7280;
  --primitive-gray-600: #4b5563;
  --primitive-gray-700: #374151;
  --primitive-gray-800: #1f2937;
  --primitive-gray-900: #111827;
  --primitive-gray-950: #030712;

  /* Blue */
  --primitive-blue-50:  #eff6ff;
  --primitive-blue-100: #dbeafe;
  --primitive-blue-500: #3b82f6;
  --primitive-blue-600: #2563eb;
  --primitive-blue-700: #1d4ed8;

  /* Green */
  --primitive-green-50:  #f0fdf4;
  --primitive-green-100: #dcfce7;
  --primitive-green-500: #22c55e;
  --primitive-green-600: #16a34a;
  --primitive-green-800: #166534;

  /* Red */
  --primitive-red-50:  #fef2f2;
  --primitive-red-100: #fee2e2;
  --primitive-red-500: #ef4444;
  --primitive-red-600: #dc2626;
  --primitive-red-800: #991b1b;

  /* Yellow */
  --primitive-yellow-50:  #fefce8;
  --primitive-yellow-100: #fef9c3;
  --primitive-yellow-500: #eab308;
  --primitive-yellow-600: #ca8a04;
  --primitive-yellow-800: #854d0e;

  /* Purple */
  --primitive-purple-50:  #faf5ff;
  --primitive-purple-100: #f3e8ff;
  --primitive-purple-500: #a855f7;
  --primitive-purple-600: #9333ea;
  --primitive-purple-800: #6b21a8;

  /* Indigo */
  --primitive-indigo-600: #4f46e5;
  --primitive-indigo-800: #3730a3;
}
```

### 4.2 Semantic Tokens (Tier 2)

Meaning-based tokens that map to primitives. These change between themes.

```css
/* ── Light theme (default) ── */
:root, [data-theme="light"] {
  /* Backgrounds */
  --color-bg-primary:    var(--primitive-gray-50);
  --color-bg-surface:    #ffffff;
  --color-bg-elevated:   #ffffff;
  --color-bg-sidebar:    var(--primitive-gray-900);
  --color-bg-overlay:    rgba(0, 0, 0, 0.5);

  /* Text */
  --color-text-primary:   var(--primitive-gray-900);
  --color-text-secondary: var(--primitive-gray-500);
  --color-text-tertiary:  var(--primitive-gray-400);
  --color-text-inverse:   #ffffff;
  --color-text-on-sidebar: var(--primitive-gray-100);

  /* Borders */
  --color-border-primary:   var(--primitive-gray-200);
  --color-border-secondary: var(--primitive-gray-100);

  /* Interactive */
  --color-interactive-primary:    var(--primitive-blue-600);
  --color-interactive-hover:      var(--primitive-blue-700);
  --color-interactive-destructive: var(--primitive-red-600);
  --color-interactive-secondary:   var(--primitive-gray-600);

  /* Focus */
  --color-focus-ring: var(--primitive-blue-600);

  /* Status (used in badges, alerts, KPIs) */
  --color-status-success-bg:   var(--primitive-green-100);
  --color-status-success-text: var(--primitive-green-800);
  --color-status-success-kpi:  var(--primitive-green-600);

  --color-status-warning-bg:   var(--primitive-yellow-100);
  --color-status-warning-text: var(--primitive-yellow-800);
  --color-status-warning-kpi:  var(--primitive-yellow-600);

  --color-status-error-bg:   var(--primitive-red-100);
  --color-status-error-text: var(--primitive-red-800);
  --color-status-error-kpi:  var(--primitive-red-600);

  --color-status-info-bg:   var(--primitive-blue-100);
  --color-status-info-text: var(--primitive-blue-700);
  --color-status-info-kpi:  var(--primitive-blue-600);

  --color-status-neutral-bg:   var(--primitive-gray-100);
  --color-status-neutral-text: var(--primitive-gray-700);
}

/* ── Dark theme ── */
[data-theme="dark"] {
  --color-bg-primary:    var(--primitive-gray-950);
  --color-bg-surface:    var(--primitive-gray-900);
  --color-bg-elevated:   var(--primitive-gray-800);
  --color-bg-sidebar:    var(--primitive-gray-950);
  --color-bg-overlay:    rgba(0, 0, 0, 0.7);

  --color-text-primary:   var(--primitive-gray-50);
  --color-text-secondary: var(--primitive-gray-400);
  --color-text-tertiary:  var(--primitive-gray-500);
  --color-text-inverse:   var(--primitive-gray-900);
  --color-text-on-sidebar: var(--primitive-gray-300);

  --color-border-primary:   var(--primitive-gray-700);
  --color-border-secondary: var(--primitive-gray-800);

  --color-interactive-primary:    var(--primitive-blue-500);
  --color-interactive-hover:      var(--primitive-blue-600);
  --color-interactive-destructive: var(--primitive-red-500);
  --color-interactive-secondary:   var(--primitive-gray-400);

  --color-focus-ring: var(--primitive-blue-500);

  --color-status-success-bg:   rgba(22, 163, 74, 0.2);
  --color-status-success-text: var(--primitive-green-500);
  --color-status-success-kpi:  var(--primitive-green-500);

  --color-status-warning-bg:   rgba(234, 179, 8, 0.2);
  --color-status-warning-text: var(--primitive-yellow-500);
  --color-status-warning-kpi:  var(--primitive-yellow-500);

  --color-status-error-bg:   rgba(239, 68, 68, 0.2);
  --color-status-error-text: var(--primitive-red-500);
  --color-status-error-kpi:  var(--primitive-red-500);

  --color-status-info-bg:   rgba(59, 130, 246, 0.2);
  --color-status-info-text: var(--primitive-blue-500);
  --color-status-info-kpi:  var(--primitive-blue-500);

  --color-status-neutral-bg:   var(--primitive-gray-800);
  --color-status-neutral-text: var(--primitive-gray-400);
}
```

### 4.3 Component Tokens (Tier 3)

Specific to a component or region. Defined in terms of semantic tokens.

```css
:root {
  /* Sidebar */
  --sidebar-bg:           var(--color-bg-sidebar);
  --sidebar-text:         var(--color-text-on-sidebar);
  --sidebar-active-bg:    var(--primitive-gray-800);
  --sidebar-hover-bg:     var(--primitive-gray-800);
  --sidebar-width:        14rem; /* 224px */
  --sidebar-width-collapsed: 3.5rem; /* 56px */

  /* Cards */
  --card-bg:              var(--color-bg-surface);
  --card-border:          var(--color-border-primary);
  --card-radius:          0.5rem;
  --card-padding:         1rem; /* or 1.5rem for spacious */

  /* Header */
  --header-bg:            var(--color-bg-surface);
  --header-border:        var(--color-border-primary);
  --header-height:        3.5rem;

  /* Tables */
  --table-header-bg:      var(--color-bg-primary);
  --table-row-hover:      var(--color-bg-primary);
  --table-border:         var(--color-border-secondary);
}
```

### 4.4 Tailwind Integration

Map semantic tokens to Tailwind's `theme.extend` so utility classes resolve to
the token system:

```js
// tailwind.config.js (extend block)
colors: {
  surface:     'var(--color-bg-surface)',
  elevated:    'var(--color-bg-elevated)',
  primary:     'var(--color-interactive-primary)',
  destructive: 'var(--color-interactive-destructive)',
  'text-primary':   'var(--color-text-primary)',
  'text-secondary': 'var(--color-text-secondary)',
  // ... status colors follow the same pattern
}
```

### 4.5 Theme Switching and FOUC Prevention

**Three-way preference model:** Light / System / Dark. The user's explicit choice
is stored in `localStorage` (`thestudio_theme`). When set to "System" (or no
stored value), the `prefers-color-scheme` media query controls the theme.

**Flash of Wrong Theme (FOUC) prevention:** A blocking inline script in `<head>`
reads `localStorage` synchronously and sets `data-theme` on `<html>` before
the first paint. This runs before any stylesheet or body content renders.

```html
<script>
  (function() {
    var stored = localStorage.getItem('thestudio_theme');
    var prefersDark = window.matchMedia &&
      window.matchMedia('(prefers-color-scheme: dark)').matches;
    var theme = stored || (prefersDark ? 'dark' : 'light');
    document.documentElement.setAttribute('data-theme', theme);
    document.documentElement.classList.add('no-transition');
  })();
</script>
```

```css
.no-transition * { transition: none !important; }
```

Remove `no-transition` after first paint to restore animations:

```javascript
window.addEventListener('load', function() {
  requestAnimationFrame(function() {
    document.documentElement.classList.remove('no-transition');
  });
});
```

**System preference listener:** When the user selects "System", watch for OS
changes and update in real time:

```javascript
window.matchMedia('(prefers-color-scheme: dark)')
  .addEventListener('change', function(e) {
    if (!localStorage.getItem('thestudio_theme')) {
      document.documentElement.setAttribute('data-theme',
        e.matches ? 'dark' : 'light');
    }
  });
```

**Sidebar-invariant rule:** The sidebar is dark in both themes. Sidebar tokens
(`--sidebar-bg`, `--sidebar-text`, `--sidebar-active-bg`) are **not overridden**
in the `[data-theme="dark"]` block. In dark mode the content area darkens to
match the sidebar — the sidebar does not lighten.

**Contrast enforcement:** Both themes must pass WCAG 2.2 AA minimums:

| Pairing | Minimum ratio | Notes |
|---------|---------------|-------|
| Body text on surface | 4.5:1 | Primary readability |
| Secondary text on surface | 4.5:1 | Subtitles, metadata |
| Tertiary text on surface | 3:1 | Large/bold text only (>= 18px or 14px bold) |
| Interactive elements on surface | 3:1 | Buttons, links, icons |
| Status badge text on badge bg | 4.5:1 | Dark mode badges may need `font-semibold` |
| Non-text contrast (icons, borders) | 3:1 | SC 1.4.11 |

### 4.6 Extended Token Categories

These tokens extend the base semantic tier (Section 4.2) for state, motion,
and overlay patterns introduced in Epic 75:

```css
:root, [data-theme="light"] {
  /* State overlays */
  --state-hover-overlay:    rgba(0, 0, 0, 0.04);
  --state-active-overlay:   rgba(0, 0, 0, 0.08);
  --state-disabled-opacity: 0.5;
  --state-selected-bg:      var(--primitive-blue-50);

  /* Motion */
  --motion-duration-instant: 0ms;
  --motion-duration-fast:    100ms;
  --motion-duration-normal:  200ms;
  --motion-duration-slow:    300ms;
  --motion-easing-default:   cubic-bezier(0.4, 0, 0.2, 1);
  --motion-easing-enter:     cubic-bezier(0, 0, 0.2, 1);
  --motion-easing-exit:      cubic-bezier(0.4, 0, 1, 1);

  /* Overlay / scrim */
  --color-bg-scrim:   rgba(0, 0, 0, 0.5);
  --color-bg-overlay: rgba(255, 255, 255, 0.97);
}

[data-theme="dark"] {
  --state-hover-overlay:  rgba(255, 255, 255, 0.06);
  --state-active-overlay: rgba(255, 255, 255, 0.10);
  --state-selected-bg:    var(--primitive-blue-950);
  --color-bg-overlay:     rgba(17, 24, 39, 0.97);
}
```

---

### 4.7 For Developers: Using Design Tokens

#### Canonical source

The canonical implementation of all design tokens is:

```
static/css/tokens.css
```

Both frontend surfaces import this file:

- **Admin UI (Jinja2):** `<link rel="stylesheet" href="/static/css/tokens.css">` in `base.html`
- **React Dashboard:** `frontend/src/theme.css` (synced copy, imported in `index.css`)

#### Jinja2 template usage (Admin UI)

Use Tailwind CDN arbitrary value syntax to reference tokens:

```html
<div class="bg-[var(--color-bg-surface)] border border-[var(--color-border-primary)] rounded-lg p-4">
  <h3 class="text-[var(--color-text-primary)]">Card Title</h3>
  <p class="text-[var(--color-text-secondary)]">Description</p>
  <button class="bg-[var(--color-interactive-primary)] hover:bg-[var(--color-interactive-hover)] text-white px-4 py-2 rounded">
    Action
  </button>
</div>
```

#### React component usage

React components can use tokens via Tailwind v4 `@theme` utilities or directly via CSS custom properties:

```tsx
// Via Tailwind v4 @theme utilities:
<div className="bg-surface border border-primary rounded-lg p-4">
  <h3 className="text-primary">Card Title</h3>
  <p className="text-secondary">Description</p>
</div>

// Or via CSS custom properties directly:
<div style={{ backgroundColor: 'var(--color-bg-surface)' }}>
```

#### Adding a new token

1. Add the token to `static/css/tokens.css` (both `:root` and `.dark` / `[data-theme="dark"]`)
2. Copy the change to `frontend/src/theme.css`
3. If needed, add a `@theme` mapping in `frontend/src/index.css`
4. Both surfaces pick up the new token automatically

---

## 5. Color System

### 5.1 Status and Severity

Status colors carry universal meaning across every surface. Each status has
background, text, and KPI variants for both themes (defined via semantic tokens
in Section 4.2).

| Status | Meaning | Light bg/text | Dark bg/text | Tailwind (light) |
|--------|---------|---------------|--------------|------------------|
| Success | OK, healthy, passing | `green-100` / `green-800` | `green-500/20` / `green-500` | `bg-green-100 text-green-800` |
| Warning | Degraded, stuck, slow | `yellow-100` / `yellow-800` | `yellow-500/20` / `yellow-500` | `bg-yellow-100 text-yellow-800` |
| Error | Failed, unhealthy, blocked | `red-100` / `red-800` | `red-500/20` / `red-500` | `bg-red-100 text-red-800` |
| Info | In progress, running, active | `blue-100` / `blue-700` | `blue-500/20` / `blue-500` | `bg-blue-100 text-blue-800` |
| Neutral | Unknown, pending, default | `gray-100` / `gray-700` | `gray-800` / `gray-400` | `bg-gray-100 text-gray-700` |

KPI accent colors (for big-number displays):

| Status | Light | Dark |
|--------|-------|------|
| Success | `text-green-600` | `text-green-500` |
| Warning | `text-yellow-600` | `text-yellow-500` |
| Error | `text-red-600` | `text-red-500` |
| Info | `text-blue-600` | `text-blue-500` |

### 5.2 Trust Tier Mapping

Trust tiers are a core domain concept in TheStudio. They have dedicated colors
that must not be reused for other purposes.

| Tier | Color | Light | Dark | Usage |
|------|-------|-------|------|-------|
| EXECUTE | Purple | `bg-purple-100 text-purple-800` | `purple-500/20` / `purple-500` | Badges, tier selectors, autonomy dials |
| SUGGEST | Blue | `bg-blue-100 text-blue-800` | `blue-500/20` / `blue-500` | Badges, mode indicators |
| OBSERVE | Gray | `bg-gray-100 text-gray-700` | `gray-800` / `gray-400` | Badges, default state |

### 5.3 Role Mapping

| Role | Color | Light | Dark |
|------|-------|-------|------|
| ADMIN | Red | `bg-red-100 text-red-800` | `red-500/20` / `red-500` |
| OPERATOR | Yellow | `bg-yellow-100 text-yellow-800` | `yellow-500/20` / `yellow-500` |
| Other / fallback | Blue | `bg-blue-100 text-blue-800` | `blue-500/20` / `blue-500` |

### 5.4 Interactive Colors

| Element | Light | Dark |
|---------|-------|------|
| Primary action | `bg-blue-600 text-white hover:bg-blue-700` | `bg-blue-500 text-white hover:bg-blue-600` |
| Secondary action | `bg-gray-600 text-white hover:bg-gray-700` | `bg-gray-500 text-white hover:bg-gray-600` |
| Destructive action | `bg-red-600 text-white hover:bg-red-700` | `bg-red-500 text-white hover:bg-red-600` |
| Ghost action | `text-gray-600 hover:bg-gray-100` | `text-gray-400 hover:bg-gray-800` |
| Link | `text-blue-600 hover:underline` | `text-blue-400 hover:underline` |

### 5.5 Color Accessibility Rules

1. Every color pairing must meet WCAG 2.2 AA contrast (4.5:1 for normal text,
   3:1 for large text and UI components).
2. Never use color as the sole indicator of state. Always pair with text,
   icon, or shape.
3. Status badge text (OK, FAILED, STUCK, etc.) must remain readable without
   the background color.

---

## 6. Typography Scale

### 6.1 Font Stack

```css
--font-sans: 'Inter', ui-sans-serif, system-ui, -apple-system,
  BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
--font-mono: 'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, Monaco,
  Consolas, 'Liberation Mono', 'Courier New', monospace;
```

Use `--font-sans` for all body, navigation, and UI text. Use `--font-mono` for
code, IDs, hashes, commit SHAs, API paths, and machine-readable values.

### 6.2 Type Scale

| Role | Size | Weight | Line height | Tracking | Element |
|------|------|--------|-------------|----------|---------|
| Page title | 20px (1.25rem) | 600 (semibold) | 1.4 | normal | `h1` |
| Section title | 16px (1rem) | 600 (semibold) | 1.5 | normal | `h2` |
| Subsection title | 14px (0.875rem) | 600 (semibold) | 1.5 | normal | `h3` |
| Label / overline | 12px (0.75rem) | 600 (semibold) | 1.5 | 0.05em | `label`, `th` |
| Body | 14px (0.875rem) | 400 (regular) | 1.5 | normal | `p`, `td` |
| Caption / metadata | 12px (0.75rem) | 400 (regular) | 1.5 | normal | `small` |
| KPI number | 24-30px (1.5-1.875rem) | 700 (bold) | 1.2 | -0.01em | `data` |
| Code inline | 13px (0.8125rem) | 400 (regular) | 1.5 | normal | `code` |

### 6.3 Tailwind Mapping

```
Page title:      text-xl font-semibold
Section title:   text-base font-semibold
Subsection:      text-sm font-semibold
Label/overline:  text-xs font-semibold uppercase tracking-wide
Body:            text-sm
Caption:         text-xs text-secondary
KPI:             text-2xl font-bold  |  text-3xl font-bold
Code:            font-mono text-[13px]
```

### 6.4 Typography Rules

1. Headings use `--color-text-primary`. Metadata uses `--color-text-secondary`
   or `--color-text-tertiary`.
2. Overline labels (table headers, section labels) are uppercase with wide
   tracking.
3. Body text never goes below 12px. Interactive labels never go below 12px.
4. Maximum reading width for prose: 65ch.

---

## 7. Spacing and Density

### 7.1 Base Unit

All spacing derives from a **4px base unit**. Valid spacing values:

```
4px  (0.25rem)  --space-1
8px  (0.5rem)   --space-2
12px (0.75rem)  --space-3
16px (1rem)     --space-4
20px (1.25rem)  --space-5
24px (1.5rem)   --space-6
32px (2rem)     --space-8
40px (2.5rem)   --space-10
48px (3rem)     --space-12
64px (4rem)     --space-16
```

### 7.2 Density Modes

Three density modes cover the range of TheStudio use cases.

| Mode | Row height | Cell padding | Gap | Use case |
|------|-----------|--------------|-----|----------|
| Compact | 32px | `py-1 px-2` | `gap-2` | Data tables, activity logs, event feeds |
| Comfortable (default) | 40px | `py-2 px-4` | `gap-4` | Standard views, forms, cards |
| Spacious | 48px+ | `py-3 px-6` | `gap-6` | Setup wizards, onboarding, landing views |

### 7.3 Layout Spacing

| Context | Value |
|---------|-------|
| Page padding (main area) | `p-6` (24px) |
| Section gap | `gap-6` (24px) |
| Card padding | `p-4` (16px) or `p-6` (24px) |
| Card internal gap | `gap-4` (16px) |
| Sidebar item padding | `px-3 py-2` |
| Header bar padding | `px-6 py-4` |

---

## 8. Layout and Navigation

### 8.1 App Shell Pattern

Every surface uses the app shell: a persistent sidebar for primary navigation
alongside a scrollable main content area.

```
+--[ Sidebar ]--+--[ Header bar ]---------------------------+
|               |  Breadcrumb / Context   Actions  User     |
|  Logo         +--------------------------------------------+
|               |                                            |
|  Nav items    |  Main content area                         |
|  (vertical)   |  (scrollable, responsive)                  |
|               |                                            |
|  ...          |                                            |
|               |                                            |
|  Settings     |                                            |
|  Help         |                                            |
+---------------+--------------------------------------------+
```

### 8.2 Sidebar

The sidebar is the primary navigation element on every surface.

| Property | Value |
|----------|-------|
| Width (expanded) | 224px (`w-56`) |
| Width (collapsed) | 56px |
| Background | `--sidebar-bg` (dark in both themes) |
| Text | `--sidebar-text` (light in both themes) |
| Active item | `bg-gray-800 text-white` |
| Hover item | `hover:bg-gray-800` |
| Unselected text | `text-gray-300` |
| Collapsible | Yes, via toggle or keyboard shortcut |

Navigation items use icon + label format. Icons are text symbols, Lucide, or
Heroicons (consistent set per surface). The sidebar includes cross-app links
(Admin Console links to Pipeline Dashboard and vice versa), visually
distinguished with an indigo background (`bg-indigo-800`).

### 8.3 Header Bar

The header bar sits above the main content area and provides contextual
information and actions.

| Property | Value |
|----------|-------|
| Height | 56px (`h-14`) |
| Background | `--header-bg` / `bg-white` (light), `bg-gray-900` (dark) |
| Border | Bottom border: `border-b border-gray-200` / `border-gray-700` |
| Left | Breadcrumb or current context (surface name, active tab) |
| Center | Optional: search / filter bar |
| Right | Actions, notification bell, user menu, app switcher |

### 8.4 Secondary Navigation

Horizontal tabs, segmented controls, and filter bars are secondary navigation
**within** the main content area. They sit below the header bar and above the
content. They do not replace the sidebar.

```html
<!-- Secondary tab bar inside main content -->
<nav role="tablist" aria-label="Pipeline views" class="flex border-b border-gray-200">
  <button role="tab" aria-selected="true" class="px-4 py-2 text-sm font-medium
    border-b-2 border-blue-600 text-blue-600">Pipeline</button>
  <button role="tab" aria-selected="false" class="px-4 py-2 text-sm font-medium
    text-gray-500 hover:text-gray-700">Triage</button>
</nav>
```

### 8.5 Content Area

| Property | Value |
|----------|-------|
| Background | `--color-bg-primary` |
| Padding | `p-6` |
| Max width | `max-w-7xl` (1280px) for prose-heavy pages; full width for dashboards |
| Grid | CSS Grid or Flexbox; 12-column grid for complex layouts |

### 8.6 Responsive Behavior

| Breakpoint | Shell behavior |
|------------|---------------|
| >= 1280px (xl) | Sidebar expanded + full content |
| >= 768px (md) | Sidebar collapsed (icons only) + full content |
| < 768px (sm) | Sidebar hidden, hamburger toggle, content full-width |

Mobile is read-only at minimum. Critical workflows (status checks, approvals,
triage actions) must remain functional on tablet.

---

## 9. Component Recipes

All component recipes include light and dark variants. Dark variants are
achieved through the semantic token system; classes below show the light-theme
Tailwind utilities. Dark equivalents resolve automatically when
`[data-theme="dark"]` is set on a parent element.

### 9.1 Cards

The primary content container across all surfaces.

```html
<div class="bg-white rounded-lg border border-gray-200 p-4">
  <!-- Card content -->
</div>

<!-- Dark variant (via tokens or explicit) -->
<div class="bg-gray-900 rounded-lg border border-gray-700 p-4">
  <!-- Card content -->
</div>
```

| Property | Light | Dark |
|----------|-------|------|
| Background | `bg-white` | `bg-gray-900` |
| Border | `border-gray-200` | `border-gray-700` |
| Radius | `rounded-lg` (8px) | `rounded-lg` |
| Padding | `p-4` (compact) or `p-6` (comfortable) | Same |
| Shadow | None by default; `shadow-sm` for elevated cards | `shadow-none` |

### 9.2 Tables

```html
<div class="bg-white rounded-lg border border-gray-200 overflow-hidden">
  <table class="w-full text-sm">
    <thead>
      <tr class="bg-gray-50 text-xs font-semibold text-gray-500 uppercase tracking-wide">
        <th scope="col" class="px-4 py-2 text-left">Name</th>
        <th scope="col" class="px-4 py-2 text-right">Count</th>
      </tr>
    </thead>
    <tbody class="divide-y divide-gray-100">
      <tr class="hover:bg-gray-50">
        <td class="px-4 py-2">Row data</td>
        <td class="px-4 py-2 text-right font-mono">42</td>
      </tr>
    </tbody>
  </table>
</div>
```

| Property | Light | Dark |
|----------|-------|------|
| Header bg | `bg-gray-50` | `bg-gray-800` |
| Header text | `text-gray-500` | `text-gray-400` |
| Row divider | `divide-gray-100` | `divide-gray-800` |
| Row hover | `hover:bg-gray-50` | `hover:bg-gray-800` |
| Numeric columns | Right-aligned, `font-mono` | Same |

All `<th>` elements must include `scope="col"` or `scope="row"` for screen
reader compliance.

### 9.3 Badges

Compact pills for status, role, and category indicators.

```html
<span class="inline-block px-2 py-0.5 rounded text-xs font-semibold
  bg-green-100 text-green-800">OK</span>

<!-- Dark variant -->
<span class="inline-block px-2 py-0.5 rounded text-xs font-semibold
  bg-green-500/20 text-green-500">OK</span>
```

Badge text should be short. Use uppercase for operational status (OK, FAILED,
STUCK, RUNNING). Use sentence case for descriptive labels.

### 9.4 Buttons

| Variant | Light | Dark |
|---------|-------|------|
| Primary | `bg-blue-600 text-white hover:bg-blue-700 focus-visible:ring-2` | `bg-blue-500 text-white hover:bg-blue-600` |
| Secondary | `bg-gray-600 text-white hover:bg-gray-700` | `bg-gray-500 text-white hover:bg-gray-600` |
| Destructive | `bg-red-600 text-white hover:bg-red-700` | `bg-red-500 text-white hover:bg-red-600` |
| Ghost | `text-gray-600 hover:bg-gray-100` | `text-gray-400 hover:bg-gray-800` |
| Icon-only | Same as ghost + `p-2 rounded` | Same |

All buttons: `rounded-md px-3 py-2 text-sm font-medium`. Minimum touch target:
24x24px (32px recommended). Labels are verb-first ("Save changes", "Import
issue", "Delete workflow").

### 9.5 Links

```html
<a href="..." class="text-blue-600 hover:underline focus-visible:ring-2
  focus-visible:ring-blue-600 focus-visible:ring-offset-2 rounded">
  View pipeline
</a>
```

External links include a subtle external-link icon and `target="_blank"
rel="noopener noreferrer"`.

### 9.6 Modals and Dialogs

```html
<div role="dialog" aria-modal="true" aria-labelledby="modal-title"
  class="fixed inset-0 z-50 flex items-center justify-center">
  <!-- Backdrop -->
  <div class="absolute inset-0 bg-black/50" aria-hidden="true"></div>
  <!-- Panel -->
  <div class="relative bg-white rounded-lg shadow-xl max-w-lg w-full mx-4 p-6">
    <h2 id="modal-title" class="text-lg font-semibold">Title</h2>
    <!-- Content -->
    <div class="mt-4 flex justify-end gap-3">
      <button class="...secondary...">Cancel</button>
      <button class="...primary...">Confirm</button>
    </div>
  </div>
</div>
```

Requirements:
- `role="dialog"` and `aria-modal="true"` on the container.
- `aria-labelledby` pointing to the title element.
- Focus trapped inside the dialog while open (use `useFocusTrap` hook).
- `Escape` key closes the dialog.
- Focus returns to the trigger element on close.
- Backdrop click closes (unless the dialog requires explicit action).
- Dark variant: `bg-gray-900 border border-gray-700`.

### 9.7 Dropdowns and Menus

```html
<div class="relative">
  <button aria-haspopup="true" aria-expanded="false">Menu</button>
  <div role="menu" class="absolute right-0 mt-1 w-48 bg-white rounded-md
    shadow-lg border border-gray-200 py-1 z-50">
    <button role="menuitem" class="w-full text-left px-3 py-2 text-sm
      hover:bg-gray-100">Action</button>
  </div>
</div>
```

Requirements:
- `aria-haspopup` and `aria-expanded` on trigger.
- `role="menu"` on the list, `role="menuitem"` on items.
- Arrow key navigation within the menu.
- `Escape` closes, focus returns to trigger.

### 9.8 Form Inputs

```html
<label for="repo-name" class="block text-sm font-medium text-gray-700">
  Repository name
</label>
<input id="repo-name" type="text"
  class="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2
  text-sm shadow-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
  aria-describedby="repo-name-help" />
<p id="repo-name-help" class="mt-1 text-xs text-gray-500">
  Format: owner/repo
</p>
```

| Property | Light | Dark |
|----------|-------|------|
| Border | `border-gray-300` | `border-gray-600` |
| Background | `bg-white` | `bg-gray-800` |
| Text | `text-gray-900` | `text-gray-100` |
| Focus | `focus:border-blue-500 focus:ring-blue-500` | Same |
| Error | `border-red-500` + error message below | Same |

Every input must have an associated `<label>`. Use `aria-describedby` for help
text and error messages. Password fields must support password managers (no
`autocomplete="off"` on credential fields).

### 9.9 Alerts and Toasts

```html
<!-- Persistent alert -->
<div role="alert" class="rounded-md bg-red-50 border border-red-200 p-4">
  <p class="text-sm font-medium text-red-800">
    Pipeline failed: lint check returned 3 errors.
  </p>
  <p class="mt-1 text-sm text-red-700">
    Review the errors in the gate inspector, then re-trigger the pipeline.
  </p>
</div>

<!-- Toast (auto-dismiss) -->
<div role="status" aria-live="polite"
  class="fixed bottom-4 right-4 bg-white rounded-lg shadow-lg border
  border-gray-200 p-4 max-w-sm z-50">
  <p class="text-sm font-medium text-green-800">Settings saved.</p>
</div>
```

| Variant | Light bg | Light border | Light text |
|---------|----------|--------------|------------|
| Error | `bg-red-50` | `border-red-200` | `text-red-800` |
| Warning | `bg-yellow-50` | `border-yellow-200` | `text-yellow-800` |
| Success | `bg-green-50` | `border-green-200` | `text-green-800` |
| Info | `bg-blue-50` | `border-blue-200` | `text-blue-800` |

Toasts auto-dismiss after 5 seconds. Success confirmations auto-dismiss after
3 seconds. Errors persist until dismissed. Toasts use `role="status"` and
`aria-live="polite"`.

### 9.10 Loading States

Prefer **skeleton screens** over spinners for content areas. Use spinners only
for isolated actions (button loading state, inline refresh).

```html
<!-- Skeleton line -->
<div class="animate-pulse bg-gray-200 rounded h-4 w-3/4"></div>

<!-- Skeleton card -->
<div class="animate-pulse bg-gray-200 rounded-lg h-32 w-full"></div>

<!-- Button loading -->
<button disabled class="...primary... opacity-75">
  <svg class="animate-spin h-4 w-4 mr-2 inline" ...></svg>
  Saving...
</button>
```

Dark skeleton: `bg-gray-700` instead of `bg-gray-200`. Reduced motion: replace
`animate-pulse` with static gray fill (see Section 12).

### 9.11 Empty States

Every empty collection, table, or view uses the shared empty state pattern.

```html
<div class="flex flex-col items-center justify-center py-12 text-center">
  <div class="text-gray-400 mb-4"><!-- Icon or illustration --></div>
  <h3 class="text-sm font-semibold text-gray-900">No repositories registered</h3>
  <p class="mt-1 text-sm text-gray-500">
    Register a repository to start processing issues.
  </p>
  <button class="mt-4 ...primary...">Register repository</button>
</div>
```

Requirements:
- Heading states what is missing.
- Description explains why or what to do.
- Primary CTA provides the next action.
- Optional secondary link for alternative path.

### 9.12 Error States

Every error state communicates three things:
1. **What happened** (concise description).
2. **Why** (cause if known, or "unexpected" if not).
3. **What to do** (specific action: retry, check settings, contact support).

```html
<div role="alert" class="flex flex-col items-center py-12 text-center">
  <div class="text-red-400 mb-4"><!-- Error icon --></div>
  <h3 class="text-sm font-semibold text-gray-900">Failed to load pipeline data</h3>
  <p class="mt-1 text-sm text-gray-500">
    The API returned a 503 error. The service may be restarting.
  </p>
  <button class="mt-4 ...primary..." onclick="location.reload()">Retry</button>
</div>
```

### 9.13 Icon System

All UI icons use inline SVG with `currentColor` for color inheritance. Never use
icon fonts, `<img>` embeds, or hardcoded fill/stroke colors.

**Library assignment (never mix libraries on the same surface):**

| Surface | Library | Rationale |
|---------|---------|-----------|
| Admin Console (Jinja2/HTMX) | Heroicons v2 (inline SVG macro) | No build step; consistent 24px grid |
| Pipeline Dashboard (React) | Lucide React (`lucide-react`) | Tree-shakeable; clean TypeScript types |

**Size grid:** Icons render on a fixed optical grid. Using non-standard sizes
(18px, 22px) causes subpixel blurring on non-retina displays.

| Size | Token | Use case |
|------|-------|----------|
| 16px | `h-4 w-4` | Dense/inline indicators, table cells, badges |
| 20px | `h-5 w-5` | UI default — buttons, navigation, form inputs |
| 24px | `h-6 w-6` | Section headers, page titles, empty states |
| 32px | `h-8 w-8` | Hero illustrations, onboarding |

**Variant rule:** Choose one variant per surface and do not mix. Outline (1.5px
stroke) for general UI; Solid (filled) for emphasis and status indicators only.

**Color:** All icons use `stroke="currentColor"` (outline) or
`fill="currentColor"` (solid). This inherits the parent element's text color
and automatically adapts to dark mode via semantic tokens.

**Accessibility rules:**

| Context | Pattern |
|---------|---------|
| Decorative icon alongside text label | `aria-hidden="true"` on `<svg>` |
| Icon-only button | `aria-label` on the `<button>`, `aria-hidden="true"` on `<svg>` |
| Standalone meaningful icon (status) | `role="img"` + `aria-label` on `<svg>` |
| Non-text contrast | Icons conveying state must meet 3:1 against background (SC 1.4.11) |

**Jinja2 macro recipe (Admin Console):**

```html
{%- macro icon(name, size="md", class="") -%}
  {%- set sizes = {"sm": "h-4 w-4", "md": "h-5 w-5", "lg": "h-6 w-6"} -%}
  <svg class="{{ sizes[size] }} {{ class }}" aria-hidden="true" fill="none"
    viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
    {%- if name == "dashboard" -%}
      <path stroke-linecap="round" stroke-linejoin="round"
        d="M3.75 6A2.25 2.25 0 016 3.75h2.25A2.25..." />
    {%- elif name == "close" -%}
      <path stroke-linecap="round" stroke-linejoin="round"
        d="M6 18L18 6M6 6l12 12" />
    {%- endif -%}
  </svg>
{%- endmacro -%}
```

**React recipe:**

```tsx
import { X, Plus, AlertCircle } from 'lucide-react';

// With label — icon is decorative
<button className="inline-flex items-center gap-2 px-3 py-2 text-sm">
  <Plus className="h-4 w-4" aria-hidden="true" />
  Add task
</button>

// Icon-only button
<button aria-label="Close panel" className="p-2 rounded-md">
  <X className="h-5 w-5" aria-hidden="true" />
</button>

// Standalone meaningful icon
<AlertCircle className="h-5 w-5 text-red-600"
  role="img" aria-label="Pipeline failed" />
```

**Anti-patterns:**
- Icon fonts (pseudo-element abuse, breaks high-contrast mode)
- Hardcoded `fill="#374151"` (breaks dark mode and token system)
- `<img src="icon.svg">` (cannot inherit color, CORS issues)
- Mixing outline and solid variants on the same surface
- `aria-label` on the `<svg>` (inconsistent AT support; put it on the `<button>`)
- Sizes outside the grid (18px, 22px — subpixel blur)

### 9.14 Inspector Panel (Sliding Detail View)

The inspector panel is the primary detail-view pattern. It slides in from the
right edge when a list row or card is clicked, preserving the underlying list
context. This pattern replaces full-page navigation for entity inspection.

**Role selection:**

| Use case | ARIA role | Focus behavior |
|----------|-----------|----------------|
| Browsable inspector (click row, view details, click another row) | `role="complementary"` + `aria-label` | No focus trap — user can Tab back to list |
| Action panel (requires input before returning) | `role="dialog"` + `aria-modal="true"` | Full focus trap |

**Specifications:**

| Property | Value | Notes |
|----------|-------|-------|
| Default width | 400px (`w-[400px]`) | Detail view, metadata, audit trail |
| Wide variant | 560px (`w-[560px]`) | Code diffs, evidence review, multi-section forms |
| Position | `fixed right-0 top-0 bottom-0` | Full height, flush right |
| Z-index | `z-40` | Below command palette (z-50+), above content |
| Enter animation | `translateX(100%) → translateX(0)`, 200ms `ease-out` | GPU-accelerated via `transform` |
| Exit animation | `translateX(0) → translateX(100%)`, 150ms `ease-in` | Exit faster than enter |
| Backdrop (dialog variant only) | `bg-black/40`, clickable to dismiss | Not used for complementary panels |
| Keyboard dismiss | `Escape` always closes | Returns focus to trigger element |
| Focus on open | Close button or first focusable element | After transition completes |
| Focus on close | Return to the element that triggered open | Store ref before opening |
| Content loading | Skeleton screen, not spinner | Panel opens immediately; content streams in |
| >= 1280px viewport | Push layout (content area shrinks) | Preferred — avoids obscuring data |
| 768–1279px viewport | Overlay with backdrop | Panel overlaps content |
| < 768px viewport | Full-screen takeover | Mobile fallback |

**Keyboard contract:**

| Key | Behavior |
|-----|----------|
| `Escape` | Close panel, return focus to trigger |
| `Tab` | Navigate within panel (complementary: can also Tab to list) |
| `Shift+Tab` | Navigate backward |

**HTML structure (complementary/inspector):**

```html
<aside
  id="detail-panel"
  role="complementary"
  aria-label="Repository detail"
  aria-hidden="true"
  class="fixed right-0 top-0 bottom-0 w-[400px] bg-white border-l
    border-gray-200 shadow-xl z-40 transform translate-x-full
    transition-transform duration-200 ease-out
    data-[open]:translate-x-0">
  <!-- Sticky header -->
  <div class="sticky top-0 flex items-center justify-between
    px-6 py-4 border-b border-gray-200 bg-white z-10">
    <h2 class="text-base font-semibold text-gray-900">Repository detail</h2>
    <button aria-label="Close detail panel"
      class="p-2 rounded-md text-gray-500 hover:bg-gray-100
        focus-visible:ring-2 focus-visible:ring-blue-600">
      <svg class="h-5 w-5" aria-hidden="true" fill="none" viewBox="0 0 24 24"
        stroke="currentColor" stroke-width="1.5">
        <path stroke-linecap="round" stroke-linejoin="round"
          d="M6 18L18 6M6 6l12 12" />
      </svg>
    </button>
  </div>
  <!-- Scrollable content -->
  <div class="overflow-y-auto h-full pb-20 px-6 py-4">
    <!-- Content or skeleton -->
  </div>
</aside>
```

**Dark mode:** Panel background uses `var(--color-bg-surface)`. Border uses
`var(--color-border-primary)`. All content inside follows semantic tokens.

**Anti-patterns:**
- `role="dialog"` + `aria-modal` for a browsable inspector (traps focus, wrong semantics)
- Animating `right` property (triggers layout recalculation; use `transform`)
- Loading content before panel opens (perceived latency; open with skeleton)
- No `aria-hidden` on closed panel (screen readers discover off-screen content)
- Panel z-index above command palette (palette must always be topmost)

### 9.15 Kanban Board

The kanban board is a column-based view for workflow state visualization. It
serves as an alternative to the table view, toggled by the user. Columns
represent pipeline or workflow states; cards represent individual work items.

**Layout specifications:**

| Property | Value | Notes |
|----------|-------|-------|
| Column width | 280px fixed (`w-[280px]`) | Fixed width, not fluid |
| Column gap | 16px (`gap-4`) | Between columns |
| Column header | 40px height | Status label + count badge |
| Card padding | `p-3` (compact) | Dense operational view |
| Card gap | 8px (`gap-2`) | Within column |
| Card border-radius | `rounded-md` (6px) | Matches card standard |
| Status indicator | 3px colored left border (`border-l-[3px]`) | Never background-fill the whole card |
| Column scroll | `overflow-y-auto max-h-[calc(100vh-12rem)]` | Columns scroll independently |
| Board scroll | `overflow-x-auto` on container | Horizontal scroll for > 4 columns |

**Status border colors:**

| Status | Border class | Token |
|--------|-------------|-------|
| Queued / Pending | `border-l-gray-300` | `--color-status-neutral` |
| In Progress / Running | `border-l-yellow-500` | `--color-status-warning` |
| Blocked / Failed | `border-l-red-500` | `--color-status-error` |
| Review | `border-l-blue-500` | `--color-status-info` |
| Complete / Done | `border-l-green-500` | `--color-status-success` |

**Drag-and-drop:**

| Property | Specification |
|----------|---------------|
| Library (Admin/HTMX) | SortableJS v1.15 with keyboard plugin |
| Library (React) | dnd-kit (`@dnd-kit/core` + `@dnd-kit/sortable`) |
| Drag handle | Explicit grip icon (`GripVertical`, 20x20px) — never make the whole card draggable |
| Drag overlay | Semi-transparent clone at 80% opacity |
| Drop zone highlight | `ring-2 ring-blue-500 bg-blue-50/30` on target column |
| Activation constraint | 8px distance threshold (prevents accidental drags) |

**Keyboard alternative (required — drag-and-drop must not be the only path):**

| Key | Behavior |
|-----|----------|
| `Space` or `Enter` | Pick up focused card |
| Arrow keys | Move card between positions/columns |
| `Space` or `Enter` | Drop card at current position |
| `Escape` | Cancel drag, return to original position |

**Accessibility requirements:**

1. Board container: `role="region"` + `aria-label="Workflow board"`
2. Each column: `role="group"` + `aria-label="[column name] — N tasks"`
3. Drag operations announced via `aria-live="assertive"` region
4. Visually-hidden instruction block referenced by `aria-describedby` on each
   drag handle: "Press Space to pick up. Use arrow keys to move. Press Space
   to drop or Escape to cancel."
5. Cards focusable and activatable (Enter/Space) to open inspector panel
6. Status conveyed by text label AND color (never color alone)
7. Drag overlay has `aria-hidden="true"`
8. Card count in column header has `aria-label="N cards"`

**Column header recipe:**

```html
<div class="flex items-center justify-between px-3 py-2
  border-b border-gray-200 bg-gray-50 rounded-t-md">
  <div class="flex items-center gap-2">
    <span class="h-2 w-2 rounded-full bg-yellow-500" aria-hidden="true"></span>
    <h3 class="text-sm font-semibold text-gray-700">Running</h3>
  </div>
  <span class="inline-flex items-center justify-center h-5 min-w-[1.25rem]
    px-1.5 rounded-full bg-gray-200 text-xs font-semibold text-gray-600"
    aria-label="3 tasks">3</span>
</div>
```

**Card recipe:**

```html
<div class="bg-white rounded-md border border-gray-200 p-3
  border-l-[3px] border-l-yellow-500 hover:shadow-sm transition-shadow"
  role="article" aria-label="Task: Fix auth bug, status: Running">
  <div class="flex items-start gap-2">
    <button aria-label="Reorder task: Fix auth bug"
      aria-describedby="kanban-instructions"
      class="mt-0.5 p-0.5 rounded text-gray-300 hover:text-gray-500
        focus-visible:ring-2 cursor-grab active:cursor-grabbing">
      <svg class="h-4 w-4" aria-hidden="true"><!-- GripVertical --></svg>
    </button>
    <div class="flex-1 min-w-0">
      <p class="text-sm font-medium text-gray-900 truncate">Fix auth bug</p>
      <p class="text-xs text-gray-500 mt-1 font-mono">#TPK-142</p>
    </div>
  </div>
</div>
<p id="kanban-instructions" class="sr-only">
  Press Space or Enter to pick up. Use arrow keys to move between columns.
  Press Space or Enter to drop, or Escape to cancel.
</p>
```

**Dark mode:** Card background uses `var(--color-bg-surface)`. Status border
colors are invariant across themes (already high-contrast). Column header
background uses `var(--color-bg-elevated)`.

**Anti-patterns:**
- Making the whole card the drag target (prevents text selection)
- Coloring the full column background by status (fails at 5+ columns)
- No `activationConstraint` on pointer sensor (every click becomes a drag)
- Re-fetching all columns after every drop (use optimistic update)
- Horizontal scroll without visual affordance (add fade-out on right edge)
- No keyboard alternative to drag-and-drop (WCAG failure)

---

## 10. State Design Rules

Every async operation and every data view has explicit state handling.

### 10.1 Loading

- Every async operation has an explicit loading indicator.
- Layout dimensions are preserved during loading (no layout shift).
- Skeleton screens for content regions; spinners for inline/button actions.
- Loading text is operational: "Loading pipeline data..." not "Please wait...".

### 10.2 Empty

- Every empty collection displays guidance text + CTA.
- Empty copy states what is missing, not what went wrong.
- CTA links to the action that populates the collection.
- Never show a blank area where data should be.

### 10.3 Error

- Every error displays: what happened, why, what to do.
- Errors use `role="alert"` for screen reader announcement.
- Network errors offer a retry action.
- Validation errors appear inline next to the field, not only in a banner.

### 10.4 Success

- Success confirmation is shown, then auto-dismissed (3-5 seconds).
- Use `role="status"` + `aria-live="polite"` for screen reader announcement.
- Success state returns the user to the previous view or updated data.
- Destructive action success confirms what was removed/changed.

---

## 11. Accessibility Standard

WCAG 2.2 AA is the mandatory compliance floor for all surfaces.

### 11.1 Focus Indicators

All interactive elements must have a visible focus indicator.

```css
:focus-visible {
  outline: 2px solid var(--color-focus-ring);
  outline-offset: 2px;
}
```

| Property | Value |
|----------|-------|
| Style | `2px solid` |
| Color | `--color-focus-ring` (blue-600 light, blue-500 dark) |
| Offset | `2px` minimum |
| Shape | Follows border-radius of the element |

Never remove focus outlines globally. Use `:focus-visible` (not `:focus`) to
show outlines only on keyboard navigation.

### 11.2 Touch Targets

| Level | Size | Usage |
|-------|------|-------|
| Minimum (WCAG 2.2) | 24x24px | Inline icons, compact controls |
| Recommended | 44x44px | Primary actions, mobile-facing controls |
| Comfortable | 48x48px | Touch-primary interfaces, wizard steps |

Ensure spacing between adjacent targets prevents accidental activation.

### 11.3 Non-Color Cues

Every use of color to convey information must be paired with at least one
non-color cue:

- Text labels (OK, FAILED, STUCK)
- Icons or shapes
- Position or pattern
- Underlines for links

### 11.4 Keyboard Navigation

1. All interactive elements reachable via Tab.
2. Logical tab order matching visual layout (no `tabindex` > 0).
3. Skip navigation link as the first focusable element on every page.
4. Arrow keys for menu navigation, tab bar navigation, and grid cells.
5. `Escape` closes any overlay (modal, dropdown, tooltip, panel).
6. `Enter` or `Space` activates buttons and links.

### 11.5 Screen Reader Support

1. Use semantic HTML elements (`<nav>`, `<main>`, `<header>`, `<table>`,
   `<button>`, `<dialog>`) as the primary accessibility layer.
2. ARIA roles only when semantic HTML is insufficient.
3. Live regions for dynamic content:
   - `aria-live="polite"` for status updates, toast messages.
   - `aria-live="assertive"` for error alerts requiring immediate attention.
   - `role="status"` for non-critical state changes.
4. All images have `alt` text. Decorative images use `alt=""` and
   `aria-hidden="true"`.
5. Form inputs have associated `<label>` elements (not placeholder-only).
6. Tables use `<th scope="col|row">` for header cells.
7. Landmark regions: `<nav>`, `<main>`, `<aside>` with `aria-label` when
   multiple of the same landmark exist.

### 11.6 Reduced Motion

Respect `prefers-reduced-motion: reduce`:

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
}
```

When reduced motion is active:
- State changes are instant (no animation).
- Skeleton screens show static placeholders (no pulse).
- Loading uses text indicators, not animated spinners.

### 11.7 High Contrast

Support `prefers-contrast: more`:

```css
@media (prefers-contrast: more) {
  :root {
    --color-border-primary: var(--primitive-gray-900);
    --color-text-secondary: var(--primitive-gray-700);
    /* Increase contrast on all semantic boundaries */
  }
}
```

### 11.8 Authentication Accessibility

- Password managers are supported (no `autocomplete="off"` on credential
  fields).
- No CAPTCHAs. Use alternative bot detection.
- Session timeout warnings give 20+ seconds to extend.
- Authentication errors are descriptive: "Incorrect password" not "Login
  failed".

---

## 12. Motion and Animation

### 12.1 Timing

| Category | Duration | Easing | Examples |
|----------|----------|--------|----------|
| Micro-interaction | 150ms | `ease-out` | Button hover, badge appear, tooltip |
| Panel/overlay | 200-300ms | `ease-out` (enter), `ease-in` (exit) | Modal, sidebar, dropdown |
| Page transition | 200ms | `ease-in-out` | Tab switch, route change |
| Loading pulse | 1.5s | `ease-in-out` (loop) | Skeleton screen |

### 12.2 Principles

1. Animation communicates state change, not decoration.
2. No animation blocks user interaction.
3. Exit animations are faster than enter animations.
4. Content is usable before animation completes.
5. Skeleton screens are preferred over spinners for content loading.
6. Use `transform` and `opacity` for GPU-accelerated animations; avoid
   animating `width`, `height`, or `top`/`left`.

### 12.3 Reduced Motion Behavior

When `prefers-reduced-motion: reduce` is active:
- All transitions and animations are instant.
- Skeleton pulse is replaced with static fill.
- Auto-playing motion (spinners, progress bars) uses text fallback.
- Page transitions are instant cuts, not fades or slides.

---

## 13. AI-First Interaction Model

TheStudio is an AI delivery platform. AI interactions are first-class citizens
with dedicated governance, not bolted-on features.

### 13.1 Prompt-First Sequence (Required)

Every AI-assisted flow must follow this five-step sequence. Skipping steps 2-5
is a compliance violation.

```
1. Intent capture     User provides goal, context, constraints
2. Intent preview     System restates planned action, scope, assumptions
3. Mode choice        User selects: observe / suggest / execute
4. Evidence output    Results include provenance, confidence, sources
5. Human decision     User approves, edits, retries, or rejects
```

Each step has a corresponding UI component:

| Step | Component | Required? |
|------|-----------|-----------|
| 1. Intent capture | `PromptObject` form or freeform input | Yes |
| 2. Intent preview | `IntentPreview` card | Yes |
| 3. Mode choice | `ExecutionModeSelector` | Yes |
| 4. Evidence output | `TrustMetadata` + `AuditTimeline` | Yes |
| 5. Human decision | `DecisionControls` (approve/edit/reject) | Yes |

### 13.2 Prompt Object Standard

All prompt-driven actions use a consistent data shape in UI and API payload:

```typescript
interface PromptObject {
  goal: string;             // What outcome the user wants
  context: string;          // Relevant repo/task/environment context
  constraints: string[];    // Non-goals, policy bounds, budget/time limits
  success_criteria: string; // How the user defines acceptable result
  mode: 'observe' | 'suggest' | 'execute';
}
```

UI should expose these fields directly or infer them from context with editable
defaults. The user must always be able to see and modify the full prompt object
before execution.

### 13.3 Trust Signals

Every AI-generated output displays:

| Signal | Implementation | Required? |
|--------|---------------|-----------|
| Confidence | Qualitative indicator (high/medium/low) or percentage | Yes |
| Provenance | Source summary or evidence link | Yes |
| Timestamp | When the AI output was generated | Yes |
| Ownership | "You are responsible for final action" | Yes |
| Model | Which model produced the output | Recommended |
| Cost | Token/cost estimate when significant | Recommended |

Never present AI output as guaranteed fact without verification affordances.

### 13.4 Progressive Autonomy

Trust tiers govern what AI can do without explicit approval:

| Tier | Behavior | UI Pattern |
|------|----------|------------|
| OBSERVE | AI analyzes, human acts | Read-only output, manual action buttons |
| SUGGEST | AI proposes, human approves | Editable suggestions, approve/reject controls |
| EXECUTE | AI acts, human reviews | Action taken, undo/rollback available, notification |

The current tier is always visible in the UI (badge or indicator). Tier
escalation (SUGGEST to EXECUTE) requires explicit user confirmation.

### 13.5 AI Content Labeling

AI-generated or AI-transformed content is labeled with a consistent, subtle
marker:

```html
<span class="inline-flex items-center gap-1 text-xs text-gray-500">
  <svg class="h-3 w-3" aria-hidden="true"><!-- AI icon --></svg>
  <span>AI-generated</span>
</span>
```

Rules:
- The marker is subtle and non-decorative.
- It appears consistently on all AI-generated content.
- It does not use anthropomorphic language ("I think", "I believe").
- It is visually distinct from user-authored content markers.

### 13.6 Friction Points

High-impact actions require explicit confirmation:

| Action | Friction level |
|--------|---------------|
| Publish (PR, deployment) | Confirmation dialog + risk summary |
| Delete (data, config) | Confirmation dialog + type-to-confirm |
| Execute (autonomous AI action) | Preview + explicit approve |
| Compliance-affecting change | Confirmation + audit log entry |
| Bulk operations (>5 items) | Summary of scope + confirmation |

### 13.7 Audit Trail

All AI actions are recorded with:
- What changed (before/after or diff)
- Who initiated (user) and what executed (AI model + tier)
- When (timestamp with timezone)
- Whether the action is reversible (and how to reverse it)

The audit trail is accessible via `AuditTimeline` component and is never
hidden from the user who initiated the action.

---

## 14. 2026 Capability Standards

These capabilities are required on all surfaces unless explicitly noted.

### 14.1 Command Palette

**Required on all surfaces.** Activated via `Ctrl+K` (Windows/Linux) or
`Cmd+K` (macOS).

Capabilities:
- Navigate to any page or entity
- Run common actions (import issue, trigger pipeline, open settings)
- Search entities (repos, tasks, workflows)
- Recent items and history recall
- Keyboard shortcut reference

Commands with side effects show a confirmation summary before execution.
The palette supports fuzzy matching and recency-weighted ranking.

**Specifications:**

| Property | Value | Notes |
|----------|-------|-------|
| Trigger | `Ctrl+K` / `Cmd+K` | Global, works from any focus state |
| Close | `Escape`, backdrop click | Always dismissible |
| Z-index | `z-[60]` | Above all other layers (panels z-40, modals z-50) |
| Backdrop | `bg-black/50`, `fixed inset-0` | Clickable to dismiss, `aria-hidden="true"` |
| Width | `max-w-2xl w-full` (672px) | Centered horizontally, top 20% vertically |
| Max height | `max-h-[60vh]` | Results scroll; input stays visible |
| Input height | 52px | Comfortable typing target |
| Result item height | 40px | Consistent for keyboard scanning |
| Debounce (local) | 80ms | Navigation items, recent history |
| Debounce (remote) | 250ms | API-backed entity search |
| Default state | Last 5 recent items | Shown before user types |
| Animation | Fade + scale, 200ms `ease-out` | `opacity-0 scale-95` → `opacity-100 scale-100` |

**Result categories:** Navigation / Actions / Recent / Search results.
Each category has a header (`role="presentation"`, non-focusable).

**Keyboard navigation:**

| Key | Behavior |
|-----|----------|
| `ArrowDown` / `ArrowUp` | Cycle through results (wraps at boundaries) |
| `Enter` | Activate selected result |
| `Escape` | Close palette, return focus to previous element |

**WAI-ARIA pattern:** Combobox (`role="combobox"` on input) controlling a
listbox (`role="listbox"` with `role="option"` children). The input tracks
`aria-activedescendant` as arrow keys move selection. Category headers use
`role="presentation"`. Empty state uses a disabled option
(`aria-disabled="true"`) — never an empty listbox.

**Anti-patterns:**
- `role="search"` + `role="listitem"` (wrong pattern; combobox + listbox required)
- Debounce > 200ms for local data (feels broken)
- Opening to empty state with no recent items (show suggested actions)
- Z-index below modals (palette becomes inaccessible)
- No `aria-activedescendant` updates (screen readers lose track of selection)

### 14.2 Customizable Views

Users can customize dashboard layouts (widget order, show/hide, density).
Every customizable view includes:
- **Reset to team standard** button (one click restore)
- Semantic rules preserved regardless of layout (status colors, KPI names)
- Customization state persisted in localStorage with fallback to server

### 14.3 Responsive Design

| Breakpoint | Behavior |
|------------|----------|
| Desktop (>=1280px) | Full layout, sidebar expanded |
| Tablet (>=768px) | Sidebar collapsed, content adapted |
| Mobile (<768px) | Sidebar hidden, read-only at minimum |

Desktop is the primary design target. Tablet must be fully functional for
common workflows. Mobile must at minimum support read-only status checks and
approvals.

Progressive density reduction: tables collapse to compact tables, then to
card/list layouts on smaller screens.

### 14.4 Localization Readiness

- Use `Intl` APIs for date, time, number, and currency formatting.
- No hard-coded text widths; allow 40% string expansion for translation.
- Icons and copy are culturally neutral.
- Forms, tables, and prompts remain usable when localized.
- Date/time displays include timezone when operationally relevant.

### 14.5 Collaboration

Where multi-user workflows exist:
- Inline comments and mentions tied to artifacts (tasks, workflows, evidence).
- Comment threads with `CommentThread` component.
- Change history with `ChangeHistory` component.
- Audit: who commented, when, and what decision resulted.

---

## 15. Content and Voice

### 15.1 Tone

Concise, operational, and direct. TheStudio serves operators making decisions
under time pressure. Every word must earn its place.

### 15.2 Writing Rules

| Rule | Example | Not this |
|------|---------|----------|
| Verb-first button labels | "Save changes", "Import issue" | "Changes", "Issue import" |
| Specific error messages | "Repository not found: owner/repo" | "Something went wrong" |
| No anthropomorphic AI copy | "Analysis complete" | "I think the issue is..." |
| Sentence case for UI text | "Pipeline status" | "Pipeline Status" (except proper nouns) |
| Active voice | "Pipeline failed lint check" | "Lint check was failed by pipeline" |
| Present tense for status | "Running", "Failed" | "Has been running", "Was failed" |

### 15.3 Terminology

Use consistent terms across all surfaces:

| Correct term | Not this |
|-------------|----------|
| Pipeline | Workflow (when referring to TheStudio pipeline) |
| Task | Issue (after intake; "issue" is the GitHub source) |
| Trust tier | Permission level, access level |
| Gate | Check, validation (when referring to pipeline gates) |
| Evidence | Proof, output (when referring to pipeline artifacts) |
| Repository | Repo (in labels; "repo" acceptable in compact contexts) |

### 15.4 Error Message Structure

Every user-facing error follows this structure:

```
[What happened]: Brief description of the failure.
[Why]: Cause if known, or "unexpected error" with correlation ID.
[What to do]: Specific next action the user should take.
```

Example:
> **Failed to import issue.** The GitHub API returned a 403 error because
> the installation token lacks the `issues:read` scope. Re-authorize the
> GitHub App with the required permissions.

---

## 16. Onboarding and Guidance

### 16.1 Pattern Selection

| Pattern | Use case | Max size |
|---------|----------|----------|
| Setup wizard | First-run or major reconfiguration | 8-10 steps |
| Help panel | On-demand conceptual and task guidance | Unlimited (searchable) |
| Inline tooltip | Single concept, 1-2 lines | 2 lines / ~80 chars |
| Product tour | Guided walkthrough of a workflow | 5-7 steps |
| Feature spotlight | Version-specific new/changed UI highlights | 1-3 highlights |

### 16.2 Interaction Rules

- Only one primary guidance layer active at a time (wizard, tour, or
  spotlight).
- Every guidance overlay has a clear dismiss path and replay path.
- Guidance never blocks critical emergency controls.
- If target elements are absent (empty state, permissions), guidance skips
  gracefully.

### 16.3 Fatigue Controls

- Tours: 5-7 steps maximum.
- Spotlights: 1-3 highlights per version.
- Auto-launch limited to first-run or significant version change.
- Repeated interruption patterns are prohibited.
- Dismissal is always one action away.

### 16.4 Persistence

- Completion/dismissal state persisted per guidance type and scope.
- Key naming by feature and version (e.g., `tour_pipeline_v2.1`).
- Replay available from Help menu.
- Reset only on explicit trigger (version bump, manual reset, role change).

### 16.5 Accessibility for Guidance

- Full keyboard navigation for all guidance types.
- `Escape` closes current guidance layer.
- Focus trapped in modal/tour contexts.
- Focus returns to invoking element on close.
- Screen-reader-friendly labels and progress context for multi-step guidance.

### 16.6 Measurement

Track outcome metrics, not coverage counts:
- Time-to-first-value
- Wizard step completion / drop-off rates
- Replay / help usage frequency
- Support ticket deflection where measurable

---

## 17. PR Compliance Checklist

Every PR that touches frontend code must satisfy the applicable items below.
Items that do not apply to the change should be marked N/A with justification.

### Shell and Layout
- [ ] Uses app shell pattern (sidebar + header + content area).
- [ ] Sidebar is primary navigation; horizontal elements are secondary only.
- [ ] Content area uses standard padding and max-width constraints.
- [ ] Responsive behavior defined for desktop, tablet, and mobile.

### Tokens and Typography
- [ ] Uses semantic tokens (not raw color values) for theme-sensitive
      properties.
- [ ] Typography follows the type scale (Section 6).
- [ ] Spacing uses 4px-base values (Section 7).

### Color and Status
- [ ] Status colors follow semantic mapping (Section 5.1).
- [ ] Trust tier colors follow mapping (Section 5.2).
- [ ] Color is never the sole indicator of state (non-color cue present).
- [ ] All color pairings meet WCAG 2.2 AA contrast ratios.
- [ ] Light and dark theme variants defined or verified.

### States
- [ ] Loading state has explicit indicator (skeleton or spinner).
- [ ] Empty state has guidance text + CTA.
- [ ] Error state communicates what/why/what-to-do.
- [ ] Success state confirms and auto-dismisses.

### Accessibility
- [ ] Focus indicators visible on all interactive elements (2px solid, 2px
      offset).
- [ ] Touch targets meet 24x24px minimum.
- [ ] Keyboard navigation works (Tab, Escape, Enter/Space, Arrow keys).
- [ ] Semantic HTML used (`button`, `nav`, `main`, `dialog`, `table` with
      `th[scope]`).
- [ ] ARIA attributes correct where used.
- [ ] `prefers-reduced-motion` respected.
- [ ] Screen reader tested (or ARIA review completed).

### AI Features (if applicable)
- [ ] Follows 5-step prompt-first sequence.
- [ ] Trust signals displayed (confidence, provenance, timestamp, ownership).
- [ ] AI-generated content labeled.
- [ ] Friction applied to high-impact actions.
- [ ] Human override available.

### Content and Voice
- [ ] Button labels are verb-first.
- [ ] Error messages follow what/why/what-to-do structure.
- [ ] No anthropomorphic AI copy.
- [ ] Terminology consistent with Section 15.3.

### 2026 Capabilities (if applicable)
- [ ] Command palette integration for new actions.
- [ ] Locale-aware formatting for dates, numbers, currencies.
- [ ] Customizable views include reset-to-team-standard.

### Meta
- [ ] This style guide updated if a new reusable pattern was introduced.

---

## 18. Verification and References

### 18.1 Reference Implementation

The Admin Console (`/admin/ui/*`) is the verified reference implementation.
Key template files:

- `src/admin/templates/base.html` (shell, sidebar, skip-nav, tooltip CSS)
- `src/admin/templates/dashboard.html` (dashboard layout)
- `src/admin/templates/partials/dashboard_content.html` (KPI cards, tables)
- `src/admin/templates/components/status_badge.html` (badge recipes)
- `src/admin/templates/components/empty_state.html` (empty state partial)

### 18.2 Pipeline Dashboard Components

Key React components that implement this guide:

- `frontend/src/App.tsx` (shell, tab navigation, wizard gate)
- `frontend/src/components/HeaderBar.tsx` (header bar, app switcher)
- `frontend/src/components/EmptyState.tsx` (shared empty state)
- `frontend/src/components/ErrorStates.tsx` (error + disconnection)
- `frontend/src/components/CommandPalette.tsx` (command palette)
- `frontend/src/components/ai/` (prompt-first components: PromptObject,
  IntentPreview, ExecutionModeSelector, DecisionControls, TrustMetadata,
  AuditTimeline)
- `frontend/src/hooks/useFocusTrap.ts` (focus trap for modals)

### 18.3 External References

Design system inspirations:

- [Linear](https://linear.app) -- keyboard-first, command palette, dark mode,
  opinionated defaults
- [Stripe](https://stripe.com/docs) -- documentation as product, clean
  hierarchy, actionable error messages
- [Apple Human Interface Guidelines](https://developer.apple.com/design/human-interface-guidelines/) --
  progressive disclosure, consistency, accessibility
- [IBM Carbon for AI](https://carbondesignsystem.com/guidelines/carbon-for-ai/) --
  AI transparency, explainability, trust calibration

Standards:

- [WCAG 2.2](https://www.w3.org/TR/WCAG22/) -- Web Content Accessibility
  Guidelines (AA compliance mandatory)
- [EU Accessibility Act](https://ec.europa.eu/social/main.jsp?catId=1202) --
  enforced June 2025, WCAG 2.2 AA as baseline
- [WAI-ARIA 1.2](https://www.w3.org/TR/wai-aria-1.2/) -- ARIA roles, states,
  and properties

Research:

- [NN/g: Dashboards and preattentive processing](https://www.nngroup.com/articles/dashboards-preattentive/)
- [Google Cloud: UX considerations for generative AI apps](https://cloud.google.com/blog/products/ai-machine-learning/how-to-build-a-genai-application)
- [Microsoft Learn: UX guidance for generative AI applications](https://learn.microsoft.com/en-us/microsoft-cloud/dev/copilot/isv/ux-guidance)
- [shadcn/ui](https://ui.shadcn.com/) -- copy-paste components, Radix
  primitives, Tailwind tokens (2026 dominant pattern)

---

*If implementation diverges from this guide, update this document in the same
PR. This guide governs all surfaces. No exemptions.*
