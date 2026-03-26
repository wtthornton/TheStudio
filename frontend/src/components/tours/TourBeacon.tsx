/**
 * TourBeacon — Epic 47.4
 *
 * A small pulsing button that:
 *   - Appears on first visit (when the associated tour has not been completed)
 *   - Starts the tour when clicked
 *   - Hides itself permanently after the tour is marked as completed
 *
 * Usage
 * -----
 *   import { TourBeacon } from './tours/TourBeacon'
 *   import { PIPELINE_TOUR_STEPS } from './tours/registry'
 *
 *   // Inside a tab panel:
 *   <TourBeacon tourId="pipeline" steps={PIPELINE_TOUR_STEPS} label="Pipeline tour" />
 *
 * The beacon is intentionally lightweight — it renders null once isCompleted is
 * true so it adds zero DOM overhead after a tour has been taken.
 */

import type { Step } from 'react-joyride'
import { useTourState } from './useTourState'
import type { TourId } from './registry'

// ── Props ─────────────────────────────────────────────────────────────────────

export interface TourBeaconProps {
  /** Registered tour identifier from registry.ts. */
  tourId: TourId
  /** Step array to pass to Joyride when the user clicks the beacon. */
  steps: Step[]
  /**
   * Human-readable label shown next to the pulsing dot.
   * @default "Take the tour"
   */
  label?: string
  /** Additional Tailwind classes for positioning / margin. */
  className?: string
}

// ── Component ─────────────────────────────────────────────────────────────────

/**
 * TourBeacon
 *
 * Renders a pulsing indigo button that triggers a guided tour.  Disappears
 * once the user has completed (or skipped) the tour and the completion flag
 * is written to localStorage by `useTourState`.
 */
export function TourBeacon({
  tourId,
  steps,
  label = 'Take the tour',
  className = '',
}: TourBeaconProps) {
  const { isCompleted, start } = useTourState(tourId)

  // Hidden permanently after tour completion — zero DOM footprint.
  if (isCompleted) return null

  return (
    <button
      type="button"
      onClick={() => start(steps)}
      className={[
        'relative inline-flex items-center gap-2',
        'rounded-full border border-indigo-500/40 bg-indigo-900/20',
        'px-3 py-1.5 text-xs font-medium text-indigo-300',
        'transition-colors hover:bg-indigo-900/40 hover:text-indigo-200',
        'focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500',
        className,
      ].join(' ')}
      aria-label={`Start guided tour: ${label}`}
      data-testid={`tour-beacon-${tourId}`}
    >
      {/* Pulsing dot */}
      <span className="relative flex h-2 w-2" aria-hidden="true">
        <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-indigo-400 opacity-75" />
        <span className="relative inline-flex h-2 w-2 rounded-full bg-indigo-500" />
      </span>

      {label}
    </button>
  )
}
