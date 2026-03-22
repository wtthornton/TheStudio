import './index.css'
import { useState, useCallback } from 'react'
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
import { TriageQueue } from './components/planning/TriageQueue'
import IntentEditor from './components/planning/IntentEditor'
import RoutingPreview from './components/planning/RoutingPreview'
import BacklogBoard from './components/planning/BacklogBoard'
import { TrustConfiguration } from './components/TrustConfiguration'
import { BudgetDashboard } from './components/BudgetDashboard'
import { NotificationBell } from './components/NotificationBell'
import { PIPELINE_STAGES } from './lib/constants'

type Tab = 'pipeline' | 'triage' | 'intent' | 'routing' | 'board' | 'trust' | 'budget'

function App() {
  useSSE()
  useInitialLoad()

  const stages = usePipelineStore((s) => s.stages)
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<Tab>('pipeline')

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
    <div className="min-h-screen bg-gray-950 text-gray-100 pb-16">
      {/* S4.F10: Disconnection banner */}
      <DisconnectionBanner />

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
          </nav>
        </div>
        <div className="flex items-center gap-4">
          <HeaderBar />
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
            <IntentEditor taskId={selectedTaskId} />
          ) : (
            <div className="flex flex-col items-center justify-center py-20 text-gray-500">
              <p className="text-sm">Select a task from the Pipeline tab to review its intent specification.</p>
              <button
                onClick={() => setActiveTab('pipeline')}
                className="mt-3 rounded bg-gray-700 px-3 py-1.5 text-xs text-gray-300 hover:bg-gray-600"
              >
                Go to Pipeline
              </button>
            </div>
          )}
        </div>
      ) : activeTab === 'routing' ? (
        /* Routing Review (Epic 36, Slice 3) */
        <div className="mx-auto max-w-6xl px-6 py-6">
          {selectedTaskId ? (
            <RoutingPreview taskId={selectedTaskId} />
          ) : (
            <div className="flex flex-col items-center justify-center py-20 text-gray-500">
              <p className="text-sm">Select a task from the Pipeline tab to review its expert routing.</p>
              <button
                onClick={() => setActiveTab('pipeline')}
                className="mt-3 rounded bg-gray-700 px-3 py-1.5 text-xs text-gray-300 hover:bg-gray-600"
              >
                Go to Pipeline
              </button>
            </div>
          )}
        </div>
      ) : activeTab === 'board' ? (
        /* Backlog Board (Epic 36, Slice 4) */
        <div className="mx-auto max-w-screen-2xl px-6 py-6">
          <BacklogBoard onTaskClick={(taskId) => {
            setSelectedTaskId(taskId)
            setActiveTab('pipeline')
          }} />
        </div>
      ) : activeTab === 'trust' ? (
        /* Trust Tier Configuration (Epic 37, Slice 3) */
        <TrustConfiguration />
      ) : (
        /* Budget Dashboard (Epic 37, Slice 4) */
        <BudgetDashboard />
      )}
    </div>
  )
}

export default App
