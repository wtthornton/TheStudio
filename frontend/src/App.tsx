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
import { PIPELINE_STAGES } from './lib/constants'

function App() {
  useSSE()
  useInitialLoad()

  const stages = usePipelineStore((s) => s.stages)
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null)

  // Check if pipeline has any tasks
  const hasAnyTasks = PIPELINE_STAGES.some((s) => stages[s.id].taskCount > 0)

  const handleMinimapClick = useCallback((taskId: string) => {
    setSelectedTaskId(taskId)
  }, [])

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 pb-16">
      {/* S4.F10: Disconnection banner */}
      <DisconnectionBanner />

      {/* Header */}
      <header className="flex items-center justify-between border-b border-gray-800 px-6 py-4">
        <h1 className="text-lg font-semibold">TheStudio Pipeline Dashboard</h1>
        <div className="flex items-center gap-6">
          <HeaderBar />
          <ConnectionIndicator />
        </div>
      </header>

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
    </div>
  )
}

export default App
