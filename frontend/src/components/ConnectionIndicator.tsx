/** Shows SSE connection status: green dot when connected, red when disconnected. */

import { usePipelineStore } from '../stores/pipeline-store'

export function ConnectionIndicator() {
  const connected = usePipelineStore((s) => s.connected)

  return (
    <div className="flex items-center gap-2" data-testid="connection-indicator">
      <span
        className={`inline-block h-2.5 w-2.5 rounded-full ${connected ? 'bg-emerald-500' : 'bg-red-500 animate-pulse'}`}
        data-testid="connection-dot"
      />
      <span className="text-xs text-gray-400" data-testid="connection-label">
        {connected ? 'Connected' : 'Disconnected'}
      </span>
    </div>
  )
}
