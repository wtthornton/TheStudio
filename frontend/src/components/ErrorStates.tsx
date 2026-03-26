/** Error state components for the dashboard.
 * S4.F10: SSE disconnection banner, S4.F11: Reconnection with full state refresh,
 * S4.F12: API error cards, S4.F13: Empty state Pipeline Rail,
 * S4.F14: Empty states for Activity Stream, Gate Inspector, Minimap
 * Epic 46.2: EmptyPipelineRail uses EmptyState + ImportModal CTA
 */

import { useState, useEffect, useCallback, useRef, lazy, Suspense } from 'react'
import { usePipelineStore } from '../stores/pipeline-store'
import { EmptyState } from './EmptyState'

const ImportModal = lazy(() => import('./github/ImportModal'))

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
        role="status"
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
      role="alert"
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
    <div role="alert" className="rounded-lg border border-red-800 bg-red-900/20 p-4" data-testid="error-card">
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

// --- Pipeline wireframe SVG illustration ---

function PipelineWireframeSVG() {
  return (
    <svg
      width="80"
      height="48"
      viewBox="0 0 80 48"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
    >
      {/* Stage boxes */}
      <rect x="2"  y="16" width="14" height="16" rx="3" stroke="currentColor" strokeWidth="1.5" />
      <rect x="22" y="16" width="14" height="16" rx="3" stroke="currentColor" strokeWidth="1.5" />
      <rect x="42" y="16" width="14" height="16" rx="3" stroke="currentColor" strokeWidth="1.5" />
      <rect x="62" y="16" width="14" height="16" rx="3" stroke="currentColor" strokeWidth="1.5" />
      {/* Connector arrows */}
      <line x1="16" y1="24" x2="22" y2="24" stroke="currentColor" strokeWidth="1.5" strokeDasharray="3 2" />
      <line x1="36" y1="24" x2="42" y2="24" stroke="currentColor" strokeWidth="1.5" strokeDasharray="3 2" />
      <line x1="56" y1="24" x2="62" y2="24" stroke="currentColor" strokeWidth="1.5" strokeDasharray="3 2" />
      {/* Dots inside boxes to suggest content */}
      <circle cx="9"  cy="24" r="2" fill="currentColor" opacity="0.4" />
      <circle cx="29" cy="24" r="2" fill="currentColor" opacity="0.4" />
      <circle cx="49" cy="24" r="2" fill="currentColor" opacity="0.4" />
      <circle cx="69" cy="24" r="2" fill="currentColor" opacity="0.4" />
    </svg>
  )
}

// --- S4.F13 / Epic 46.2: Empty State Pipeline Rail ---

export function EmptyPipelineRail() {
  const [importOpen, setImportOpen] = useState(false)

  return (
    <>
      <EmptyState
        data-testid="empty-pipeline-rail"
        icon={<PipelineWireframeSVG />}
        heading="No tasks in the pipeline"
        description="Import a GitHub issue to kick off the AI delivery pipeline — from intent to draft PR."
        primaryAction={{
          label: 'Import an Issue',
          onClick: () => setImportOpen(true),
        }}
        secondaryAction={{
          label: 'Learn about the pipeline',
          href: '/admin/ui/settings',
        }}
      />
      {importOpen && (
        <Suspense fallback={null}>
          <ImportModal
            open={importOpen}
            onClose={() => setImportOpen(false)}
          />
        </Suspense>
      )}
    </>
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
