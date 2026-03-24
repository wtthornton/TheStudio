/** Triage queue — list of issues awaiting developer review (Epic 36). */

import { useEffect, useState, useCallback } from 'react'
import { useTriageStore } from '../../stores/triage-store'
import { TriageCard } from './TriageCard'
import { EditPanel } from './EditPanel'
import type { RejectionReason } from '../../lib/api'
import { useRepoContext } from '../../contexts/RepoContext'
import { EmptyState } from '../EmptyState'
import { useGitHubEvents } from '../../hooks/useGitHubEvents'

export function TriageQueue() {
  const { tasks, loading, error, loadTasks, accept, reject, edit } = useTriageStore()
  const { selectedRepo } = useRepoContext()
  const [editingTaskId, setEditingTaskId] = useState<string | null>(null)

  useEffect(() => {
    void loadTasks(selectedRepo)
  }, [loadTasks, selectedRepo])

  // Reload the queue when GitHub issue events arrive (new comments, label
  // changes) so TriageCards reflect the latest issue state without polling.
  // Story 38.26: useGitHubEvents with no taskId captures all github.event.*
  // messages; we only react to issue_comment and issues sub-types.
  const { lastEvent } = useGitHubEvents()
  useEffect(() => {
    if (!lastEvent) return
    const subType = lastEvent.event_type.replace('github.event.', '')
    if (subType === 'issue_comment' || subType === 'issues') {
      void loadTasks(selectedRepo)
    }
  }, [lastEvent, loadTasks, selectedRepo])

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
    <div data-tour="triage-queue">
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
        <div
          className="mb-4 p-3 rounded border border-red-700 bg-red-900/30 text-red-400 text-sm"
          role="alert"
        >
          {error}
          <button
            type="button"
            onClick={() => void loadTasks(selectedRepo)}
            className="ml-2 underline rounded-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-red-400 focus-visible:ring-offset-2 focus-visible:ring-offset-gray-950"
          >
            Retry
          </button>
        </div>
      )}

      {/* Empty state */}
      {tasks.length === 0 && !error && (
        <EmptyState
          data-testid="empty-triage-queue"
          icon={
            <svg width="48" height="48" viewBox="0 0 48 48" fill="none" aria-hidden="true">
              <rect x="6" y="10" width="36" height="28" rx="4" stroke="currentColor" strokeWidth="1.5" />
              <line x1="13" y1="18" x2="35" y2="18" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
              <line x1="13" y1="24" x2="29" y2="24" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
              <line x1="13" y1="30" x2="22" y2="30" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
            </svg>
          }
          heading="No issues awaiting triage"
          description="Issues sent to the webhook endpoint will appear here for your review before entering the pipeline."
          primaryAction={{
            label: 'Configure Webhook',
            href: '/admin/ui/settings',
          }}
          secondaryAction={{
            label: 'Learn about triage mode',
            href: '/admin/ui/settings#triage',
          }}
        />
      )}

      {/* Task list */}
      <div className="space-y-3" data-tour="triage-list">
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
