/** Horizontal rail of 9 pipeline stage nodes with connecting arrows. */

import { PIPELINE_STAGES } from '../lib/constants'
import { usePipelineStore } from '../stores/pipeline-store'
import { StageNode } from './StageNode'

export function PipelineStatus() {
  const stages = usePipelineStore((s) => s.stages)

  return (
    <div className="flex items-center gap-2 overflow-x-auto px-4 py-6" data-testid="pipeline-rail">
      {PIPELINE_STAGES.map((stage, i) => {
        const state = stages[stage.id]
        return (
          <div key={stage.id} className="flex items-center gap-2">
            <StageNode
              label={stage.label}
              color={stage.color}
              status={state.status}
              taskCount={state.taskCount}
            />
            {i < PIPELINE_STAGES.length - 1 && (
              <svg width="24" height="12" viewBox="0 0 24 12" className="text-gray-600" aria-hidden>
                <line x1="0" y1="6" x2="18" y2="6" stroke="currentColor" strokeWidth="2" />
                <polygon points="18,2 24,6 18,10" fill="currentColor" />
              </svg>
            )}
          </div>
        )
      })}
    </div>
  )
}
