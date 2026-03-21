/** Zustand store for pipeline stage state, driven by SSE events. */

import { create } from 'zustand'
import type { StageId } from '../lib/constants'
import { PIPELINE_STAGES } from '../lib/constants'

export type StageStatus = 'idle' | 'active' | 'review' | 'passed' | 'failed'

export interface StageState {
  status: StageStatus
  taskCount: number
  activeTasks: string[] // taskpacket IDs currently in this stage
}

export interface EventEntry {
  id: number
  type: string
  stage?: string
  taskpacketId?: string
  timestamp: number // Date.now()
}

const MAX_EVENTS = 20

export interface PipelineState {
  stages: Record<StageId, StageState>
  lastEventId: number | null
  connected: boolean
  events: EventEntry[]
  totalCost: number
  selectedStage: StageId | null
  stageMetrics: Record<string, { passRate: number | null; avgDuration: number | null; throughput: number }> | null
  tasksLoading: boolean
  metricsLoading: boolean
}

export interface PipelineActions {
  /** A task entered a stage. */
  stageEnter: (stage: StageId, taskpacketId: string) => void
  /** A task exited a stage. */
  stageExit: (stage: StageId, taskpacketId: string, success: boolean) => void
  /** A gate passed or failed. */
  gateResult: (stage: StageId, passed: boolean) => void
  /** Update running cost from SSE cost events. */
  costUpdate: (taskId: string, costDelta: number, totalCost: number) => void
  /** Update the last-received event ID for reconnection. */
  setLastEventId: (id: number) => void
  /** Update connection status. */
  setConnected: (connected: boolean) => void
  /** Push a raw event to the log (keeps last 20). */
  pushEvent: (type: string, stage?: string, taskpacketId?: string) => void
  /** Select a stage for the detail panel (null to close). */
  setSelectedStage: (stage: StageId | null) => void
  /** Set stage metrics from API response. */
  setStageMetrics: (metrics: Record<string, { passRate: number | null; avgDuration: number | null; throughput: number }> | null) => void
  /** Set loading states. */
  setTasksLoading: (loading: boolean) => void
  setMetricsLoading: (loading: boolean) => void
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
    events: [],
    totalCost: 0,
    selectedStage: null,
    stageMetrics: null,
    tasksLoading: false,
    metricsLoading: false,

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

    costUpdate: (_taskId, _costDelta, totalCost) => set({ totalCost }),

    setLastEventId: (id) => set({ lastEventId: id }),
    setConnected: (connected) => set({ connected }),
    pushEvent: (type, stage, taskpacketId) =>
      set((state) => {
        const entry: EventEntry = {
          id: (state.lastEventId ?? 0) + 1,
          type,
          stage,
          taskpacketId,
          timestamp: Date.now(),
        }
        const events = [entry, ...state.events].slice(0, MAX_EVENTS)
        return { events }
      }),
    setSelectedStage: (stage) => set({ selectedStage: stage }),
    setStageMetrics: (metrics) => set({ stageMetrics: metrics }),
    setTasksLoading: (loading) => set({ tasksLoading: loading }),
    setMetricsLoading: (loading) => set({ metricsLoading: loading }),
    reset: () => set({ stages: initialStages(), lastEventId: null, events: [], totalCost: 0, stageMetrics: null }),
  }),
)
