/** ExpertCard — displays a single expert selection (Epic 36, Story 36.15b). */

import type { ExpertSelectionRead } from '../../lib/api'

export interface ExpertCardProps {
  selection: ExpertSelectionRead
  /** Only provided for AUTO experts — omit for MANDATORY. */
  onRemove?: () => void
}

/* ── helpers ─────────────────────────────────────────────────── */

function weightColor(weight: number): string {
  if (weight >= 0.7) return 'text-emerald-400'
  if (weight >= 0.4) return 'text-amber-400'
  return 'text-red-400'
}

function LockIcon() {
  return (
    <svg
      className="inline h-3 w-3"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      strokeWidth={2}
      aria-label="Mandatory"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"
      />
    </svg>
  )
}

/* ── component ───────────────────────────────────────────────── */

export default function ExpertCard({ selection, onRemove }: ExpertCardProps) {
  const isMandatory = selection.selection_reason === 'MANDATORY'

  return (
    <div className="rounded-lg border border-gray-700 bg-gray-900 p-4">
      {/* Header row */}
      <div className="flex items-center justify-between gap-2 mb-3">
        <div className="flex items-center gap-2">
          {/* Expert class badge */}
          <span className="bg-blue-900 text-blue-300 text-xs px-2 py-0.5 rounded font-medium">
            {selection.expert_class}
          </span>

          {/* Selection reason badge */}
          {isMandatory ? (
            <span className="flex items-center gap-1 bg-gray-700 text-gray-300 text-xs px-2 py-0.5 rounded">
              <LockIcon />
              MANDATORY
            </span>
          ) : (
            <span className="bg-gray-800 text-gray-400 text-xs px-2 py-0.5 rounded">
              AUTO
            </span>
          )}
        </div>

        {/* Remove button — AUTO experts only */}
        {!isMandatory && onRemove && (
          <button
            onClick={onRemove}
            className="text-red-400 hover:text-red-300 text-xs transition-colors"
          >
            Remove
          </button>
        )}
      </div>

      {/* Pattern */}
      <p className="text-sm text-gray-400 mb-2">
        Pattern:{' '}
        <span className="text-gray-300">{selection.pattern}</span>
      </p>

      {/* Reputation row */}
      <div className="flex items-center gap-4 mb-2 text-sm">
        <span className={weightColor(selection.reputation_weight)}>
          Weight: {selection.reputation_weight.toFixed(2)}
        </span>
        <span className="text-gray-400">
          Confidence: {selection.reputation_confidence.toFixed(2)}
        </span>
      </div>

      {/* Score */}
      <p className="text-sm font-semibold text-gray-200">
        Score: {selection.selection_score.toFixed(2)}
      </p>
    </div>
  )
}
