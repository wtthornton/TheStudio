/** Header bar showing active count, queued count, and running cost total.
 * Updated via SSE cost events. Zero state: "0 active / 0 queued / $0.00".
 * Epic 46.5: Onboarding hint shown when all KPIs are zero.
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

  const allZero = activeCount === 0 && queuedCount === 0 && totalCost === 0

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
      {allZero && (
        <span
          className="ml-2 rounded-full border border-indigo-700 bg-indigo-900/40 px-3 py-0.5 text-xs text-indigo-300"
          data-testid="onboarding-hint"
        >
          Import your first GitHub issue to get started →
        </span>
      )}
    </div>
  )
}
