/** IntentEditor — container for intent review workflow (Epic 36, 36.11d). */

import { useEffect, useState, useCallback } from 'react'
import { useIntentStore } from '../../stores/intent-store'
import { fetchTaskDetail } from '../../lib/api'
import type { TaskPacketRead } from '../../lib/api'
import SourceContext from './SourceContext'
import IntentSpec from './IntentSpec'
import IntentEditMode from './IntentEditMode'
import VersionSelector from './VersionSelector'
import RefinementModal from './RefinementModal'
import VersionDiff from './VersionDiff'
import { EmptyState } from '../EmptyState'

function IntentIcon() {
  return (
    <svg width="48" height="48" viewBox="0 0 48 48" fill="none" className="text-gray-500">
      <rect x="8" y="6" width="32" height="36" rx="3" stroke="currentColor" strokeWidth="2" />
      <line x1="14" y1="16" x2="34" y2="16" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      <line x1="14" y1="22" x2="34" y2="22" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      <line x1="14" y1="28" x2="26" y2="28" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      <circle cx="36" cy="34" r="6" fill="none" stroke="currentColor" strokeWidth="2" />
      <path d="M33 34l2 2 4-4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

interface IntentEditorProps {
  taskId: string
  /** Called when the user clicks the "Go to Pipeline" CTA (no-intent empty state). */
  onNavigateToPipeline?: () => void
}

export default function IntentEditor({ taskId, onNavigateToPipeline }: IntentEditorProps) {
  const [task, setTask] = useState<TaskPacketRead | null>(null)
  const [taskLoading, setTaskLoading] = useState(true)
  const [taskError, setTaskError] = useState<string | null>(null)

  // Reject confirmation state
  const [rejectOpen, setRejectOpen] = useState(false)
  const [rejectReason, setRejectReason] = useState('')

  // Diff mode state
  const [diffMode, setDiffMode] = useState(false)
  const [diffBaseVersion, setDiffBaseVersion] = useState<number | null>(null)

  const {
    current,
    versions,
    selectedVersion,
    loading,
    error,
    saving,
    mode,
    refineModalOpen,
    loadIntent,
    approve,
    reject,
    requestRefine,
    selectVersion,
    setMode,
    setRefineModalOpen,
    reset,
  } = useIntentStore()

  // Fetch task detail
  useEffect(() => {
    let cancelled = false
    setTaskLoading(true)
    setTaskError(null)
    fetchTaskDetail(taskId)
      .then((data) => {
        if (!cancelled) {
          setTask(data)
          setTaskLoading(false)
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setTaskError(err instanceof Error ? err.message : 'Failed to load task')
          setTaskLoading(false)
        }
      })
    return () => { cancelled = true }
  }, [taskId])

  // Fetch intent
  useEffect(() => {
    loadIntent(taskId)
    return () => { reset() }
  }, [taskId, loadIntent, reset])

  const handleApprove = useCallback(async () => {
    await approve()
  }, [approve])

  const handleRejectConfirm = useCallback(async () => {
    if (!rejectReason.trim()) return
    await reject(rejectReason.trim())
    setRejectOpen(false)
    setRejectReason('')
  }, [reject, rejectReason])

  const handleEdit = useCallback(() => {
    setMode('edit')
  }, [setMode])

  const handleRefine = useCallback(() => {
    setRefineModalOpen(true)
  }, [setRefineModalOpen])

  // Loading state
  if (taskLoading || loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-sm text-gray-400">Loading intent review…</div>
      </div>
    )
  }

  // Error state
  if (taskError || error) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="rounded border border-red-800 bg-red-900/30 px-4 py-3 text-sm text-red-300">
          {taskError || error}
        </div>
      </div>
    )
  }

  // No intent yet
  if (!current) {
    return (
      <EmptyState
        icon={<IntentIcon />}
        heading="No Intent Specification Yet"
        description="This task hasn't been through the Intent Builder yet. Once the pipeline processes the issue, you'll be able to review and approve the intent spec here."
        primaryAction={
          onNavigateToPipeline
            ? { label: 'Go to Pipeline', onClick: onNavigateToPipeline }
            : undefined
        }
        data-testid="intent-empty-state"
      />
    )
  }

  return (
    <div className="flex flex-col gap-4">
      {/* Toolbar: version selector + action buttons */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <VersionSelector
            versions={versions}
            selectedVersion={selectedVersion}
            onSelect={selectVersion}
          />
          {versions.length >= 2 && (
            <button
              onClick={() => {
                if (!diffMode && current) {
                  // Default: compare previous version to current
                  const currentIdx = versions.findIndex((v) => v.version === current.version)
                  const prevVersion = currentIdx > 0 ? versions[currentIdx - 1] : versions[0]
                  setDiffBaseVersion(prevVersion.version)
                }
                setDiffMode(!diffMode)
              }}
              className={`rounded px-2 py-1 text-xs font-medium ${
                diffMode
                  ? 'bg-amber-700 text-amber-100'
                  : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
              }`}
              data-testid="compare-toggle"
            >
              {diffMode ? 'Hide Diff' : 'Compare Versions'}
            </button>
          )}
          {diffMode && (
            <select
              value={diffBaseVersion ?? ''}
              onChange={(e) => setDiffBaseVersion(Number(e.target.value))}
              className="rounded border border-gray-600 bg-gray-800 px-2 py-1 text-xs text-gray-300 focus:border-amber-500 focus:outline-none"
              data-testid="diff-base-selector"
            >
              {versions
                .filter((v) => v.version !== (selectedVersion ?? current?.version))
                .map((v) => (
                  <option key={v.version} value={v.version}>
                    v{v.version} — {v.source}
                  </option>
                ))}
            </select>
          )}
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleApprove}
            disabled={saving}
            className="rounded bg-emerald-700 px-3 py-1.5 text-xs font-medium text-emerald-100 hover:bg-emerald-600 disabled:opacity-50"
          >
            {saving ? 'Saving…' : 'Approve'}
          </button>
          <button
            onClick={handleEdit}
            disabled={saving || mode === 'edit'}
            className="rounded bg-blue-700 px-3 py-1.5 text-xs font-medium text-blue-100 hover:bg-blue-600 disabled:opacity-50"
          >
            Edit
          </button>
          <button
            onClick={handleRefine}
            disabled={saving}
            className="rounded bg-purple-700 px-3 py-1.5 text-xs font-medium text-purple-100 hover:bg-purple-600 disabled:opacity-50"
          >
            Refine
          </button>
          {rejectOpen ? (
            <div className="flex items-center gap-1">
              <input
                type="text"
                value={rejectReason}
                onChange={(e) => setRejectReason(e.target.value)}
                placeholder="Rejection reason…"
                className="rounded border border-gray-600 bg-gray-800 px-2 py-1 text-xs text-gray-200 placeholder-gray-500 focus:border-red-500 focus:outline-none"
                autoFocus
                onKeyDown={(e) => {
                  if (e.key === 'Enter') handleRejectConfirm()
                  if (e.key === 'Escape') { setRejectOpen(false); setRejectReason('') }
                }}
              />
              <button
                onClick={handleRejectConfirm}
                disabled={!rejectReason.trim() || saving}
                className="rounded bg-red-700 px-2 py-1 text-xs font-medium text-red-100 hover:bg-red-600 disabled:opacity-50"
              >
                Confirm
              </button>
              <button
                onClick={() => { setRejectOpen(false); setRejectReason('') }}
                className="rounded px-2 py-1 text-xs text-gray-400 hover:text-gray-200"
              >
                Cancel
              </button>
            </div>
          ) : (
            <button
              onClick={() => setRejectOpen(true)}
              disabled={saving}
              className="rounded bg-red-800 px-3 py-1.5 text-xs font-medium text-red-200 hover:bg-red-700 disabled:opacity-50"
            >
              Reject
            </button>
          )}
        </div>
      </div>

      {/* Split pane: source context (left) + intent spec (right) */}
      <div className="grid grid-cols-[2fr_3fr] gap-4">
        {/* Left panel: source context */}
        <div className="rounded-lg border border-gray-700 bg-gray-900 p-4">
          {task ? (
            <SourceContext task={task} />
          ) : (
            <div className="text-sm text-gray-500 italic">Task not available</div>
          )}
        </div>

        {/* Right panel: intent spec (view), edit form, or version diff */}
        <div className="rounded-lg border border-gray-700 bg-gray-900 p-4">
          {diffMode && diffBaseVersion != null ? (
            (() => {
              const baseSpec = versions.find((v) => v.version === diffBaseVersion)
              if (!baseSpec) return <IntentSpec spec={current} />
              return <VersionDiff left={baseSpec} right={current} />
            })()
          ) : mode === 'edit' ? (
            <IntentEditMode spec={current} />
          ) : (
            <IntentSpec spec={current} />
          )}
        </div>
      </div>

      {/* Refinement modal */}
      <RefinementModal
        open={refineModalOpen}
        saving={saving}
        onSubmit={requestRefine}
        onClose={() => setRefineModalOpen(false)}
      />
    </div>
  )
}
