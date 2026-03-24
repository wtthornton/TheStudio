/**
 * HelpMenu — dropdown help menu mounted in HeaderBar.
 * Epic 45.2: shared help hub for Epics 44 (Wizard), 45 (Help), 47 (Tours), 48 (API Docs).
 *
 * Items
 * -----
 *  • Help Panel  — opens the slide-in contextual help panel (Epic 45)
 *  • Setup Wizard — re-launches the onboarding wizard (Epic 44)
 *  • Guided Tours — placeholder; extended by Epic 47.8 with 4 tour links
 *  • API Docs     — navigates to the API Reference tab (Epic 48)
 */

import { useState, useRef, useEffect } from 'react'

// ── icon helpers ──────────────────────────────────────────────────────────────

function QuestionMarkIcon({ className }: { className?: string }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      strokeWidth={2}
      aria-hidden="true"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
      />
    </svg>
  )
}

function BookOpenIcon({ className }: { className?: string }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      strokeWidth={2}
      aria-hidden="true"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"
      />
    </svg>
  )
}

function WizardIcon({ className }: { className?: string }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      strokeWidth={2}
      aria-hidden="true"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M9 12l2 2 4-4M7.835 4.697a3.42 3.42 0 001.946-.806 3.42 3.42 0 014.438 0 3.42 3.42 0 001.946.806 3.42 3.42 0 013.138 3.138 3.42 3.42 0 00.806 1.946 3.42 3.42 0 010 4.438 3.42 3.42 0 00-.806 1.946 3.42 3.42 0 01-3.138 3.138 3.42 3.42 0 00-1.946.806 3.42 3.42 0 01-4.438 0 3.42 3.42 0 00-1.946-.806 3.42 3.42 0 01-3.138-3.138 3.42 3.42 0 00-.806-1.946 3.42 3.42 0 010-4.438 3.42 3.42 0 00.806-1.946 3.42 3.42 0 013.138-3.138z"
      />
    </svg>
  )
}

function ToursIcon({ className }: { className?: string }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      strokeWidth={2}
      aria-hidden="true"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7"
      />
    </svg>
  )
}

function ApiDocsIcon({ className }: { className?: string }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      strokeWidth={2}
      aria-hidden="true"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4"
      />
    </svg>
  )
}

// ── types ─────────────────────────────────────────────────────────────────────

export interface HelpMenuProps {
  /** Opens the slide-in contextual help panel (Epic 45). */
  onOpenHelpPanel: () => void
  /**
   * Re-launches the setup wizard (Epic 44).
   * The caller is responsible for clearing the localStorage completion flag
   * before calling this so the wizard gate in App.tsx fires.
   */
  onOpenWizard: () => void
  /**
   * Activates the API Docs tab (Epic 48).
   * Typically calls the tab-switching function in App.tsx.
   */
  onOpenApiDocs: () => void
  /**
   * Optional: start a specific guided tour (Epic 47).
   * If not provided the "Guided Tours" item is rendered as disabled.
   */
  onStartTour?: (tourId: string) => void
  /**
   * Tour definitions provided by Epic 47's registry.
   * Each entry will be rendered as a sub-item under "Guided Tours".
   * If omitted or empty the section shows a single placeholder item.
   */
  tours?: Array<{ id: string; label: string; description?: string }>
}

// ── component ─────────────────────────────────────────────────────────────────

/**
 * HelpMenu renders a "?" icon button that opens a dropdown containing:
 *   1. Help Panel       — slide-in contextual help (Epic 45)
 *   2. Setup Wizard     — re-launch onboarding wizard (Epic 44)
 *   3. Guided Tours     — placeholder, extended by Epic 47.8
 *   4. API Docs         — API Reference tab (Epic 48)
 */
export function HelpMenu({
  onOpenHelpPanel,
  onOpenWizard,
  onOpenApiDocs,
  onStartTour,
  tours = [],
}: HelpMenuProps) {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  // Close on outside click
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    if (open) {
      document.addEventListener('mousedown', handleClickOutside)
    }
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [open])

  // Close on Escape
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === 'Escape') setOpen(false)
    }
    if (open) {
      document.addEventListener('keydown', handleKeyDown)
    }
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [open])

  function close() {
    setOpen(false)
  }

  function handleHelpPanel() {
    close()
    onOpenHelpPanel()
  }

  function handleWizard() {
    close()
    onOpenWizard()
  }

  function handleApiDocs() {
    close()
    onOpenApiDocs()
  }

  function handleTour(tourId: string) {
    close()
    onStartTour?.(tourId)
  }

  const toursAvailable = typeof onStartTour === 'function'

  return (
    <div ref={ref} className="relative" data-testid="help-menu">
      {/* Trigger button */}
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label="Help menu"
        className="flex h-8 w-8 items-center justify-center rounded border border-gray-700 bg-gray-900 text-gray-400 hover:border-gray-500 hover:bg-gray-800 hover:text-gray-100 focus:outline-none focus:ring-2 focus:ring-indigo-500"
        data-testid="help-menu-trigger"
      >
        <QuestionMarkIcon className="h-4 w-4" />
      </button>

      {/* Dropdown */}
      {open && (
        <div
          role="menu"
          aria-label="Help options"
          className="absolute right-0 top-full z-50 mt-1 min-w-[14rem] rounded-lg border border-gray-700 bg-gray-900 py-1 shadow-xl"
          data-testid="help-menu-dropdown"
        >
          {/* ── Help Panel ── */}
          <button
            type="button"
            role="menuitem"
            onClick={handleHelpPanel}
            className="flex w-full items-center gap-3 px-4 py-2.5 text-left text-sm text-gray-300 hover:bg-gray-800 hover:text-gray-100 focus:outline-none focus:bg-gray-800"
            data-testid="help-menu-help-panel"
          >
            <BookOpenIcon className="h-4 w-4 shrink-0 text-indigo-400" />
            <div>
              <div className="font-medium">Help Panel</div>
              <div className="text-xs text-gray-500">Contextual documentation</div>
            </div>
          </button>

          {/* ── Setup Wizard ── */}
          <button
            type="button"
            role="menuitem"
            onClick={handleWizard}
            className="flex w-full items-center gap-3 px-4 py-2.5 text-left text-sm text-gray-300 hover:bg-gray-800 hover:text-gray-100 focus:outline-none focus:bg-gray-800"
            data-testid="help-menu-wizard"
          >
            <WizardIcon className="h-4 w-4 shrink-0 text-indigo-400" />
            <div>
              <div className="font-medium">Setup Wizard</div>
              <div className="text-xs text-gray-500">Re-run onboarding steps</div>
            </div>
          </button>

          {/* ── Guided Tours ── */}
          {toursAvailable && tours.length > 0 ? (
            /* Epic 47.8: real tour links */
            <>
              <div
                className="px-4 pt-3 pb-1 text-xs font-semibold uppercase tracking-wider text-gray-500"
                aria-hidden="true"
              >
                Guided Tours
              </div>
              {tours.map((tour) => (
                <button
                  key={tour.id}
                  type="button"
                  role="menuitem"
                  onClick={() => handleTour(tour.id)}
                  className="flex w-full items-center gap-3 px-4 py-2 text-left text-sm text-gray-300 hover:bg-gray-800 hover:text-gray-100 focus:outline-none focus:bg-gray-800"
                  data-testid={`help-menu-tour-${tour.id}`}
                >
                  <ToursIcon className="h-4 w-4 shrink-0 text-indigo-400" />
                  <div>
                    <div className="font-medium">{tour.label}</div>
                    {tour.description && (
                      <div className="text-xs text-gray-500">{tour.description}</div>
                    )}
                  </div>
                </button>
              ))}
            </>
          ) : (
            /* Placeholder shown until Epic 47 is wired up */
            <button
              type="button"
              role="menuitem"
              disabled={!toursAvailable}
              onClick={toursAvailable ? () => handleTour('pipeline') : undefined}
              className={[
                'flex w-full items-center gap-3 px-4 py-2.5 text-left text-sm',
                toursAvailable
                  ? 'text-gray-300 hover:bg-gray-800 hover:text-gray-100 focus:outline-none focus:bg-gray-800'
                  : 'cursor-not-allowed text-gray-600',
              ].join(' ')}
              data-testid="help-menu-tours"
            >
              <ToursIcon className="h-4 w-4 shrink-0 text-gray-600" />
              <div>
                <div className="font-medium">Guided Tours</div>
                <div className="text-xs text-gray-600">Coming soon (Epic 47)</div>
              </div>
            </button>
          )}

          {/* Divider */}
          <div className="my-1 border-t border-gray-700" aria-hidden="true" />

          {/* ── API Docs ── */}
          <button
            type="button"
            role="menuitem"
            onClick={handleApiDocs}
            className="flex w-full items-center gap-3 px-4 py-2.5 text-left text-sm text-gray-300 hover:bg-gray-800 hover:text-gray-100 focus:outline-none focus:bg-gray-800"
            data-testid="help-menu-api-docs"
          >
            <ApiDocsIcon className="h-4 w-4 shrink-0 text-indigo-400" />
            <div>
              <div className="font-medium">API Docs</div>
              <div className="text-xs text-gray-500">Interactive API reference</div>
            </div>
          </button>
        </div>
      )}
    </div>
  )
}
