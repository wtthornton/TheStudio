/** Loopback arcs on the Pipeline Rail — animated dashed arcs from failing stage to target.
 * S4.F1: Arc rendering, S4.F2: Timeline entries, S4.F3: Escalation indicator,
 * S4.F4: Resolution animation, S4.F5: History panel
 */

import { useMemo } from 'react'
import { usePipelineStore } from '../stores/pipeline-store'
import { PIPELINE_STAGES } from '../lib/constants'
import type { StageId } from '../lib/constants'

export interface LoopbackEvent {
  id: string
  taskId: string
  fromStage: StageId
  toStage: StageId
  reason: string
  attempt: number
  maxAttempts: number
  resolved: boolean
  outcome?: string
  timestamp: number
}

// Store loopback events — extends the pipeline store
export interface LoopbackState {
  loopbacks: LoopbackEvent[]
}

// Get stage index in pipeline for arc positioning
function stageIndex(stageId: string): number {
  return PIPELINE_STAGES.findIndex((s) => s.id === stageId)
}

/** S4.F1: Animated dashed arc between two stage nodes */
function LoopbackArcSvg({ from, to, attempt, maxAttempts, resolved }: {
  from: StageId
  to: StageId
  attempt: number
  maxAttempts: number
  resolved: boolean
}) {
  const fromIdx = stageIndex(from)
  const toIdx = stageIndex(to)
  if (fromIdx < 0 || toIdx < 0) return null

  // Calculate SVG path — arc from right to left above the pipeline rail
  const startX = fromIdx * 80 + 24 // center of stage node
  const endX = toIdx * 80 + 24
  const midX = (startX + endX) / 2
  const arcHeight = Math.abs(fromIdx - toIdx) * 20 + 30

  const isEscalated = attempt >= maxAttempts
  const strokeColor = resolved ? '#10b981' : isEscalated ? '#ef4444' : '#f59e0b'
  const animClass = resolved ? 'animate-loopback-resolve' : 'animate-dash-flow'

  return (
    <g className={animClass}>
      <path
        d={`M ${startX} 0 Q ${midX} ${-arcHeight} ${endX} 0`}
        fill="none"
        stroke={strokeColor}
        strokeWidth="2"
        strokeDasharray={resolved ? 'none' : '6 4'}
        strokeLinecap="round"
      />
      {/* Arrow at target */}
      <polygon
        points={`${endX - 4},-6 ${endX},0 ${endX + 4},-6`}
        fill={strokeColor}
      />
      {/* Badge */}
      <g transform={`translate(${midX - 20}, ${-arcHeight - 14})`}>
        <rect
          x="0" y="0" width="40" height="16" rx="4"
          fill={isEscalated ? '#7f1d1d' : '#78350f'}
          stroke={strokeColor}
          strokeWidth="1"
        />
        <text x="20" y="12" textAnchor="middle" fontSize="9" fill="white">
          #{attempt}/{maxAttempts}
        </text>
      </g>
    </g>
  )
}

/** S4.F3: Escalation indicator */
function EscalationBanner({ loopback }: { loopback: LoopbackEvent }) {
  return (
    <div className="flex items-center gap-2 rounded border border-red-700 bg-red-900/30 px-3 py-2 text-xs" data-testid="escalation-banner">
      <span className="text-red-400 font-medium">ESCALATED</span>
      <span className="text-gray-400">—</span>
      <span className="text-gray-300">needs human review</span>
      <span className="text-gray-500 ml-auto">{loopback.reason}</span>
    </div>
  )
}

/** S4.F5: Loopback history panel */
export function LoopbackHistory({ taskId }: { taskId: string }) {
  const loopbacks = usePipelineStore((s) => {
    // Derive from events — loopback events have specific type
    return s.events
      .filter((e) => (e.type === 'pipeline.loopback.start' || e.type === 'pipeline.loopback.resolve') && e.taskpacketId === taskId)
  })

  if (loopbacks.length === 0) return null

  return (
    <div className="rounded-lg border border-gray-700 bg-gray-900" data-testid="loopback-history">
      <div className="border-b border-gray-700 px-3 py-2">
        <h4 className="text-xs font-semibold text-gray-300">Loopback History</h4>
      </div>
      <div className="divide-y divide-gray-800">
        {loopbacks.map((event) => (
          <div key={event.id} className="flex items-center gap-3 px-3 py-2 text-xs">
            <span className={event.type.includes('resolve') ? 'text-emerald-400' : 'text-amber-400'}>
              {event.type.includes('resolve') ? '✓' : '↩'}
            </span>
            <span className="text-gray-300">{event.stage ?? '?'}</span>
            <span className="text-gray-500">
              {new Date(event.timestamp).toLocaleTimeString('en-US', { hour12: false })}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}

/** S4.F2: Loopback entries in TaskPacket Timeline */
export function LoopbackTimelineEntry({ loopback }: { loopback: LoopbackEvent }) {
  const fromStage = PIPELINE_STAGES.find((s) => s.id === loopback.fromStage)
  const toStage = PIPELINE_STAGES.find((s) => s.id === loopback.toStage)
  const isEscalated = loopback.attempt >= loopback.maxAttempts

  return (
    <div
      className={`flex items-center gap-2 rounded border px-3 py-2 text-xs ${
        isEscalated ? 'border-red-700 bg-red-900/20' : 'border-amber-700 bg-amber-900/20'
      }`}
      data-testid="loopback-timeline-entry"
    >
      <span className={isEscalated ? 'text-red-400' : 'text-amber-400'}>↩</span>
      <span className="text-gray-300">
        {fromStage?.label ?? loopback.fromStage} → {toStage?.label ?? loopback.toStage}
      </span>
      <span className="rounded bg-gray-700 px-1.5 py-0.5 text-gray-300">
        Attempt {loopback.attempt}/{loopback.maxAttempts}
      </span>
      <span className="text-gray-500">{loopback.reason}</span>
      {loopback.resolved && (
        <span className="ml-auto text-emerald-400">Resolved: {loopback.outcome}</span>
      )}
    </div>
  )
}

/** Main loopback overlay on Pipeline Rail */
export function LoopbackOverlay() {
  const events = usePipelineStore((s) => s.events)

  // Derive loopback events from the event log
  const activeLoopbacks = useMemo(() => {
    const loopbacks: LoopbackEvent[] = []
    for (const event of events) {
      if (event.type === 'pipeline.loopback.start' && event.stage) {
        loopbacks.push({
          id: `lb-${event.id}`,
          taskId: event.taskpacketId ?? '',
          fromStage: event.stage as StageId,
          toStage: 'verify' as StageId,
          reason: 'Verification failed',
          attempt: 1,
          maxAttempts: 2,
          resolved: false,
          timestamp: event.timestamp,
        })
      }
    }
    return loopbacks
  }, [events])

  if (activeLoopbacks.length === 0) return null

  const escalated = activeLoopbacks.filter((lb) => lb.attempt >= lb.maxAttempts)

  return (
    <div data-testid="loopback-overlay">
      {/* SVG arcs overlay */}
      <svg
        className="pointer-events-none absolute inset-x-0 top-0"
        style={{ height: '60px', overflow: 'visible' }}
      >
        {activeLoopbacks.map((lb) => (
          <LoopbackArcSvg
            key={lb.id}
            from={lb.fromStage}
            to={lb.toStage}
            attempt={lb.attempt}
            maxAttempts={lb.maxAttempts}
            resolved={lb.resolved}
          />
        ))}
      </svg>

      {/* S4.F3: Escalation banners */}
      {escalated.map((lb) => (
        <EscalationBanner key={lb.id} loopback={lb} />
      ))}
    </div>
  )
}
