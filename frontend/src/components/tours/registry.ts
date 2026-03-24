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
 *
 * Pipeline tour steps added by Epic 47.3.
 * Triage/Analytics/Repo-Trust steps will be added by Epics 47.5–47.7.
 */

import type { Step } from 'react-joyride'

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

// ── Pipeline Tour Steps (Epic 47.3) ───────────────────────────────────────────

/**
 * Six-step guided tour of the pipeline tab.
 *
 * Targets use `data-tour` attributes added to:
 *   PipelineStatus.tsx  → data-tour="pipeline-rail"
 *   StageNode.tsx       → data-tour="stage-node", data-tour="active-pulse"
 *   GateInspector.tsx   → data-tour="gate-inspector"
 *   ActivityStream.tsx  → data-tour="activity-stream"
 *   Minimap.tsx         → data-tour="minimap"
 */
export const PIPELINE_TOUR_STEPS: Step[] = [
  {
    target: '[data-tour="pipeline-rail"]',
    title: 'The Pipeline Rail',
    content:
      'This 9-stage rail shows the full journey of every GitHub issue — from Intake all the way to a draft PR on GitHub. Each stage runs automatically in sequence.',
    disableBeacon: true,
    placement: 'bottom',
  },
  {
    target: '[data-tour="stage-node"]',
    title: 'Stage Nodes',
    content:
      'Each circle represents one pipeline stage. The ring color indicates health: indigo = active, green = passed, red = failed, gray = idle. The badge shows how many tasks are queued.',
    placement: 'bottom',
  },
  {
    target: '[data-tour="active-pulse"]',
    title: 'Active Pulse',
    content:
      'A pulsing stage has tasks currently in progress. Hover any node to see its average duration, pass rate, and the IDs of tasks currently running through it.',
    placement: 'bottom',
  },
  {
    target: '[data-tour="gate-inspector"]',
    title: 'Gate Inspector',
    content:
      'Every stage transition records pass/fail evidence here. Use the filters to find failures, click a row to inspect individual checks, and trace loopbacks back to their root cause.',
    placement: 'top',
  },
  {
    target: '[data-tour="activity-stream"]',
    title: 'Activity Stream',
    content:
      'Watch the agent work in real time — file reads, edits, test runs, and LLM calls appear as they happen. Filter by type or search for specific content to zero in on what matters.',
    placement: 'top',
  },
  {
    target: '[data-tour="minimap"]',
    title: 'Task Minimap',
    content:
      'The minimap tracks every active TaskPacket across all stages. Click a card to jump to that task, or drag to scroll when many tasks are in flight at once.',
    placement: 'top',
  },
]
