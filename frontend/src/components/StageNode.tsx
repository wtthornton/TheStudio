/** Single pipeline stage node — color-coded circle with status icon, label, task count,
 * pulse animation on active stages, and hover tooltip with metrics.
 */

import { useState, useRef, useEffect } from 'react'
import { Tooltip } from 'react-tooltip'
import type { StageStatus } from '../stores/pipeline-store'
import { usePipelineStore } from '../stores/pipeline-store'
import { STATUS_COLORS } from '../lib/constants'
import type { StageId } from '../lib/constants'

/** Short descriptions for each pipeline stage, shown as react-tooltip on stage labels. */
/** Human-readable pipeline stage status for aria-labels (non-color cue). */
const STATUS_LABELS: Record<StageStatus, string> = {
  idle: 'Idle',
  active: 'Active',
  review: 'In review',
  passed: 'Passed',
  failed: 'Failed',
}

const STAGE_DESCRIPTIONS: Record<string, string> = {
  intake: 'Webhook ingestion — validates GitHub events and creates TaskPackets',
  context: 'Enriches tasks with complexity scores, risk flags, and repo context',
  intent: 'Builds an Intent Specification — the definition of correctness for the task',
  router: 'Selects expert agents and assigns mandatory coverage requirements',
  assembler: 'Merges expert outputs and provenance into the Primary Agent context',
  implement: 'Primary Agent implements the change (developer role)',
  verify: 'Runs linting, pytest, and security scans — gates fail closed',
  qa: 'QA Agent validates output against the Intent Specification and defect taxonomy',
  publish: 'Creates a draft PR with evidence comment and lifecycle labels on GitHub',
}

export interface StageNodeProps {
  id: StageId
  label: string
  color: string
  status: StageStatus
  taskCount: number
  activeTasks: string[]
}

/** SVG status icons rendered inside the stage circle. */
function StatusIcon({ status, color }: { status: StageStatus; color: string }) {
  const size = 16
  const props = { width: size, height: size, viewBox: '0 0 16 16', 'aria-hidden': true as const }

  switch (status) {
    case 'active':
      return (
        <svg {...props} data-testid="icon-active">
          <circle cx="8" cy="8" r="5" fill={color}>
            <animate attributeName="opacity" values="1;0.4;1" dur="1.5s" repeatCount="indefinite" />
          </circle>
        </svg>
      )
    case 'review':
      return (
        <svg {...props} data-testid="icon-review">
          <ellipse cx="8" cy="8" rx="6" ry="4" fill="none" stroke={color} strokeWidth="1.5" />
          <circle cx="8" cy="8" r="2" fill={color} />
        </svg>
      )
    case 'passed':
      return (
        <svg {...props} data-testid="icon-passed">
          <polyline points="4,8.5 7,11.5 12,5" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      )
    case 'failed':
      return (
        <svg {...props} data-testid="icon-failed">
          <line x1="4.5" y1="4.5" x2="11.5" y2="11.5" stroke={color} strokeWidth="2" strokeLinecap="round" />
          <line x1="11.5" y1="4.5" x2="4.5" y2="11.5" stroke={color} strokeWidth="2" strokeLinecap="round" />
        </svg>
      )
    case 'idle':
    default:
      return (
        <svg {...props} data-testid="icon-idle">
          <circle cx="8" cy="8" r="4" fill="none" stroke={color} strokeWidth="1.5" />
        </svg>
      )
  }
}

function formatDuration(seconds: number | null): string {
  if (seconds == null) return '—'
  if (seconds < 60) return `${Math.round(seconds)}s`
  return `${Math.round(seconds / 60)}m`
}

function formatPercent(rate: number | null): string {
  if (rate == null) return '—'
  return `${Math.round(rate * 100)}%`
}

/** Tooltip shown on hover with 300ms delay. */
function StageTooltip({ id, activeTasks }: { id: StageId; activeTasks: string[] }) {
  const metrics = usePipelineStore((s) => s.stageMetrics)
  const m = metrics?.[id]

  return (
    <div
      className="absolute -top-2 left-1/2 z-50 -translate-x-1/2 -translate-y-full rounded-lg border border-gray-600 bg-gray-800 px-3 py-2 text-xs shadow-lg"
      data-testid="stage-tooltip"
    >
      <div className="space-y-1 whitespace-nowrap">
        <div className="flex justify-between gap-4">
          <span className="text-gray-400">Avg time:</span>
          <span className="font-medium">{formatDuration(m?.avgDuration ?? null)}</span>
        </div>
        <div className="flex justify-between gap-4">
          <span className="text-gray-400">Pass rate:</span>
          <span className="font-medium">{formatPercent(m?.passRate ?? null)}</span>
        </div>
        {activeTasks.length > 0 && (
          <div className="border-t border-gray-700 pt-1 mt-1">
            <span className="text-gray-400">Active:</span>
            {activeTasks.slice(0, 3).map((tid) => (
              <div key={tid} className="truncate text-gray-300" style={{ maxWidth: '140px' }}>
                {tid.slice(0, 12)}…
              </div>
            ))}
            {activeTasks.length > 3 && (
              <div className="text-gray-500">+{activeTasks.length - 3} more</div>
            )}
          </div>
        )}
      </div>
      {/* Arrow */}
      <div className="absolute left-1/2 -bottom-1 h-2 w-2 -translate-x-1/2 rotate-45 border-b border-r border-gray-600 bg-gray-800" />
    </div>
  )
}

export function StageNode({ id, label, color, status, taskCount, activeTasks }: StageNodeProps) {
  const ringColor = status === 'idle' ? STATUS_COLORS.idle : color
  const bgColor = STATUS_COLORS[status]
  const setSelectedStage = usePipelineStore((s) => s.setSelectedStage)

  const [showTooltip, setShowTooltip] = useState(false)
  const hoverTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const nodeRef = useRef<HTMLDivElement>(null)

  // Tooltip with 300ms hover delay
  function onMouseEnter() {
    hoverTimerRef.current = setTimeout(() => setShowTooltip(true), 300)
  }

  function onMouseLeave() {
    if (hoverTimerRef.current) clearTimeout(hoverTimerRef.current)
    setShowTooltip(false)
  }

  // Cleanup timer on unmount
  useEffect(() => {
    return () => {
      if (hoverTimerRef.current) clearTimeout(hoverTimerRef.current)
    }
  }, [])

  // Pulse animation class for active stages
  const pulseClass = status === 'active' ? 'animate-stage-pulse' : ''

  return (
    <div
      className="relative flex flex-col items-center gap-1"
      data-testid={`stage-${label.toLowerCase()}`}
      data-tour="stage-node"
      onMouseEnter={onMouseEnter}
      onMouseLeave={onMouseLeave}
      ref={nodeRef}
    >
      {showTooltip && <StageTooltip id={id} activeTasks={activeTasks} />}
      <button
        type="button"
        className={`relative flex h-12 w-12 items-center justify-center rounded-full border-2 cursor-pointer transition-shadow hover:shadow-lg ${pulseClass}`}
        data-tour="active-pulse"
        style={{
          borderColor: ringColor,
          backgroundColor: `${bgColor}20`,
          '--pulse-color': `${color}40`,
        } as React.CSSProperties}
        onClick={() => setSelectedStage(id)}
        aria-label={`${label} stage, ${STATUS_LABELS[status]}, ${taskCount} task${taskCount === 1 ? '' : 's'}`}
      >
        <StatusIcon status={status} color={bgColor} />
        {/* Task count badge */}
        {taskCount > 0 && (
          <span
            className="absolute -top-1 -right-1 flex h-5 min-w-5 items-center justify-center rounded-full bg-blue-500 px-1 text-xs font-bold text-white"
            data-testid={`stage-count-${label.toLowerCase()}`}
          >
            {taskCount}
          </span>
        )}
      </button>
      <span
        className="text-xs text-gray-400"
        data-tooltip-id="stage-info-tip"
        data-tooltip-content={STAGE_DESCRIPTIONS[id] ?? label}
      >
        {label}
      </span>
      {/* Epic 45.8: react-tooltip for stage descriptions */}
      <Tooltip id="stage-info-tip" place="bottom" className="z-50 max-w-xs text-xs" />
    </div>
  )
}
