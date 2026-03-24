/**
 * Spotlight Registry — Epic 50.1
 *
 * Central registry of all feature spotlight entries.  Each entry targets a
 * specific UI element, describes a new feature, and declares the app version
 * in which the feature was introduced.
 *
 * Version comparison
 * ------------------
 * On app mount, SpotlightProvider compares the current VITE_APP_VERSION against
 * the last-seen version stored in localStorage.  Any spotlight whose
 * `sinceVersion` is greater than the last-seen version (and ≤ current) is
 * queued for display.
 *
 * Adding a new spotlight
 * ----------------------
 *   1. Add an entry to SPOTLIGHT_REGISTRY with the version the feature ships in.
 *   2. Add a `data-spotlight="<id>"` attribute to the target DOM element.
 *   3. The SpotlightProvider will automatically show it on next app load after
 *      an upgrade.
 *
 * Spotlight entries for initial features added by Epic 50.3.
 */

// ── Types ──────────────────────────────────────────────────────────────────────

/** Unique identifier for each registered spotlight. */
export type SpotlightId = string

/** Popover side — maps to driver.js Side type. */
export type PopoverSide = 'top' | 'right' | 'bottom' | 'left' | 'over'

/** A single feature spotlight entry. */
export interface SpotlightEntry {
  /** Stable identifier.  Must be unique across all entries. */
  id: SpotlightId
  /**
   * The app version that introduced this feature.
   * Format: semver string e.g. "1.2.0".
   * The spotlight fires when current > lastSeen AND sinceVersion > lastSeen.
   */
  sinceVersion: string
  /** Short title shown in the spotlight popover. */
  title: string
  /** Body text describing the new feature (1-2 sentences). */
  description: string
  /**
   * CSS selector for the target element.
   * Prefer `data-spotlight` attribute selectors: `[data-spotlight="id"]`.
   */
  target: string
  /** Which side of the target the popover appears on. Defaults to "bottom". */
  side?: PopoverSide
  /** Alignment within the side ("start" | "center" | "end"). Defaults to "center". */
  align?: 'start' | 'center' | 'end'
}

// ── Registry ───────────────────────────────────────────────────────────────────

/**
 * All registered spotlights in display order.
 *
 * Each entry corresponds to a `data-spotlight` attribute on a DOM element.
 * Add new entries here; add matching `data-spotlight="<id>"` attributes to
 * the target component.
 *
 * Initial entries (v1.0.0) added by Epic 50.3:
 *   - help-panel  → HelpMenu trigger button
 *   - setup-wizard → Setup Wizard menu item
 *   - api-tab      → API nav tab in App.tsx
 */
export const SPOTLIGHT_REGISTRY: readonly SpotlightEntry[] = [
  {
    id: 'help-panel',
    sinceVersion: '1.0.0',
    title: '📖 Contextual Help Panel',
    description:
      'Click the ? button to open the Help Panel — tab-aware documentation, full-text search, and concept articles are one click away.',
    target: '[data-spotlight="help-panel"]',
    side: 'bottom',
    align: 'end',
  },
  {
    id: 'setup-wizard',
    sinceVersion: '1.0.0',
    title: '🧙 Setup Wizard',
    description:
      'Need to re-run onboarding? Open the Help menu and choose Setup Wizard to register a repo, configure your webhook, and set your trust tier.',
    target: '[data-spotlight="setup-wizard"]',
    side: 'bottom',
    align: 'end',
  },
  {
    id: 'api-tab',
    sinceVersion: '1.0.0',
    title: '🔌 Interactive API Docs',
    description:
      'The API tab embeds the full Scalar reference — browse every endpoint, inspect schemas, and send live requests directly from your browser.',
    target: '[data-spotlight="api-tab"]',
    side: 'bottom',
    align: 'center',
  },
]

// ── Storage keys ──────────────────────────────────────────────────────────────

/** localStorage key storing the last version for which spotlights were shown. */
export const SPOTLIGHT_VERSION_KEY = 'studio:spotlight:last_seen_version'

/** Sentinel stored when the user explicitly dismisses all spotlights. */
export const SPOTLIGHT_DISMISSED_KEY = 'studio:spotlight:dismissed_at'

// ── Version comparison ────────────────────────────────────────────────────────

/**
 * Parse a semver string into a numeric triple `[major, minor, patch]`.
 *
 * Handles strings like "1.2.3", "1.2.3-beta.1" (pre-release stripped),
 * and the Vite dev fallback "0.0.0".  Returns [0, 0, 0] for unrecognised input.
 */
export function parseSemver(version: string): [number, number, number] {
  const cleaned = version.split('-')[0] // strip pre-release suffix
  const parts = cleaned.split('.').map(Number)
  const [major = 0, minor = 0, patch = 0] = parts
  if ([major, minor, patch].some(isNaN)) return [0, 0, 0]
  return [major, minor, patch]
}

/**
 * Returns `true` when `a` is strictly greater than `b`.
 *
 * @example
 *   isVersionGreater("1.3.0", "1.2.9") // true
 *   isVersionGreater("1.2.0", "1.2.0") // false
 *   isVersionGreater("1.2.0", "1.3.0") // false
 */
export function isVersionGreater(a: string, b: string): boolean {
  const [aMaj, aMin, aPat] = parseSemver(a)
  const [bMaj, bMin, bPat] = parseSemver(b)
  if (aMaj !== bMaj) return aMaj > bMaj
  if (aMin !== bMin) return aMin > bMin
  return aPat > bPat
}

/**
 * Returns `true` when `a` equals `b` (semver comparison, ignores pre-release).
 */
export function isVersionEqual(a: string, b: string): boolean {
  const [aMaj, aMin, aPat] = parseSemver(a)
  const [bMaj, bMin, bPat] = parseSemver(b)
  return aMaj === bMaj && aMin === bMin && aPat === bPat
}

// ── Pending spotlight logic ────────────────────────────────────────────────────

/**
 * Returns spotlights that should be shown for an upgrade from
 * `lastSeenVersion` to `currentVersion`.
 *
 * A spotlight is pending when:
 *   - Its `sinceVersion` is greater than `lastSeenVersion` (user hasn't seen it)
 *   - Its `sinceVersion` is ≤ `currentVersion` (the feature actually ships now)
 *
 * When `lastSeenVersion` is null (first install), all spotlights whose
 * `sinceVersion` ≤ `currentVersion` are returned.
 *
 * When `currentVersion` equals `lastSeenVersion`, returns an empty array.
 */
export function getPendingSpotlights(
  currentVersion: string,
  lastSeenVersion: string | null,
): SpotlightEntry[] {
  // No upgrade if versions match
  if (lastSeenVersion !== null && isVersionEqual(currentVersion, lastSeenVersion)) {
    return []
  }

  return SPOTLIGHT_REGISTRY.filter((entry) => {
    // Feature must exist in the current version
    if (isVersionGreater(entry.sinceVersion, currentVersion)) return false
    // Feature must be new since the last-seen version
    if (lastSeenVersion === null) return true
    return isVersionGreater(entry.sinceVersion, lastSeenVersion)
  })
}

// ── localStorage helpers ──────────────────────────────────────────────────────

/** Reads the last-seen version from localStorage.  Returns null if not set. */
export function getLastSeenVersion(): string | null {
  try {
    return localStorage.getItem(SPOTLIGHT_VERSION_KEY)
  } catch {
    return null
  }
}

/** Persists the current version as last-seen so spotlights won't re-fire. */
export function markVersionSeen(version: string): void {
  try {
    localStorage.setItem(SPOTLIGHT_VERSION_KEY, version)
  } catch {
    // Silently ignore quota or security errors
  }
}

/** Records a dismissal timestamp (ISO string) for analytics / debugging. */
export function recordDismissal(): void {
  try {
    localStorage.setItem(SPOTLIGHT_DISMISSED_KEY, new Date().toISOString())
  } catch {
    // Silently ignore
  }
}

/**
 * Resets spotlight history — clears both last-seen version and dismissal record.
 * Useful in development and for "re-run spotlights" debug menu item.
 */
export function resetSpotlightHistory(): void {
  try {
    localStorage.removeItem(SPOTLIGHT_VERSION_KEY)
    localStorage.removeItem(SPOTLIGHT_DISMISSED_KEY)
  } catch {
    // Silently ignore
  }
}
