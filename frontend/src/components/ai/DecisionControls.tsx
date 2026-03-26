/**
 * DecisionControls — Human decision bar for AI action outcomes.
 *
 * Per SG 8.1 step 5: "approve, edit, retry, or reject".
 * Per SG 8.5: high-impact actions (approve in execute mode) show confirmation dialog.
 *
 * Epic 55.2
 */

import { useState, useCallback, useEffect, useRef } from 'react'

interface DecisionControlsProps {
  onApprove: () => void
  onEdit: () => void
  onRetry: () => void
  onReject: () => void
  disabledActions?: Partial<{
    approve: boolean
    edit: boolean
    retry: boolean
    reject: boolean
  }>
  /** When true, Approve triggers a confirmation dialog first (SG 8.5) */
  requireConfirmation?: boolean
}

export function DecisionControls({
  onApprove,
  onEdit,
  onRetry,
  onReject,
  disabledActions = {},
  requireConfirmation = false,
}: DecisionControlsProps) {
  const [confirmOpen, setConfirmOpen] = useState(false)
  const confirmRef = useRef<HTMLDivElement>(null)

  const handleApprove = useCallback(() => {
    if (requireConfirmation) {
      setConfirmOpen(true)
    } else {
      onApprove()
    }
  }, [requireConfirmation, onApprove])

  const handleConfirmApprove = useCallback(() => {
    setConfirmOpen(false)
    onApprove()
  }, [onApprove])

  // Close confirmation on Escape
  useEffect(() => {
    if (!confirmOpen) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setConfirmOpen(false)
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [confirmOpen])

  return (
    <div className="relative" data-testid="decision-controls">
      <nav
        aria-label="Decision actions"
        className="flex items-center gap-2 rounded-lg border border-gray-700 bg-gray-900 px-4 py-2.5"
      >
        {/* Approve */}
        <button
          type="button"
          onClick={handleApprove}
          disabled={!!disabledActions.approve}
          className="flex items-center gap-1.5 rounded bg-blue-600 px-3 py-1.5 text-xs font-medium text-white transition-colors hover:bg-blue-700 disabled:opacity-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-400"
          data-testid="decision-approve-btn"
        >
          <span aria-hidden="true">&#x2713;</span>
          Approve
        </button>

        {/* Edit */}
        <button
          type="button"
          onClick={onEdit}
          disabled={!!disabledActions.edit}
          className="flex items-center gap-1.5 rounded bg-blue-800/60 px-3 py-1.5 text-xs font-medium text-blue-300 transition-colors hover:bg-blue-700/60 disabled:opacity-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-400"
          data-testid="decision-edit-btn"
        >
          <span aria-hidden="true">&#x270E;</span>
          Edit
        </button>

        {/* Retry */}
        <button
          type="button"
          onClick={onRetry}
          disabled={!!disabledActions.retry}
          className="flex items-center gap-1.5 rounded bg-amber-800/60 px-3 py-1.5 text-xs font-medium text-amber-300 transition-colors hover:bg-amber-700/60 disabled:opacity-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-amber-400"
          data-testid="decision-retry-btn"
        >
          <span aria-hidden="true">&#x21BB;</span>
          Retry
        </button>

        {/* Reject */}
        <button
          type="button"
          onClick={onReject}
          disabled={!!disabledActions.reject}
          className="flex items-center gap-1.5 rounded bg-red-800/60 px-3 py-1.5 text-xs font-medium text-red-300 transition-colors hover:bg-red-700/60 disabled:opacity-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-red-400"
          data-testid="decision-reject-btn"
        >
          <span aria-hidden="true">&#x2715;</span>
          Reject
        </button>
      </nav>

      {/* SG 8.5: Confirmation dialog for high-impact approve */}
      {confirmOpen && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60"
          onClick={(e) => {
            if (e.target === e.currentTarget) setConfirmOpen(false)
          }}
          data-testid="decision-confirm-backdrop"
        >
          <div
            ref={confirmRef}
            role="dialog"
            aria-modal="true"
            aria-labelledby="decision-confirm-heading"
            className="w-full max-w-sm rounded-lg border border-emerald-800 bg-gray-900 p-5 shadow-xl"
            onClick={(e) => e.stopPropagation()}
          >
            <h3
              id="decision-confirm-heading"
              className="mb-2 text-sm font-semibold text-gray-100"
            >
              Confirm Approval
            </h3>
            <p className="mb-4 text-xs text-gray-400">
              This action will be applied. Please confirm you have reviewed the output and are
              ready to proceed.
            </p>
            <div className="flex items-center justify-end gap-2">
              <button
                type="button"
                onClick={() => setConfirmOpen(false)}
                className="rounded px-3 py-1.5 text-xs text-gray-400 hover:text-gray-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-gray-500"
                data-testid="decision-confirm-cancel-btn"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleConfirmApprove}
                className="rounded bg-blue-600 px-4 py-1.5 text-xs font-medium text-white hover:bg-blue-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-400"
                data-testid="decision-confirm-approve-btn"
              >
                Confirm Approval
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
