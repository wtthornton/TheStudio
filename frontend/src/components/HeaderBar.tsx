/** Header bar showing active count, queued count, and running cost total.
 * Updated via SSE cost events. Zero state: "0 active / 0 queued / $0.00".
 * Epic 46.5: Onboarding hint shown when all KPIs are zero.
 * Epic 44.9: "Setup incomplete" badge when wizard was skipped.
 * Epic 49.1: AppSwitcher for cross-app navigation.
 * Epic 49.4: Settings deep link to /admin/ui/settings.
 * Epic 45.3: HelpMenu + HelpPanel mounted here.
 */

import { useState } from 'react'
import { usePipelineStore } from '../stores/pipeline-store'
import { PIPELINE_STAGES } from '../lib/constants'
import {
  isSetupWizardSkipped,
  isSetupWizardComplete,
} from './wizard/wizardStorage'
import { AppSwitcher } from './AppSwitcher'
import { HelpMenu } from './help/HelpMenu'
import { HelpPanel } from './help/HelpPanel'

interface HeaderBarProps {
  /** Called when the user clicks the "Setup incomplete" resume link. */
  onResumeWizard?: () => void
  /** Called when the user selects "API Docs" from the HelpMenu (switches App tab). */
  onOpenApiDocs?: () => void
  /**
   * The currently active tab key (e.g. 'pipeline', 'triage').
   * Passed to HelpPanel so it can display route-aware content (Epic 45.4).
   */
  activeTab?: string
}

export function HeaderBar({ onResumeWizard, onOpenApiDocs, activeTab }: HeaderBarProps = {}) {
  const stages = usePipelineStore((s) => s.stages)
  const totalCost = usePipelineStore((s) => s.totalCost)

  // Active = unique task IDs across all stages
  const allActive = new Set(
    PIPELINE_STAGES.flatMap((s) => stages[s.id].activeTasks),
  )
  const activeCount = allActive.size

  // Queued = tasks in intake that haven't progressed
  const queuedCount = stages.intake.activeTasks.length

  const allZero = activeCount === 0 && queuedCount === 0 && totalCost === 0

  const setupSkipped = isSetupWizardSkipped() && !isSetupWizardComplete()

  // Epic 45.3: local toggle state for HelpPanel
  const [helpPanelOpen, setHelpPanelOpen] = useState(false)

  return (
    <div className="flex items-center gap-6 text-sm" data-testid="header-bar">
      <AppSwitcher />
      <span className="text-gray-400" data-testid="active-count">
        <span className="font-medium text-emerald-400">{activeCount}</span> active
      </span>
      <span className="text-gray-400" data-testid="queued-count">
        <span className="font-medium text-amber-400">{queuedCount}</span> queued
      </span>
      <span className="text-gray-400" data-testid="running-cost">
        <span className="font-medium text-cyan-400">${totalCost.toFixed(2)}</span>
      </span>
      {allZero && !setupSkipped && (
        <span
          className="ml-2 rounded-full border border-indigo-700 bg-indigo-900/40 px-3 py-0.5 text-xs text-indigo-300"
          data-testid="onboarding-hint"
        >
          Import your first GitHub issue to get started →
        </span>
      )}
      {setupSkipped && onResumeWizard && (
        <button
          type="button"
          onClick={onResumeWizard}
          className="ml-2 rounded-full border border-amber-700 bg-amber-900/40 px-3 py-0.5 text-xs text-amber-300 hover:bg-amber-900/70 focus:outline-none focus:ring-2 focus:ring-amber-500"
          data-testid="setup-incomplete-badge"
        >
          ⚠ Setup incomplete — resume →
        </button>
      )}
      <a
        href="/admin/ui/settings"
        className="ml-auto rounded px-2.5 py-1 text-xs text-gray-500 hover:text-gray-300 focus:outline-none focus:ring-1 focus:ring-indigo-500"
        title="Admin Settings"
        data-testid="admin-settings-link"
        aria-label="Admin Settings"
      >
        ⚙ Settings
      </a>

      {/* Epic 45.3: Help menu */}
      <HelpMenu
        onOpenHelpPanel={() => setHelpPanelOpen(true)}
        onOpenWizard={() => {
          onResumeWizard?.()
        }}
        onOpenApiDocs={() => {
          onOpenApiDocs?.()
        }}
      />

      {/* Epic 45.3: Slide-in help panel (45.4: activeTab for route-aware content) */}
      <HelpPanel
        open={helpPanelOpen}
        onClose={() => setHelpPanelOpen(false)}
        activeTab={activeTab}
      />
    </div>
  )
}
