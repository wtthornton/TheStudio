/**
 * TourProvider — Epic 47.1
 *
 * Wraps the app with a react-joyride v3 guided-tour context.
 * Dark tooltip styles match TheStudio's gray-900 palette.
 *
 * Usage
 * -----
 *   // Wrap your app:
 *   <TourProvider>
 *     <App />
 *   </TourProvider>
 *
 *   // Start a tour from any child:
 *   const { startTour, stopTour } = useTour()
 *   startTour('pipeline', steps)
 *
 * Extended by Epic 47.2 (registry + useTourState) and 47.3-47.7 (per-tour steps).
 */

import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import {
  Joyride,
  STATUS,
  type EventData,
  type Controls,
  type Step,
  type Styles,
  type PartialDeep,
} from 'react-joyride'

// ── Dark theme styles ──────────────────────────────────────────────────────────

/**
 * Custom Joyride styles that apply TheStudio's dark palette.
 *
 * Color palette:
 *   Background  gray-900  #111827
 *   Border      gray-700  #374151
 *   Muted text  gray-400  #9ca3af
 *   Body text   gray-300  #d1d5db
 *   Title text  gray-100  #f3f4f6
 *   Accent      indigo-500 #6366f1
 */
const DARK_STYLES: PartialDeep<Styles> = {
  tooltip: {
    borderRadius: '0.5rem',
    border: '1px solid #374151',
    boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.8)',
    padding: '1rem',
    fontSize: '0.875rem',
    maxWidth: '360px',
    backgroundColor: '#111827',
  },
  tooltipContainer: {
    textAlign: 'left',
  },
  tooltipTitle: {
    color: '#f3f4f6',
    fontSize: '0.9375rem',
    fontWeight: 600,
    marginBottom: '0.5rem',
  },
  tooltipContent: {
    color: '#d1d5db',
    lineHeight: '1.6',
    padding: '0.25rem 0',
  },
  tooltipFooter: {
    marginTop: '0.75rem',
    gap: '0.5rem',
  },
  buttonPrimary: {
    backgroundColor: '#6366f1',
    borderRadius: '0.375rem',
    color: '#ffffff',
    fontSize: '0.875rem',
    fontWeight: '500',
    padding: '0.375rem 0.875rem',
  },
  buttonBack: {
    color: '#9ca3af',
    fontSize: '0.875rem',
    marginRight: '0.25rem',
  },
  buttonSkip: {
    color: '#6b7280',
    fontSize: '0.8125rem',
  },
  buttonClose: {
    color: '#6b7280',
    height: '1rem',
    width: '1rem',
    top: '0.75rem',
    right: '0.75rem',
  },
  beacon: {
    borderRadius: '50%',
  },
  beaconInner: {
    backgroundColor: '#6366f1',
  },
  beaconOuter: {
    backgroundColor: 'rgba(99, 102, 241, 0.2)',
    borderColor: '#6366f1',
  },
  overlay: {
    backgroundColor: 'rgba(0, 0, 0, 0.65)',
  },
}

// ── Joyride default options ────────────────────────────────────────────────────

/**
 * Options applied to every step by default.
 * Individual step definitions can override any of these.
 */
const JOYRIDE_OPTIONS = {
  /** Show 1 of N progress in the tooltip. */
  showProgress: true,
  /** Show Back + Skip + primary (Next/Finish) buttons. */
  buttons: ['back', 'skip', 'primary'] as Array<'back' | 'close' | 'primary' | 'skip'>,
  /** Primary button and beacon accent color. */
  primaryColor: '#6366f1',
  /** Tooltip background. */
  backgroundColor: '#111827',
  /** Overlay backdrop color. */
  overlayColor: 'rgba(0, 0, 0, 0.65)',
  /** Text color. */
  textColor: '#d1d5db',
  /** Arrow fill to match tooltip background. */
  arrowColor: '#111827',
}

// ── Context ────────────────────────────────────────────────────────────────────

export interface TourContextValue {
  /** Start a named tour with the given steps. Replaces any active tour. */
  startTour: (tourId: string, steps: Step[]) => void
  /** Stop the currently active tour. */
  stopTour: () => void
  /** ID of the currently running tour, or null if no tour is active. */
  activeTourId: string | null
  /** Whether a tour is currently running. */
  isRunning: boolean
}

const TourContext = createContext<TourContextValue | null>(null)

// ── Provider ───────────────────────────────────────────────────────────────────

export interface TourProviderProps {
  children: ReactNode
}

/**
 * TourProvider mounts a single Joyride instance and exposes `startTour` /
 * `stopTour` via context so any descendant can trigger a tour without prop
 * drilling.
 *
 * All tours share dark-theme tooltip styles and the default options above.
 * Individual tours pass their own `Step[]` array to `startTour`.
 */
export function TourProvider({ children }: TourProviderProps) {
  const [activeTourId, setActiveTourId] = useState<string | null>(null)
  const [steps, setSteps] = useState<Step[]>([])
  const [isRunning, setIsRunning] = useState(false)

  const startTour = useCallback((tourId: string, tourSteps: Step[]) => {
    // Reset then start so Joyride always begins at step 0
    setIsRunning(false)
    setActiveTourId(tourId)
    setSteps(tourSteps)
    // Use a microtask to let Joyride reset before re-enabling
    Promise.resolve().then(() => setIsRunning(true))
  }, [])

  const stopTour = useCallback(() => {
    setIsRunning(false)
    setActiveTourId(null)
    setSteps([])
  }, [])

  const handleEvent = useCallback(
    (data: EventData, _controls: Controls) => {
      const { status } = data
      if (status === STATUS.FINISHED || status === STATUS.SKIPPED) {
        stopTour()
      }
    },
    [stopTour],
  )

  const contextValue = useMemo<TourContextValue>(
    () => ({ startTour, stopTour, activeTourId, isRunning }),
    [startTour, stopTour, activeTourId, isRunning],
  )

  return (
    <TourContext.Provider value={contextValue}>
      <Joyride
        steps={steps}
        run={isRunning}
        continuous
        scrollToFirstStep
        onEvent={handleEvent}
        options={JOYRIDE_OPTIONS}
        styles={DARK_STYLES}
        locale={{
          back: 'Back',
          close: 'Close',
          last: 'Finish',
          next: 'Next →',
          skip: 'Skip tour',
        }}
      />
      {children}
    </TourContext.Provider>
  )
}

// ── Hook ───────────────────────────────────────────────────────────────────────

/**
 * useTour — access the tour context from any descendant of TourProvider.
 *
 * @throws if used outside a TourProvider tree.
 */
export function useTour(): TourContextValue {
  const ctx = useContext(TourContext)
  if (!ctx) {
    throw new Error('useTour must be used inside a <TourProvider>')
  }
  return ctx
}
