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
import { RepoContextProvider } from './contexts/RepoContext'
import { RepoSelector } from './components/RepoSelector'
import { RepoSettings } from './components/RepoSettings'
import { ApiReference } from './components/ApiReference'
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

function App() {
  useSSE()
  useInitialLoad()

  const stages = usePipelineStore((s) => s.stages)
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<Tab>('pipeline')
  const [importModalOpen, setImportModalOpen] = useState(false)
  const [showSetupWizard, setShowSetupWizard] = useState(false)

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
    <RepoContextProvider>
    <div className="min-h-screen bg-gray-950 text-gray-100 pb-16">
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

      {/* Header */}
      <header className="flex items-center justify-between border-b border-gray-800 px-6 py-4">
        <div className="flex items-center gap-6">
          <h1 className="text-lg font-semibold">TheStudio Pipeline Dashboard</h1>
          <nav className="flex gap-1">
            <button
              onClick={() => setActiveTab('pipeline')}
              className={`px-3 py-1.5 text-sm rounded ${activeTab === 'pipeline' ? 'bg-gray-700 text-gray-100' : 'text-gray-400 hover:text-gray-200'}`}
            >
              Pipeline
            </button>
            <button
              onClick={() => setActiveTab('triage')}
              className={`px-3 py-1.5 text-sm rounded ${activeTab === 'triage' ? 'bg-gray-700 text-gray-100' : 'text-gray-400 hover:text-gray-200'}`}
            >
              Triage
            </button>
            <button
              onClick={() => setActiveTab('intent')}
              className={`px-3 py-1.5 text-sm rounded ${activeTab === 'intent' ? 'bg-gray-700 text-gray-100' : 'text-gray-400 hover:text-gray-200'}`}
            >
              Intent Review
            </button>
            <button
              onClick={() => setActiveTab('routing')}
              className={`px-3 py-1.5 text-sm rounded ${activeTab === 'routing' ? 'bg-gray-700 text-gray-100' : 'text-gray-400 hover:text-gray-200'}`}
            >
              Routing Review
            </button>
            <button
              onClick={() => setActiveTab('board')}
              className={`px-3 py-1.5 text-sm rounded ${activeTab === 'board' ? 'bg-gray-700 text-gray-100' : 'text-gray-400 hover:text-gray-200'}`}
            >
              Backlog
            </button>
            <button
              onClick={() => setActiveTab('trust')}
              className={`px-3 py-1.5 text-sm rounded ${activeTab === 'trust' ? 'bg-gray-700 text-gray-100' : 'text-gray-400 hover:text-gray-200'}`}
            >
              Trust Tiers
            </button>
            <button
              onClick={() => setActiveTab('budget')}
              className={`px-3 py-1.5 text-sm rounded ${activeTab === 'budget' ? 'bg-gray-700 text-gray-100' : 'text-gray-400 hover:text-gray-200'}`}
            >
              Budget
            </button>
            <button
              onClick={() => setActiveTab('activity')}
              className={`px-3 py-1.5 text-sm rounded ${activeTab === 'activity' ? 'bg-gray-700 text-gray-100' : 'text-gray-400 hover:text-gray-200'}`}
            >
              Activity Log
            </button>
            <button
              onClick={() => setActiveTab('analytics')}
              className={`px-3 py-1.5 text-sm rounded ${activeTab === 'analytics' ? 'bg-gray-700 text-gray-100' : 'text-gray-400 hover:text-gray-200'}`}
            >
              Analytics
            </button>
            <button
              onClick={() => setActiveTab('reputation')}
              className={`px-3 py-1.5 text-sm rounded ${activeTab === 'reputation' ? 'bg-gray-700 text-gray-100' : 'text-gray-400 hover:text-gray-200'}`}
            >
              Reputation
            </button>
            {/* Epic 41 — Repo Settings tab */}
            <button
              onClick={() => setActiveTab('repos')}
              className={`px-3 py-1.5 text-sm rounded ${activeTab === 'repos' ? 'bg-gray-700 text-gray-100' : 'text-gray-400 hover:text-gray-200'}`}
            >
              Repos
            </button>
            <button
              onClick={() => setActiveTab('api')}
              className={`px-3 py-1.5 text-sm rounded ${activeTab === 'api' ? 'bg-gray-700 text-gray-100' : 'text-gray-400 hover:text-gray-200'}`}
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
            onClick={() => setImportModalOpen(true)}
            className="rounded bg-blue-700 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-600"
          >
            ↓ Import Issues
          </button>
          <HeaderBar onResumeWizard={handleSetupWizardResume} />
          {/* Epic 44.10: Re-launch Setup Wizard (replaced by HelpMenu when Epic 45 ships) */}
          {!showSetupWizard && (
            <button
              type="button"
              onClick={handleSetupWizardResume}
              className="rounded border border-gray-700 px-3 py-1.5 text-sm text-gray-500 hover:border-gray-500 hover:text-gray-300"
              data-testid="relaunch-wizard-btn"
              title="Re-launch Setup Wizard"
            >
              ⚙ Setup
            </button>
          )}
          <NotificationBell onNavigate={handleNotificationNavigate} />
          <ConnectionIndicator />
        </div>
      </header>

      {activeTab === 'pipeline' ? (
        <>
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
        <Analytics onNavigateToPipeline={() => setActiveTab('pipeline')} />
      ) : activeTab === 'reputation' ? (
        /* Reputation & Outcomes (Epic 39, Slice 2) */
        <Reputation />
      ) : activeTab === 'repos' ? (
        /* Repository Settings & Fleet Health (Epic 41, Slice 2 — 41.11 + 41.14) */
        <RepoSettings />
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
    </RepoContextProvider>
  )
}

export default App
