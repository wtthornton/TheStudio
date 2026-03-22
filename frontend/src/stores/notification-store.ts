/** Zustand store for notifications — Epic 37 Slice 5. */

import { create } from 'zustand'
import {
  fetchNotifications,
  markNotificationRead,
  markAllNotificationsRead,
} from '../lib/api'
import type { NotificationRead } from '../lib/api'

export interface NotificationState {
  notifications: NotificationRead[]
  unreadCount: number
  total: number
  loading: boolean
  error: string | null
  open: boolean
}

export interface NotificationActions {
  load: () => Promise<void>
  markRead: (id: string) => Promise<void>
  markAllRead: () => Promise<void>
  /** Called from SSE when a notification-generating event arrives. */
  onPipelineEvent: () => void
  setOpen: (open: boolean) => void
  clearError: () => void
}

const initialState: NotificationState = {
  notifications: [],
  unreadCount: 0,
  total: 0,
  loading: false,
  error: null,
  open: false,
}

export const useNotificationStore = create<NotificationState & NotificationActions>(
  (set, get) => ({
    ...initialState,

    load: async () => {
      set({ loading: true, error: null })
      try {
        const data = await fetchNotifications({ limit: 50 })
        set({
          notifications: data.items,
          unreadCount: data.unread_count,
          total: data.total,
          loading: false,
        })
      } catch (err) {
        set({
          error: err instanceof Error ? err.message : 'Failed to load notifications',
          loading: false,
        })
      }
    },

    markRead: async (id: string) => {
      try {
        const updated = await markNotificationRead(id)
        set((state) => ({
          notifications: state.notifications.map((n) => (n.id === id ? updated : n)),
          unreadCount: Math.max(0, state.unreadCount - (updated.read ? 1 : 0)),
        }))
        // Re-fetch to sync unread_count accurately
        const data = await fetchNotifications({ limit: 50 })
        set({
          notifications: data.items,
          unreadCount: data.unread_count,
          total: data.total,
        })
      } catch (err) {
        set({ error: err instanceof Error ? err.message : 'Failed to mark read' })
      }
    },

    markAllRead: async () => {
      try {
        await markAllNotificationsRead()
        const data = await fetchNotifications({ limit: 50 })
        set({
          notifications: data.items,
          unreadCount: data.unread_count,
          total: data.total,
        })
      } catch (err) {
        set({ error: err instanceof Error ? err.message : 'Failed to mark all read' })
      }
    },

    onPipelineEvent: () => {
      // Debounce: skip if already loading
      if (!get().loading) {
        void get().load()
      }
    },

    setOpen: (open: boolean) => {
      set({ open })
      // Load fresh data when opening the dropdown
      if (open) {
        void get().load()
      }
    },

    clearError: () => set({ error: null }),
  }),
)
