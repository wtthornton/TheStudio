/** Two-row pipeline rail: 9 stage nodes with directional SVG arrows.
 *
 * Row 1: Intake → Context → Intent → Router → Assembler
 * Row 2: Implement → Verify → QA → Publish
 * A vertical arrow connects Assembler (row 1) to Implement (row 2).
 */

import { Tooltip } from 'react-tooltip'
import { PIPELINE_STAGES } from '../lib/constants'
import { usePipelineStore } from '../stores/pipeline-store'
import { StageNode } from './StageNode'

const ROW_1 = PIPELINE_STAGES.slice(0, 5) // Intake..Assembler
const ROW_2 = PIPELINE_STAGES.slice(5)    // Implement..Publish

function HorizontalArrow({ fromLabel, toLabel }: { fromLabel?: string; toLabel?: string }) {
  return (
    <svg
      width="32" height="12" viewBox="0 0 32 12"
      className="shrink-0 text-gray-600"
      aria-hidden
      data-tooltip-id="pipeline-tip"
      data-tooltip-content={fromLabel && toLabel ? `${fromLabel} → ${toLabel}` : undefined}
    >
      <line x1="0" y1="6" x2="24" y2="6" stroke="currentColor" strokeWidth="2" />
      <polygon points="24,2 32,6 24,10" fill="currentColor" />
    </svg>
  )
}

function VerticalArrow() {
  return (
    <svg
      width="12" height="32" viewBox="0 0 12 32"
      className="shrink-0 text-gray-600"
      aria-hidden
      data-tooltip-id="pipeline-tip"
      data-tooltip-content="Pipeline continues from Assembler to Implement stage"
    >
      <line x1="6" y1="0" x2="6" y2="24" stroke="currentColor" strokeWidth="2" />
      <polygon points="2,24 6,32 10,24" fill="currentColor" />
    </svg>
  )
}

export function PipelineStatus() {
  const stages = usePipelineStore((s) => s.stages)

  return (
    <div className="flex flex-col items-end gap-2 px-4 py-6" data-testid="pipeline-rail">
      {/* Row 1: Intake → Assembler */}
      <div className="flex items-center gap-2">
        {ROW_1.map((stage, i) => {
          const state = stages[stage.id]
          return (
            <div key={stage.id} className="flex items-center gap-2">
              <StageNode
                id={stage.id}
                label={stage.label}
                color={stage.color}
                status={state.status}
                taskCount={state.taskCount}
                activeTasks={state.activeTasks}
              />
              {i < ROW_1.length - 1 && (
                <HorizontalArrow fromLabel={ROW_1[i].label} toLabel={ROW_1[i + 1].label} />
              )}
            </div>
          )
        })}
      </div>

      {/* Vertical connector: Assembler → Implement */}
      <div className="flex justify-end pr-6">
        <VerticalArrow />
      </div>

      {/* Row 2: Implement → Publish */}
      <div className="flex items-center gap-2">
        {ROW_2.map((stage, i) => {
          const state = stages[stage.id]
          return (
            <div key={stage.id} className="flex items-center gap-2">
              <StageNode
                id={stage.id}
                label={stage.label}
                color={stage.color}
                status={state.status}
                taskCount={state.taskCount}
                activeTasks={state.activeTasks}
              />
              {i < ROW_2.length - 1 && (
                <HorizontalArrow fromLabel={ROW_2[i].label} toLabel={ROW_2[i + 1].label} />
              )}
            </div>
          )
        })}
      </div>
      {/* Epic 45.8: react-tooltip for pipeline arrows */}
      <Tooltip id="pipeline-tip" place="top" className="z-50 max-w-xs text-xs" />
    </div>
  )
}
