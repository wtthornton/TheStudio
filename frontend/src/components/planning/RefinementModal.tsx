/** RefinementModal — modal overlay for requesting AI refinement (Epic 36, 36.11f). */

import { useState, useCallback, useEffect, useRef } from 'react'

interface RefinementModalProps {
  open: boolean
  saving: boolean
  onSubmit: (feedback: string) => void
  onClose: () => void
}

const MIN_FEEDBACK_LENGTH = 10

export default function RefinementModal({ open, saving, onSubmit, onClose }: RefinementModalProps) {
  const [feedback, setFeedback] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const isValid = feedback.trim().length >= MIN_FEEDBACK_LENGTH

  // Focus textarea when modal opens
  useEffect(() => {
    if (open) {
      setFeedback('')
      // Defer focus to next frame so DOM is ready
      requestAnimationFrame(() => {
        textareaRef.current?.focus()
      })
    }
  }, [open])

  // Escape key closes modal (not while saving)
  useEffect(() => {
    if (!open) return
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !saving) {
        onClose()
      }
    }
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [open, saving, onClose])

  const handleSubmit = useCallback(() => {
    if (!isValid || saving) return
    onSubmit(feedback.trim())
  }, [feedback, isValid, saving, onSubmit])

  const handleBackdropClick = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      if (e.target === e.currentTarget && !saving) {
        onClose()
      }
    },
    [saving, onClose],
  )

  if (!open) return null

  const charsRemaining = MIN_FEEDBACK_LENGTH - feedback.trim().length

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60"
      onClick={handleBackdropClick}
      data-testid="refinement-modal-backdrop"
      role="presentation"
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="refinement-modal-title"
        className="w-full max-w-lg rounded-lg border border-gray-700 bg-gray-900 p-6 shadow-xl"
      >
        <h3 id="refinement-modal-title" className="mb-1 text-sm font-semibold text-gray-100">
          Request AI Refinement
        </h3>
        <p className="mb-4 text-xs text-gray-400">
          Describe what should be changed or improved in the intent specification.
        </p>

        <textarea
          ref={textareaRef}
          value={feedback}
          onChange={(e) => setFeedback(e.target.value)}
          placeholder="e.g. Add error handling for network timeouts, clarify the caching strategy…"
          rows={5}
          disabled={saving}
          className="w-full rounded border border-gray-600 bg-gray-800 px-3 py-2 text-sm text-gray-200 placeholder-gray-500 focus:border-purple-500 focus:outline-none disabled:opacity-50"
          data-testid="refinement-feedback"
        />

        <div className="mt-2 flex items-center justify-between">
          <span className={`text-xs ${charsRemaining > 0 ? 'text-amber-400' : 'text-gray-500'}`}>
            {charsRemaining > 0
              ? `${charsRemaining} more character${charsRemaining === 1 ? '' : 's'} needed`
              : `${feedback.trim().length} characters`}
          </span>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={onClose}
              disabled={saving}
              className="rounded px-3 py-1.5 text-xs text-gray-400 hover:text-gray-200 disabled:opacity-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-purple-500 focus-visible:ring-offset-2 focus-visible:ring-offset-gray-900"
              data-testid="refinement-cancel"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleSubmit}
              disabled={!isValid || saving}
              className="rounded bg-purple-700 px-3 py-1.5 text-xs font-medium text-purple-100 hover:bg-purple-600 disabled:opacity-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-purple-500 focus-visible:ring-offset-2 focus-visible:ring-offset-gray-900"
              data-testid="refinement-submit"
            >
              {saving ? 'Refining…' : 'Submit'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
