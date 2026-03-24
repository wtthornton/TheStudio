/** Backlog board Zustand store — groups all TaskPackets into Kanban columns. */

import { create } from 'zustand'
import { fetchTasks } from '../lib/api'
import type { TaskPacketRead } from '../lib/api'

// Column definitions: id, display label, and the set of backend statuses they capture.
export const BOARD_COLUMNS = [
  {
    id: 'triage' as const,
    label: 'Triage',
    statuses: ['triage'],
    headerClass: 'text-amber-400 border-amber-800',
  },
  {
    id: 'planning' as const,
    label: 'Planning',
    statuses: [
      'received',
      'enriched',
      'clarification_requested',
      'human_review_required',
      'intent_built',
    ],
    headerClass: 'text-blue-400 border-blue-800',
  },
  {
    id: 'building' as const,
    label: 'Building',
    statuses: ['in_progress'],
    headerClass: 'text-violet-400 border-violet-800',
  },
  {
    id: 'verify' as const,
    label: 'Verify',
    statuses: [
      'verification_passed',
      'verification_failed',
      'awaiting_approval',
      'awaiting_approval_expired',
    ],
    headerClass: 'text-orange-400 border-orange-800',
  },
  {
    id: 'done' as const,
    label: 'Done',
    statuses: ['published'],
    headerClass: 'text-emerald-400 border-emerald-800',
  },
  {
    id: 'rejected' as const,
    label: 'Rejected',
    statuses: ['rejected', 'failed'],
    headerClass: 'text-red-400 border-red-800',
  },
] as const

export type ColumnId = (typeof BOARD_COLUMNS)[number]['id']

/** Group a flat task list into per-column buckets. */
export function groupTasksByColumn(tasks: TaskPacketRead[]): Record<ColumnId, TaskPacketRead[]> {
  const groups: Record<string, TaskPacketRead[]> = {}
  for (const col of BOARD_COLUMNS) {
    groups[col.id] = []
  }
  for (const task of tasks) {
    const col = BOARD_COLUMNS.find((c) => (c.statuses as readonly string[]).includes(task.status))
    if (col) {
      groups[col.id].push(task)
    }
  }
  return groups as Record<ColumnId, TaskPacketRead[]>
}

// --- State + Actions ---

export interface BacklogState {
  tasks: TaskPacketRead[]
  loading: boolean
  error: string | null
  lastLoaded: number | null
}

export interface BacklogActions {
  /** Load tasks, optionally filtered by repo full_name. */
  loadBoard: (repo?: string | null) => Promise<void>
  reset: () => void
}

const initialState: BacklogState = {
  tasks: [],
  loading: false,
  error: null,
  lastLoaded: null,
}

export const useBacklogStore = create<BacklogState & BacklogActions>((set) => ({
  ...initialState,

  loadBoard: async (repo?: string | null) => {
    set({ loading: true, error: null })
    try {
      const result = await fetchTasks({ limit: 200, repo })
      set({ tasks: result.items, loading: false, lastLoaded: Date.now() })
    } catch (err) {
      set({
        loading: false,
        error: err instanceof Error ? err.message : 'Failed to load tasks',
      })
    }
  },

  reset: () => set(initialState),
}))
