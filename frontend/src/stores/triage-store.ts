/** Zustand store for triage queue state (Epic 36). */

import { create } from 'zustand'
import type { TriageTask, RejectionReason } from '../lib/api'
import { fetchTriageTasks, acceptTriageTask, rejectTriageTask, editTriageTask } from '../lib/api'

export interface TriageState {
  tasks: TriageTask[]
  loading: boolean
  error: string | null
}

export interface TriageActions {
  /** Fetch triage tasks from the API, optionally filtered by repo full_name. */
  loadTasks: (repo?: string | null) => Promise<void>
  /** Accept a task (transition to pipeline). */
  accept: (taskId: string) => Promise<void>
  /** Reject a task with a reason. */
  reject: (taskId: string, reason: RejectionReason) => Promise<void>
  /** Edit a task's fields. */
  edit: (taskId: string, fields: { issue_title?: string; issue_body?: string }) => Promise<void>
  /** Add a task from SSE event. */
  addTask: (task: TriageTask) => void
  /** Remove a task by ID (after accept/reject via SSE). */
  removeTask: (taskId: string) => void
}

export const useTriageStore = create<TriageState & TriageActions>((set, get) => ({
  tasks: [],
  loading: false,
  error: null,

  loadTasks: async (repo?: string | null) => {
    set({ loading: true, error: null })
    try {
      const { items } = await fetchTriageTasks(repo)
      set({ tasks: items, loading: false })
    } catch (err) {
      set({ error: err instanceof Error ? err.message : 'Failed to load', loading: false })
    }
  },

  accept: async (taskId: string) => {
    try {
      await acceptTriageTask(taskId)
      set({ tasks: get().tasks.filter((t) => t.id !== taskId) })
    } catch (err) {
      set({ error: err instanceof Error ? err.message : 'Failed to accept' })
    }
  },

  reject: async (taskId: string, reason: RejectionReason) => {
    try {
      await rejectTriageTask(taskId, reason)
      set({ tasks: get().tasks.filter((t) => t.id !== taskId) })
    } catch (err) {
      set({ error: err instanceof Error ? err.message : 'Failed to reject' })
    }
  },

  edit: async (taskId: string, fields) => {
    try {
      const updated = await editTriageTask(taskId, fields)
      set({ tasks: get().tasks.map((t) => (t.id === taskId ? updated : t)) })
    } catch (err) {
      set({ error: err instanceof Error ? err.message : 'Failed to edit' })
    }
  },

  addTask: (task: TriageTask) => {
    set({ tasks: [task, ...get().tasks] })
  },

  removeTask: (taskId: string) => {
    set({ tasks: get().tasks.filter((t) => t.id !== taskId) })
  },
}))
