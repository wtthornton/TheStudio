/**
 * Tour Registry — Epic 47.2
 *
 * Central registry of all product tours.  Each entry declares the tour's
 * identifier, human-readable label, and the localStorage key used to persist
 * completion state.  Step arrays are injected at runtime by each tour module
 * (47.3 – 47.7) so this file stays import-cycle free.
 *
 * Adding a new tour
 * -----------------
 *   1. Add an entry to TOUR_REGISTRY below.
 *   2. Create your step array in the appropriate component file.
 *   3. Call `useTourState(tourId).start(steps)` from a TourBeacon or menu item.
 */

// ── Types ─────────────────────────────────────────────────────────────────────

/** Unique identifier for each registered tour. */
export type TourId = 'pipeline' | 'triage' | 'analytics' | 'repo-trust'

/** Static metadata for a single tour. */
export interface TourMeta {
  /** Stable string key used in localStorage and analytics. */
  id: TourId
  /** Human-readable name shown in HelpMenu and tour beacons. */
  label: string
  /** Short description shown in the Guided Tours section. */
  description: string
  /** localStorage key that stores whether the tour has been completed. */
  storageKey: string
}

// ── Registry ──────────────────────────────────────────────────────────────────

/**
 * Ordered list of all tours.  The order controls the display order in HelpMenu.
 * Epics 47.3 – 47.7 will populate step definitions; registration here is
 * intentionally step-free.
 */
export const TOUR_REGISTRY: readonly TourMeta[] = [
  {
    id: 'pipeline',
    label: 'Pipeline Overview',
    description: 'Walk through the 9-stage pipeline rail, stage nodes, gates, and activity stream.',
    storageKey: 'studio:tour:pipeline:completed',
  },
  {
    id: 'triage',
    label: 'Triage Queue',
    description: 'Learn how to review incoming issues, accept or reject them, and inspect intent.',
    storageKey: 'studio:tour:triage:completed',
  },
  {
    id: 'analytics',
    label: 'Analytics & Reputation',
    description: 'Explore KPIs, throughput charts, bottleneck detection, and expert reputation.',
    storageKey: 'studio:tour:analytics:completed',
  },
  {
    id: 'repo-trust',
    label: 'Repo & Trust Tiers',
    description: 'Configure repositories, trust tiers, and budget controls.',
    storageKey: 'studio:tour:repo-trust:completed',
  },
] as const

// ── Helpers ───────────────────────────────────────────────────────────────────

/** Look up a tour by id.  Returns undefined if not found. */
export function getTourMeta(id: TourId): TourMeta | undefined {
  return TOUR_REGISTRY.find((t) => t.id === id)
}

/** Returns true if the given localStorage key indicates tour completion. */
export function isTourCompleted(storageKey: string): boolean {
  try {
    return localStorage.getItem(storageKey) === 'true'
  } catch {
    // localStorage may be unavailable in SSR or restricted environments
    return false
  }
}

/** Marks a tour as completed in localStorage. */
export function markTourCompleted(storageKey: string): void {
  try {
    localStorage.setItem(storageKey, 'true')
  } catch {
    // silently ignore quota or security errors
  }
}

/** Clears the completion flag so the tour can be replayed. */
export function resetTourCompletion(storageKey: string): void {
  try {
    localStorage.removeItem(storageKey)
  } catch {
    // silently ignore
  }
}

/** Resets ALL tour completion flags.  Used by "Restart all tours" menu item. */
export function resetAllTours(): void {
  for (const tour of TOUR_REGISTRY) {
    resetTourCompletion(tour.storageKey)
  }
}
