/** BacklogBoard — Kanban view with 6 columns: Triage, Planning, Building, Verify, Done, Rejected. */

import { useEffect, useState } from 'react'
import { useBacklogStore, BOARD_COLUMNS, groupTasksByColumn } from '../../stores/backlog-store'
import { BacklogCard } from './BacklogCard'
import CreateTaskModal from './CreateTaskModal'
import { useRepoContext } from '../../contexts/RepoContext'
import { EmptyState } from '../EmptyState'

function BacklogIcon() {
  return (
    <svg width="48" height="48" viewBox="0 0 48 48" fill="none" className="text-gray-500">
      <rect x="4" y="10" width="10" height="28" rx="2" stroke="currentColor" strokeWidth="2" />
      <rect x="19" y="16" width="10" height="22" rx="2" stroke="currentColor" strokeWidth="2" />
      <rect x="34" y="6" width="10" height="32" rx="2" stroke="currentColor" strokeWidth="2" />
    </svg>
  )
}

interface BacklogBoardProps {
  /** Called when the user clicks a card — passes the task UUID up to the parent. */
  onTaskClick: (taskId: string) => void
  /** Called when the user clicks the "Go to Pipeline" CTA in the empty state. */
  onNavigateToPipeline?: () => void
}

export default function BacklogBoard({ onTaskClick, onNavigateToPipeline }: BacklogBoardProps) {
  const { tasks, loading, error, loadBoard } = useBacklogStore()
  const { selectedRepo } = useRepoContext()
  const [showCreateModal, setShowCreateModal] = useState(false)

  useEffect(() => {
    void loadBoard(selectedRepo)
  }, [loadBoard, selectedRepo])

  if (loading && tasks.length === 0) {
    return (
      <div className="flex items-center justify-center py-20 text-gray-500">
        <span className="text-sm">Loading backlog…</span>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-gray-500">
        <p className="text-sm text-red-400 mb-2">{error}</p>
        <button
          onClick={() => void loadBoard()}
          className="rounded bg-gray-700 px-3 py-1.5 text-xs text-gray-300 hover:bg-gray-600 transition-colors"
        >
          Retry
        </button>
      </div>
    )
  }

  const groups = groupTasksByColumn(tasks)
  const totalTasks = tasks.length

  // Empty board — no tasks at all
  if (totalTasks === 0) {
    return (
      <EmptyState
        icon={<BacklogIcon />}
        heading="Backlog is Empty"
        description="No tasks have been imported yet. Import a GitHub issue from the Pipeline tab to get started, then watch it move through Triage → Planning → Building."
        primaryAction={
          onNavigateToPipeline
            ? { label: 'Go to Pipeline', onClick: onNavigateToPipeline }
            : undefined
        }
        secondaryAction={{ label: '+ New Task', onClick: () => setShowCreateModal(true) }}
        data-testid="backlog-empty-state"
      />
    )
  }

  return (
    <div className="flex flex-col gap-4">
      {/* Board header */}
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-100">Backlog Board</h2>
        <div className="flex items-center gap-3">
          <span className="text-xs text-gray-500">
            {totalTasks} task{totalTasks !== 1 ? 's' : ''}
          </span>
          <button
            onClick={() => void loadBoard()}
            disabled={loading}
            className="min-h-[44px] rounded bg-gray-700 px-3 py-2 text-xs text-gray-300 hover:bg-gray-600
                       disabled:opacity-50 disabled:cursor-not-allowed transition-colors
                       focus:outline-none focus-visible:ring-2 focus-visible:ring-gray-500 focus-visible:ring-offset-2 focus-visible:ring-offset-gray-950"
          >
            {loading ? 'Refreshing…' : 'Refresh'}
          </button>
          <button
            onClick={() => setShowCreateModal(true)}
            className="min-h-[44px] rounded bg-blue-700 px-3 py-2 text-xs font-medium text-blue-100 hover:bg-blue-600 transition-colors
                       focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 focus-visible:ring-offset-gray-950"
            data-testid="open-create-task"
          >
            + New Task
          </button>
        </div>
      </div>

      <CreateTaskModal
        open={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        onCreated={() => { void loadBoard() }}
      />

      {/* Kanban columns — horizontally scrollable */}
      <div className="overflow-x-auto pb-2">
        <div className="flex gap-3" style={{ minWidth: `${BOARD_COLUMNS.length * 200}px` }}>
          {BOARD_COLUMNS.map((col) => {
            const colTasks = groups[col.id]
            const [textColorClass, borderColorClass] = col.headerClass.split(' ')

            return (
              <div
                key={col.id}
                className="flex flex-col flex-1 min-w-[190px]"
              >
                {/* Column header */}
                <div
                  className={`flex items-center justify-between pb-2 mb-2 border-b ${borderColorClass}`}
                >
                  <span
                    className={`text-xs font-semibold uppercase tracking-wide ${textColorClass}`}
                  >
                    {col.label}
                  </span>
                  <span className="text-xs text-gray-500 tabular-nums">
                    {colTasks.length}
                  </span>
                </div>

                {/* Task cards */}
                <div className="flex flex-col gap-2">
                  {colTasks.length === 0 ? (
                    <p className="text-xs text-gray-700 italic text-center py-4">Empty</p>
                  ) : (
                    colTasks.map((task) => (
                      <BacklogCard key={task.id} task={task} onClick={onTaskClick} />
                    ))
                  )}
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
