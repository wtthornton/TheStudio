/** BacklogCard — compact Kanban card for a single TaskPacket. */

import type { TaskPacketRead } from '../../lib/api'

interface BacklogCardProps {
  task: TaskPacketRead
  onClick: (taskId: string) => void
}

/** Extract a numeric complexity score from complexity_index, if present. */
function getComplexityScore(task: TaskPacketRead): number | null {
  const ci = task.complexity_index
  if (!ci) return null
  if (typeof ci['score'] === 'number') return ci['score'] as number
  if (typeof ci['complexity_score'] === 'number') return ci['complexity_score'] as number
  return null
}

/** Sum the cost values from stage_timings if any exist. */
function getTotalCost(task: TaskPacketRead): number | null {
  const timings = task.stage_timings
  if (!timings) return null
  const total = Object.values(timings).reduce((sum, t) => sum + (t.cost ?? 0), 0)
  return total > 0 ? total : null
}

function complexityColorClass(score: number): string {
  if (score >= 7) return 'text-red-400'
  if (score >= 4) return 'text-amber-400'
  return 'text-emerald-400'
}

/** Derive a human-readable category from the task's scope or risk data. */
function getCategory(task: TaskPacketRead): string | null {
  const ci = task.complexity_index
  if (!ci) return null
  if (typeof ci['category'] === 'string') return ci['category'] as string
  return null
}

export function BacklogCard({ task, onClick }: BacklogCardProps) {
  const score = getComplexityScore(task)
  const cost = getTotalCost(task)
  const category = getCategory(task)
  const riskCount = task.risk_flags
    ? Object.values(task.risk_flags).filter(Boolean).length
    : 0

  return (
    <button
      onClick={() => onClick(task.id)}
      className="w-full text-left rounded-lg border border-gray-700 bg-gray-900 p-3
                 hover:border-gray-500 hover:bg-gray-800 transition-colors focus:outline-none
                 focus:ring-1 focus:ring-gray-500"
    >
      {/* Row 1: issue number + repo */}
      <div className="flex items-center justify-between mb-1 gap-1">
        <span className="text-xs font-mono text-gray-500">#{task.issue_id}</span>
        {category && (
          <span className="text-xs text-gray-600 truncate max-w-[90px]">{category}</span>
        )}
      </div>

      {/* Row 2: title */}
      <p className="text-sm text-gray-100 leading-snug mb-2 line-clamp-2 min-h-[2.5rem]">
        {task.issue_title ?? (
          <span className="text-gray-600 italic">No title</span>
        )}
      </p>

      {/* Row 3: complexity score / cost / risk flags */}
      <div className="flex items-center gap-2 flex-wrap">
        {score != null && (
          <span className={`text-xs font-mono ${complexityColorClass(score)}`} title="Complexity score">
            C:{score.toFixed(1)}
          </span>
        )}
        {cost != null && (
          <span className="text-xs font-mono text-gray-400" title="Total cost">
            ${cost.toFixed(3)}
          </span>
        )}
        {riskCount > 0 && (
          <span className="text-xs text-red-400" title={`${riskCount} risk flag(s)`}>
            ⚑ {riskCount}
          </span>
        )}
        {score == null && cost == null && riskCount === 0 && (
          <span className="text-xs text-gray-700 italic">pending</span>
        )}
      </div>

      {/* Row 4: PR link (shown when published) */}
      {task.pr_url && (
        <a
          href={task.pr_url}
          target="_blank"
          rel="noopener noreferrer"
          onClick={(e) => e.stopPropagation()}
          className="mt-2 inline-flex items-center gap-1 text-xs text-blue-400 hover:text-blue-300 truncate"
          title={`PR #${task.pr_number}`}
        >
          PR #{task.pr_number}
        </a>
      )}
    </button>
  )
}
