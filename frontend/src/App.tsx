import './index.css'
import { useSSE } from './hooks/useSSE'
import { PipelineStatus } from './components/PipelineStatus'
import { ConnectionIndicator } from './components/ConnectionIndicator'
import { EventLog } from './components/EventLog'

function App() {
  useSSE()

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      {/* Header */}
      <header className="flex items-center justify-between border-b border-gray-800 px-6 py-4">
        <h1 className="text-lg font-semibold">TheStudio Pipeline Dashboard</h1>
        <ConnectionIndicator />
      </header>

      {/* Pipeline rail */}
      <section className="flex justify-center">
        <PipelineStatus />
      </section>

      {/* Event log */}
      <section className="mx-auto max-w-2xl px-6 py-4">
        <EventLog />
      </section>
    </div>
  )
}

export default App
