/**
 * useTourState — Epic 47.2
 *
 * Per-tour hook that wires together:
 *   - localStorage persistence (completed flag)
 *   - TourProvider integration (startTour / stopTour)
 *   - Start / complete / reset lifecycle
 *
 * Usage
 * -----
 *   const { isCompleted, isActive, start, complete, reset } = useTourState('pipeline')
 *
 *   // Start the tour with a step array defined by the caller:
 *   start(PIPELINE_STEPS)
 *
 *   // Replay the tour (clears completion flag then starts):
 *   reset()
 *   start(PIPELINE_STEPS)
 */

import { useCallback, useEffect, useState } from 'react'
import type { Step } from 'react-joyride'
import { useTour } from './TourProvider'
import {
  getTourMeta,
  isTourCompleted,
  markTourCompleted,
  resetTourCompletion,
  type TourId,
} from './registry'

// ── Return type ───────────────────────────────────────────────────────────────

export interface TourState {
  /** True if the user has previously finished or skipped this tour. */
  isCompleted: boolean
  /** True if this tour is the currently running tour. */
  isActive: boolean
  /**
   * Start the tour.  If steps are provided they are passed to TourProvider;
   * if omitted the caller must have already seeded the registry with steps.
   * Clears the completion flag so the tour plays from the beginning.
   */
  start: (steps: Step[]) => void
  /**
   * Mark the tour as completed and stop it.
   * Called automatically when Joyride fires STATUS.FINISHED; can also be
   * called imperatively (e.g., from a "skip" handler).
   */
  complete: () => void
  /**
   * Clear the completion flag so the tour can be replayed.
   * Does NOT start the tour — call `start(steps)` afterward.
   */
  reset: () => void
}

// ── Hook ──────────────────────────────────────────────────────────────────────

/**
 * useTourState
 *
 * @param tourId  Registered tour identifier (see registry.ts).
 * @returns       Lifecycle helpers and state flags for the given tour.
 */
export function useTourState(tourId: TourId): TourState {
  const maybeMeta = getTourMeta(tourId)
  if (!maybeMeta) {
    throw new Error(
      `useTourState: unknown tourId "${tourId}". Register it in registry.ts first.`,
    )
  }
  const meta = maybeMeta

  const { startTour, stopTour, activeTourId } = useTour()

  // ── Completed flag ──────────────────────────────────────────────────────────

  const [isCompleted, setIsCompleted] = useState<boolean>(() =>
    isTourCompleted(meta.storageKey),
  )

  // Keep local state in sync if another tab or component updates localStorage
  useEffect(() => {
    function handleStorage(e: StorageEvent) {
      if (e.key === meta.storageKey) {
        setIsCompleted(e.newValue === 'true')
      }
    }
    window.addEventListener('storage', handleStorage)
    return () => window.removeEventListener('storage', handleStorage)
  }, [meta.storageKey])

  // ── Derived state ───────────────────────────────────────────────────────────

  const isActive = activeTourId === tourId

  // ── Lifecycle callbacks ─────────────────────────────────────────────────────

  const start = useCallback(
    (steps: Step[]) => {
      // Allow replay: clear completion flag before starting
      resetTourCompletion(meta.storageKey)
      setIsCompleted(false)
      startTour(tourId, steps)
    },
    [meta.storageKey, startTour, tourId],
  )

  const complete = useCallback(() => {
    markTourCompleted(meta.storageKey)
    setIsCompleted(true)
    // Only stop the tour if this tour is currently active to avoid
    // interrupting an unrelated tour triggered in parallel.
    if (activeTourId === tourId) {
      stopTour()
    }
  }, [meta.storageKey, activeTourId, tourId, stopTour])

  const reset = useCallback(() => {
    resetTourCompletion(meta.storageKey)
    setIsCompleted(false)
  }, [meta.storageKey])

  return { isCompleted, isActive, start, complete, reset }
}
