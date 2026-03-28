import './index.css'
import { useState, useCallback, useEffect } from 'react'
import { useSSE } from './hooks/useSSE'
import { useInitialLoad } from './hooks/useInitialLoad'
import { usePipelineStore } from './stores/pipeline-store'
import { PipelineStatus } from './components/PipelineStatus'
import { ConnectionIndicator } from './components/ConnectionIndicator'
import { HeaderBar } from './components/HeaderBar'
import { EventLog } from './components/EventLog'
import { StageDetailPanel } from './components/StageDetailPanel'
import { TaskTimeline } from './components/TaskTimeline'
import { GateInspector } from './components/GateInspector'
import { ActivityStream } from './components/ActivityStream'
import { LoopbackOverlay } from './components/LoopbackArc'
import { Minimap } from './components/Minimap'
import { DisconnectionBanner } from './components/ErrorStates'
import { EmptyPipelineRail } from './components/ErrorStates'
import { EmptyState } from './components/EmptyState'
import { TriageQueue } from './components/planning/TriageQueue'
import IntentEditor from './components/planning/IntentEditor'
import RoutingPreview from './components/planning/RoutingPreview'
import BacklogBoard from './components/planning/BacklogBoard'
import { TrustConfiguration } from './components/TrustConfiguration'
import { BudgetDashboard } from './components/BudgetDashboard'
import { NotificationBell } from './components/NotificationBell'
import { SteeringActivityLog } from './components/SteeringActivityLog'
import ImportModal from './components/github/ImportModal'
import { Analytics } from './components/analytics/Analytics'
import { Reputation } from './components/reputation/Reputation'
import { PIPELINE_STAGES } from './lib/constants'
import { useRepoContext } from './contexts/RepoContext'
import { RepoSelector } from './components/RepoSelector'
import { RepoSettings } from './components/RepoSettings'
import { ApiReference } from './components/ApiReference'
import { TourBeacon } from './components/tours/TourBeacon'
import {
  PIPELINE_TOUR_STEPS,
  TRIAGE_TOUR_STEPS,
  ANALYTICS_TOUR_STEPS,
  REPO_TRUST_TOUR_STEPS,
  TOUR_REGISTRY,
} from './components/tours/registry'
import { useTour } from './components/tours/TourProvider'
import { WizardShell } from './components/wizard/WizardShell'
import { HealthCheckStep } from './components/wizard/HealthCheckStep'
import { RepoRegistrationStep } from './components/wizard/RepoRegistrationStep'
import { WebhookConfigStep } from './components/wizard/WebhookConfigStep'
import { TrustTierStep } from './components/wizard/TrustTierStep'
import { LLMProviderStep } from './components/wizard/LLMProviderStep'
import {
  isSetupWizardComplete,
  isSetupWizardSkipped,
  markSetupWizardComplete,
  markSetupWizardSkipped,
  clearSetupWizardSkipped,
} from './components/wizard/wizardStorage'
import { IncompleteBanner } from './components/wizard/IncompleteBanner'

type Tab =
  | 'pipeline'
  | 'triage'
  | 'intent'
  | 'routing'
  | 'board'
  | 'trust'
  | 'budget'
  | 'activity'
  | 'analytics'
  | 'reputation'
  | 'repos'
  | 'api'

const VALID_TABS: Tab[] = [
  'pipeline', 'triage', 'intent', 'routing', 'board',
  'trust', 'budget', 'activity', 'analytics', 'reputation', 'repos', 'api',
]

/** Primary nav tab styles: visible :focus ring for keyboard + programmatic focus (WCAG 2.4.11). */
function primaryNavTabClass(active: boolean): string {
  const ring =
    'shrink-0 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:ring-offset-gray-950'
  return active
    ? `${ring} bg-gray-700 text-gray-100`
    : `${ring} text-gray-300 hover:text-gray-100`
}

/** Parse ?tab= from the current URL, returning it if valid or 'pipeline'. */
function getInitialTab(): Tab {
  const param = new URLSearchParams(window.location.search).get('tab')
  return param && (VALID_TABS as string[]).includes(param) ? (param as Tab) : 'pipeline'
}

/** Map tour IDs to their step arrays for the HelpMenu replay handler. */
const TOUR_STEPS_MAP: Record<string, Parameters<ReturnType<typeof useTour>['startTour']>[1]> = {
  pipeline: PIPELINE_TOUR_STEPS,
  triage: TRIAGE_TOUR_STEPS,
  analytics: ANALYTICS_TOUR_STEPS,
  'repo-trust': REPO_TRUST_TOUR_STEPS,
}

function App() {
  useSSE()
  useInitialLoad()

  // Epic 47.8: tour context for HelpMenu replay links
  const { startTour } = useTour()

  const { setSelectedRepo } = useRepoContext()
  const stages = usePipelineStore((s) => s.stages)
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<Tab>(getInitialTab)
  const [importModalOpen, setImportModalOpen] = useState(false)
  const [showSetupWizard, setShowSetupWizard] = useState(false)

  // Sync ?tab= into URL whenever activeTab changes (Epic 49.3).
  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    params.set('tab', activeTab)
    window.history.replaceState(null, '', `${window.location.pathname}?${params.toString()}`)
  }, [activeTab])

  // Parse ?repo= on mount and apply to repo context (Epic 49.3).
  useEffect(() => {
    const repoParam = new URLSearchParams(window.location.search).get('repo')
    if (repoParam) {
      setSelectedRepo(decodeURIComponent(repoParam))
    }
  }, [setSelectedRepo])

  useEffect(() => {
    if (isSetupWizardComplete() || isSetupWizardSkipped()) {
      setShowSetupWizard(false)
    } else {
      setShowSetupWizard(true)
    }
  }, [])

  const handleSetupWizardComplete = useCallback(() => {
    markSetupWizardComplete()
    setShowSetupWizard(false)
  }, [])

  const handleSetupWizardSkip = useCallback(() => {
    markSetupWizardSkipped()
    setShowSetupWizard(false)
  }, [])

  const handleSetupWizardResume = useCallback(() => {
    clearSetupWizardSkipped()
    setShowSetupWizard(true)
  }, [])

  // Epic 47.8: start a tour from HelpMenu by tourId
  const handleStartTour = useCallback(
    (tourId: string) => {
      const steps = TOUR_STEPS_MAP[tourId]
      if (steps) startTour(tourId, steps)
    },
    [startTour],
  )

  // Check if pipeline has any tasks
  const hasAnyTasks = PIPELINE_STAGES.some((s) => stages[s.id].taskCount > 0)

  const handleMinimapClick = useCallback((taskId: string) => {
    setSelectedTaskId(taskId)
  }, [])

  const handleNotificationNavigate = useCallback((tab: string, taskId?: string) => {
    setActiveTab(tab as Tab)
    if (taskId) setSelectedTaskId(taskId)
  }, [])

  return (
    <div
      className="min-h-screen bg-gray-950 text-gray-100 pb-16"
      data-dashboard-shell
    >
      {showSetupWizard ? (
        <div
          className="fixed inset-0 z-[100] flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm"
          role="dialog"
          aria-modal="true"
          aria-labelledby="setup-wizard-title"
        >
          <WizardShell
            title="Setup"
            onComplete={handleSetupWizardComplete}
            onSkip={handleSetupWizardSkip}
          >
            <HealthCheckStep />
            <RepoRegistrationStep />
            <WebhookConfigStep />
            <TrustTierStep />
            <LLMProviderStep />
          </WizardShell>
        </div>
      ) : null}

      {/* S4.F10: Disconnection banner */}
      <DisconnectionBanner />
      {/* Epic 44.9: Incomplete setup banner */}
      <IncompleteBanner onResume={handleSetupWizardResume} />

      {/* Header — responsive: title hidden on small screens to give nav more space;
          nav scrolls horizontally on small screens (overflow-x-auto + flex-nowrap). */}
      <header className="flex items-center justify-between border-b border-gray-800 px-4 sm:px-6 py-3 sm:py-4 gap-2">
        <div className="flex items-center gap-2 sm:gap-4 min-w-0 overflow-hidden">
          <h1 className="text-lg font-semibold shrink-0 hidden md:block">TheStudio Pipeline Dashboard</h1>
          <h1 className="text-sm font-semibold shrink-0 md:hidden">TheStudio</h1>
          <nav
            className="flex gap-1 overflow-x-auto scrollbar-none flex-nowrap rounded-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:ring-offset-gray-950"
            aria-label="Primary navigation"
            tabIndex={0}
          >
            <button
              type="button"
              onClick={() => setActiveTab('pipeline')}
              className={primaryNavTabClass(activeTab === 'pipeline')}
            >
              Pipeline
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('triage')}
              className={primaryNavTabClass(activeTab === 'triage')}
            >
              Triage
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('intent')}
              className={primaryNavTabClass(activeTab === 'intent')}
            >
              Intent Review
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('routing')}
              className={primaryNavTabClass(activeTab === 'routing')}
            >
              Routing Review
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('board')}
              className={primaryNavTabClass(activeTab === 'board')}
            >
              Backlog
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('trust')}
              className={primaryNavTabClass(activeTab === 'trust')}
            >
              Trust Tiers
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('budget')}
              className={primaryNavTabClass(activeTab === 'budget')}
            >
              Budget
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('activity')}
              className={primaryNavTabClass(activeTab === 'activity')}
            >
              Activity Log
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('analytics')}
              className={primaryNavTabClass(activeTab === 'analytics')}
            >
              Analytics
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('reputation')}
              className={primaryNavTabClass(activeTab === 'reputation')}
            >
              Reputation
            </button>
            {/* Epic 41 — Repo Settings tab */}
            <button
              type="button"
              onClick={() => setActiveTab('repos')}
              className={primaryNavTabClass(activeTab === 'repos')}
            >
              Repos
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('api')}
              className={primaryNavTabClass(activeTab === 'api')}
              data-spotlight="api-tab"
            >
              API
            </button>
          </nav>
        </div>
        <div className="flex items-center gap-4">
          {/* Epic 41 — Repo Selector */}
          <RepoSelector />
          {/* Epic 38 — Import GitHub Issues */}
          <button
            type="button"
            onClick={() => setImportModalOpen(true)}
            className="rounded bg-blue-700 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-400 focus:ring-offset-2 focus:ring-offset-gray-950"
          >
            ↓ Import Issues
          </button>
          {/* Epic 45.3: HelpMenu mounted inside HeaderBar; onOpenApiDocs switches tab */}
          {/* Epic 45.4: activeTab passed for route-aware help content */}
          {/* Epic 45.5: onSwitchTab wires help search results to tab navigation */}
          {/* Epic 47.8: onStartTour + tours wired to enable HelpMenu replay links */}
          <HeaderBar
            onResumeWizard={handleSetupWizardResume}
            onOpenApiDocs={() => setActiveTab('api')}
            activeTab={activeTab}
            onSwitchTab={(tab) => setActiveTab(tab as Tab)}
            onStartTour={handleStartTour}
            tours={TOUR_REGISTRY as unknown as Array<{ id: string; label: string; description?: string }>}
          />
          <NotificationBell onNavigate={handleNotificationNavigate} />
          <ConnectionIndicator />
        </div>
      </header>

      {activeTab === 'pipeline' ? (
        <>
          {/* Epic 47.4 — Pipeline tour beacon (hidden after completion) */}
          <div className="flex justify-end px-6 pt-3">
            <TourBeacon tourId="pipeline" steps={PIPELINE_TOUR_STEPS} label="Pipeline tour" />
          </div>

          {/* Pipeline rail with loopback overlay */}
          <section className="relative flex justify-center">
            <LoopbackOverlay />
            {hasAnyTasks ? <PipelineStatus /> : <EmptyPipelineRail />}
          </section>

          {/* Main content area */}
          <div className="mx-auto max-w-6xl px-6 py-4">
            {selectedTaskId ? (
              <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
                {/* TaskPacket Timeline */}
                <div className="rounded-lg border border-gray-700 bg-gray-900 p-4">
                  <TaskTimeline taskId={selectedTaskId} onClose={() => setSelectedTaskId(null)} />
                </div>
                {/* Activity Stream */}
                <div>
                  <ActivityStream taskId={selectedTaskId} />
                </div>
              </div>
            ) : (
              <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
                {/* Event log */}
                <div>
                  <EventLog />
                </div>
                {/* Gate Inspector */}
                <div>
                  <GateInspector />
                </div>
              </div>
            )}
          </div>

          {/* Stage detail panel (slide-in) */}
          <StageDetailPanel />

          {/* S4.F6: Minimap bottom bar */}
          <Minimap activeTaskId={selectedTaskId ?? undefined} onTaskClick={handleMinimapClick} />
        </>
      ) : activeTab === 'triage' ? (
        /* Triage Queue (Epic 36) */
        <div className="mx-auto max-w-4xl px-6 py-6">
          {/* Epic 47.5 — Triage tour beacon added here */}
          <TriageQueue />
        </div>
      ) : activeTab === 'intent' ? (
        /* Intent Review (Epic 36, Slice 2) */
        <div className="mx-auto max-w-6xl px-6 py-6">
          {selectedTaskId ? (
            <IntentEditor
              taskId={selectedTaskId}
              onNavigateToPipeline={() => setActiveTab('pipeline')}
            />
          ) : (
            <EmptyState
              heading="No Task Selected"
              description="Select a task from the Pipeline tab to review its intent specification. The intent spec defines what the agent should implement."
              primaryAction={{ label: 'Go to Pipeline', onClick: () => setActiveTab('pipeline') }}
              secondaryAction={{ label: 'Open Backlog', onClick: () => setActiveTab('board') }}
              data-testid="intent-no-task-state"
            />
          )}
        </div>
      ) : activeTab === 'routing' ? (
        /* Routing Review (Epic 36, Slice 3) */
        <div className="mx-auto max-w-6xl px-6 py-6">
          {selectedTaskId ? (
            <RoutingPreview
              taskId={selectedTaskId}
              onNavigateToPipeline={() => setActiveTab('pipeline')}
            />
          ) : (
            <EmptyState
              heading="No Task Selected"
              description="Select a task from the Pipeline tab to review its expert routing. Routing determines which specialist agents work on the implementation."
              primaryAction={{ label: 'Go to Pipeline', onClick: () => setActiveTab('pipeline') }}
              secondaryAction={{ label: 'Open Backlog', onClick: () => setActiveTab('board') }}
              data-testid="routing-no-task-state"
            />
          )}
        </div>
      ) : activeTab === 'board' ? (
        /* Backlog Board (Epic 36, Slice 4) */
        <div className="mx-auto max-w-screen-2xl px-6 py-6">
          <BacklogBoard
            onTaskClick={(taskId) => {
              setSelectedTaskId(taskId)
              setActiveTab('pipeline')
            }}
            onNavigateToPipeline={() => setActiveTab('pipeline')}
          />
        </div>
      ) : activeTab === 'trust' ? (
        /* Trust Tier Configuration (Epic 37, Slice 3) */
        <TrustConfiguration />
      ) : activeTab === 'budget' ? (
        /* Budget Dashboard (Epic 37, Slice 4) */
        <BudgetDashboard />
      ) : activeTab === 'analytics' ? (
        /* Operational Analytics (Epic 39, Slice 1) */
        /* Epic 47.6 — Analytics tour beacon added here */
        <Analytics onNavigateToPipeline={() => setActiveTab('pipeline')} />
      ) : activeTab === 'reputation' ? (
        /* Reputation & Outcomes (Epic 39, Slice 2) */
        <Reputation />
      ) : activeTab === 'repos' ? (
        /* Repository Settings & Fleet Health (Epic 41, Slice 2 — 41.11 + 41.14) */
        <>
          {/* Epic 47.7 — Repo & Trust tour beacon */}
          <div className="flex justify-end px-6 pt-3">
            <TourBeacon tourId="repo-trust" steps={REPO_TRUST_TOUR_STEPS} label="Repo & Trust tour" />
          </div>
          <RepoSettings />
        </>
      ) : activeTab === 'api' ? (
        <div className="mx-auto max-w-[100rem] px-6 py-6">
          <h2 className="mb-4 text-sm font-medium text-gray-300">HTTP API (OpenAPI)</h2>
          <ApiReference />
        </div>
      ) : (
        /* Steering Activity Log (Epic 37, Slice 5 — 37.28) */
        <SteeringActivityLog />
      )}

      {/* Epic 38, Story 38.3 — GitHub Issue Import Modal */}
      <ImportModal
        open={importModalOpen}
        onClose={() => setImportModalOpen(false)}
        onImported={(count) => {
          // Refresh triage queue / pipeline if issues were created
          if (count > 0) setActiveTab('triage')
          setImportModalOpen(false)
        }}
      />
    </div>
  )
}

export default App
