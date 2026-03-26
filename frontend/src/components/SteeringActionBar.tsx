/**
 * SteeringActionBar — Pause/Resume toggle, Abort, Redirect, and Retry controls.
 * Renders in the TaskPacket detail header. Buttons disabled while action is in-flight.
 * SSE `pipeline.steering.action` events update status automatically.
 *
 * Covers: S1.37.6 (pause/resume/abort) + S2.37.11 (redirect/retry)
 */

import { useState, useCallback, useEffect, useRef } from 'react'
import { useSteeringStore } from '../stores/steering-store'
import { PIPELINE_STAGES } from '../lib/constants'

interface SteeringActionBarProps {
  taskId: string
  taskStatus: string
  /** Current pipeline stage ID (e.g. 'verify'). Used by RedirectModal to list valid earlier stages. */
  currentStage?: string | null
}

const MIN_REASON_LENGTH = 10

// ---------------------------------------------------------------------------
// AbortConfirmDialog
// ---------------------------------------------------------------------------

/** Inline confirmation dialog for abort — modal overlay with mandatory reason. */
function AbortConfirmDialog() {
  const { saving, error, abortModalOpen, abort, setAbortModalOpen } = useSteeringStore()
  const [reason, setReason] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const isValid = reason.trim().length >= MIN_REASON_LENGTH
  const charsRemaining = MIN_REASON_LENGTH - reason.trim().length

  useEffect(() => {
    if (abortModalOpen) {
      setReason('')
      requestAnimationFrame(() => {
        textareaRef.current?.focus()
      })
    }
  }, [abortModalOpen])

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
      <div
        className="w-full max-w-md rounded-lg border border-red-800 bg-gray-900 p-6 shadow-xl"
        role="dialog"
        aria-modal="true"
        aria-labelledby="steering-abort-heading"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-4 flex items-center gap-3">
          <span className="text-xl" aria-hidden="true">⚠️</span>
          <div>
            <h3 id="steering-abort-heading" className="text-sm font-semibold text-red-400">
              Abort Task
            </h3>
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
              type="button"
              onClick={() => setAbortModalOpen(false)}
              disabled={saving}
              className="rounded px-3 py-1.5 text-xs text-gray-400 hover:text-gray-200 disabled:opacity-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-red-500"
              data-testid="abort-cancel-btn"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleSubmit}
              disabled={!isValid || saving}
              className="rounded bg-red-700 px-3 py-1.5 text-xs font-medium text-red-100 hover:bg-red-600 disabled:opacity-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-red-400"
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

// ---------------------------------------------------------------------------
// RedirectModal
// ---------------------------------------------------------------------------

/**
 * RedirectModal — select an earlier pipeline stage + mandatory reason.
 * Only stages with index strictly less than the current stage are offered.
 */
function RedirectModal() {
  const {
    saving,
    error,
    currentStage,
    redirectModalOpen,
    redirect,
    setRedirectModalOpen,
  } = useSteeringStore()

  const currentIdx = PIPELINE_STAGES.findIndex((s) => s.id === currentStage)
  const validTargets = currentIdx > 0 ? PIPELINE_STAGES.slice(0, currentIdx) : []

  const [selectedStage, setSelectedStage] = useState<string>('')
  const [reason, setReason] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const isValid =
    selectedStage !== '' && reason.trim().length >= MIN_REASON_LENGTH

  const charsRemaining = MIN_REASON_LENGTH - reason.trim().length

  useEffect(() => {
    if (redirectModalOpen) {
      setSelectedStage(validTargets.length > 0 ? validTargets[validTargets.length - 1].id : '')
      setReason('')
      requestAnimationFrame(() => {
        textareaRef.current?.focus()
      })
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [redirectModalOpen])

  useEffect(() => {
    if (!redirectModalOpen) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setRedirectModalOpen(false)
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [redirectModalOpen, setRedirectModalOpen])

  const handleSubmit = useCallback(() => {
    if (!isValid || saving) return
    void redirect(selectedStage, reason.trim())
  }, [isValid, redirect, reason, saving, selectedStage])

  const handleBackdropClick = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      if (e.target === e.currentTarget) setRedirectModalOpen(false)
    },
    [setRedirectModalOpen],
  )

  if (!redirectModalOpen) return null

  // Re-run scope: everything from target stage onward
  const targetLabel = validTargets.find((s) => s.id === selectedStage)?.label ?? selectedStage
  const currentLabel = PIPELINE_STAGES[currentIdx]?.label ?? currentStage ?? 'current'

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60"
      onClick={handleBackdropClick}
      data-testid="redirect-modal-backdrop"
    >
      <div
        className="w-full max-w-lg rounded-lg border border-violet-800 bg-gray-900 p-6 shadow-xl"
        role="dialog"
        aria-modal="true"
        aria-labelledby="steering-redirect-heading"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-4 flex items-center gap-3">
          <span className="text-xl" aria-hidden="true">↩️</span>
          <div>
            <h3 id="steering-redirect-heading" className="text-sm font-semibold text-violet-300">
              Redirect Task to Earlier Stage
            </h3>
            <p className="mt-0.5 text-xs text-gray-400">
              Currently at <span className="font-medium text-gray-300">{currentLabel}</span>. Select an earlier stage to re-enter.
            </p>
          </div>
        </div>

        {/* Warning about re-run scope */}
        {selectedStage && (
          <div className="mb-4 flex items-start gap-2 rounded border border-amber-800/50 bg-amber-950/30 p-3">
            <span className="mt-0.5 text-sm">⚠️</span>
            <p className="text-xs text-amber-300">
              Re-running from <strong>{targetLabel}</strong> will re-execute all stages from{' '}
              <strong>{targetLabel}</strong> through <strong>{currentLabel}</strong>. Stage artifacts and
              cost will accumulate. This action cannot be undone.
            </p>
          </div>
        )}

        {/* Stage radio group */}
        <fieldset className="mb-4">
          <legend className="mb-2 text-xs font-medium text-gray-300">
            Target stage <span className="text-red-400">*</span>
          </legend>

          {validTargets.length === 0 ? (
            <p className="text-xs text-gray-500">No earlier stages available (task is at the first stage).</p>
          ) : (
            <div className="space-y-1.5">
              {validTargets.map((stage, idx) => (
                <label
                  key={stage.id}
                  className="flex cursor-pointer items-center gap-3 rounded border border-gray-700 px-3 py-2 hover:border-violet-700 has-[:checked]:border-violet-600 has-[:checked]:bg-violet-950/30"
                >
                  <input
                    type="radio"
                    name="redirect-stage"
                    value={stage.id}
                    checked={selectedStage === stage.id}
                    onChange={() => setSelectedStage(stage.id)}
                    className="accent-violet-500"
                    data-testid={`redirect-stage-radio-${stage.id}`}
                  />
                  <span className="text-xs font-medium text-gray-200">{stage.label}</span>
                  <span className="ml-auto text-xs text-gray-500">Stage {idx + 1}</span>
                </label>
              ))}
            </div>
          )}
        </fieldset>

        {/* Reason textarea */}
        <label className="mb-1 block text-xs font-medium text-gray-300">
          Reason <span className="text-red-400">*</span>
        </label>
        <textarea
          ref={textareaRef}
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          placeholder="e.g. Context was enriched incorrectly, need to re-run intent analysis with updated constraints…"
          rows={3}
          disabled={saving || validTargets.length === 0}
          className="w-full rounded border border-gray-600 bg-gray-800 px-3 py-2 text-sm text-gray-200 placeholder-gray-500 focus:border-blue-500 focus:outline-none disabled:opacity-50"
          data-testid="redirect-reason-input"
        />

        {error && (
          <p className="mt-1 text-xs text-red-400" data-testid="redirect-error">{error}</p>
        )}

        <div className="mt-3 flex items-center justify-between">
          <span className={`text-xs ${charsRemaining > 0 ? 'text-amber-400' : 'text-gray-500'}`}>
            {charsRemaining > 0
              ? `${charsRemaining} more character${charsRemaining === 1 ? '' : 's'} required`
              : `${reason.trim().length} characters`}
          </span>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setRedirectModalOpen(false)}
              disabled={saving}
              className="rounded px-3 py-1.5 text-xs text-gray-400 hover:text-gray-200 disabled:opacity-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
              data-testid="redirect-cancel-btn"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleSubmit}
              disabled={!isValid || saving || validTargets.length === 0}
              className="rounded bg-blue-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-700 disabled:opacity-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-400"
              data-testid="redirect-confirm-btn"
            >
              {saving ? 'Redirecting…' : 'Redirect Task'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// RetryConfirmDialog
// ---------------------------------------------------------------------------

/** Confirmation dialog for retry — re-runs the current stage from the beginning. */
function RetryConfirmDialog() {
  const {
    saving,
    error,
    currentStage,
    retryModalOpen,
    retry,
    setRetryModalOpen,
  } = useSteeringStore()

  const currentLabel =
    PIPELINE_STAGES.find((s) => s.id === currentStage)?.label ?? currentStage ?? 'current stage'

  useEffect(() => {
    if (!retryModalOpen) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setRetryModalOpen(false)
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [retryModalOpen, setRetryModalOpen])

  const handleBackdropClick = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      if (e.target === e.currentTarget) setRetryModalOpen(false)
    },
    [setRetryModalOpen],
  )

  const handleConfirm = useCallback(() => {
    if (saving) return
    void retry()
  }, [retry, saving])

  if (!retryModalOpen) return null

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60"
      onClick={handleBackdropClick}
      data-testid="retry-confirm-backdrop"
    >
      <div
        className="w-full max-w-md rounded-lg border border-amber-800 bg-gray-900 p-6 shadow-xl"
        role="dialog"
        aria-modal="true"
        aria-labelledby="steering-retry-heading"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-4 flex items-center gap-3">
          <span className="text-xl" aria-hidden="true">🔄</span>
          <div>
            <h3 id="steering-retry-heading" className="text-sm font-semibold text-amber-400">
              Retry Stage
            </h3>
            <p className="mt-0.5 text-xs text-gray-400">
              Re-run the <span className="font-medium text-gray-300">{currentLabel}</span> stage from the
              beginning. Existing stage artifacts will be cleared.
            </p>
          </div>
        </div>

        <div className="mb-4 flex items-start gap-2 rounded border border-amber-800/50 bg-amber-950/30 p-3">
          <span className="mt-0.5 text-sm">⚠️</span>
          <p className="text-xs text-amber-300">
            This will clear artifacts from the <strong>{currentLabel}</strong> stage and re-execute it.
            Additional cost will be incurred. The task will remain at the same stage until the retry completes.
          </p>
        </div>

        {error && (
          <p className="mb-3 text-xs text-red-400" data-testid="retry-error">{error}</p>
        )}

        <div className="flex items-center justify-end gap-2">
          <button
            type="button"
            onClick={() => setRetryModalOpen(false)}
            disabled={saving}
            className="rounded px-3 py-1.5 text-xs text-gray-400 hover:text-gray-200 disabled:opacity-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-amber-500"
            data-testid="retry-cancel-btn"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleConfirm}
            disabled={saving}
            className="rounded bg-amber-700 px-3 py-1.5 text-xs font-medium text-amber-100 hover:bg-amber-600 disabled:opacity-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-amber-400"
            data-testid="retry-confirm-btn"
          >
            {saving ? 'Retrying…' : `Retry ${currentLabel}`}
          </button>
        </div>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// SteeringActionBar
// ---------------------------------------------------------------------------

/** SteeringActionBar — pause/resume toggle + abort/redirect/retry buttons. */
export function SteeringActionBar({ taskId, taskStatus, currentStage = null }: SteeringActionBarProps) {
  const {
    steeringStatus,
    saving,
    error,
    init,
    pause,
    resume,
    setAbortModalOpen,
    setRedirectModalOpen,
    setRetryModalOpen,
    clearError,
  } = useSteeringStore()

  // Initialise store whenever taskId, taskStatus, or currentStage changes
  useEffect(() => {
    init(taskId, taskStatus, currentStage)
  }, [taskId, taskStatus, currentStage, init])

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
          <span className="rounded bg-[rgba(239,68,68,0.2)] px-2 py-0.5 text-xs font-medium text-red-500" data-testid="status-aborted">
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

        {/* Redirect button */}
        <button
          onClick={() => setRedirectModalOpen(true)}
          disabled={saving}
          title="Redirect task to an earlier stage"
          className="flex items-center gap-1.5 rounded bg-violet-900/40 px-2.5 py-1 text-xs font-medium text-violet-400 transition-colors hover:bg-violet-800/60 disabled:opacity-50"
          data-testid="redirect-btn"
        >
          <span>↩</span>
          Redirect
        </button>

        {/* Retry button */}
        <button
          onClick={() => setRetryModalOpen(true)}
          disabled={saving}
          title="Retry current stage"
          className="flex items-center gap-1.5 rounded bg-blue-900/40 px-2.5 py-1 text-xs font-medium text-blue-400 transition-colors hover:bg-blue-800/60 disabled:opacity-50"
          data-testid="retry-btn"
        >
          <span>🔄</span>
          Retry
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

      {/* Modals */}
      <AbortConfirmDialog />
      <RedirectModal />
      <RetryConfirmDialog />
    </>
  )
}
