/** Zustand store for task steering (pause/resume/abort/redirect/retry) state — Epic 37 Slices 1+2. */

import { create } from 'zustand'
import { pauseTask, resumeTask, abortTask, redirectTask, retryTask } from '../lib/api'

/** Steering-relevant status for the active task. */
export type SteeringStatus = 'running' | 'paused' | 'aborted' | null

export interface SteeringState {
  taskId: string | null
  /** Derived from task status or SSE steering events. */
  steeringStatus: SteeringStatus
  /** Current stage of the task (needed for redirect modal to compute valid earlier stages). */
  currentStage: string | null
  saving: boolean
  error: string | null
  abortModalOpen: boolean
  redirectModalOpen: boolean
  retryModalOpen: boolean
}

export interface SteeringActions {
  /** Initialise store with taskId, current task status, and current stage. */
  init: (taskId: string, taskStatus: string, currentStage?: string | null) => void
  /** Send pause signal to Temporal workflow. */
  pause: () => Promise<void>
  /** Send resume signal to Temporal workflow. */
  resume: () => Promise<void>
  /** Send abort signal with mandatory reason. */
  abort: (reason: string) => Promise<void>
  /** Send redirect signal to target stage with reason. */
  redirect: (targetStage: string, reason: string) => Promise<void>
  /** Send retry signal for current stage. */
  retry: () => Promise<void>
  /** Update steering status from an SSE event. */
  setSteeringStatus: (status: SteeringStatus) => void
  /** Open or close the abort confirmation modal. */
  setAbortModalOpen: (open: boolean) => void
  /** Open or close the redirect modal. */
  setRedirectModalOpen: (open: boolean) => void
  /** Open or close the retry confirmation modal. */
  setRetryModalOpen: (open: boolean) => void
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
  currentStage: null,
  saving: false,
  error: null,
  abortModalOpen: false,
  redirectModalOpen: false,
  retryModalOpen: false,
}

export const useSteeringStore = create<SteeringState & SteeringActions>((set, get) => ({
  ...initialState,

  init: (taskId, taskStatus, currentStage = null) => {
    set({ taskId, steeringStatus: deriveSteeringStatus(taskStatus), currentStage, error: null })
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

  redirect: async (targetStage, reason) => {
    const { taskId } = get()
    if (!taskId) return
    set({ saving: true, error: null })
    try {
      await redirectTask(taskId, targetStage, reason)
      set({ saving: false, redirectModalOpen: false })
    } catch (err) {
      set({ error: err instanceof Error ? err.message : 'Failed to redirect task', saving: false })
    }
  },

  retry: async () => {
    const { taskId } = get()
    if (!taskId) return
    set({ saving: true, error: null })
    try {
      await retryTask(taskId)
      set({ saving: false, retryModalOpen: false })
    } catch (err) {
      set({ error: err instanceof Error ? err.message : 'Failed to retry stage', saving: false })
    }
  },

  setSteeringStatus: (status) => set({ steeringStatus: status }),

  setAbortModalOpen: (open) => set({ abortModalOpen: open, error: null }),

  setRedirectModalOpen: (open) => set({ redirectModalOpen: open, error: null }),

  setRetryModalOpen: (open) => set({ retryModalOpen: open, error: null }),

  clearError: () => set({ error: null }),

  reset: () => set(initialState),
}))
