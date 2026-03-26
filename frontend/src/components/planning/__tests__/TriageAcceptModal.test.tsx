/**
 * Tests for TriageAcceptModal — Story 54.3 prompt-first triage accept flow.
 *
 * Covers:
 *  - Modal renders intent preview on open
 *  - Step progress indicator shows step 2 initially
 *  - "Continue to Mode Selection" advances to step 3
 *  - ExecutionModeSelector visible after advancing
 *  - Confirm button disabled until step 3 is reached
 *  - Confirm calls onConfirm with taskId and selected mode
 *  - Cancel calls onClose
 *  - "Edit First" calls onEdit with taskId
 *  - Escape key calls onClose
 *  - Backdrop click calls onClose
 *  - Ownership notice rendered
 *  - Enrichment data rendered when present
 *  - No enrichment — graceful render without estimate fields
 */

import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { TriageAcceptModal } from '../TriageAcceptModal'
import type { TriageTask } from '../../../lib/api'

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const baseTask: TriageTask = {
  id: 'task-001',
  repo: 'owner/repo',
  issue_id: 42,
  status: 'triaged',
  issue_title: 'Add retry logic to webhook handler',
  issue_body: 'When the webhook fails, we need automatic retries.',
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
  rejection_reason: null,
  triage_enrichment: {
    complexity_hint: 'medium',
    file_count_estimate: 3,
    cost_estimate_range: { min: 0.05, max: 0.15 },
  },
}

const taskWithoutEnrichment: TriageTask = {
  id: 'task-002',
  repo: 'owner/repo',
  issue_id: 99,
  status: 'triaged',
  issue_title: 'Fix the login bug',
  issue_body: null,
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
  rejection_reason: null,
  triage_enrichment: null,
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function renderModal(overrides: Partial<Parameters<typeof TriageAcceptModal>[0]> = {}) {
  const onConfirm = vi.fn()
  const onEdit = vi.fn()
  const onClose = vi.fn()
  render(
    <TriageAcceptModal
      task={baseTask}
      onConfirm={onConfirm}
      onEdit={onEdit}
      onClose={onClose}
      {...overrides}
    />,
  )
  return { onConfirm, onEdit, onClose }
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('TriageAcceptModal', () => {
  it('renders the modal with task title', () => {
    renderModal()
    expect(screen.getByRole('dialog')).toBeDefined()
    expect(screen.getByText('Add retry logic to webhook handler')).toBeDefined()
  })

  it('shows issue number', () => {
    renderModal()
    expect(screen.getByText('Issue #42')).toBeDefined()
  })

  it('shows intent preview section', () => {
    renderModal()
    expect(screen.getByTestId('triage-intent-preview')).toBeDefined()
    expect(screen.getByTestId('intent-planned-action')).toBeDefined()
  })

  it('renders prompt-first step progress indicator', () => {
    renderModal()
    expect(screen.getByTestId('prompt-first-steps')).toBeDefined()
  })

  it('shows enrichment data when present', () => {
    renderModal()
    expect(screen.getByTestId('intent-complexity')).toBeDefined()
    expect(screen.getByText('medium')).toBeDefined()
    expect(screen.getByTestId('intent-files')).toBeDefined()
    expect(screen.getByTestId('intent-cost')).toBeDefined()
  })

  it('shows "Continue to Mode Selection" button on step 2', () => {
    renderModal()
    expect(screen.getByTestId('intent-preview-continue')).toBeDefined()
  })

  it('hides mode selector until user advances to step 3', () => {
    renderModal()
    expect(screen.queryByTestId('triage-mode-selector')).toBeNull()
  })

  it('shows mode selector after clicking Continue', () => {
    renderModal()
    fireEvent.click(screen.getByTestId('intent-preview-continue'))
    expect(screen.getByTestId('triage-mode-selector')).toBeDefined()
    expect(screen.getByTestId('execution-mode-selector')).toBeDefined()
  })

  it('Confirm button is disabled on step 2', () => {
    renderModal()
    const confirmBtn = screen.getByTestId('triage-accept-confirm-btn') as HTMLButtonElement
    expect(confirmBtn.disabled).toBe(true)
  })

  it('Confirm button enabled after advancing to step 3', () => {
    renderModal()
    fireEvent.click(screen.getByTestId('intent-preview-continue'))
    const confirmBtn = screen.getByTestId('triage-accept-confirm-btn') as HTMLButtonElement
    expect(confirmBtn.disabled).toBe(false)
  })

  it('calls onConfirm with taskId and default mode (suggest) on confirm', () => {
    const { onConfirm } = renderModal()
    fireEvent.click(screen.getByTestId('intent-preview-continue'))
    fireEvent.click(screen.getByTestId('triage-accept-confirm-btn'))
    expect(onConfirm).toHaveBeenCalledWith('task-001', 'suggest')
  })

  it('calls onConfirm with execute mode when execute is selected', () => {
    const { onConfirm } = renderModal()
    fireEvent.click(screen.getByTestId('intent-preview-continue'))
    fireEvent.click(screen.getByTestId('mode-option-execute'))
    fireEvent.click(screen.getByTestId('triage-accept-confirm-btn'))
    expect(onConfirm).toHaveBeenCalledWith('task-001', 'execute')
  })

  it('calls onClose when Cancel is clicked', () => {
    const { onClose } = renderModal()
    fireEvent.click(screen.getByTestId('triage-accept-cancel-btn'))
    expect(onClose).toHaveBeenCalledTimes(1)
  })

  it('calls onEdit with taskId when "Edit First" is clicked', () => {
    const { onEdit } = renderModal()
    fireEvent.click(screen.getByTestId('triage-accept-edit-btn'))
    expect(onEdit).toHaveBeenCalledWith('task-001')
  })

  it('calls onClose when Escape key is pressed', () => {
    const { onClose } = renderModal()
    fireEvent.keyDown(document, { key: 'Escape' })
    expect(onClose).toHaveBeenCalledTimes(1)
  })

  it('calls onClose when backdrop is clicked', () => {
    const { onClose } = renderModal()
    fireEvent.click(screen.getByTestId('triage-accept-backdrop'))
    expect(onClose).toHaveBeenCalledTimes(1)
  })

  it('shows AI label in intent preview', () => {
    renderModal()
    expect(screen.getByText('AI-generated intent summary')).toBeDefined()
  })

  it('shows ownership notice', () => {
    renderModal()
    expect(screen.getByTestId('ownership-notice')).toBeDefined()
  })

  it('renders gracefully without enrichment data', () => {
    render(
      <TriageAcceptModal
        task={taskWithoutEnrichment}
        onConfirm={vi.fn()}
        onEdit={vi.fn()}
        onClose={vi.fn()}
      />,
    )
    expect(screen.getByText('Fix the login bug')).toBeDefined()
    expect(screen.queryByTestId('intent-complexity')).toBeNull()
  })

  it('close button calls onClose', () => {
    const { onClose } = renderModal()
    fireEvent.click(screen.getByTestId('triage-accept-close'))
    expect(onClose).toHaveBeenCalledTimes(1)
  })
})
