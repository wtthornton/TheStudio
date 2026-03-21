/** Error state components for the dashboard.
 * S4.F10: SSE disconnection banner, S4.F11: Reconnection with full state refresh,
 * S4.F12: API error cards, S4.F13: Empty state Pipeline Rail,
 * S4.F14: Empty states for Activity Stream, Gate Inspector, Minimap
 */

import { useState, useEffect, useCallback, useRef } from 'react'
import { usePipelineStore } from '../stores/pipeline-store'

// --- S4.F10 + S4.F11: SSE Disconnection Banner ---

export function DisconnectionBanner() {
  const connected = usePipelineStore((s) => s.connected)
  const [retryCount, setRetryCount] = useState(0)
  const [showRestored, setShowRestored] = useState(false)
  const wasDisconnectedRef = useRef(false)

  // Track retry attempts when disconnected
  useEffect(() => {
    if (!connected) {
      wasDisconnectedRef.current = true
      const interval = setInterval(() => {
        setRetryCount((c) => c + 1)
      }, 5000)
      return () => clearInterval(interval)
    }
  }, [connected])

  // Handle reconnection — intentional synchronous setState to reset UI state
  useEffect(() => {
    if (connected && wasDisconnectedRef.current) {
      wasDisconnectedRef.current = false
      // eslint-disable-next-line react-hooks/set-state-in-effect -- intentional: resetting reconnection UI
      setShowRestored(true)
      setRetryCount(0)
      const timer = setTimeout(() => setShowRestored(false), 3000)
      return () => clearTimeout(timer)
    }
  }, [connected])

  const handleRetry = useCallback(() => {
    // Force page reload to reconnect SSE
    window.location.reload()
  }, [])

  if (showRestored) {
    return (
      <div
        className="fixed top-4 left-1/2 z-50 -translate-x-1/2 rounded-lg border border-emerald-700 bg-emerald-900/90 px-4 py-2 shadow-lg"
        data-testid="connection-restored-toast"
      >
        <span className="text-sm text-emerald-300">Connection restored</span>
      </div>
    )
  }

  if (connected) return null

  return (
    <div
      className="fixed top-0 left-0 right-0 z-50 flex items-center justify-center gap-4 bg-amber-900/90 px-4 py-2 shadow-lg"
      data-testid="disconnection-banner"
    >
      <div className="flex items-center gap-2">
        <div className="h-2 w-2 animate-pulse rounded-full bg-amber-400" />
        <span className="text-sm text-amber-200">Reconnecting…</span>
        {retryCount > 0 && (
          <span className="text-xs text-amber-400">Attempt {retryCount}</span>
        )}
      </div>
      <button
        onClick={handleRetry}
        className="rounded border border-amber-600 px-2 py-0.5 text-xs text-amber-200 hover:bg-amber-800"
        data-testid="retry-button"
      >
        Retry Now
      </button>
    </div>
  )
}

// --- S4.F12: API Error Card ---

interface ErrorCardProps {
  message: string
  onRetry: () => void
  onDismiss: () => void
}

export function ErrorCard({ message, onRetry, onDismiss }: ErrorCardProps) {
  return (
    <div className="rounded-lg border border-red-800 bg-red-900/20 p-4" data-testid="error-card">
      <div className="flex items-start gap-3">
        <span className="text-red-400 text-lg shrink-0">!</span>
        <div className="flex-1">
          <p className="text-sm text-red-300">{message}</p>
          <div className="mt-2 flex gap-2">
            <button
              onClick={onRetry}
              className="rounded bg-red-800 px-3 py-1 text-xs text-red-200 hover:bg-red-700"
            >
              Retry
            </button>
            <button
              onClick={onDismiss}
              className="rounded border border-red-700 px-3 py-1 text-xs text-red-300 hover:bg-red-900"
            >
              Dismiss
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

// --- S4.F13: Empty State Pipeline Rail ---

export function EmptyPipelineRail() {
  return (
    <div className="flex flex-col items-center gap-4 py-12" data-testid="empty-pipeline-rail">
      <svg width="64" height="64" viewBox="0 0 64 64" className="text-gray-600">
        <rect x="8" y="24" width="48" height="16" rx="4" fill="none" stroke="currentColor" strokeWidth="2" />
        <line x1="20" y1="32" x2="44" y2="32" stroke="currentColor" strokeWidth="2" strokeDasharray="4 4" />
      </svg>
      <p className="text-sm text-gray-500">No tasks in the pipeline</p>
      <div className="flex gap-3">
        <button className="rounded-lg bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-500" disabled>
          Import Issues
        </button>
        <button className="rounded-lg border border-gray-600 px-4 py-2 text-sm text-gray-300 hover:border-gray-500" disabled>
          Create Task
        </button>
      </div>
      <p className="text-xs text-gray-600">Button actions available in Phase 2</p>
    </div>
  )
}

// --- S4.F14: Empty States ---

export function EmptyActivityStream() {
  return (
    <div className="flex flex-col items-center gap-2 py-8" data-testid="empty-activity-stream">
      <span className="text-2xl text-gray-600">📋</span>
      <p className="text-sm text-gray-500">No activity recorded for this task</p>
      <p className="text-xs text-gray-600">Activity will appear as the agent processes the task</p>
    </div>
  )
}

export function EmptyGateInspector() {
  return (
    <div className="flex flex-col items-center gap-2 py-8" data-testid="empty-gate-inspector">
      <span className="text-2xl text-gray-600">🔒</span>
      <p className="text-sm text-gray-500">No gate events recorded</p>
      <p className="text-xs text-gray-600">Gate results appear after verification and QA stages</p>
    </div>
  )
}

export function EmptyMinimap() {
  return (
    <div className="py-3 text-center text-xs text-gray-500" data-testid="empty-minimap">
      No active tasks — the minimap shows tasks currently being processed
    </div>
  )
}
