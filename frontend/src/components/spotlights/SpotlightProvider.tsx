/**
 * SpotlightProvider — Epic 50.1
 *
 * Wraps the app with a Driver.js powered feature-spotlight context.
 *
 * On mount it compares the current app version (VITE_APP_VERSION, injected by
 * vite.config.ts in Epic 50.2) against the last-seen version persisted in
 * localStorage.  When a version bump is detected it queues pending spotlights
 * from the registry, then drives them via driver.js popovers.
 *
 * Dark theme CSS is added by Epic 50.4 (frontend/src/index.css).
 * Spotlight entries targeting real UI elements are added by Epic 50.3.
 *
 * Usage
 * -----
 *   // Wrap your app:
 *   <SpotlightProvider>
 *     <App />
 *   </SpotlightProvider>
 *
 *   // Trigger programmatically from any descendant:
 *   const { runSpotlights, resetAndRun } = useSpotlight()
 *   runSpotlights()
 *
 * Version injection
 * -----------------
 *   VITE_APP_VERSION is set by vite.config.ts (Epic 50.2).
 *   Falls back to "0.0.0" in development before 50.2 lands.
 */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  type ReactNode,
} from 'react'
import { driver } from 'driver.js'
import type { Driver } from 'driver.js'
import {
  type SpotlightEntry,
  getPendingSpotlights,
  getLastSeenVersion,
  markVersionSeen,
  recordDismissal,
  resetSpotlightHistory,
} from './registry'

// ── App version ───────────────────────────────────────────────────────────────

/**
 * Current application version, injected at build time by Vite (Epic 50.2).
 * Falls back to "0.0.0" so the provider is inert in development until 50.2 lands.
 */
const APP_VERSION: string =
  (import.meta.env.VITE_APP_VERSION as string | undefined) ?? '0.0.0'

// ── Context ───────────────────────────────────────────────────────────────────

export interface SpotlightContextValue {
  /** Manually trigger pending spotlight tour (re-uses version comparison). */
  runSpotlights: () => void
  /**
   * Reset localStorage history and immediately run all spotlights whose
   * `sinceVersion` ≤ current version.  Useful for dev/debug and re-run menus.
   */
  resetAndRun: () => void
  /** Current app version string (VITE_APP_VERSION or "0.0.0" fallback). */
  appVersion: string
}

const SpotlightContext = createContext<SpotlightContextValue | null>(null)

// ── Driver.js config builder ───────────────────────────────────────────────────

/**
 * Creates a configured driver.js Driver instance from a list of spotlight
 * entries.  Dark-theme styles are applied via the `popoverClass` option which
 * references CSS added by Epic 50.4.
 *
 * @param entries - Spotlight entries to convert to driver steps.
 * @param onDestroyed - Called when the tour finishes or is dismissed.
 */
function buildDriver(entries: SpotlightEntry[], onDestroyed: () => void): Driver {
  return driver({
    animate: true,
    smoothScroll: true,
    allowClose: true,
    overlayColor: 'rgb(0, 0, 0)',
    overlayOpacity: 0.6,
    stagePadding: 8,
    stageRadius: 6,
    showProgress: true,
    showButtons: ['next', 'previous', 'close'],
    progressText: '{{current}} of {{total}}',
    nextBtnText: 'Next →',
    prevBtnText: '← Back',
    doneBtnText: 'Done',
    /** Dark theme CSS class applied to all popovers (defined in Epic 50.4). */
    popoverClass: 'studio-spotlight',
    onDestroyed: onDestroyed,
    steps: entries.map((entry) => ({
      element: entry.target,
      popover: {
        title: entry.title,
        description: entry.description,
        side: entry.side ?? 'bottom',
        align: entry.align ?? 'center',
      },
    })),
  })
}

// ── Provider ───────────────────────────────────────────────────────────────────

export interface SpotlightProviderProps {
  children: ReactNode
  /**
   * Override the app version — useful in tests or Storybook.
   * Defaults to the VITE_APP_VERSION build-time constant.
   */
  version?: string
}

/**
 * SpotlightProvider mounts at the root of the app (alongside TourProvider).
 *
 * On mount it:
 *   1. Reads the last-seen version from localStorage.
 *   2. Computes pending spotlights via `getPendingSpotlights`.
 *   3. Defers the drive by one tick so the DOM is fully rendered.
 *   4. After spotlights complete (or are dismissed), marks the version seen.
 */
export function SpotlightProvider({ children, version }: SpotlightProviderProps) {
  const effectiveVersion = version ?? APP_VERSION
  const driverRef = useRef<Driver | null>(null)

  /** Run spotlights for a given list of entries, then mark version seen. */
  const driveEntries = useCallback(
    (entries: SpotlightEntry[]) => {
      if (entries.length === 0) return

      // Destroy any in-flight instance before starting a new one
      driverRef.current?.destroy()

      const onDestroyed = () => {
        markVersionSeen(effectiveVersion)
        recordDismissal()
        driverRef.current = null
      }

      const driverInstance = buildDriver(entries, onDestroyed)
      driverRef.current = driverInstance

      // Defer to next tick to ensure all target DOM nodes are mounted
      setTimeout(() => {
        driverInstance.drive()
      }, 0)
    },
    [effectiveVersion],
  )

  /** Public: run pending spotlights using version comparison. */
  const runSpotlights = useCallback(() => {
    const lastSeen = getLastSeenVersion()
    const pending = getPendingSpotlights(effectiveVersion, lastSeen)
    driveEntries(pending)
  }, [effectiveVersion, driveEntries])

  /** Public: reset history then run all spotlights ≤ current version. */
  const resetAndRun = useCallback(() => {
    resetSpotlightHistory()
    // After reset lastSeen is null → getPendingSpotlights returns all entries
    const pending = getPendingSpotlights(effectiveVersion, null)
    driveEntries(pending)
  }, [effectiveVersion, driveEntries])

  // Auto-fire on mount when a version upgrade is detected
  useEffect(() => {
    runSpotlights()
    // Cleanup: destroy driver on unmount
    return () => {
      driverRef.current?.destroy()
    }
    // Only run on initial mount — version is stable
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const contextValue = useMemo<SpotlightContextValue>(
    () => ({ runSpotlights, resetAndRun, appVersion: effectiveVersion }),
    [runSpotlights, resetAndRun, effectiveVersion],
  )

  return (
    <SpotlightContext.Provider value={contextValue}>
      {children}
    </SpotlightContext.Provider>
  )
}

// ── Hook ───────────────────────────────────────────────────────────────────────

/**
 * useSpotlight — access the spotlight context from any descendant of
 * SpotlightProvider.
 *
 * @throws if used outside a SpotlightProvider tree.
 */
export function useSpotlight(): SpotlightContextValue {
  const ctx = useContext(SpotlightContext)
  if (!ctx) {
    throw new Error('useSpotlight must be used inside a <SpotlightProvider>')
  }
  return ctx
}
