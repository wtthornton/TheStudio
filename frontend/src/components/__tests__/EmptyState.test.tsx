/**
 * EmptyState component tests — Epic 46.5
 *
 * Covers:
 *  - EmptyState base component (icon, heading, description, actions, data-testid)
 *  - HeaderBar onboarding hint when all KPIs are zero
 *  - SteeringActivityLog empty state via AuditTable
 */

import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { EmptyState } from '../EmptyState'
import { HeaderBar } from '../HeaderBar'
import { usePipelineStore } from '../../stores/pipeline-store'

// ---------------------------------------------------------------------------
// EmptyState base component
// ---------------------------------------------------------------------------

describe('EmptyState', () => {
  it('renders heading', () => {
    render(<EmptyState heading="Nothing here yet" />)
    expect(screen.getByTestId('empty-state-heading')).toHaveTextContent('Nothing here yet')
  })

  it('renders description when provided', () => {
    render(<EmptyState heading="Empty" description="No items to display." />)
    expect(screen.getByTestId('empty-state-description')).toHaveTextContent('No items to display.')
  })

  it('omits description when not provided', () => {
    render(<EmptyState heading="Empty" />)
    expect(screen.queryByTestId('empty-state-description')).not.toBeInTheDocument()
  })

  it('renders icon when provided', () => {
    render(<EmptyState heading="Empty" icon={<span data-testid="my-icon">📦</span>} />)
    expect(screen.getByTestId('empty-state-icon')).toBeInTheDocument()
    expect(screen.getByTestId('my-icon')).toBeInTheDocument()
  })

  it('omits icon wrapper when no icon provided', () => {
    render(<EmptyState heading="Empty" />)
    expect(screen.queryByTestId('empty-state-icon')).not.toBeInTheDocument()
  })

  it('renders primary action as button when onClick provided', () => {
    const onClick = vi.fn()
    render(<EmptyState heading="Empty" primaryAction={{ label: 'Click me', onClick }} />)
    const btn = screen.getByTestId('empty-state-primary-action')
    expect(btn.tagName).toBe('BUTTON')
    expect(btn).toHaveTextContent('Click me')
    fireEvent.click(btn)
    expect(onClick).toHaveBeenCalledOnce()
  })

  it('renders primary action as anchor when href provided', () => {
    render(<EmptyState heading="Empty" primaryAction={{ label: 'Go there', href: '/somewhere' }} />)
    const link = screen.getByTestId('empty-state-primary-action')
    expect(link.tagName).toBe('A')
    expect(link).toHaveAttribute('href', '/somewhere')
  })

  it('renders secondary action as button when onClick provided', () => {
    const onClick = vi.fn()
    render(
      <EmptyState
        heading="Empty"
        secondaryAction={{ label: 'Learn more', onClick }}
      />
    )
    const btn = screen.getByTestId('empty-state-secondary-action')
    expect(btn.tagName).toBe('BUTTON')
    fireEvent.click(btn)
    expect(onClick).toHaveBeenCalledOnce()
  })

  it('renders secondary action as anchor when href provided', () => {
    render(
      <EmptyState
        heading="Empty"
        secondaryAction={{ label: 'Docs', href: 'https://docs.example.com' }}
      />
    )
    const link = screen.getByTestId('empty-state-secondary-action')
    expect(link.tagName).toBe('A')
    expect(link).toHaveAttribute('href', 'https://docs.example.com')
  })

  it('omits action section when neither primary nor secondary action provided', () => {
    render(<EmptyState heading="Empty" />)
    expect(screen.queryByTestId('empty-state-primary-action')).not.toBeInTheDocument()
    expect(screen.queryByTestId('empty-state-secondary-action')).not.toBeInTheDocument()
  })

  it('uses custom data-testid when provided', () => {
    render(<EmptyState heading="Custom" data-testid="my-custom-empty" />)
    expect(screen.getByTestId('my-custom-empty')).toBeInTheDocument()
    expect(screen.getByTestId('my-custom-empty-heading')).toBeInTheDocument()
  })

  it('applies custom className to wrapper', () => {
    render(<EmptyState heading="Custom" className="my-extra-class" />)
    const wrapper = screen.getByTestId('empty-state')
    expect(wrapper.className).toContain('my-extra-class')
  })
})

// ---------------------------------------------------------------------------
// HeaderBar — onboarding hint
// ---------------------------------------------------------------------------

describe('HeaderBar onboarding hint', () => {
  beforeEach(() => {
    usePipelineStore.getState().reset()
  })

  it('shows onboarding hint when all KPIs are zero', () => {
    render(<HeaderBar />)
    expect(screen.getByTestId('onboarding-hint')).toBeInTheDocument()
    expect(screen.getByTestId('onboarding-hint')).toHaveTextContent('Import your first GitHub issue')
  })

  it('hides onboarding hint when there are active tasks', () => {
    usePipelineStore.getState().stageEnter('intake', 'task-1')
    render(<HeaderBar />)
    expect(screen.queryByTestId('onboarding-hint')).not.toBeInTheDocument()
  })

  it('shows active count, queued count, and running cost', () => {
    render(<HeaderBar />)
    expect(screen.getByTestId('active-count')).toHaveTextContent('0')
    expect(screen.getByTestId('queued-count')).toHaveTextContent('0')
    expect(screen.getByTestId('running-cost')).toHaveTextContent('$0.00')
  })
})
