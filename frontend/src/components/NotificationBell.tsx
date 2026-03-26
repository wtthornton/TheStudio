/** NotificationBell — top-bar bell icon with unread badge + dropdown.
 *
 * Dropdown sections:
 *  - "New" — unread notifications (newest first)
 *  - "Earlier" — read notifications
 *
 * Each item shows a type icon, title, message excerpt, relative timestamp.
 * Clicking an item navigates to the relevant view (pipeline task, budget, trust).
 * Mark-all-read clears the badge.
 *
 * Epic 37 Slice 5 — 37.27
 */

import { useEffect, useRef, useCallback } from 'react'
import { useNotificationStore } from '../stores/notification-store'
import type { NotificationRead, NotificationType } from '../lib/api'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatRelativeTime(iso: string): string {
  const now = Date.now()
  const then = new Date(iso).getTime()
  const diffMs = now - then
  const diffSec = Math.floor(diffMs / 1000)
  if (diffSec < 60) return 'just now'
  const diffMin = Math.floor(diffSec / 60)
  if (diffMin < 60) return `${diffMin}m ago`
  const diffHr = Math.floor(diffMin / 60)
  if (diffHr < 24) return `${diffHr}h ago`
  const diffDay = Math.floor(diffHr / 24)
  if (diffDay < 7) return `${diffDay}d ago`
  return new Date(iso).toLocaleDateString()
}

const TYPE_ICONS: Record<NotificationType, string> = {
  gate_fail: '🚫',
  cost_update: '💰',
  steering_action: '🔧',
  trust_tier_assigned: '🔒',
}

const TYPE_LABELS: Record<NotificationType, string> = {
  gate_fail: 'Gate Failure',
  cost_update: 'Cost Alert',
  steering_action: 'Steering',
  trust_tier_assigned: 'Trust Tier',
}

// ---------------------------------------------------------------------------
// NotificationItem
// ---------------------------------------------------------------------------

interface NotificationItemProps {
  notification: NotificationRead
  onNavigate: (tab: string, taskId?: string) => void
}

function NotificationItem({ notification, onNavigate }: NotificationItemProps) {
  const markRead = useNotificationStore((s) => s.markRead)

  const handleClick = useCallback(() => {
    if (!notification.read) {
      void markRead(notification.id)
    }
    // Navigate to relevant view
    if (notification.type === 'cost_update') {
      onNavigate('budget')
    } else if (notification.type === 'trust_tier_assigned') {
      onNavigate('trust')
    } else if (notification.task_id) {
      // gate_fail, steering_action → pipeline tab with task selected
      onNavigate('pipeline', notification.task_id)
    } else {
      onNavigate('pipeline')
    }
  }, [notification, markRead, onNavigate])

  const icon = TYPE_ICONS[notification.type] ?? '📋'
  const label = TYPE_LABELS[notification.type] ?? notification.type

  return (
    <button
      onClick={handleClick}
      data-testid="notification-item"
      className={`w-full text-left px-4 py-3 hover:bg-gray-700/50 transition-colors border-b border-gray-800 last:border-b-0 ${
        notification.read ? 'opacity-60' : ''
      }`}
    >
      <div className="flex items-start gap-3">
        <span className="text-lg shrink-0 mt-0.5">{icon}</span>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 mb-0.5">
            <span className="text-xs font-medium text-gray-400">{label}</span>
            {!notification.read && (
              <span className="inline-block w-1.5 h-1.5 rounded-full bg-blue-400 shrink-0" />
            )}
            <span className="text-xs text-gray-500 ml-auto shrink-0">
              {formatRelativeTime(notification.created_at)}
            </span>
          </div>
          <p className="text-sm font-medium text-gray-200 truncate">{notification.title}</p>
          <p className="text-xs text-gray-400 mt-0.5 line-clamp-2">{notification.message}</p>
        </div>
      </div>
    </button>
  )
}

// ---------------------------------------------------------------------------
// NotificationDropdown
// ---------------------------------------------------------------------------

interface NotificationDropdownProps {
  onNavigate: (tab: string, taskId?: string) => void
  onClose: () => void
}

function NotificationDropdown({ onNavigate, onClose }: NotificationDropdownProps) {
  const notifications = useNotificationStore((s) => s.notifications)
  const unreadCount = useNotificationStore((s) => s.unreadCount)
  const loading = useNotificationStore((s) => s.loading)
  const markAllRead = useNotificationStore((s) => s.markAllRead)

  const newItems = notifications.filter((n) => !n.read)
  const earlierItems = notifications.filter((n) => n.read)

  const handleMarkAll = useCallback(() => {
    void markAllRead()
  }, [markAllRead])

  const handleNavigate = useCallback(
    (tab: string, taskId?: string) => {
      onNavigate(tab, taskId)
      onClose()
    },
    [onNavigate, onClose],
  )

  return (
    <div
      className="absolute right-0 top-full mt-2 w-96 rounded-lg border border-gray-700 bg-gray-900 shadow-2xl z-50"
      data-testid="notification-dropdown"
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-700">
        <h3 className="text-sm font-semibold text-gray-100">Notifications</h3>
        {unreadCount > 0 && (
          <button
            onClick={handleMarkAll}
            className="text-xs text-blue-400 hover:text-blue-300 transition-colors"
            data-testid="mark-all-read"
          >
            Mark all read
          </button>
        )}
      </div>

      {/* Body */}
      <div className="max-h-96 overflow-y-auto">
        {loading && notifications.length === 0 ? (
          <div className="px-4 py-8 text-center text-sm text-gray-500">Loading…</div>
        ) : notifications.length === 0 ? (
          <div className="px-4 py-8 text-center text-sm text-gray-500">No notifications</div>
        ) : (
          <>
            {newItems.length > 0 && (
              <>
                <div className="px-4 py-1.5 bg-gray-800/50">
                  <span className="text-xs font-semibold text-gray-400 uppercase tracking-wide">
                    New
                  </span>
                </div>
                {newItems.map((n) => (
                  <NotificationItem
                    key={n.id}
                    notification={n}
                    onNavigate={handleNavigate}
                  />
                ))}
              </>
            )}
            {earlierItems.length > 0 && (
              <>
                <div className="px-4 py-1.5 bg-gray-800/50">
                  <span className="text-xs font-semibold text-gray-400 uppercase tracking-wide">
                    Earlier
                  </span>
                </div>
                {earlierItems.map((n) => (
                  <NotificationItem
                    key={n.id}
                    notification={n}
                    onNavigate={handleNavigate}
                  />
                ))}
              </>
            )}
          </>
        )}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// NotificationBell (main export)
// ---------------------------------------------------------------------------

interface NotificationBellProps {
  onNavigate: (tab: string, taskId?: string) => void
}

export function NotificationBell({ onNavigate }: NotificationBellProps) {
  const unreadCount = useNotificationStore((s) => s.unreadCount)
  const open = useNotificationStore((s) => s.open)
  const setOpen = useNotificationStore((s) => s.setOpen)
  const load = useNotificationStore((s) => s.load)

  const containerRef = useRef<HTMLDivElement>(null)

  // Initial load on mount
  useEffect(() => {
    void load()
  }, [load])

  // Close on outside click
  useEffect(() => {
    if (!open) return

    function handleOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }

    document.addEventListener('mousedown', handleOutside)
    return () => document.removeEventListener('mousedown', handleOutside)
  }, [open, setOpen])

  // Close on Escape
  useEffect(() => {
    if (!open) return

    function handleKey(e: KeyboardEvent) {
      if (e.key === 'Escape') setOpen(false)
    }

    document.addEventListener('keydown', handleKey)
    return () => document.removeEventListener('keydown', handleKey)
  }, [open, setOpen])

  const toggle = useCallback(() => setOpen(!open), [open, setOpen])
  const close = useCallback(() => setOpen(false), [setOpen])

  return (
    <div className="relative" ref={containerRef} data-component="NotificationBell">
      <button
        onClick={toggle}
        aria-label={`Notifications${unreadCount > 0 ? ` (${unreadCount} unread)` : ''}`}
        data-testid="notification-bell"
        className={`relative p-1.5 rounded transition-colors ${
          open
            ? 'bg-gray-700 text-gray-100'
            : 'text-gray-400 hover:text-gray-200 hover:bg-gray-800'
        }`}
      >
        {/* Bell icon (inline SVG) */}
        <svg
          xmlns="http://www.w3.org/2000/svg"
          className="h-5 w-5"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth={2}
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
          <path d="M13.73 21a2 2 0 0 1-3.46 0" />
        </svg>

        {/* Unread badge */}
        {unreadCount > 0 && (
          <span
            data-testid="unread-badge"
            className="absolute -top-0.5 -right-0.5 min-w-[1rem] h-4 px-0.5 rounded-full bg-blue-500 text-white text-[10px] font-bold flex items-center justify-center leading-none"
          >
            {unreadCount > 99 ? '99+' : unreadCount}
          </span>
        )}
      </button>

      {open && (
        <NotificationDropdown onNavigate={onNavigate} onClose={close} />
      )}
    </div>
  )
}
