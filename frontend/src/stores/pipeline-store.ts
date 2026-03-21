/** Zustand store for pipeline stage state, driven by SSE events. */

import { create } from 'zustand'
import type { StageId } from '../lib/constants'
import { PIPELINE_STAGES } from '../lib/constants'

export type StageStatus = 'idle' | 'active' | 'passed' | 'failed'

export interface StageState {
  status: StageStatus
  taskCount: number
  activeTasks: string[] // taskpacket IDs currently in this stage
}

export interface PipelineState {
  stages: Record<StageId, StageState>
  lastEventId: number | null
  connected: boolean
}

export interface PipelineActions {
  /** A task entered a stage. */
  stageEnter: (stage: StageId, taskpacketId: string) => void
  /** A task exited a stage. */
  stageExit: (stage: StageId, taskpacketId: string, success: boolean) => void
  /** A gate passed or failed. */
  gateResult: (stage: StageId, passed: boolean) => void
  /** Update the last-received event ID for reconnection. */
  setLastEventId: (id: number) => void
  /** Update connection status. */
  setConnected: (connected: boolean) => void
  /** Reset all stages to idle (e.g. after full_state). */
  reset: () => void
}

function initialStages(): Record<StageId, StageState> {
  const stages = {} as Record<StageId, StageState>
  for (const s of PIPELINE_STAGES) {
    stages[s.id] = { status: 'idle', taskCount: 0, activeTasks: [] }
  }
  return stages
}

export const usePipelineStore = create<PipelineState & PipelineActions>()(
  (set) => ({
    stages: initialStages(),
    lastEventId: null,
    connected: false,

    stageEnter: (stage, taskpacketId) =>
      set((state) => {
        const prev = state.stages[stage]
        const activeTasks = prev.activeTasks.includes(taskpacketId)
          ? prev.activeTasks
          : [...prev.activeTasks, taskpacketId]
        return {
          stages: {
            ...state.stages,
            [stage]: {
              status: 'active' as const,
              taskCount: prev.taskCount + 1,
              activeTasks,
            },
          },
        }
      }),

    stageExit: (stage, taskpacketId, success) =>
      set((state) => {
        const prev = state.stages[stage]
        const activeTasks = prev.activeTasks.filter((id) => id !== taskpacketId)
        return {
          stages: {
            ...state.stages,
            [stage]: {
              status: activeTasks.length > 0 ? ('active' as const) : success ? ('passed' as const) : ('failed' as const),
              taskCount: prev.taskCount,
              activeTasks,
            },
          },
        }
      }),

    gateResult: (stage, passed) =>
      set((state) => {
        const prev = state.stages[stage]
        return {
          stages: {
            ...state.stages,
            [stage]: {
              ...prev,
              status: passed ? ('passed' as const) : ('failed' as const),
            },
          },
        }
      }),

    setLastEventId: (id) => set({ lastEventId: id }),
    setConnected: (connected) => set({ connected }),
    reset: () => set({ stages: initialStages(), lastEventId: null }),
  }),
)
