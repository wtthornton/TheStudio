/** IntentEditor — container for intent review workflow (Epic 36, 36.11d). */

import { useEffect, useState, useCallback } from 'react'
import { useIntentStore } from '../../stores/intent-store'
import { fetchTaskDetail } from '../../lib/api'
import type { TaskPacketRead } from '../../lib/api'
import SourceContext from './SourceContext'
import IntentSpec from './IntentSpec'
import VersionSelector from './VersionSelector'

interface IntentEditorProps {
  taskId: string
}

export default function IntentEditor({ taskId }: IntentEditorProps) {
  const [task, setTask] = useState<TaskPacketRead | null>(null)
  const [taskLoading, setTaskLoading] = useState(true)
  const [taskError, setTaskError] = useState<string | null>(null)

  // Reject confirmation state
  const [rejectOpen, setRejectOpen] = useState(false)
  const [rejectReason, setRejectReason] = useState('')

  const {
    current,
    versions,
    selectedVersion,
    loading,
    error,
    saving,
    mode,
    loadIntent,
    approve,
    reject,
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
      <div className="flex items-center justify-center py-20">
        <div className="text-sm text-gray-500 italic">
          No intent specification found for this task.
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-4">
      {/* Toolbar: version selector + action buttons */}
      <div className="flex items-center justify-between">
        <VersionSelector
          versions={versions}
          selectedVersion={selectedVersion}
          onSelect={selectVersion}
        />

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

        {/* Right panel: intent spec (view mode) */}
        <div className="rounded-lg border border-gray-700 bg-gray-900 p-4">
          <IntentSpec spec={current} />
        </div>
      </div>
    </div>
  )
}
