/**
 * Epic 44.9 — Incomplete setup banner.
 * Shown when the user skipped the setup wizard but hasn't completed it.
 * Provides a "Resume Setup" CTA and a dismiss button.
 */

import { useState, useEffect } from 'react'
import { isSetupWizardSkipped, isSetupWizardComplete } from './wizardStorage'

interface IncompleteBannerProps {
  /** Called when the user clicks "Resume Setup →" */
  onResume: () => void
}

export function IncompleteBanner({ onResume }: IncompleteBannerProps) {
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    setVisible(isSetupWizardSkipped() && !isSetupWizardComplete())
  }, [])

  if (!visible) return null

  return (
    <div
      className="flex items-center justify-center gap-3 border-b border-amber-700 bg-amber-900/70 px-4 py-2 text-sm text-amber-200"
      role="alert"
      aria-live="polite"
      data-testid="incomplete-banner"
    >
      <span className="text-amber-300">⚠</span>
      <span>Setup is incomplete — your pipeline may not work correctly.</span>
      <button
        type="button"
        onClick={onResume}
        className="rounded border border-amber-600 px-3 py-0.5 text-xs font-medium text-amber-100 hover:bg-amber-800 focus:outline-none focus:ring-2 focus:ring-amber-500"
        data-testid="incomplete-banner-resume"
      >
        Resume Setup →
      </button>
      <button
        type="button"
        onClick={() => setVisible(false)}
        className="ml-1 text-amber-400 hover:text-amber-200 focus:outline-none focus:ring-2 focus:ring-amber-500"
        aria-label="Dismiss banner"
        data-testid="incomplete-banner-dismiss"
      >
        ✕
      </button>
    </div>
  )
}
