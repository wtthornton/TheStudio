/**
 * DashboardCustomizer — Epic 56.1
 *
 * Settings panel for showing/hiding and reordering dashboard widgets.
 * Views are persisted to localStorage under `thestudio_dashboard_views`.
 */

import { useState, useEffect, useCallback } from 'react'
import type { DashboardWidget, DashboardView } from './DashboardCustomizer.types'

const STORAGE_KEY = 'thestudio_dashboard_views'

const DEFAULT_WIDGETS: DashboardWidget[] = [
  { id: 'pipeline', label: 'Pipeline Status', visible: true, order: 0 },
  { id: 'triage', label: 'Triage Queue', visible: true, order: 1 },
  { id: 'activity', label: 'Activity Stream', visible: true, order: 2 },
  { id: 'budget', label: 'Budget Overview', visible: true, order: 3 },
  { id: 'analytics', label: 'Analytics', visible: true, order: 4 },
  { id: 'reputation', label: 'Reputation', visible: true, order: 5 },
]

const DEFAULT_VIEW: DashboardView = {
  name: 'Team Standard',
  widgets: DEFAULT_WIDGETS,
  isDefault: true,
}

function loadViews(): DashboardView[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) {
      const parsed = JSON.parse(raw) as DashboardView[]
      if (Array.isArray(parsed) && parsed.length > 0) return parsed
    }
  } catch {
    // corrupt data — fall back to defaults
  }
  return [DEFAULT_VIEW]
}

function persistViews(views: DashboardView[]): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(views))
}

export interface DashboardCustomizerProps {
  /** Called when the active view changes so the parent can re-render widgets. */
  onViewChange?: (view: DashboardView) => void
}

export function DashboardCustomizer({ onViewChange }: DashboardCustomizerProps) {
  const [views, setViews] = useState<DashboardView[]>(loadViews)
  const [activeViewName, setActiveViewName] = useState<string>(views[0].name)
  const [newViewName, setNewViewName] = useState('')

  const activeView = views.find((v) => v.name === activeViewName) ?? views[0]

  // Persist whenever views change
  useEffect(() => {
    persistViews(views)
  }, [views])

  // Notify parent when active view changes
  useEffect(() => {
    onViewChange?.(activeView)
  }, [activeView, onViewChange])

  const handleToggleWidget = useCallback(
    (widgetId: string) => {
      setViews((prev) =>
        prev.map((v) =>
          v.name === activeViewName
            ? {
                ...v,
                widgets: v.widgets.map((w) =>
                  w.id === widgetId ? { ...w, visible: !w.visible } : w,
                ),
              }
            : v,
        ),
      )
    },
    [activeViewName],
  )

  const handleMoveUp = useCallback(
    (widgetId: string) => {
      setViews((prev) =>
        prev.map((v) => {
          if (v.name !== activeViewName) return v
          const sorted = [...v.widgets].sort((a, b) => a.order - b.order)
          const idx = sorted.findIndex((w) => w.id === widgetId)
          if (idx <= 0) return v
          // Swap orders
          const newWidgets = sorted.map((w, i) => {
            if (i === idx - 1) return { ...w, order: idx }
            if (i === idx) return { ...w, order: idx - 1 }
            return { ...w, order: i }
          })
          return { ...v, widgets: newWidgets }
        }),
      )
    },
    [activeViewName],
  )

  const handleMoveDown = useCallback(
    (widgetId: string) => {
      setViews((prev) =>
        prev.map((v) => {
          if (v.name !== activeViewName) return v
          const sorted = [...v.widgets].sort((a, b) => a.order - b.order)
          const idx = sorted.findIndex((w) => w.id === widgetId)
          if (idx < 0 || idx >= sorted.length - 1) return v
          const newWidgets = sorted.map((w, i) => {
            if (i === idx) return { ...w, order: idx + 1 }
            if (i === idx + 1) return { ...w, order: idx }
            return { ...w, order: i }
          })
          return { ...v, widgets: newWidgets }
        }),
      )
    },
    [activeViewName],
  )

  const handleSaveView = useCallback(() => {
    const trimmed = newViewName.trim()
    if (!trimmed) return

    const currentWidgets = activeView.widgets.map((w) => ({ ...w }))
    const existing = views.find((v) => v.name === trimmed)

    if (existing) {
      setViews((prev) =>
        prev.map((v) => (v.name === trimmed ? { ...v, widgets: currentWidgets } : v)),
      )
    } else {
      const newView: DashboardView = { name: trimmed, widgets: currentWidgets }
      setViews((prev) => [...prev, newView])
    }
    setActiveViewName(trimmed)
    setNewViewName('')
  }, [newViewName, activeView.widgets, views])

  const handleResetToDefault = useCallback(() => {
    const defaultWidgets = DEFAULT_WIDGETS.map((w) => ({ ...w }))
    setViews((prev) =>
      prev.map((v) =>
        v.name === activeViewName ? { ...v, widgets: defaultWidgets } : v,
      ),
    )
  }, [activeViewName])

  const handleSelectView = useCallback((name: string) => {
    setActiveViewName(name)
  }, [])

  const sortedWidgets = [...activeView.widgets].sort((a, b) => a.order - b.order)

  return (
    <section
      className="rounded-lg border border-gray-800 bg-gray-900 p-4"
      data-testid="dashboard-customizer"
      aria-label="Dashboard Customizer"
    >
      <h2 className="mb-3 text-sm font-semibold text-gray-100">Dashboard Views</h2>

      {/* View selector */}
      <div className="mb-4 flex items-center gap-2">
        <label htmlFor="view-selector" className="text-xs text-gray-400">
          Active view:
        </label>
        <select
          id="view-selector"
          value={activeViewName}
          onChange={(e) => handleSelectView(e.target.value)}
          className="rounded border border-gray-700 bg-gray-800 px-2 py-1 text-sm text-gray-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
          data-testid="view-selector"
        >
          {views.map((v) => (
            <option key={v.name} value={v.name}>
              {v.name}
            </option>
          ))}
        </select>
      </div>

      {/* Widget list */}
      <ul className="mb-4 space-y-1" data-testid="widget-list">
        {sortedWidgets.map((widget, idx) => (
          <li
            key={widget.id}
            className="flex items-center justify-between rounded border border-gray-800 bg-gray-950 px-3 py-2"
            data-testid={`widget-item-${widget.id}`}
          >
            <label className="flex items-center gap-2 text-sm text-gray-300">
              <input
                type="checkbox"
                checked={widget.visible}
                onChange={() => handleToggleWidget(widget.id)}
                className="rounded border-gray-600 bg-gray-800 text-blue-500 focus:ring-2 focus:ring-blue-500"
                data-testid={`widget-toggle-${widget.id}`}
              />
              {widget.label}
            </label>
            <div className="flex gap-1">
              <button
                type="button"
                onClick={() => handleMoveUp(widget.id)}
                disabled={idx === 0}
                className="rounded px-1.5 py-0.5 text-xs text-gray-400 hover:text-gray-200 disabled:opacity-30 focus:outline-none focus:ring-2 focus:ring-blue-500"
                aria-label={`Move ${widget.label} up`}
                data-testid={`widget-up-${widget.id}`}
              >
                ↑
              </button>
              <button
                type="button"
                onClick={() => handleMoveDown(widget.id)}
                disabled={idx === sortedWidgets.length - 1}
                className="rounded px-1.5 py-0.5 text-xs text-gray-400 hover:text-gray-200 disabled:opacity-30 focus:outline-none focus:ring-2 focus:ring-blue-500"
                aria-label={`Move ${widget.label} down`}
                data-testid={`widget-down-${widget.id}`}
              >
                ↓
              </button>
            </div>
          </li>
        ))}
      </ul>

      {/* Save view */}
      <div className="mb-3 flex items-center gap-2">
        <input
          type="text"
          value={newViewName}
          onChange={(e) => setNewViewName(e.target.value)}
          placeholder="New view name..."
          className="flex-1 rounded border border-gray-700 bg-gray-800 px-2 py-1 text-sm text-gray-200 placeholder:text-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
          data-testid="new-view-name"
          aria-label="New view name"
        />
        <button
          type="button"
          onClick={handleSaveView}
          disabled={!newViewName.trim()}
          className="rounded bg-blue-600 px-3 py-1 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50 focus:outline-none focus:ring-2 focus:ring-blue-500"
          data-testid="save-view-btn"
        >
          Save View
        </button>
      </div>

      {/* Reset */}
      <button
        type="button"
        onClick={handleResetToDefault}
        className="rounded border border-gray-700 px-3 py-1 text-sm text-gray-400 hover:text-gray-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
        data-testid="reset-view-btn"
      >
        Reset to Team Standard
      </button>
    </section>
  )
}
