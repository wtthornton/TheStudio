/** Zustand store for task steering (pause/resume/abort) state — Epic 37 Slice 1. */

import { create } from 'zustand'
import { pauseTask, resumeTask, abortTask } from '../lib/api'

/** Steering-relevant status for the active task. */
export type SteeringStatus = 'running' | 'paused' | 'aborted' | null

export interface SteeringState {
  taskId: string | null
  /** Derived from task status or SSE steering events. */
  steeringStatus: SteeringStatus
  saving: boolean
  error: string | null
  abortModalOpen: boolean
}

export interface SteeringActions {
  /** Initialise store with taskId and current task status. */
  init: (taskId: string, taskStatus: string) => void
  /** Send pause signal to Temporal workflow. */
  pause: () => Promise<void>
  /** Send resume signal to Temporal workflow. */
  resume: () => Promise<void>
  /** Send abort signal with mandatory reason. */
  abort: (reason: string) => Promise<void>
  /** Update steering status from an SSE event. */
  setSteeringStatus: (status: SteeringStatus) => void
  /** Open or close the abort confirmation modal. */
  setAbortModalOpen: (open: boolean) => void
  /** Clear current error. */
  clearError: () => void
  /** Reset store to initial state. */
  reset: () => void
}

/** Map task status string to SteeringStatus. */
function deriveSteeringStatus(taskStatus: string): SteeringStatus {
  if (taskStatus === 'paused') return 'paused'
  if (taskStatus === 'aborted') return 'aborted'
  const activeStatuses = ['running', 'active', 'in_progress', 'processing', 'pending']
  if (activeStatuses.includes(taskStatus)) return 'running'
  return null
}

const initialState: SteeringState = {
  taskId: null,
  steeringStatus: null,
  saving: false,
  error: null,
  abortModalOpen: false,
}

export const useSteeringStore = create<SteeringState & SteeringActions>((set, get) => ({
  ...initialState,

  init: (taskId, taskStatus) => {
    set({ taskId, steeringStatus: deriveSteeringStatus(taskStatus), error: null })
  },

  pause: async () => {
    const { taskId } = get()
    if (!taskId) return
    set({ saving: true, error: null })
    try {
      await pauseTask(taskId)
      set({ steeringStatus: 'paused', saving: false })
    } catch (err) {
      set({ error: err instanceof Error ? err.message : 'Failed to pause task', saving: false })
    }
  },

  resume: async () => {
    const { taskId } = get()
    if (!taskId) return
    set({ saving: true, error: null })
    try {
      await resumeTask(taskId)
      set({ steeringStatus: 'running', saving: false })
    } catch (err) {
      set({ error: err instanceof Error ? err.message : 'Failed to resume task', saving: false })
    }
  },

  abort: async (reason) => {
    const { taskId } = get()
    if (!taskId) return
    set({ saving: true, error: null })
    try {
      await abortTask(taskId, reason)
      set({ steeringStatus: 'aborted', saving: false, abortModalOpen: false })
    } catch (err) {
      set({ error: err instanceof Error ? err.message : 'Failed to abort task', saving: false })
    }
  },

  setSteeringStatus: (status) => set({ steeringStatus: status }),

  setAbortModalOpen: (open) => set({ abortModalOpen: open, error: null }),

  clearError: () => set({ error: null }),

  reset: () => set(initialState),
}))
