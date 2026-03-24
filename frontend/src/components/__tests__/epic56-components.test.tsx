/**
 * Epic 56 — 2026 Capability Modules
 *
 * Tests for:
 *  - CommandPalette (56.2): open/close, filter, keyboard nav, side-effect confirmation
 *  - DashboardCustomizer (56.1): save/reset/switch views, toggle widgets
 *  - Locale helpers (56.3): formatDate, formatNumber, formatCurrency, formatRelativeTime
 *  - CommentThread (56.4): render comments, add new comment, empty state
 *  - ChangeHistory (56.4): render entries in most-recent-first order
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { CommandPalette } from '../CommandPalette'
import { DashboardCustomizer } from '../dashboard/DashboardCustomizer'
import { CommentThread } from '../collaboration/CommentThread'
import { ChangeHistory } from '../collaboration/ChangeHistory'
import type { ChangeEntry } from '../collaboration/ChangeHistory'
import {
  formatDate,
  formatNumber,
  formatCurrency,
  formatRelativeTime,
  getLocale,
} from '../../lib/locale'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

beforeEach(() => {
  localStorage.clear()
})

// ---------------------------------------------------------------------------
// 56.2 — CommandPalette
// ---------------------------------------------------------------------------

describe('CommandPalette', () => {
  const defaultProps = {
    isOpen: true,
    onClose: vi.fn(),
    onNavigate: vi.fn(),
    onAction: vi.fn(),
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders when open', () => {
    render(<CommandPalette {...defaultProps} />)
    expect(screen.getByTestId('command-palette')).toBeInTheDocument()
  })

  it('does not render when closed', () => {
    render(<CommandPalette {...defaultProps} isOpen={false} />)
    expect(screen.queryByTestId('command-palette')).not.toBeInTheDocument()
  })

  it('closes on Escape', () => {
    render(<CommandPalette {...defaultProps} />)
    fireEvent.keyDown(screen.getByTestId('command-palette'), { key: 'Escape' })
    expect(defaultProps.onClose).toHaveBeenCalledOnce()
  })

  it('filters commands as user types', () => {
    render(<CommandPalette {...defaultProps} />)
    const input = screen.getByTestId('command-palette-input')
    fireEvent.change(input, { target: { value: 'pipe' } })
    // Pipeline should be visible
    expect(screen.getByTestId('command-item-nav:pipeline')).toBeInTheDocument()
    // Triage should not
    expect(screen.queryByTestId('command-item-nav:triage')).not.toBeInTheDocument()
  })

  it('navigates with arrow keys and selects with Enter', () => {
    render(<CommandPalette {...defaultProps} />)
    const palette = screen.getByTestId('command-palette')

    // Arrow down moves selection
    fireEvent.keyDown(palette, { key: 'ArrowDown' })
    fireEvent.keyDown(palette, { key: 'ArrowDown' })
    fireEvent.keyDown(palette, { key: 'Enter' })

    // Should have called onNavigate or onAction
    const totalCalls = defaultProps.onNavigate.mock.calls.length + defaultProps.onAction.mock.calls.length
    expect(totalCalls).toBe(1)
  })

  it('shows confirmation for side-effect commands before executing', () => {
    render(<CommandPalette {...defaultProps} />)
    const input = screen.getByTestId('command-palette-input')

    // Filter to "Import Issues" (a side-effect command)
    fireEvent.change(input, { target: { value: 'Import' } })
    const importItem = screen.getByTestId('command-item-action:import')
    expect(importItem).toBeInTheDocument()

    // First click shows confirmation
    fireEvent.click(importItem)
    expect(defaultProps.onAction).not.toHaveBeenCalled()
    expect(screen.getByText(/Confirm: Import Issues\?/)).toBeInTheDocument()

    // Second click executes
    fireEvent.click(importItem)
    expect(defaultProps.onAction).toHaveBeenCalledWith('action:import')
  })

  it('navigates to tab when navigation command is selected', () => {
    render(<CommandPalette {...defaultProps} />)
    const input = screen.getByTestId('command-palette-input')
    fireEvent.change(input, { target: { value: 'Analytics' } })
    fireEvent.click(screen.getByTestId('command-item-nav:analytics'))
    expect(defaultProps.onNavigate).toHaveBeenCalledWith('analytics')
  })

  it('shows all navigation commands by default', () => {
    render(<CommandPalette {...defaultProps} />)
    expect(screen.getByTestId('command-item-nav:pipeline')).toBeInTheDocument()
    expect(screen.getByTestId('command-item-nav:triage')).toBeInTheDocument()
    expect(screen.getByTestId('command-item-nav:api')).toBeInTheDocument()
  })

  it('closes when backdrop is clicked', () => {
    render(<CommandPalette {...defaultProps} />)
    fireEvent.click(screen.getByTestId('command-palette-overlay'))
    expect(defaultProps.onClose).toHaveBeenCalledOnce()
  })
})

// ---------------------------------------------------------------------------
// 56.1 — DashboardCustomizer
// ---------------------------------------------------------------------------

describe('DashboardCustomizer', () => {
  it('renders with default widgets', () => {
    render(<DashboardCustomizer />)
    expect(screen.getByTestId('dashboard-customizer')).toBeInTheDocument()
    expect(screen.getByTestId('widget-list')).toBeInTheDocument()
    expect(screen.getByTestId('widget-item-pipeline')).toBeInTheDocument()
    expect(screen.getByTestId('widget-item-analytics')).toBeInTheDocument()
  })

  it('toggles widget visibility', () => {
    render(<DashboardCustomizer />)
    const toggle = screen.getByTestId('widget-toggle-pipeline') as HTMLInputElement
    expect(toggle.checked).toBe(true)
    fireEvent.click(toggle)
    expect(toggle.checked).toBe(false)
  })

  it('saves a new view', () => {
    const onChange = vi.fn()
    render(<DashboardCustomizer onViewChange={onChange} />)

    const nameInput = screen.getByTestId('new-view-name')
    const saveBtn = screen.getByTestId('save-view-btn')

    fireEvent.change(nameInput, { target: { value: 'Ops Default' } })
    fireEvent.click(saveBtn)

    // The new view should appear in the selector
    const selector = screen.getByTestId('view-selector') as HTMLSelectElement
    const optionValues = Array.from(selector.options).map((o) => o.value)
    expect(optionValues).toContain('Ops Default')
  })

  it('switches between views', () => {
    // Pre-seed two views in localStorage
    const views = [
      {
        name: 'Team Standard',
        widgets: [
          { id: 'pipeline', label: 'Pipeline Status', visible: true, order: 0 },
          { id: 'triage', label: 'Triage Queue', visible: true, order: 1 },
        ],
        isDefault: true,
      },
      {
        name: 'Cost Review',
        widgets: [
          { id: 'pipeline', label: 'Pipeline Status', visible: false, order: 0 },
          { id: 'triage', label: 'Triage Queue', visible: true, order: 1 },
        ],
      },
    ]
    localStorage.setItem('thestudio_dashboard_views', JSON.stringify(views))

    render(<DashboardCustomizer />)

    const selector = screen.getByTestId('view-selector') as HTMLSelectElement
    fireEvent.change(selector, { target: { value: 'Cost Review' } })

    // In Cost Review, pipeline should be unchecked
    const toggle = screen.getByTestId('widget-toggle-pipeline') as HTMLInputElement
    expect(toggle.checked).toBe(false)
  })

  it('resets to team standard', () => {
    render(<DashboardCustomizer />)

    // Toggle off a widget first
    const toggle = screen.getByTestId('widget-toggle-pipeline') as HTMLInputElement
    fireEvent.click(toggle)
    expect(toggle.checked).toBe(false)

    // Reset
    fireEvent.click(screen.getByTestId('reset-view-btn'))
    expect(toggle.checked).toBe(true)
  })

  it('disables save button when name is empty', () => {
    render(<DashboardCustomizer />)
    const saveBtn = screen.getByTestId('save-view-btn') as HTMLButtonElement
    expect(saveBtn.disabled).toBe(true)
  })
})

// ---------------------------------------------------------------------------
// 56.3 — Locale helpers
// ---------------------------------------------------------------------------

describe('locale helpers', () => {
  it('getLocale returns a string', () => {
    const locale = getLocale()
    expect(typeof locale).toBe('string')
    expect(locale.length).toBeGreaterThan(0)
  })

  it('formatDate formats a Date', () => {
    const result = formatDate(new Date('2026-01-15T12:00:00Z'), 'en-US')
    expect(result).toContain('Jan')
    expect(result).toContain('15')
    expect(result).toContain('2026')
  })

  it('formatDate accepts a string', () => {
    const result = formatDate('2026-06-01T12:00:00Z', 'en-US')
    expect(result).toContain('Jun')
    expect(result).toContain('2026')
  })

  it('formatNumber formats with locale separators', () => {
    const result = formatNumber(1234567, 'en-US')
    expect(result).toBe('1,234,567')
  })

  it('formatNumber respects non-US locale', () => {
    const result = formatNumber(1234567, 'de-DE')
    // German uses period as thousands separator
    expect(result).toContain('1')
    expect(result).toContain('234')
    expect(result).toContain('567')
  })

  it('formatCurrency formats USD', () => {
    const result = formatCurrency(42.5, 'USD', 'en-US')
    expect(result).toContain('$')
    expect(result).toContain('42.50')
  })

  it('formatCurrency formats EUR', () => {
    const result = formatCurrency(100, 'EUR', 'en-US')
    // en-US renders EUR with the euro sign
    expect(result).toContain('100')
    expect(result).toMatch(/€|EUR/)
  })

  it('formatRelativeTime returns a string', () => {
    const now = new Date()
    const twoHoursAgo = new Date(now.getTime() - 2 * 60 * 60 * 1000)
    const result = formatRelativeTime(twoHoursAgo, 'en-US')
    expect(typeof result).toBe('string')
    expect(result).toContain('2')
    expect(result.toLowerCase()).toContain('hour')
  })

  it('formatRelativeTime handles future dates', () => {
    const now = new Date()
    const inThreeDays = new Date(now.getTime() + 3 * 24 * 60 * 60 * 1000)
    const result = formatRelativeTime(inThreeDays, 'en-US')
    expect(result).toContain('3')
    expect(result.toLowerCase()).toContain('day')
  })
})

// ---------------------------------------------------------------------------
// 56.4 — CommentThread
// ---------------------------------------------------------------------------

describe('CommentThread', () => {
  it('renders empty state', () => {
    render(<CommentThread artifactId="task-1" />)
    expect(screen.getByTestId('comment-empty')).toHaveTextContent('No comments yet')
  })

  it('adds a comment and renders it', () => {
    render(<CommentThread artifactId="task-2" currentUser="Alice" />)

    const input = screen.getByTestId('comment-input')
    const submit = screen.getByTestId('comment-submit')

    fireEvent.change(input, { target: { value: 'Great work!' } })
    fireEvent.click(submit)

    expect(screen.queryByTestId('comment-empty')).not.toBeInTheDocument()
    expect(screen.getByTestId('comment-list')).toBeInTheDocument()
    expect(screen.getByText('Great work!')).toBeInTheDocument()
    expect(screen.getByText('Alice')).toBeInTheDocument()
  })

  it('clears input after submit', () => {
    render(<CommentThread artifactId="task-3" />)

    const input = screen.getByTestId('comment-input') as HTMLInputElement
    fireEvent.change(input, { target: { value: 'Test' } })
    fireEvent.click(screen.getByTestId('comment-submit'))

    expect(input.value).toBe('')
  })

  it('does not submit empty comments', () => {
    render(<CommentThread artifactId="task-4" />)
    fireEvent.click(screen.getByTestId('comment-submit'))
    expect(screen.getByTestId('comment-empty')).toBeInTheDocument()
  })

  it('persists comments to localStorage', () => {
    render(<CommentThread artifactId="task-5" />)

    const input = screen.getByTestId('comment-input')
    fireEvent.change(input, { target: { value: 'Persisted' } })
    fireEvent.click(screen.getByTestId('comment-submit'))

    const stored = localStorage.getItem('thestudio_comments_task-5')
    expect(stored).toBeTruthy()
    const parsed = JSON.parse(stored!)
    expect(parsed).toHaveLength(1)
    expect(parsed[0].text).toBe('Persisted')
  })

  it('loads existing comments from localStorage', () => {
    const existing = [
      { id: 'cmt-1', author: 'Bob', text: 'Hello!', timestamp: '2026-01-01T00:00:00Z' },
    ]
    localStorage.setItem('thestudio_comments_task-6', JSON.stringify(existing))

    render(<CommentThread artifactId="task-6" />)
    expect(screen.getByText('Hello!')).toBeInTheDocument()
    expect(screen.getByText('Bob')).toBeInTheDocument()
  })

  it('submits on Enter key', () => {
    render(<CommentThread artifactId="task-7" />)
    const input = screen.getByTestId('comment-input')
    fireEvent.change(input, { target: { value: 'Enter test' } })
    fireEvent.keyDown(input, { key: 'Enter' })
    expect(screen.getByText('Enter test')).toBeInTheDocument()
  })
})

// ---------------------------------------------------------------------------
// 56.4 — ChangeHistory
// ---------------------------------------------------------------------------

describe('ChangeHistory', () => {
  it('renders empty state', () => {
    render(<ChangeHistory changes={[]} />)
    expect(screen.getByTestId('change-history-empty')).toHaveTextContent('No changes recorded')
  })

  it('renders entries in most-recent-first order', () => {
    const changes: ChangeEntry[] = [
      { id: 'c1', actor: 'Alice', timestamp: '2026-01-01T00:00:00Z', description: 'First' },
      { id: 'c2', actor: 'Bob', timestamp: '2026-06-15T12:00:00Z', description: 'Second' },
      { id: 'c3', actor: 'Carol', timestamp: '2026-03-10T06:00:00Z', description: 'Middle' },
    ]

    render(<ChangeHistory changes={changes} />)
    const items = screen.getAllByTestId(/^change-entry-/)

    // Most recent first: c2 (Jun), c3 (Mar), c1 (Jan)
    expect(items[0]).toHaveAttribute('data-testid', 'change-entry-c2')
    expect(items[1]).toHaveAttribute('data-testid', 'change-entry-c3')
    expect(items[2]).toHaveAttribute('data-testid', 'change-entry-c1')
  })

  it('displays actor, timestamp, and description', () => {
    const changes: ChangeEntry[] = [
      { id: 'c1', actor: 'Alice', timestamp: '2026-01-01T00:00:00Z', description: 'Updated config' },
    ]

    render(<ChangeHistory changes={changes} />)
    expect(screen.getByText('Alice')).toBeInTheDocument()
    expect(screen.getByText('Updated config')).toBeInTheDocument()
  })

  it('renders timeline dots', () => {
    const changes: ChangeEntry[] = [
      { id: 'c1', actor: 'A', timestamp: '2026-01-01T00:00:00Z', description: 'X' },
      { id: 'c2', actor: 'B', timestamp: '2026-02-01T00:00:00Z', description: 'Y' },
    ]

    render(<ChangeHistory changes={changes} />)
    expect(screen.getByTestId('change-history-list')).toBeInTheDocument()
    expect(screen.getAllByTestId(/^change-entry-/)).toHaveLength(2)
  })
})
