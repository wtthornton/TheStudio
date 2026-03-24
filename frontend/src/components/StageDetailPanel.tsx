/** Slide-in right panel showing stage details. Opens on stage node click, closes on X or Escape.
 * Content: TaskPackets in stage with progress %, model, cost. Stage metrics (pass rate, avg time).
 */

import { useEffect, useCallback, useState } from 'react'
import { usePipelineStore } from '../stores/pipeline-store'
import { PIPELINE_STAGES } from '../lib/constants'
import { fetchTasks } from '../lib/api'
import type { TaskPacketRead } from '../lib/api'

function formatDuration(seconds: number | null): string {
  if (seconds == null) return '—'
  if (seconds < 60) return `${Math.round(seconds)}s`
  if (seconds < 3600) return `${Math.round(seconds / 60)}m`
  return `${(seconds / 3600).toFixed(1)}h`
}

function formatPercent(rate: number | null): string {
  if (rate == null) return '—'
  return `${Math.round(rate * 100)}%`
}

function stageProgress(task: TaskPacketRead): number {
  if (!task.stage_timings) return 0
  const completed = Object.values(task.stage_timings).filter((t) => t.start && t.end).length
  return Math.round((completed / 9) * 100)
}

function taskModel(task: TaskPacketRead, stage: string): string {
  return task.stage_timings?.[stage]?.model ?? '—'
}

function taskCost(task: TaskPacketRead, stage: string): string {
  const cost = task.stage_timings?.[stage]?.cost
  return cost != null ? `$${cost.toFixed(4)}` : '—'
}

export function StageDetailPanel() {
  const selectedStage = usePipelineStore((s) => s.selectedStage)
  const stageMetrics = usePipelineStore((s) => s.stageMetrics)
  const stages = usePipelineStore((s) => s.stages)
  const setSelectedStage = usePipelineStore((s) => s.setSelectedStage)

  const [tasks, setTasks] = useState<TaskPacketRead[]>([])
  const [loading, setLoading] = useState(false)

  const close = useCallback(() => setSelectedStage(null), [setSelectedStage])

  // Close on Escape
  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      if (e.key === 'Escape') close()
    }
    if (selectedStage) {
      document.addEventListener('keydown', onKeyDown)
      return () => document.removeEventListener('keydown', onKeyDown)
    }
  }, [selectedStage, close])

  // Fetch tasks when stage selected
  useEffect(() => {
    if (!selectedStage) return
    const stage = selectedStage
    let cancelled = false
    async function load() {
      try {
        const { items } = await fetchTasks({ limit: 50 })
        if (cancelled) return
        const filtered = items.filter((t) => t.stage_timings?.[stage]?.start)
        setTasks(filtered)
      } catch {
        if (!cancelled) setTasks([])
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    void load()
    return () => { cancelled = true }
  }, [selectedStage])

  if (!selectedStage) return null

  const stageConfig = PIPELINE_STAGES.find((s) => s.id === selectedStage)
  const stageState = stages[selectedStage]
  const metrics = stageMetrics?.[selectedStage]

  return (
    <div
      className="fixed inset-y-0 right-0 z-50 flex"
      data-testid="stage-detail-panel"
    >
      {/* Backdrop */}
      <div className="fixed inset-0 bg-black/30" onClick={close} />

      {/* Panel */}
      <div
        className="relative ml-auto flex h-full w-96 flex-col bg-gray-900 shadow-xl animate-slide-in-right"
        role="dialog"
        aria-modal="true"
        aria-labelledby="stage-detail-title"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-gray-700 px-4 py-3">
          <div className="flex items-center gap-2">
            <div
              className="h-3 w-3 rounded-full"
              style={{ backgroundColor: stageConfig?.color ?? '#6b7280' }}
              aria-hidden="true"
            />
            <h2 id="stage-detail-title" className="text-lg font-semibold">
              {stageConfig?.label ?? selectedStage}
            </h2>
            <span className="rounded bg-gray-700 px-2 py-0.5 text-xs text-gray-300">
              {stageState.status}
            </span>
          </div>
          <button
            type="button"
            onClick={close}
            className="rounded p-1 text-gray-400 hover:bg-gray-800 hover:text-gray-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
            aria-label="Close panel"
            data-testid="panel-close"
          >
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="5" y1="5" x2="15" y2="15" />
              <line x1="15" y1="5" x2="5" y2="15" />
            </svg>
          </button>
        </div>

        {/* Metrics summary */}
        <div className="grid grid-cols-3 gap-2 border-b border-gray-700 px-4 py-3">
          <div className="text-center">
            <div className="text-xs text-gray-500">Pass Rate</div>
            <div className="text-sm font-medium">{formatPercent(metrics?.passRate ?? null)}</div>
          </div>
          <div className="text-center">
            <div className="text-xs text-gray-500">Avg Time</div>
            <div className="text-sm font-medium">{formatDuration(metrics?.avgDuration ?? null)}</div>
          </div>
          <div className="text-center">
            <div className="text-xs text-gray-500">Throughput</div>
            <div className="text-sm font-medium">{metrics?.throughput ?? 0}</div>
          </div>
        </div>

        {/* Active tasks count */}
        <div className="border-b border-gray-700 px-4 py-2 text-xs text-gray-400">
          {stageState.activeTasks.length} active · {stageState.taskCount} total processed
        </div>

        {/* Task list */}
        <div className="flex-1 overflow-y-auto px-4 py-2">
          {loading ? (
            <div className="flex items-center justify-center py-8" data-testid="panel-loading">
              <div className="h-6 w-6 animate-spin rounded-full border-2 border-gray-600 border-t-blue-400" />
            </div>
          ) : tasks.length === 0 ? (
            <div className="py-8 text-center text-sm text-gray-500" data-testid="panel-empty">
              No tasks have entered this stage
            </div>
          ) : (
            <ul className="space-y-2" data-testid="panel-task-list">
              {tasks.map((task) => (
                <li
                  key={task.id}
                  className="rounded-lg border border-gray-700 bg-gray-800 p-3"
                  data-testid="panel-task-item"
                >
                  <div className="flex items-center justify-between">
                    <span className="truncate text-sm font-medium text-gray-200" title={task.id}>
                      {task.id.slice(0, 8)}…
                    </span>
                    <span className="rounded bg-gray-700 px-1.5 py-0.5 text-xs text-gray-300">
                      {task.status}
                    </span>
                  </div>
                  <div className="mt-2 flex items-center gap-4 text-xs text-gray-400">
                    <span>{stageProgress(task)}% complete</span>
                    <span>Model: {taskModel(task, selectedStage)}</span>
                    <span>Cost: {taskCost(task, selectedStage)}</span>
                  </div>
                  {/* Progress bar */}
                  <div className="mt-2 h-1 w-full rounded-full bg-gray-700">
                    <div
                      className="h-1 rounded-full bg-blue-500 transition-all"
                      style={{ width: `${stageProgress(task)}%` }}
                    />
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  )
}
