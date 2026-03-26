/** RoutingPreview — container for routing review (Epic 36, Story 36.15b+c). */

import { useEffect } from 'react'
import { useRoutingStore } from '../../stores/routing-store'
import ExpertCard from './ExpertCard'
import AddExpertDropdown from './AddExpertDropdown'
import { EmptyState } from '../EmptyState'

function RoutingIcon() {
  return (
    <svg width="48" height="48" viewBox="0 0 48 48" fill="none" className="text-gray-500">
      <circle cx="8" cy="24" r="4" stroke="currentColor" strokeWidth="2" />
      <circle cx="40" cy="12" r="4" stroke="currentColor" strokeWidth="2" />
      <circle cx="40" cy="36" r="4" stroke="currentColor" strokeWidth="2" />
      <line x1="12" y1="22" x2="36" y2="14" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      <line x1="12" y1="26" x2="36" y2="34" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  )
}

export interface RoutingPreviewProps {
  taskId: string
  onClose?: () => void
  /** Called when the user clicks the "Go to Pipeline" CTA (no-routing empty state). */
  onNavigateToPipeline?: () => void
}

/* ── icons ───────────────────────────────────────────────────── */

function SpinnerIcon() {
  return (
    <svg
      className="h-5 w-5 animate-spin text-gray-400"
      fill="none"
      viewBox="0 0 24 24"
    >
      <circle
        className="opacity-25"
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="4"
      />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
      />
    </svg>
  )
}

/* ── component ───────────────────────────────────────────────── */

export default function RoutingPreview({ taskId, onClose, onNavigateToPipeline }: RoutingPreviewProps) {
  const { routing, loading, error, saving, loadRouting, approve, override } =
    useRoutingStore()

  useEffect(() => {
    void loadRouting(taskId)
  }, [taskId, loadRouting])

  /* Loading */
  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <SpinnerIcon />
        <span className="ml-2 text-sm text-gray-400">Loading routing data…</span>
      </div>
    )
  }

  /* Error */
  if (error) {
    return (
      <div className="rounded-lg border border-red-800 bg-red-950 p-4">
        <p className="text-sm text-red-400 mb-3">{error}</p>
        <button
          onClick={() => void loadRouting(taskId)}
          className="text-xs text-red-300 hover:text-red-200 underline"
        >
          Retry
        </button>
      </div>
    )
  }

  /* No data yet */
  if (!routing) {
    return (
      <EmptyState
        icon={<RoutingIcon />}
        heading="No Routing Data Yet"
        description="Expert routing hasn't been assigned for this task. Once the Router stage runs, you'll see which experts are selected and why."
        primaryAction={
          onNavigateToPipeline
            ? { label: 'Go to Pipeline', onClick: onNavigateToPipeline }
            : undefined
        }
        data-testid="routing-empty-state"
      />
    )
  }

  const handleRemoveExpert = (expertClass: string) => {
    void override(`remove:${expertClass}`)
  }

  const handleAddExpert = (expertClass: string) => {
    void override(`add:${expertClass}`)
  }

  return (
    <div className="space-y-4" data-tour="routing-preview" data-component="RoutingPreview">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h2 className="text-base font-semibold text-gray-100">Expert Routing Review</h2>
          <span className="bg-gray-800 text-gray-400 text-xs px-2 py-0.5 rounded font-mono">
            {taskId.slice(0, 8)}…
          </span>
        </div>
        {onClose && (
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-300 text-sm transition-colors"
          >
            ✕
          </button>
        )}
      </div>

      {/* Rationale */}
      {routing.rationale && (
        <div className="rounded-lg border border-gray-700 bg-gray-800 p-3">
          <p className="text-xs font-semibold uppercase tracking-wider text-gray-500 mb-1">
            Rationale
          </p>
          <p className="text-sm text-gray-400 italic">{routing.rationale}</p>
        </div>
      )}

      {/* Expert cards grid */}
      {routing.selections.length === 0 ? (
        <div className="rounded-lg border border-gray-700 bg-gray-900 p-6 text-center">
          <p className="text-sm text-gray-500">No experts selected.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {routing.selections.map((sel) => {
            const isMandatory = sel.selection_reason === 'MANDATORY'
            return (
              <ExpertCard
                key={sel.expert_id}
                selection={sel}
                onRemove={
                  isMandatory
                    ? undefined
                    : () => handleRemoveExpert(sel.expert_class)
                }
              />
            )
          })}
        </div>
      )}

      {/* Budget remaining */}
      <div className="flex items-center gap-2">
        <span className="bg-gray-800 text-gray-300 text-xs px-2 py-1 rounded">
          Budget: {routing.budget_remaining} expert slot
          {routing.budget_remaining !== 1 ? 's' : ''} remaining
        </span>
      </div>

      {/* Action bar */}
      <div className="flex items-center justify-between gap-3 pt-2 border-t border-gray-700">
        <div>
          <AddExpertDropdown
            selectedClasses={routing.selections.map((s) => s.expert_class)}
            onAdd={handleAddExpert}
            disabled={saving}
          />
        </div>

        <button
          onClick={() => void approve()}
          disabled={saving}
          className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm font-medium px-4 py-1.5 rounded transition-colors"
        >
          {saving ? 'Approving…' : 'Approve Routing'}
        </button>
      </div>
    </div>
  )
}
