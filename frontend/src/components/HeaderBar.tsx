/** Header bar showing active count, queued count, and running cost total.
 * Updated via SSE cost events. Zero state: "0 active / 0 queued / $0.00".
 * Epic 46.5: Onboarding hint shown when all KPIs are zero.
 * Epic 44.9: "Setup incomplete" badge when wizard was skipped.
 * Epic 49.1: AppSwitcher for cross-app navigation.
 * Epic 49.4: Settings deep link to /admin/ui/settings.
 * Epic 45.3: HelpMenu + HelpPanel mounted here.
 */

import { useState } from 'react'
import { Tooltip } from 'react-tooltip'
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
  /**
   * Called when the user clicks a search result in HelpPanel (Epic 45.5).
   * The caller (App.tsx) switches to the target tab.
   */
  onSwitchTab?: (tabKey: string) => void
  /**
   * Called when the user selects a tour from HelpMenu (Epic 47.8).
   * The caller (App.tsx) starts the corresponding tour.
   */
  onStartTour?: (tourId: string) => void
  /**
   * Tour definitions from the tour registry (Epic 47.8).
   * Passed through to HelpMenu to render 4 replay links.
   */
  tours?: Array<{ id: string; label: string; description?: string }>
}

export function HeaderBar({ onResumeWizard, onOpenApiDocs, activeTab, onSwitchTab, onStartTour, tours }: HeaderBarProps = {}) {
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
    <div className="flex items-center gap-6 text-sm" data-testid="header-bar" data-component="HeaderBar">
      <AppSwitcher />
      <span
        className="text-gray-400"
        data-testid="active-count"
        data-tooltip-id="header-tip"
        data-tooltip-content="Tasks currently processing through the pipeline"
      >
        <span className="font-medium text-emerald-400">{activeCount}</span> active
      </span>
      <span
        className="text-gray-400"
        data-testid="queued-count"
        data-tooltip-id="header-tip"
        data-tooltip-content="Tasks waiting in the Intake queue"
      >
        <span className="font-medium text-amber-400">{queuedCount}</span> queued
      </span>
      <span
        className="text-gray-400"
        data-testid="running-cost"
        data-tooltip-id="header-tip"
        data-tooltip-content="Cumulative LLM API spend this session"
      >
        <span className="font-medium text-cyan-400">${totalCost.toFixed(2)}</span>
      </span>
      {allZero && !setupSkipped && (
        <span
          className="ml-2 rounded-full border border-indigo-700 bg-indigo-900/40 px-3 py-0.5 text-xs text-indigo-300"
          data-testid="onboarding-hint"
          data-tooltip-id="header-tip"
          data-tooltip-content="Import a GitHub issue to start the AI delivery pipeline"
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
          data-tooltip-id="header-tip"
          data-tooltip-content="Complete the setup wizard to enable all features"
        >
          ⚠ Setup incomplete — resume →
        </button>
      )}
      <a
        href="/admin/ui/settings"
        className="ml-auto rounded px-2.5 py-1 text-xs text-gray-500 hover:text-gray-300 focus:outline-none focus:ring-1 focus:ring-blue-500"
        title="Admin Settings"
        data-testid="admin-settings-link"
        aria-label="Admin Settings"
        data-tooltip-id="header-tip"
        data-tooltip-content="Open Admin Settings console"
      >
        ⚙ Settings
      </a>

      {/* Epic 45.3: Help menu; Epic 47.8: onStartTour + tours wired */}
      <HelpMenu
        onOpenHelpPanel={() => setHelpPanelOpen(true)}
        onOpenWizard={() => {
          onResumeWizard?.()
        }}
        onOpenApiDocs={() => {
          onOpenApiDocs?.()
        }}
        onStartTour={onStartTour}
        tours={tours}
      />

      {/* Epic 45.3: Slide-in help panel (45.4: activeTab, 45.5: onSwitchTab search) */}
      <HelpPanel
        open={helpPanelOpen}
        onClose={() => setHelpPanelOpen(false)}
        activeTab={activeTab}
        onSwitchTab={onSwitchTab}
      />

      {/* Epic 45.8: react-tooltip instance for header KPI hints */}
      <Tooltip id="header-tip" place="bottom" className="z-50 max-w-xs text-xs" />
    </div>
  )
}
