/** Zustand store for routing review state (Epic 36, Slice 3). */

import { create } from 'zustand'
import type { RoutingResultRead } from '../lib/api'
import { fetchRouting, approveRouting, overrideRouting } from '../lib/api'

export interface RoutingState {
  taskId: string | null
  routing: RoutingResultRead | null
  loading: boolean
  error: string | null
  saving: boolean
}

export interface RoutingActions {
  /** Load routing result for a task. */
  loadRouting: (taskId: string) => Promise<void>
  /** Approve the current routing plan. */
  approve: () => Promise<void>
  /** Override the routing plan with a reason. */
  override: (reason: string) => Promise<void>
  /** Reset store to initial state. */
  reset: () => void
}

const initialState: RoutingState = {
  taskId: null,
  routing: null,
  loading: false,
  error: null,
  saving: false,
}

export const useRoutingStore = create<RoutingState & RoutingActions>((set, get) => ({
  ...initialState,

  loadRouting: async (taskId: string) => {
    set({ loading: true, error: null, taskId })
    try {
      const data = await fetchRouting(taskId)
      set({ routing: data, loading: false })
    } catch (err) {
      set({ error: err instanceof Error ? err.message : 'Failed to load routing', loading: false })
    }
  },

  approve: async () => {
    const { taskId } = get()
    if (!taskId) return
    set({ saving: true, error: null })
    try {
      await approveRouting(taskId)
      // Re-fetch to get updated state
      const data = await fetchRouting(taskId)
      set({ routing: data, saving: false })
    } catch (err) {
      set({ error: err instanceof Error ? err.message : 'Failed to approve routing', saving: false })
    }
  },

  override: async (reason: string) => {
    const { taskId } = get()
    if (!taskId) return
    set({ saving: true, error: null })
    try {
      await overrideRouting(taskId, reason)
      // Re-fetch to get updated state
      const data = await fetchRouting(taskId)
      set({ routing: data, saving: false })
    } catch (err) {
      set({ error: err instanceof Error ? err.message : 'Failed to override routing', saving: false })
    }
  },

  reset: () => {
    set(initialState)
  },
}))
