/** ReviewerActions — Approve, request changes, close, or view a PR.
 *
 * Epic 38, Story 38.11.
 *
 * Buttons:
 *  - Approve & Merge   — confirmation dialog → POST .../pr/approve
 *  - Request Changes   — textarea form       → POST .../pr/request-changes
 *  - Close PR          — opens PR on GitHub (no backend close endpoint)
 *  - View on GitHub    — opens PR on GitHub
 *
 * All destructive actions require explicit confirmation.
 * Success and error feedback is displayed inline below the actions.
 * Buttons are disabled when the task has no associated PR.
 */

import { useState } from 'react'
import { approvePR, requestChangesPR } from '../../lib/api'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface ReviewerActionsProps {
  taskId: string
  /** PR URL from the TaskPacket — if null/undefined the PR buttons are disabled. */
  prUrl?: string | null
  /** PR number — displayed in confirmation dialogs. */
  prNumber?: number | null
  /** Called after a successful approve-and-merge so the parent can refresh. */
  onApproved?: () => void
  /** Called after a successful request-changes so the parent can refresh. */
  onRequestedChanges?: () => void
}

type UIMode = 'idle' | 'confirm-approve' | 'request-changes-form'

interface Feedback {
  type: 'success' | 'error'
  message: string
}

// ---------------------------------------------------------------------------
// Small helper components
// ---------------------------------------------------------------------------

function ActionButton({
  onClick,
  disabled,
  variant,
  children,
}: {
  onClick: () => void
  disabled?: boolean
  variant: 'primary' | 'danger' | 'secondary'
  children: React.ReactNode
}) {
  const base = 'px-4 py-2 rounded text-sm font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-offset-1 focus:ring-offset-gray-900 disabled:opacity-40 disabled:cursor-not-allowed'
  const colors: Record<string, string> = {
    primary: 'bg-green-700 hover:bg-green-600 text-white focus:ring-green-500',
    danger: 'bg-red-700 hover:bg-red-600 text-white focus:ring-red-500',
    secondary: 'bg-gray-700 hover:bg-gray-600 text-gray-200 focus:ring-gray-500',
  }
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`${base} ${colors[variant]}`}
    >
      {children}
    </button>
  )
}

function GhostButton({
  onClick,
  children,
}: {
  onClick: () => void
  children: React.ReactNode
}) {
  return (
    <button
      onClick={onClick}
      className="px-3 py-1.5 rounded text-sm text-gray-400 hover:text-gray-200 hover:bg-gray-800 transition-colors"
    >
      {children}
    </button>
  )
}

// ---------------------------------------------------------------------------
// Confirm-approve panel
// ---------------------------------------------------------------------------

function ConfirmApprovePanel({
  prNumber,
  onConfirm,
  onCancel,
  loading,
}: {
  prNumber?: number | null
  onConfirm: () => void
  onCancel: () => void
  loading: boolean
}) {
  return (
    <div className="border border-yellow-700 bg-yellow-950 rounded p-4 space-y-3">
      <p className="text-sm text-yellow-200 font-medium">
        Confirm: Approve &amp; Merge PR{prNumber ? ` #${prNumber}` : ''}?
      </p>
      <p className="text-xs text-yellow-400">
        This will perform a squash merge. This action cannot be undone.
      </p>
      <div className="flex gap-2">
        <ActionButton onClick={onConfirm} disabled={loading} variant="primary">
          {loading ? 'Merging…' : 'Confirm Merge'}
        </ActionButton>
        <GhostButton onClick={onCancel}>Cancel</GhostButton>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Request-changes form panel
// ---------------------------------------------------------------------------

function RequestChangesPanel({
  onSubmit,
  onCancel,
  loading,
}: {
  onSubmit: (body: string, triggerLoopback: boolean) => void
  onCancel: () => void
  loading: boolean
}) {
  const [body, setBody] = useState('')
  const [triggerLoopback, setTriggerLoopback] = useState(false)

  function handleSubmit() {
    if (!body.trim()) return
    onSubmit(body.trim(), triggerLoopback)
  }

  return (
    <div className="border border-gray-600 bg-gray-800 rounded p-4 space-y-3">
      <p className="text-sm text-gray-200 font-medium">Request Changes</p>
      <textarea
        value={body}
        onChange={(e) => setBody(e.target.value)}
        placeholder="Describe the changes needed…"
        rows={4}
        className="w-full rounded bg-gray-900 border border-gray-600 text-sm text-gray-200 placeholder-gray-600 px-3 py-2 focus:outline-none focus:ring-1 focus:ring-blue-500 resize-y"
        disabled={loading}
      />
      <label className="flex items-center gap-2 text-xs text-gray-400 cursor-pointer select-none">
        <input
          type="checkbox"
          checked={triggerLoopback}
          onChange={(e) => setTriggerLoopback(e.target.checked)}
          disabled={loading}
          className="rounded border-gray-600 bg-gray-900 text-blue-500 focus:ring-blue-500"
        />
        Trigger workflow loopback (retry current pipeline stage)
      </label>
      <div className="flex gap-2">
        <ActionButton
          onClick={handleSubmit}
          disabled={loading || !body.trim()}
          variant="secondary"
        >
          {loading ? 'Submitting…' : 'Submit Review'}
        </ActionButton>
        <GhostButton onClick={onCancel}>Cancel</GhostButton>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Feedback banner
// ---------------------------------------------------------------------------

function FeedbackBanner({
  feedback,
  onDismiss,
}: {
  feedback: Feedback
  onDismiss: () => void
}) {
  const isSuccess = feedback.type === 'success'
  const containerClass = isSuccess
    ? 'border border-green-700 bg-green-950 text-green-300'
    : 'border border-red-700 bg-red-950 text-red-300'

  return (
    <div className={`rounded p-3 flex items-start justify-between gap-3 text-sm ${containerClass}`}>
      <span>{feedback.message}</span>
      <button
        onClick={onDismiss}
        aria-label="Dismiss"
        className="shrink-0 text-xs opacity-60 hover:opacity-100"
      >
        ✕
      </button>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export default function ReviewerActions({
  taskId,
  prUrl,
  prNumber,
  onApproved,
  onRequestedChanges,
}: ReviewerActionsProps) {
  const [mode, setMode] = useState<UIMode>('idle')
  const [loading, setLoading] = useState(false)
  const [feedback, setFeedback] = useState<Feedback | null>(null)

  const hasPR = Boolean(prUrl)

  // ---- Approve & Merge ----

  async function handleApproveConfirm() {
    setLoading(true)
    try {
      const result = await approvePR(taskId)
      setFeedback({
        type: 'success',
        message: result.message ?? `PR #${result.pr_number} merged successfully.`,
      })
      setMode('idle')
      onApproved?.()
    } catch (err: unknown) {
      setFeedback({
        type: 'error',
        message: err instanceof Error ? err.message : 'Approve failed — unknown error.',
      })
      setMode('idle')
    } finally {
      setLoading(false)
    }
  }

  // ---- Request Changes ----

  async function handleRequestChangesSubmit(body: string, triggerLoopback: boolean) {
    setLoading(true)
    try {
      const result = await requestChangesPR(taskId, body, triggerLoopback)
      setFeedback({
        type: 'success',
        message:
          result.message ??
          `Review submitted on PR #${result.pr_number}.` +
            (triggerLoopback ? ' Loopback signal sent.' : ''),
      })
      setMode('idle')
      onRequestedChanges?.()
    } catch (err: unknown) {
      setFeedback({
        type: 'error',
        message: err instanceof Error ? err.message : 'Request-changes failed — unknown error.',
      })
      setMode('idle')
    } finally {
      setLoading(false)
    }
  }

  // ---- Render ----

  return (
    <div className="space-y-3">
      {/* Feedback banner */}
      {feedback && (
        <FeedbackBanner feedback={feedback} onDismiss={() => setFeedback(null)} />
      )}

      {/* No-PR notice */}
      {!hasPR && (
        <p className="text-xs text-gray-500 italic">
          No pull request associated with this task yet. Actions will be enabled once a PR is
          published.
        </p>
      )}

      {/* Confirm-approve panel */}
      {mode === 'confirm-approve' && (
        <ConfirmApprovePanel
          prNumber={prNumber}
          onConfirm={handleApproveConfirm}
          onCancel={() => setMode('idle')}
          loading={loading}
        />
      )}

      {/* Request-changes form */}
      {mode === 'request-changes-form' && (
        <RequestChangesPanel
          onSubmit={handleRequestChangesSubmit}
          onCancel={() => setMode('idle')}
          loading={loading}
        />
      )}

      {/* Primary action buttons (shown when idle) */}
      {mode === 'idle' && (
        <div className="flex flex-wrap gap-2">
          {/* Approve & Merge */}
          <ActionButton
            onClick={() => setMode('confirm-approve')}
            disabled={!hasPR || loading}
            variant="primary"
          >
            ✓ Approve &amp; Merge
          </ActionButton>

          {/* Request Changes */}
          <ActionButton
            onClick={() => setMode('request-changes-form')}
            disabled={!hasPR || loading}
            variant="secondary"
          >
            ↩ Request Changes
          </ActionButton>

          {/* Close PR — opens GitHub; no backend close endpoint */}
          {prUrl ? (
            <a
              href={prUrl}
              target="_blank"
              rel="noopener noreferrer"
              title="Close on GitHub — opens the PR page where you can close it"
              className="px-4 py-2 rounded text-sm font-medium bg-gray-700 hover:bg-gray-600 text-red-400 hover:text-red-300 transition-colors"
            >
              ✕ Close PR ↗
            </a>
          ) : (
            <button
              disabled
              className="px-4 py-2 rounded text-sm font-medium bg-gray-700 text-red-400 opacity-40 cursor-not-allowed"
            >
              ✕ Close PR
            </button>
          )}

          {/* View on GitHub */}
          {prUrl ? (
            <a
              href={prUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="px-4 py-2 rounded text-sm font-medium bg-gray-700 hover:bg-gray-600 text-blue-400 hover:text-blue-300 transition-colors"
            >
              View on GitHub ↗
            </a>
          ) : (
            <button
              disabled
              className="px-4 py-2 rounded text-sm font-medium bg-gray-700 text-blue-400 opacity-40 cursor-not-allowed"
            >
              View on GitHub
            </button>
          )}
        </div>
      )}
    </div>
  )
}
