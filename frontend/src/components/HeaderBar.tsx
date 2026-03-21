/** Header bar showing active count, queued count, and running cost total.
 * Updated via SSE cost events. Zero state: "0 active / 0 queued / $0.00".
 */

import { usePipelineStore } from '../stores/pipeline-store'
import { PIPELINE_STAGES } from '../lib/constants'

export function HeaderBar() {
  const stages = usePipelineStore((s) => s.stages)
  const totalCost = usePipelineStore((s) => s.totalCost)

  // Active = unique task IDs across all stages
  const allActive = new Set(
    PIPELINE_STAGES.flatMap((s) => stages[s.id].activeTasks),
  )
  const activeCount = allActive.size

  // Queued = tasks in intake that haven't progressed
  const queuedCount = stages.intake.activeTasks.length

  return (
    <div className="flex items-center gap-6 text-sm" data-testid="header-bar">
      <span className="text-gray-400" data-testid="active-count">
        <span className="font-medium text-emerald-400">{activeCount}</span> active
      </span>
      <span className="text-gray-400" data-testid="queued-count">
        <span className="font-medium text-amber-400">{queuedCount}</span> queued
      </span>
      <span className="text-gray-400" data-testid="running-cost">
        <span className="font-medium text-cyan-400">${totalCost.toFixed(2)}</span>
      </span>
    </div>
  )
}
