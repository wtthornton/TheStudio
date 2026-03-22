/** BacklogBoard — Kanban view with 6 columns: Triage, Planning, Building, Verify, Done, Rejected. */

import { useEffect } from 'react'
import { useBacklogStore, BOARD_COLUMNS, groupTasksByColumn } from '../../stores/backlog-store'
import { BacklogCard } from './BacklogCard'

interface BacklogBoardProps {
  /** Called when the user clicks a card — passes the task UUID up to the parent. */
  onTaskClick: (taskId: string) => void
}

export default function BacklogBoard({ onTaskClick }: BacklogBoardProps) {
  const { tasks, loading, error, loadBoard } = useBacklogStore()

  useEffect(() => {
    void loadBoard()
  }, [loadBoard])

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
            className="rounded bg-gray-700 px-3 py-1.5 text-xs text-gray-300 hover:bg-gray-600
                       disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {loading ? 'Refreshing…' : 'Refresh'}
          </button>
        </div>
      </div>

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
