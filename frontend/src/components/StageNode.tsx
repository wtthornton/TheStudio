/** Single pipeline stage node — color-coded circle with status icon, label, and task count. */

import type { StageStatus } from '../stores/pipeline-store'
import { STATUS_COLORS } from '../lib/constants'

export interface StageNodeProps {
  label: string
  color: string
  status: StageStatus
  taskCount: number
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
      // Eye icon
      return (
        <svg {...props} data-testid="icon-review">
          <ellipse cx="8" cy="8" rx="6" ry="4" fill="none" stroke={color} strokeWidth="1.5" />
          <circle cx="8" cy="8" r="2" fill={color} />
        </svg>
      )
    case 'passed':
      // Checkmark
      return (
        <svg {...props} data-testid="icon-passed">
          <polyline points="4,8.5 7,11.5 12,5" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      )
    case 'failed':
      // X mark
      return (
        <svg {...props} data-testid="icon-failed">
          <line x1="4.5" y1="4.5" x2="11.5" y2="11.5" stroke={color} strokeWidth="2" strokeLinecap="round" />
          <line x1="11.5" y1="4.5" x2="4.5" y2="11.5" stroke={color} strokeWidth="2" strokeLinecap="round" />
        </svg>
      )
    case 'idle':
    default:
      // Empty circle
      return (
        <svg {...props} data-testid="icon-idle">
          <circle cx="8" cy="8" r="4" fill="none" stroke={color} strokeWidth="1.5" />
        </svg>
      )
  }
}

export function StageNode({ label, color, status, taskCount }: StageNodeProps) {
  const ringColor = status === 'idle' ? STATUS_COLORS.idle : color
  const bgColor = STATUS_COLORS[status]

  return (
    <div className="flex flex-col items-center gap-1" data-testid={`stage-${label.toLowerCase()}`}>
      <div
        className="relative flex h-12 w-12 items-center justify-center rounded-full border-2"
        style={{ borderColor: ringColor, backgroundColor: `${bgColor}20` }}
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
      </div>
      <span className="text-xs text-gray-400">{label}</span>
    </div>
  )
}
