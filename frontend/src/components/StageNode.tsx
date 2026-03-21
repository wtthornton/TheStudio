/** Single pipeline stage node — color-coded circle with label and task count. */

import type { StageStatus } from '../stores/pipeline-store'
import { STATUS_COLORS } from '../lib/constants'

export interface StageNodeProps {
  label: string
  color: string
  status: StageStatus
  taskCount: number
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
        {/* Status dot */}
        <div
          className="h-4 w-4 rounded-full"
          style={{ backgroundColor: bgColor }}
          data-testid={`stage-dot-${label.toLowerCase()}`}
        />
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
