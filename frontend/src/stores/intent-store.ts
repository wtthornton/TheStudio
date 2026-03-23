/** Zustand store for intent review state (Epic 36, Slice 2). */

import { create } from 'zustand'
import type { IntentSpecRead, IntentResponse } from '../lib/api'
import { fetchIntent, approveIntent, rejectIntent, editIntent, refineIntent } from '../lib/api'

export type IntentMode = 'view' | 'edit'

export interface IntentState {
  taskId: string | null
  current: IntentSpecRead | null
  versions: IntentSpecRead[]
  selectedVersion: number | null
  loading: boolean
  error: string | null
  mode: IntentMode
  refineModalOpen: boolean
  saving: boolean
}

export interface IntentActions {
  /** Load intent spec and version history for a task. */
  loadIntent: (taskId: string) => Promise<void>
  /** Approve the current intent spec. */
  approve: () => Promise<void>
  /** Reject the current intent spec with a reason. */
  reject: (reason: string) => Promise<void>
  /** Save edited intent spec (creates new version). */
  saveEdit: (spec: {
    goal: string
    constraints: string[]
    acceptance_criteria: string[]
    non_goals: string[]
  }) => Promise<void>
  /** Request AI refinement with feedback. */
  requestRefine: (feedback: string) => Promise<void>
  /** Select a specific version for viewing. */
  selectVersion: (version: number) => void
  /** Switch between view and edit modes. */
  setMode: (mode: IntentMode) => void
  /** Open or close the refinement modal. */
  setRefineModalOpen: (open: boolean) => void
  /** Reset store to initial state. */
  reset: () => void
}

const initialState: IntentState = {
  taskId: null,
  current: null,
  versions: [],
  selectedVersion: null,
  loading: false,
  error: null,
  mode: 'view',
  refineModalOpen: false,
  saving: false,
}

export const useIntentStore = create<IntentState & IntentActions>((set, get) => ({
  ...initialState,

  loadIntent: async (taskId: string) => {
    set({ loading: true, error: null, taskId })
    try {
      const data: IntentResponse = await fetchIntent(taskId)
      set({
        current: data.current,
        versions: data.versions,
        selectedVersion: data.current?.version ?? null,
        loading: false,
      })
    } catch (err) {
      set({ error: err instanceof Error ? err.message : 'Failed to load intent', loading: false })
    }
  },

  approve: async () => {
    const { taskId } = get()
    if (!taskId) return
    set({ saving: true, error: null })
    try {
      await approveIntent(taskId)
      // Re-fetch to get updated state
      const data = await fetchIntent(taskId)
      set({
        current: data.current,
        versions: data.versions,
        selectedVersion: data.current.version,
        saving: false,
      })
    } catch (err) {
      set({ error: err instanceof Error ? err.message : 'Failed to approve', saving: false })
    }
  },

  reject: async (reason: string) => {
    const { taskId } = get()
    if (!taskId) return
    set({ saving: true, error: null })
    try {
      await rejectIntent(taskId, reason)
      // Re-fetch to get updated state
      const data = await fetchIntent(taskId)
      set({
        current: data.current,
        versions: data.versions,
        selectedVersion: data.current.version,
        saving: false,
      })
    } catch (err) {
      set({ error: err instanceof Error ? err.message : 'Failed to reject', saving: false })
    }
  },

  saveEdit: async (spec) => {
    const { taskId } = get()
    if (!taskId) return
    set({ saving: true, error: null })
    try {
      await editIntent(taskId, spec)
      // Re-fetch to get updated versions
      const data = await fetchIntent(taskId)
      set({
        current: data.current,
        versions: data.versions,
        selectedVersion: data.current.version,
        mode: 'view',
        saving: false,
      })
    } catch (err) {
      set({ error: err instanceof Error ? err.message : 'Failed to save edit', saving: false })
    }
  },

  requestRefine: async (feedback: string) => {
    const { taskId } = get()
    if (!taskId) return
    set({ saving: true, error: null })
    try {
      await refineIntent(taskId, feedback)
      // Re-fetch to get updated versions
      const data = await fetchIntent(taskId)
      set({
        current: data.current,
        versions: data.versions,
        selectedVersion: data.current.version,
        refineModalOpen: false,
        saving: false,
      })
    } catch (err) {
      set({ error: err instanceof Error ? err.message : 'Failed to refine', saving: false })
    }
  },

  selectVersion: (version: number) => {
    const { versions } = get()
    const selected = versions.find((v) => v.version === version)
    if (selected) {
      set({ selectedVersion: version, current: selected })
    }
  },

  setMode: (mode: IntentMode) => {
    set({ mode })
  },

  setRefineModalOpen: (open: boolean) => {
    set({ refineModalOpen: open })
  },

  reset: () => {
    set(initialState)
  },
}))
