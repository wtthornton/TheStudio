/**
 * Triage card component — displays a single issue awaiting triage (Epic 36).
 *
 * Story 54.3: "Accept & Plan" now triggers the TriageAcceptModal (prompt-first
 * flow) rather than accepting immediately. The card calls `onAcceptIntent` to
 * signal the queue to open the modal; actual acceptance is deferred until the
 * user completes the intent-preview → mode-selection → confirm sequence.
 */

import { useState } from 'react'
import type { TriageTask, RejectionReason } from '../../lib/api'

const REJECTION_REASONS: { value: RejectionReason; label: string }[] = [
  { value: 'duplicate', label: 'Duplicate' },
  { value: 'out_of_scope', label: 'Out of Scope' },
  { value: 'needs_info', label: 'Needs Info' },
  { value: 'wont_fix', label: "Won't Fix" },
]

const COMPLEXITY_COLORS = {
  low: 'bg-[rgba(22,163,74,0.2)] text-green-500',
  medium: 'bg-[rgba(234,179,8,0.2)] text-yellow-500',
  high: 'bg-[rgba(239,68,68,0.2)] text-red-500',
} as const

interface TriageCardProps {
  task: TriageTask
  /**
   * Called when the user clicks "Accept & Plan". The queue opens the
   * TriageAcceptModal (prompt-first flow); actual pipeline acceptance is
   * deferred until the user confirms mode selection.
   */
  onAcceptIntent: (taskId: string) => void
  onReject: (taskId: string, reason: RejectionReason) => void
  onEdit: (taskId: string) => void
}

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  return `${Math.floor(hrs / 24)}d ago`
}

export function TriageCard({ task, onAcceptIntent, onReject, onEdit }: TriageCardProps) {
  const [showReject, setShowReject] = useState(false)
  const enrichment = task.triage_enrichment

  return (
    <div className="rounded-lg border border-gray-700 bg-gray-900 p-4 hover:border-gray-600 transition-colors" data-tour="triage-card" data-component="TriageCard">
      {/* Header */}
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-2 min-w-0">
          <span className="text-gray-500 text-sm shrink-0">#{task.issue_id}</span>
          <h3 className="font-medium text-gray-100 truncate">
            {task.issue_title || 'Untitled issue'}
          </h3>
        </div>
        <span className="text-xs text-gray-500 shrink-0 ml-2">{timeAgo(task.created_at)}</span>
      </div>

      {/* Description */}
      {task.issue_body && (
        <p className="text-sm text-gray-400 mb-3 line-clamp-2">{task.issue_body}</p>
      )}

      {/* Enrichment badges */}
      {enrichment && (
        <div className="flex items-center gap-2 mb-3 text-xs">
          <span className={`px-2 py-0.5 rounded ${COMPLEXITY_COLORS[enrichment.complexity_hint]}`}>
            {enrichment.complexity_hint}
          </span>
          <span className="text-gray-500">
            ~{enrichment.file_count_estimate} file{enrichment.file_count_estimate !== 1 ? 's' : ''}
          </span>
          <span className="text-gray-500">
            ${enrichment.cost_estimate_range.min.toFixed(2)}-${enrichment.cost_estimate_range.max.toFixed(2)}
          </span>
        </div>
      )}

      {/* Action buttons — flex-wrap ensures usability at all breakpoints.
          min-h-[44px] on each button meets WCAG 2.5.5 touch-target minimum. */}
      {showReject ? (
        <div className="flex items-center gap-2 flex-wrap">
          {REJECTION_REASONS.map((r) => (
            <button
              key={r.value}
              onClick={() => { onReject(task.id, r.value); setShowReject(false) }}
              className="min-h-[44px] px-3 py-2 text-xs rounded border border-red-700 text-red-400 hover:bg-red-900/50 active:bg-red-900/70 focus:outline-none focus-visible:ring-2 focus-visible:ring-red-500 focus-visible:ring-offset-2 focus-visible:ring-offset-gray-900"
            >
              {r.label}
            </button>
          ))}
          <button
            onClick={() => setShowReject(false)}
            className="min-h-[44px] px-3 py-2 text-xs text-gray-500 hover:text-gray-300 focus:outline-none focus-visible:ring-2 focus-visible:ring-gray-500 focus-visible:ring-offset-2 focus-visible:ring-offset-gray-900"
          >
            Cancel
          </button>
        </div>
      ) : (
        <div className="flex items-center gap-2 flex-wrap" data-tour="triage-actions">
          <button
            onClick={() => onAcceptIntent(task.id)}
            className="min-h-[44px] px-3 py-2 text-sm rounded bg-blue-600 text-white hover:bg-blue-700 active:bg-blue-800 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 focus-visible:ring-offset-gray-900"
            data-testid="triage-card-accept-intent-btn"
          >
            Accept & Plan
          </button>
          <button
            onClick={() => onEdit(task.id)}
            className="min-h-[44px] px-3 py-2 text-sm rounded border border-blue-700 text-blue-400 hover:bg-blue-900/50 active:bg-blue-900/70 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 focus-visible:ring-offset-gray-900"
          >
            Edit
          </button>
          <button
            onClick={() => setShowReject(true)}
            className="min-h-[44px] px-3 py-2 text-sm rounded border border-red-700 text-red-400 hover:bg-red-900/50 active:bg-red-900/70 focus:outline-none focus-visible:ring-2 focus-visible:ring-red-500 focus-visible:ring-offset-2 focus-visible:ring-offset-gray-900"
          >
            Reject
          </button>
        </div>
      )}
    </div>
  )
}
