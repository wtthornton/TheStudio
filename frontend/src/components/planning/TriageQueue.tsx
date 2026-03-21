/** Triage queue — list of issues awaiting developer review (Epic 36). */

import { useEffect, useState, useCallback } from 'react'
import { useTriageStore } from '../../stores/triage-store'
import { TriageCard } from './TriageCard'
import { EditPanel } from './EditPanel'
import type { RejectionReason } from '../../lib/api'

export function TriageQueue() {
  const { tasks, loading, error, loadTasks, accept, reject, edit } = useTriageStore()
  const [editingTaskId, setEditingTaskId] = useState<string | null>(null)

  useEffect(() => {
    void loadTasks()
  }, [loadTasks])

  const handleAccept = useCallback((taskId: string) => {
    void accept(taskId)
  }, [accept])

  const handleReject = useCallback((taskId: string, reason: RejectionReason) => {
    void reject(taskId, reason)
  }, [reject])

  const handleEdit = useCallback((taskId: string) => {
    setEditingTaskId(taskId)
  }, [])

  const handleSave = useCallback(async (taskId: string, fields: { issue_title?: string; issue_body?: string }) => {
    if (Object.keys(fields).length > 0) {
      await edit(taskId, fields)
    }
  }, [edit])

  const handleSaveAndAccept = useCallback(async (taskId: string, fields: { issue_title?: string; issue_body?: string }) => {
    if (Object.keys(fields).length > 0) {
      await edit(taskId, fields)
    }
    await accept(taskId)
    setEditingTaskId(null)
  }, [edit, accept])

  const editingTask = editingTaskId ? tasks.find((t) => t.id === editingTaskId) : null

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12 text-gray-500">
        <svg className="animate-spin h-5 w-5 mr-2" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
        Loading triage queue...
      </div>
    )
  }

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-gray-100">
          Triage Queue
          {tasks.length > 0 && (
            <span className="ml-2 text-sm font-normal text-gray-500">({tasks.length})</span>
          )}
        </h2>
      </div>

      {/* Error */}
      {error && (
        <div className="mb-4 p-3 rounded border border-red-700 bg-red-900/30 text-red-400 text-sm">
          {error}
          <button onClick={() => void loadTasks()} className="ml-2 underline">Retry</button>
        </div>
      )}

      {/* Empty state */}
      {tasks.length === 0 && !error && (
        <div className="text-center py-12 text-gray-500">
          <p className="text-lg mb-2">No issues awaiting triage</p>
          <p className="text-sm">New issues will appear here when triage mode is enabled.</p>
        </div>
      )}

      {/* Task list */}
      <div className="space-y-3">
        {tasks.map((task) => (
          <TriageCard
            key={task.id}
            task={task}
            onAccept={handleAccept}
            onReject={handleReject}
            onEdit={handleEdit}
          />
        ))}
      </div>

      {/* Edit panel */}
      {editingTask && (
        <EditPanel
          task={editingTask}
          onSave={(id, fields) => void handleSave(id, fields)}
          onSaveAndAccept={(id, fields) => void handleSaveAndAccept(id, fields)}
          onClose={() => setEditingTaskId(null)}
        />
      )}
    </div>
  )
}
