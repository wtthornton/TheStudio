/**
 * Epic 45.10 — Vitest tests for HelpPanel.
 * Covers: open/close render, close button, backdrop, Escape key, route-awareness,
 * search results, search empty state, result click switching tab, panel reset.
 */

import { render, screen, fireEvent, act } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

// ---------------------------------------------------------------------------
// Mock ?raw imports — Vite raw imports are not supported in jsdom test env.
// We replace the whole help/index module with deterministic strings.
// ---------------------------------------------------------------------------
vi.mock('../help/index', () => ({
  HELP_CONTENT: {
    pipeline: '# Pipeline Dashboard\n\nThis is the pipeline help article.',
    triage: '# Triage Queue\n\nThis is the triage help article.',
    intent: '# Intent Review\n\nHelp for the intent tab.',
    analytics: '# Analytics\n\nHelp for analytics.',
    trust: '# Trust Tiers\n\nHelp for trust configuration.',
  },
  HELP_TITLES: {
    pipeline: 'Pipeline Dashboard',
    triage: 'Triage Queue',
    intent: 'Intent Review',
    analytics: 'Analytics',
    trust: 'Trust Tiers',
  },
}))

// Mock react-markdown to render content as plain text in a div
vi.mock('react-markdown', () => ({
  default: ({ children }: { children: string }) => (
    <div data-testid="markdown-content">{children}</div>
  ),
}))

// Import after mocks
import { HelpPanel } from '../components/help/HelpPanel'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
function renderPanel(props: Partial<React.ComponentProps<typeof HelpPanel>> = {}) {
  const defaults = {
    open: true,
    onClose: vi.fn(),
  }
  return render(<HelpPanel {...defaults} {...props} />)
}

// ===========================================================================
// Render / visibility
// ===========================================================================
describe('HelpPanel — render and visibility', () => {
  it('renders the panel element', () => {
    renderPanel()
    expect(screen.getByTestId('help-panel')).toBeInTheDocument()
  })

  it('panel has translate-x-0 class when open=true', () => {
    renderPanel({ open: true })
    expect(screen.getByTestId('help-panel')).toHaveClass('translate-x-0')
  })

  it('panel has translate-x-full class when open=false', () => {
    renderPanel({ open: false })
    expect(screen.getByTestId('help-panel')).toHaveClass('translate-x-full')
  })

  it('shows backdrop when open=true', () => {
    renderPanel({ open: true })
    expect(screen.getByTestId('help-panel-backdrop')).toBeInTheDocument()
  })

  it('does not show backdrop when open=false', () => {
    renderPanel({ open: false })
    expect(screen.queryByTestId('help-panel-backdrop')).not.toBeInTheDocument()
  })

  it('has role="dialog"', () => {
    renderPanel()
    expect(screen.getByTestId('help-panel')).toHaveAttribute('role', 'dialog')
  })

  it('has aria-modal="true"', () => {
    renderPanel()
    expect(screen.getByTestId('help-panel')).toHaveAttribute('aria-modal', 'true')
  })
})

// ===========================================================================
// Close behaviour
// ===========================================================================
describe('HelpPanel — close behaviour', () => {
  it('close button calls onClose', () => {
    const onClose = vi.fn()
    renderPanel({ onClose })
    fireEvent.click(screen.getByTestId('help-panel-close'))
    expect(onClose).toHaveBeenCalledOnce()
  })

  it('backdrop click calls onClose', () => {
    const onClose = vi.fn()
    renderPanel({ onClose })
    fireEvent.click(screen.getByTestId('help-panel-backdrop'))
    expect(onClose).toHaveBeenCalledOnce()
  })

  it('Escape key calls onClose when no query is set', () => {
    const onClose = vi.fn()
    renderPanel({ onClose })
    fireEvent.keyDown(document, { key: 'Escape' })
    expect(onClose).toHaveBeenCalledOnce()
  })

  it('Escape key with active query clears query instead of closing', () => {
    const onClose = vi.fn()
    renderPanel({ onClose })
    const input = screen.getByTestId('help-search-input')
    fireEvent.change(input, { target: { value: 'pipeline' } })
    // At this point query is set; Escape should clear it, not close
    fireEvent.keyDown(document, { key: 'Escape' })
    expect(onClose).not.toHaveBeenCalled()
    expect((input as HTMLInputElement).value).toBe('')
  })

  it('Escape does nothing when panel is closed', () => {
    const onClose = vi.fn()
    renderPanel({ open: false, onClose })
    fireEvent.keyDown(document, { key: 'Escape' })
    expect(onClose).not.toHaveBeenCalled()
  })
})

// ===========================================================================
// Route-aware content loading
// ===========================================================================
describe('HelpPanel — route-aware content', () => {
  it('shows tab title from HELP_TITLES when activeTab is provided', () => {
    renderPanel({ activeTab: 'pipeline' })
    expect(screen.getByText('Pipeline Dashboard')).toBeInTheDocument()
  })

  it('renders markdown content when activeTab is recognised', () => {
    renderPanel({ activeTab: 'triage' })
    expect(screen.getByTestId('markdown-content')).toBeInTheDocument()
  })

  it('shows fallback message when activeTab has no matching content', () => {
    renderPanel({ activeTab: 'unknown-tab' })
    expect(
      screen.getByText('No help content available for this page.'),
    ).toBeInTheDocument()
  })

  it('renders children when no activeTab is provided', () => {
    renderPanel({ activeTab: undefined, children: <p>Custom children</p> })
    expect(screen.getByText('Custom children')).toBeInTheDocument()
  })

  it('uses custom title prop over HELP_TITLES', () => {
    renderPanel({ activeTab: 'pipeline', title: 'Custom Title' })
    expect(screen.getByText('Custom Title')).toBeInTheDocument()
  })

  it('defaults to "Help" title when no activeTab and no title prop', () => {
    renderPanel({ activeTab: undefined })
    expect(screen.getByRole('heading', { name: /^help$/i })).toBeInTheDocument()
  })
})

// ===========================================================================
// Search
// ===========================================================================
describe('HelpPanel — search', () => {
  it('renders the search input', () => {
    renderPanel()
    expect(screen.getByTestId('help-search-input')).toBeInTheDocument()
  })

  it('shows search results when query matches article title', () => {
    renderPanel()
    const input = screen.getByTestId('help-search-input')
    fireEvent.change(input, { target: { value: 'Pipeline' } })
    expect(screen.getByTestId('help-search-results')).toBeInTheDocument()
  })

  it('shows empty state when query has no matches', () => {
    renderPanel()
    const input = screen.getByTestId('help-search-input')
    fireEvent.change(input, { target: { value: 'xyzzy_no_match_ever' } })
    expect(screen.getByTestId('help-search-empty')).toBeInTheDocument()
  })

  it('hides search results list when query is cleared', () => {
    renderPanel()
    const input = screen.getByTestId('help-search-input')
    fireEvent.change(input, { target: { value: 'Pipeline' } })
    expect(screen.getByTestId('help-search-results')).toBeInTheDocument()
    fireEvent.change(input, { target: { value: '' } })
    expect(screen.queryByTestId('help-search-results')).not.toBeInTheDocument()
  })

  it('clicking a search result clears query and shows article', () => {
    renderPanel({ activeTab: undefined })
    const input = screen.getByTestId('help-search-input')
    fireEvent.change(input, { target: { value: 'Pipeline' } })
    // Click the first result (pipeline article)
    const result = screen.getByTestId('help-result-pipeline')
    fireEvent.click(result)
    // Query cleared
    expect((input as HTMLInputElement).value).toBe('')
    // Markdown content should now appear
    expect(screen.getByTestId('markdown-content')).toBeInTheDocument()
  })

  it('clicking a search result calls onSwitchTab with article key', () => {
    const onSwitchTab = vi.fn()
    renderPanel({ onSwitchTab })
    const input = screen.getByTestId('help-search-input')
    fireEvent.change(input, { target: { value: 'Pipeline' } })
    fireEvent.click(screen.getByTestId('help-result-pipeline'))
    expect(onSwitchTab).toHaveBeenCalledWith('pipeline')
  })

  it('search resets when panel is closed and re-opened', async () => {
    const { rerender } = renderPanel({ open: true })
    const input = screen.getByTestId('help-search-input')
    fireEvent.change(input, { target: { value: 'Pipeline' } })
    expect(screen.getByTestId('help-search-results')).toBeInTheDocument()
    // Close panel
    rerender(<HelpPanel open={false} onClose={vi.fn()} />)
    // Re-open
    rerender(<HelpPanel open={true} onClose={vi.fn()} />)
    await act(async () => {})
    expect(screen.queryByTestId('help-search-results')).not.toBeInTheDocument()
  })
})
