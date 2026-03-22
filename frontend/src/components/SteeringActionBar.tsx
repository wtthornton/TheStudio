/**
 * SteeringActionBar — Pause/Resume toggle + Abort (with confirmation dialog).
 * Renders in the TaskPacket detail header. Buttons disabled while action is in-flight.
 * SSE `pipeline.steering.action` events update status automatically.
 *
 * Covers: S1.37.6
 */

import { useState, useCallback, useEffect, useRef } from 'react'
import { useSteeringStore } from '../stores/steering-store'

interface SteeringActionBarProps {
  taskId: string
  taskStatus: string
}

const MIN_ABORT_REASON_LENGTH = 10

/** Inline confirmation dialog for abort — modal overlay with mandatory reason. */
function AbortConfirmDialog() {
  const { saving, error, abortModalOpen, abort, setAbortModalOpen } = useSteeringStore()
  const [reason, setReason] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const isValid = reason.trim().length >= MIN_ABORT_REASON_LENGTH
  const charsRemaining = MIN_ABORT_REASON_LENGTH - reason.trim().length

  // Focus textarea when dialog opens; reset reason
  useEffect(() => {
    if (abortModalOpen) {
      setReason('')
      requestAnimationFrame(() => {
        textareaRef.current?.focus()
      })
    }
  }, [abortModalOpen])

  // Escape closes dialog
  useEffect(() => {
    if (!abortModalOpen) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setAbortModalOpen(false)
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [abortModalOpen, setAbortModalOpen])

  const handleSubmit = useCallback(() => {
    if (!isValid || saving) return
    void abort(reason.trim())
  }, [abort, isValid, reason, saving])

  const handleBackdropClick = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      if (e.target === e.currentTarget) setAbortModalOpen(false)
    },
    [setAbortModalOpen],
  )

  if (!abortModalOpen) return null

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60"
      onClick={handleBackdropClick}
      data-testid="abort-confirm-backdrop"
    >
      <div className="w-full max-w-md rounded-lg border border-red-800 bg-gray-900 p-6 shadow-xl">
        <div className="mb-4 flex items-center gap-3">
          <span className="text-xl">⚠️</span>
          <div>
            <h3 className="text-sm font-semibold text-red-400">Abort Task</h3>
            <p className="mt-0.5 text-xs text-gray-400">
              This will permanently abort the task. This action cannot be undone.
            </p>
          </div>
        </div>

        <label className="mb-1 block text-xs font-medium text-gray-300">
          Reason <span className="text-red-400">*</span>
        </label>
        <textarea
          ref={textareaRef}
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          placeholder="e.g. Duplicate issue, requirements changed, blocked by upstream dependency…"
          rows={4}
          disabled={saving}
          className="w-full rounded border border-gray-600 bg-gray-800 px-3 py-2 text-sm text-gray-200 placeholder-gray-500 focus:border-red-500 focus:outline-none disabled:opacity-50"
          data-testid="abort-reason-input"
        />

        {error && (
          <p className="mt-1 text-xs text-red-400" data-testid="abort-error">{error}</p>
        )}

        <div className="mt-3 flex items-center justify-between">
          <span className={`text-xs ${charsRemaining > 0 ? 'text-amber-400' : 'text-gray-500'}`}>
            {charsRemaining > 0
              ? `${charsRemaining} more character${charsRemaining === 1 ? '' : 's'} required`
              : `${reason.trim().length} characters`}
          </span>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setAbortModalOpen(false)}
              disabled={saving}
              className="rounded px-3 py-1.5 text-xs text-gray-400 hover:text-gray-200 disabled:opacity-50"
              data-testid="abort-cancel-btn"
            >
              Cancel
            </button>
            <button
              onClick={handleSubmit}
              disabled={!isValid || saving}
              className="rounded bg-red-700 px-3 py-1.5 text-xs font-medium text-red-100 hover:bg-red-600 disabled:opacity-50"
              data-testid="abort-confirm-btn"
            >
              {saving ? 'Aborting…' : 'Abort Task'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

/** SteeringActionBar — pause/resume toggle + abort button. */
export function SteeringActionBar({ taskId, taskStatus }: SteeringActionBarProps) {
  const {
    steeringStatus,
    saving,
    error,
    init,
    pause,
    resume,
    setAbortModalOpen,
    clearError,
  } = useSteeringStore()

  // Initialise store whenever taskId or taskStatus changes
  useEffect(() => {
    init(taskId, taskStatus)
  }, [taskId, taskStatus, init])

  const handlePauseResume = useCallback(() => {
    if (saving) return
    if (steeringStatus === 'paused') {
      void resume()
    } else {
      void pause()
    }
  }, [saving, steeringStatus, pause, resume])

  // Only render for tasks that are active, paused, or running
  if (steeringStatus === null || steeringStatus === 'aborted') {
    return (
      <div className="flex items-center gap-2">
        {steeringStatus === 'aborted' && (
          <span className="rounded bg-red-900/40 px-2 py-0.5 text-xs font-medium text-red-400" data-testid="status-aborted">
            Aborted
          </span>
        )}
      </div>
    )
  }

  const isPaused = steeringStatus === 'paused'

  return (
    <>
      <div className="flex items-center gap-2" data-testid="steering-action-bar">
        {/* Paused badge */}
        {isPaused && (
          <span className="rounded bg-amber-900/40 px-2 py-0.5 text-xs font-medium text-amber-400" data-testid="status-paused">
            Paused
          </span>
        )}

        {/* Pause / Resume toggle */}
        <button
          onClick={handlePauseResume}
          disabled={saving}
          title={isPaused ? 'Resume task' : 'Pause task'}
          className={`flex items-center gap-1.5 rounded px-2.5 py-1 text-xs font-medium transition-colors disabled:opacity-50 ${
            isPaused
              ? 'bg-emerald-800/60 text-emerald-300 hover:bg-emerald-700/60'
              : 'bg-amber-800/60 text-amber-300 hover:bg-amber-700/60'
          }`}
          data-testid="pause-resume-btn"
        >
          {saving ? (
            <span className="h-3 w-3 animate-spin rounded-full border border-current border-t-transparent" />
          ) : isPaused ? (
            <span>▶</span>
          ) : (
            <span>⏸</span>
          )}
          {saving ? 'Working…' : isPaused ? 'Resume' : 'Pause'}
        </button>

        {/* Abort button */}
        <button
          onClick={() => setAbortModalOpen(true)}
          disabled={saving}
          title="Abort task"
          className="flex items-center gap-1.5 rounded bg-red-900/40 px-2.5 py-1 text-xs font-medium text-red-400 transition-colors hover:bg-red-800/60 disabled:opacity-50"
          data-testid="abort-btn"
        >
          <span>✕</span>
          Abort
        </button>

        {/* Inline error */}
        {error && (
          <div className="flex items-center gap-1">
            <span className="text-xs text-red-400" data-testid="steering-error">{error}</span>
            <button
              onClick={clearError}
              className="text-xs text-gray-500 hover:text-gray-300"
              aria-label="Dismiss error"
            >
              ✕
            </button>
          </div>
        )}
      </div>

      {/* Abort confirmation modal */}
      <AbortConfirmDialog />
    </>
  )
}
