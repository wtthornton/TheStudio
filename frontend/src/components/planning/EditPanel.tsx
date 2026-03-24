/** Edit panel — slide-in side panel for editing a triaged task (Epic 36). */

import { useState, useEffect } from 'react'
import type { TriageTask } from '../../lib/api'

interface EditPanelProps {
  task: TriageTask
  onSave: (taskId: string, fields: { issue_title?: string; issue_body?: string }) => void
  onSaveAndAccept: (taskId: string, fields: { issue_title?: string; issue_body?: string }) => void
  onClose: () => void
}

export function EditPanel({ task, onSave, onSaveAndAccept, onClose }: EditPanelProps) {
  const [title, setTitle] = useState(task.issue_title ?? '')
  const [body, setBody] = useState(task.issue_body ?? '')

  useEffect(() => {
    const handleEsc = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', handleEsc)
    return () => window.removeEventListener('keydown', handleEsc)
  }, [onClose])

  const fields = {
    ...(title !== (task.issue_title ?? '') ? { issue_title: title } : {}),
    ...(body !== (task.issue_body ?? '') ? { issue_body: body } : {}),
  }
  const hasChanges = Object.keys(fields).length > 0

  return (
    <div
      className="fixed inset-y-0 right-0 w-[480px] bg-gray-900 border-l border-gray-700 shadow-xl z-50 flex flex-col animate-slide-in"
      role="dialog"
      aria-modal="true"
      aria-labelledby="edit-panel-title"
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-700">
        <h2 id="edit-panel-title" className="font-medium text-gray-100">
          Edit Issue #{task.issue_id}
        </h2>
        <button
          type="button"
          onClick={onClose}
          className="text-gray-500 hover:text-gray-300 text-lg focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 rounded px-1"
          aria-label="Close edit panel"
        >
          &times;
        </button>
      </div>

      {/* Form */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        <div>
          <label className="block text-sm text-gray-400 mb-1">Title</label>
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className="w-full px-3 py-2 rounded border border-gray-700 bg-gray-800 text-gray-100 focus:border-blue-500 focus:outline-none"
          />
        </div>
        <div>
          <label className="block text-sm text-gray-400 mb-1">Description</label>
          <textarea
            value={body}
            onChange={(e) => setBody(e.target.value)}
            rows={12}
            className="w-full px-3 py-2 rounded border border-gray-700 bg-gray-800 text-gray-100 focus:border-blue-500 focus:outline-none resize-y"
          />
        </div>
      </div>

      {/* Footer */}
      <div className="flex items-center gap-2 px-4 py-3 border-t border-gray-700">
        <button
          type="button"
          onClick={() => { onSave(task.id, fields); onClose() }}
          disabled={!hasChanges}
          className="px-3 py-1.5 text-sm rounded bg-blue-700 text-blue-100 hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-400"
        >
          Save
        </button>
        <button
          type="button"
          onClick={() => onSaveAndAccept(task.id, fields)}
          className="px-3 py-1.5 text-sm rounded bg-emerald-700 text-emerald-100 hover:bg-emerald-600 focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-400"
        >
          Save & Accept
        </button>
        <button
          type="button"
          onClick={onClose}
          className="px-3 py-1.5 text-sm text-gray-400 hover:text-gray-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-gray-500"
        >
          Cancel
        </button>
      </div>
    </div>
  )
}
