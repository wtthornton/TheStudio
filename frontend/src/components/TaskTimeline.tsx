/** Vertical timeline layout showing a TaskPacket's journey through pipeline stages.
 * Stage bars are color-coded and duration-proportional. Gate results shown under each bar.
 * Queued stages shown as dashed/gray. Supports click-to-expand for gate evidence.
 * Hover tooltips show timestamps, model, cost.
 *
 * Covers: S2.F1, S2.F2, S2.F3, S2.F4, S2.F5, S2.F6, S2.F11, S2.F12
 */

import { useState, useEffect, useCallback, useRef } from 'react'
import { PIPELINE_STAGES } from '../lib/constants'
import { fetchTaskDetail, fetchTaskGates, fetchTaskAudit } from '../lib/api'
import type { TaskPacketDetail, GateEvidenceRead, SteeringAuditLogRead } from '../lib/api'
import { usePipelineStore } from '../stores/pipeline-store'
import { SteeringActionBar } from './SteeringActionBar'

interface TaskTimelineProps {
  taskId: string
  onClose: () => void
}

interface StageTimingEntry {
  stage: string
  label: string
  color: string
  start: string | null
  end: string | null
  duration: number | null // seconds
  cost: number
  model: string | null
  status: 'completed' | 'active' | 'queued'
}

function parseStageTiming(task: TaskPacketDetail): StageTimingEntry[] {
  return PIPELINE_STAGES.map((s) => {
    const timing = task.stage_timings?.[s.id]
    const start = timing?.start ?? null
    const end = timing?.end ?? null
    let duration: number | null = null
    if (start && end) {
      duration = (new Date(end).getTime() - new Date(start).getTime()) / 1000
    }
    const costEntry = task.cost_by_stage.find((c) => c.stage === s.id)
    return {
      stage: s.id,
      label: s.label,
      color: s.color,
      start,
      end,
      duration,
      cost: costEntry?.cost ?? timing?.cost ?? 0,
      model: costEntry?.model ?? timing?.model ?? null,
      status: start && end ? 'completed' : start ? 'active' : 'queued',
    }
  })
}

function formatTime(iso: string | null): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleTimeString('en-US', { hour12: false })
}

function formatDuration(seconds: number | null): string {
  if (seconds == null) return '—'
  if (seconds < 1) return '<1s'
  if (seconds < 60) return `${Math.round(seconds)}s`
  if (seconds < 3600) return `${Math.round(seconds / 60)}m ${Math.round(seconds % 60)}s`
  return `${Math.floor(seconds / 3600)}h ${Math.round((seconds % 3600) / 60)}m`
}

function elapsedTime(task: TaskPacketDetail): string {
  const timings = task.stage_timings
  if (!timings) return '—'
  const starts = Object.values(timings).map((t) => t.start).filter(Boolean) as string[]
  const ends = Object.values(timings).map((t) => t.end).filter(Boolean) as string[]
  if (starts.length === 0) return '—'
  const earliest = Math.min(...starts.map((s) => new Date(s).getTime()))
  const latest = ends.length > 0
    ? Math.max(...ends.map((s) => new Date(s).getTime()))
    : Date.now()
  return formatDuration((latest - earliest) / 1000)
}

function progressPercent(task: TaskPacketDetail): number {
  if (!task.stage_timings) return 0
  const completed = Object.values(task.stage_timings).filter((t) => t.start && t.end).length
  return Math.round((completed / 9) * 100)
}

/** S2.F12: Tooltip for stage bars */
function BarTooltip({ entry }: { entry: StageTimingEntry }) {
  return (
    <div className="absolute -top-2 left-1/2 z-50 -translate-x-1/2 -translate-y-full rounded-lg border border-gray-600 bg-gray-800 px-3 py-2 text-xs shadow-lg whitespace-nowrap">
      <div className="space-y-0.5">
        <div><span className="text-gray-400">Start:</span> {formatTime(entry.start)}</div>
        <div><span className="text-gray-400">End:</span> {formatTime(entry.end)}</div>
        <div><span className="text-gray-400">Model:</span> {entry.model ?? '—'}</div>
        <div><span className="text-gray-400">Cost:</span> ${entry.cost.toFixed(4)}</div>
      </div>
      <div className="absolute left-1/2 -bottom-1 h-2 w-2 -translate-x-1/2 rotate-45 border-b border-r border-gray-600 bg-gray-800" />
    </div>
  )
}

/** S2.F6: Expandable gate evidence panel */
function GateEvidence({ gate }: { gate: GateEvidenceRead }) {
  const [expanded, setExpanded] = useState(false)
  const checks = Array.isArray(gate.checks) ? gate.checks : []

  return (
    <div className="mt-1 rounded border border-gray-700 bg-gray-800/50 px-2 py-1" data-testid="gate-evidence">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex w-full items-center gap-2 text-xs"
      >
        {gate.result === 'pass' ? (
          <span className="text-emerald-400">PASS</span>
        ) : (
          <span className="text-red-400">FAIL</span>
        )}
        <span className="text-gray-400">{checks.length} checks</span>
        {gate.defect_category && (
          <span className="text-amber-400">[{gate.defect_category}]</span>
        )}
        <span className="ml-auto text-gray-500">{expanded ? '▾' : '▸'}</span>
      </button>
      {expanded && (
        <div className="mt-1 space-y-1 border-t border-gray-700 pt-1">
          {checks.map((check, i) => (
            <div key={i} className="flex items-start gap-2 text-xs">
              <span className={check.result === 'passed' ? 'text-emerald-400' : 'text-red-400'}>
                {check.result === 'passed' ? '✓' : '✗'}
              </span>
              <span className="text-gray-300">{String(check.name ?? `Check ${i + 1}`)}</span>
              {check.details != null && (
                <span className="text-gray-500 truncate">{String(check.details)}</span>
              )}
            </div>
          ))}
          {gate.evidence_artifact && (
            <pre className="mt-1 rounded bg-gray-900 p-2 text-xs text-gray-400 overflow-x-auto max-h-32">
              {JSON.stringify(gate.evidence_artifact, null, 2)}
            </pre>
          )}
        </div>
      )}
    </div>
  )
}

/** S1.37.7: Action label map for steering audit entries */
const STEERING_ACTION_LABELS: Record<SteeringAuditLogRead['action'], string> = {
  pause: 'Paused',
  resume: 'Resumed',
  abort: 'Aborted',
  redirect: 'Redirected',
  retry: 'Retried',
}

/** S1.37.7: Steering audit entry row */
function SteeringAuditEntry({ entry }: { entry: SteeringAuditLogRead }) {
  const label = STEERING_ACTION_LABELS[entry.action] ?? entry.action
  const time = new Date(entry.timestamp).toLocaleTimeString('en-US', { hour12: false })
  const date = new Date(entry.timestamp).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })

  return (
    <div className="flex items-start gap-2 text-xs py-1 border-b border-gray-800 last:border-0" data-testid="steering-audit-entry">
      {/* Wrench icon */}
      <span className="mt-0.5 shrink-0 text-amber-400" title="Steering action" aria-label="steering action">
        🔧
      </span>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="font-medium text-gray-200">{label}</span>
          {entry.from_stage && entry.to_stage && (
            <span className="text-gray-500">
              {entry.from_stage} → {entry.to_stage}
            </span>
          )}
          {entry.actor !== 'system' && (
            <span className="text-gray-500">by {entry.actor}</span>
          )}
          <span className="ml-auto shrink-0 text-gray-500 tabular-nums">
            {date} {time}
          </span>
        </div>
        {entry.reason && (
          <p className="mt-0.5 text-gray-400 break-words">{entry.reason}</p>
        )}
      </div>
    </div>
  )
}

/** S1.37.7: Collapsible steering audit entries section */
function SteeringAuditSection({ entries }: { entries: SteeringAuditLogRead[] }) {
  const [expanded, setExpanded] = useState(true)

  if (entries.length === 0) return null

  return (
    <div className="rounded-lg border border-amber-800/40 bg-amber-900/10" data-testid="steering-audit-section">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex w-full items-center gap-2 px-3 py-2 text-xs font-medium text-amber-300"
      >
        <span>🔧</span>
        <span>Steering Actions ({entries.length})</span>
        <span className="ml-auto text-gray-500">{expanded ? '▾' : '▸'}</span>
      </button>
      {expanded && (
        <div className="px-3 pb-2">
          {entries.map((entry) => (
            <SteeringAuditEntry key={entry.id} entry={entry} />
          ))}
        </div>
      )}
    </div>
  )
}

/** S2.F1-F6, F11, F12: Full TaskPacket timeline */
export function TaskTimeline({ taskId, onClose }: TaskTimelineProps) {
  const [task, setTask] = useState<TaskPacketDetail | null>(null)
  const [gates, setGates] = useState<GateEvidenceRead[]>([])
  const [auditEntries, setAuditEntries] = useState<SteeringAuditLogRead[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const stagesState = usePipelineStore((s) => s.stages)
  const [hoveredBar, setHoveredBar] = useState<string | null>(null)
  const hoverTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  // S2.F11: Subscribe to SSE updates — re-fetch on stage changes
  const prevStagesRef = useRef(stagesState)
  useEffect(() => {
    if (prevStagesRef.current !== stagesState && task) {
      // Re-fetch task detail when stage state changes
      fetchTaskDetail(taskId).then(setTask).catch(() => {})
      fetchTaskGates(taskId).then(setGates).catch(() => {})
      fetchTaskAudit(taskId).then(setAuditEntries).catch(() => {})
    }
    prevStagesRef.current = stagesState
  }, [stagesState, task, taskId])

  const loadData = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [taskData, gateData, auditData] = await Promise.all([
        fetchTaskDetail(taskId),
        fetchTaskGates(taskId).catch(() => [] as GateEvidenceRead[]),
        fetchTaskAudit(taskId).catch(() => [] as SteeringAuditLogRead[]),
      ])
      setTask(taskData)
      setGates(gateData)
      setAuditEntries(auditData)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load')
    } finally {
      setLoading(false)
    }
  }, [taskId])

  useEffect(() => { void loadData() }, [loadData])

  // Close on Escape
  useEffect(() => {
    function onKey(e: KeyboardEvent) { if (e.key === 'Escape') onClose() }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [onClose])

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-gray-600 border-t-blue-400" />
      </div>
    )
  }

  if (error || !task) {
    return (
      <div className="rounded-lg border border-red-800 bg-red-900/20 p-4 text-center">
        <p className="text-sm text-red-400">{error ?? 'Task not found'}</p>
        <button onClick={loadData} className="mt-2 text-xs text-blue-400 hover:underline">Retry</button>
      </div>
    )
  }

  const entries = parseStageTiming(task)
  const maxDuration = Math.max(...entries.map((e) => e.duration ?? 0), 1)

  return (
    <div className="space-y-4" data-testid="task-timeline">
      {/* S2.F4: Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold text-gray-200">
            {task.id.slice(0, 8)}… <span className="font-normal text-gray-400">#{task.issue_id}</span>
          </h3>
          <div className="flex items-center gap-3 mt-1 text-xs text-gray-400">
            <span className="rounded bg-gray-700 px-1.5 py-0.5">{task.status}</span>
            <span>{progressPercent(task)}% complete</span>
            <span>{elapsedTime(task)} elapsed</span>
            <span className="text-cyan-400">${task.total_cost.toFixed(4)}</span>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {/* S1.37.6: Steering controls — pause/resume/abort */}
          <SteeringActionBar taskId={task.id} taskStatus={task.status} />
          <button onClick={onClose} className="text-gray-400 hover:text-gray-200 text-sm">Close</button>
        </div>
      </div>

      {/* Progress bar */}
      <div className="h-1.5 w-full rounded-full bg-gray-700">
        <div
          className="h-1.5 rounded-full bg-blue-500 transition-all"
          style={{ width: `${progressPercent(task)}%` }}
        />
      </div>

      {/* S1.37.7: Steering audit entries */}
      <SteeringAuditSection entries={auditEntries} />

      {/* Timeline stages */}
      <div className="space-y-2">
        {entries.map((entry) => {
          const barWidth = entry.status === 'queued'
            ? 10
            : entry.status === 'active'
              ? 50
              : Math.max(10, (entry.duration! / maxDuration) * 100)
          const gatesForStage = gates.filter((g) => g.stage === entry.stage)
          const isHovered = hoveredBar === entry.stage

          return (
            <div key={entry.stage} className="flex items-start gap-3" data-testid={`timeline-stage-${entry.stage}`}>
              {/* Stage label */}
              <div className="w-20 shrink-0 text-right">
                <span className="text-xs font-medium" style={{ color: entry.color }}>{entry.label}</span>
                <div className="text-xs text-gray-500">{formatTime(entry.start)}</div>
              </div>

              {/* Bar */}
              <div className="flex-1">
                <div
                  className="relative"
                  onMouseEnter={() => {
                    hoverTimerRef.current = setTimeout(() => setHoveredBar(entry.stage), 300)
                  }}
                  onMouseLeave={() => {
                    if (hoverTimerRef.current) clearTimeout(hoverTimerRef.current)
                    setHoveredBar(null)
                  }}
                >
                  {isHovered && entry.status !== 'queued' && <BarTooltip entry={entry} />}
                  <div
                    className={`h-6 rounded transition-all ${
                      entry.status === 'queued'
                        ? 'border border-dashed border-gray-600 bg-gray-800/30'
                        : entry.status === 'active'
                          ? 'animate-stage-pulse'
                          : ''
                    }`}
                    style={{
                      width: `${barWidth}%`,
                      backgroundColor: entry.status === 'queued' ? undefined : `${entry.color}30`,
                      borderColor: entry.status !== 'queued' ? entry.color : undefined,
                      borderWidth: entry.status !== 'queued' ? '1px' : undefined,
                      borderStyle: entry.status !== 'queued' ? 'solid' : undefined,
                      '--pulse-color': `${entry.color}40`,
                    } as React.CSSProperties}
                  >
                    {entry.status === 'queued' && (
                      <span className="flex h-full items-center px-2 text-xs text-gray-500 italic">(queued)</span>
                    )}
                    {entry.status === 'active' && (
                      <span className="flex h-full items-center px-2 text-xs text-gray-300">In progress…</span>
                    )}
                    {entry.status === 'completed' && (
                      <span className="flex h-full items-center px-2 text-xs text-gray-300">
                        {formatDuration(entry.duration)}
                      </span>
                    )}
                  </div>
                </div>

                {/* S2.F3 + S2.F6: Gate results under bar */}
                {gatesForStage.map((gate) => (
                  <GateEvidence key={gate.id} gate={gate} />
                ))}
              </div>

              {/* Duration label */}
              <div className="w-16 shrink-0 text-right text-xs text-gray-500">
                {entry.status === 'completed' ? formatDuration(entry.duration) : ''}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
