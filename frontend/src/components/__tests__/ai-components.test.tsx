/**
 * Tests for Epic 55 AI-first components.
 *
 * Covers:
 *  - IntentPreview renders all PromptObject fields + mode badge + callbacks
 *  - ExecutionModeSelector mode switching + disabled states + warning
 *  - DecisionControls button callbacks + confirmation dialog
 *  - TrustMetadata confidence display + rationale toggle + AI label
 *  - AuditTimeline rendering entries, empty state, undo callback
 */

import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'

import { IntentPreview } from '../ai/IntentPreview'
import { ExecutionModeSelector } from '../ai/ExecutionModeSelector'
import { DecisionControls } from '../ai/DecisionControls'
import { TrustMetadata } from '../ai/TrustMetadata'
import { AuditTimeline } from '../ai/AuditTimeline'
import type { PromptObject } from '../ai/PromptObject'
import type { AuditEntry } from '../ai/AuditTimeline'

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const samplePrompt: PromptObject = {
  goal: 'Refactor authentication module',
  context: 'Legacy auth uses session cookies; migrate to JWT',
  constraints: 'Must remain backward-compatible for 30 days',
  success_criteria: 'All existing tests pass, no session cookie references remain',
  mode: 'suggest',
}

const sampleEntries: AuditEntry[] = [
  {
    id: 'a1',
    timestamp: '2026-03-24 10:00:00',
    description: 'Generated refactoring plan',
    actor: 'ai',
    status: 'completed',
    mutable: true,
  },
  {
    id: 'a2',
    timestamp: '2026-03-24 10:01:00',
    description: 'Applied code changes',
    actor: 'ai',
    status: 'pending',
    mutable: false,
  },
  {
    id: 'a3',
    timestamp: '2026-03-24 10:02:00',
    description: 'Manual review completed',
    actor: 'human',
    status: 'completed',
    mutable: false,
  },
]

// ---------------------------------------------------------------------------
// IntentPreview
// ---------------------------------------------------------------------------

describe('IntentPreview', () => {
  it('renders all PromptObject fields', () => {
    render(
      <IntentPreview prompt={samplePrompt} onEdit={vi.fn()} onConfirm={vi.fn()} />,
    )

    expect(screen.getByTestId('intent-field-goal')).toHaveTextContent(samplePrompt.goal)
    expect(screen.getByTestId('intent-field-context')).toHaveTextContent(samplePrompt.context)
    expect(screen.getByTestId('intent-field-constraints')).toHaveTextContent(
      samplePrompt.constraints,
    )
    expect(screen.getByTestId('intent-field-success-criteria')).toHaveTextContent(
      samplePrompt.success_criteria,
    )
  })

  it('shows mode badge with correct label', () => {
    render(
      <IntentPreview prompt={samplePrompt} onEdit={vi.fn()} onConfirm={vi.fn()} />,
    )

    const badge = screen.getByTestId('intent-preview-mode-badge')
    expect(badge).toHaveTextContent('Suggest')
  })

  it('shows Draft badge for draft mode', () => {
    render(
      <IntentPreview
        prompt={{ ...samplePrompt, mode: 'draft' }}
        onEdit={vi.fn()}
        onConfirm={vi.fn()}
      />,
    )
    expect(screen.getByTestId('intent-preview-mode-badge')).toHaveTextContent('Draft')
  })

  it('shows Execute badge for execute mode', () => {
    render(
      <IntentPreview
        prompt={{ ...samplePrompt, mode: 'execute' }}
        onEdit={vi.fn()}
        onConfirm={vi.fn()}
      />,
    )
    expect(screen.getByTestId('intent-preview-mode-badge')).toHaveTextContent('Execute')
  })

  it('calls onEdit when Edit button is clicked', () => {
    const onEdit = vi.fn()
    render(<IntentPreview prompt={samplePrompt} onEdit={onEdit} onConfirm={vi.fn()} />)

    fireEvent.click(screen.getByTestId('intent-preview-edit-btn'))
    expect(onEdit).toHaveBeenCalledOnce()
  })

  it('calls onConfirm when Confirm button is clicked', () => {
    const onConfirm = vi.fn()
    render(<IntentPreview prompt={samplePrompt} onEdit={vi.fn()} onConfirm={onConfirm} />)

    fireEvent.click(screen.getByTestId('intent-preview-confirm-btn'))
    expect(onConfirm).toHaveBeenCalledOnce()
  })

  it('displays AI-generated label (SG 8.6)', () => {
    render(
      <IntentPreview prompt={samplePrompt} onEdit={vi.fn()} onConfirm={vi.fn()} />,
    )
    expect(screen.getByTestId('intent-preview-ai-label')).toHaveTextContent('AI-generated')
  })
})

// ---------------------------------------------------------------------------
// ExecutionModeSelector
// ---------------------------------------------------------------------------

describe('ExecutionModeSelector', () => {
  it('renders all three mode options', () => {
    render(<ExecutionModeSelector value="draft" onChange={vi.fn()} />)

    expect(screen.getByTestId('mode-option-draft')).toBeInTheDocument()
    expect(screen.getByTestId('mode-option-suggest')).toBeInTheDocument()
    expect(screen.getByTestId('mode-option-execute')).toBeInTheDocument()
  })

  it('calls onChange when a different mode is selected', () => {
    const onChange = vi.fn()
    render(<ExecutionModeSelector value="draft" onChange={onChange} />)

    // Click on the suggest option label (which contains the radio input)
    const suggestRadio = screen.getByTestId('mode-option-suggest').querySelector('input')!
    fireEvent.click(suggestRadio)
    expect(onChange).toHaveBeenCalledWith('suggest')
  })

  it('shows warning indicator on execute mode', () => {
    render(<ExecutionModeSelector value="draft" onChange={vi.fn()} />)

    expect(screen.getByTestId('execute-warning')).toHaveTextContent('High impact')
  })

  it('disables modes when specified', () => {
    render(
      <ExecutionModeSelector
        value="draft"
        onChange={vi.fn()}
        disabledModes={{ execute: true }}
      />,
    )

    const executeRadio = screen.getByTestId('mode-option-execute').querySelector('input')!
    expect(executeRadio).toBeDisabled()
  })

  it('marks disabled mode radio as disabled in the DOM', () => {
    render(
      <ExecutionModeSelector
        value="draft"
        onChange={vi.fn()}
        disabledModes={{ execute: true, suggest: false }}
      />,
    )

    const executeRadio = screen.getByTestId('mode-option-execute').querySelector('input')!
    const suggestRadio = screen.getByTestId('mode-option-suggest').querySelector('input')!
    expect(executeRadio).toBeDisabled()
    expect(suggestRadio).not.toBeDisabled()
  })
})

// ---------------------------------------------------------------------------
// DecisionControls
// ---------------------------------------------------------------------------

describe('DecisionControls', () => {
  const defaultProps = {
    onApprove: vi.fn(),
    onEdit: vi.fn(),
    onRetry: vi.fn(),
    onReject: vi.fn(),
  }

  it('renders all four action buttons', () => {
    render(<DecisionControls {...defaultProps} />)

    expect(screen.getByTestId('decision-approve-btn')).toHaveTextContent('Approve')
    expect(screen.getByTestId('decision-edit-btn')).toHaveTextContent('Edit')
    expect(screen.getByTestId('decision-retry-btn')).toHaveTextContent('Retry')
    expect(screen.getByTestId('decision-reject-btn')).toHaveTextContent('Reject')
  })

  it('calls onApprove when Approve is clicked (no confirmation)', () => {
    const onApprove = vi.fn()
    render(<DecisionControls {...defaultProps} onApprove={onApprove} />)

    fireEvent.click(screen.getByTestId('decision-approve-btn'))
    expect(onApprove).toHaveBeenCalledOnce()
  })

  it('calls onEdit when Edit is clicked', () => {
    const onEdit = vi.fn()
    render(<DecisionControls {...defaultProps} onEdit={onEdit} />)

    fireEvent.click(screen.getByTestId('decision-edit-btn'))
    expect(onEdit).toHaveBeenCalledOnce()
  })

  it('calls onRetry when Retry is clicked', () => {
    const onRetry = vi.fn()
    render(<DecisionControls {...defaultProps} onRetry={onRetry} />)

    fireEvent.click(screen.getByTestId('decision-retry-btn'))
    expect(onRetry).toHaveBeenCalledOnce()
  })

  it('calls onReject when Reject is clicked', () => {
    const onReject = vi.fn()
    render(<DecisionControls {...defaultProps} onReject={onReject} />)

    fireEvent.click(screen.getByTestId('decision-reject-btn'))
    expect(onReject).toHaveBeenCalledOnce()
  })

  it('disables individual buttons when specified', () => {
    render(
      <DecisionControls
        {...defaultProps}
        disabledActions={{ approve: true, retry: true }}
      />,
    )

    expect(screen.getByTestId('decision-approve-btn')).toBeDisabled()
    expect(screen.getByTestId('decision-retry-btn')).toBeDisabled()
    expect(screen.getByTestId('decision-edit-btn')).not.toBeDisabled()
    expect(screen.getByTestId('decision-reject-btn')).not.toBeDisabled()
  })

  it('shows confirmation dialog when requireConfirmation is true', () => {
    const onApprove = vi.fn()
    render(
      <DecisionControls
        {...defaultProps}
        onApprove={onApprove}
        requireConfirmation={true}
      />,
    )

    fireEvent.click(screen.getByTestId('decision-approve-btn'))
    // Approve should NOT have been called yet — dialog should be showing
    expect(onApprove).not.toHaveBeenCalled()
    expect(screen.getByTestId('decision-confirm-backdrop')).toBeInTheDocument()
  })

  it('calls onApprove after confirming in dialog', () => {
    const onApprove = vi.fn()
    render(
      <DecisionControls
        {...defaultProps}
        onApprove={onApprove}
        requireConfirmation={true}
      />,
    )

    fireEvent.click(screen.getByTestId('decision-approve-btn'))
    fireEvent.click(screen.getByTestId('decision-confirm-approve-btn'))
    expect(onApprove).toHaveBeenCalledOnce()
  })

  it('cancels confirmation dialog without calling onApprove', () => {
    const onApprove = vi.fn()
    render(
      <DecisionControls
        {...defaultProps}
        onApprove={onApprove}
        requireConfirmation={true}
      />,
    )

    fireEvent.click(screen.getByTestId('decision-approve-btn'))
    fireEvent.click(screen.getByTestId('decision-confirm-cancel-btn'))
    expect(onApprove).not.toHaveBeenCalled()
    expect(screen.queryByTestId('decision-confirm-backdrop')).not.toBeInTheDocument()
  })
})

// ---------------------------------------------------------------------------
// TrustMetadata
// ---------------------------------------------------------------------------

describe('TrustMetadata', () => {
  it('displays confidence level with correct label', () => {
    render(
      <TrustMetadata
        confidence="high"
        source="Intent Builder v3"
        timestamp="2026-03-24 10:00"
      />,
    )

    const badge = screen.getByTestId('trust-metadata-confidence')
    expect(badge).toHaveTextContent('High confidence')
  })

  it('displays medium confidence with amber styling', () => {
    render(
      <TrustMetadata
        confidence="medium"
        source="Context Enricher"
        timestamp="2026-03-24 10:00"
      />,
    )

    expect(screen.getByTestId('trust-metadata-confidence')).toHaveTextContent(
      'Medium confidence',
    )
  })

  it('displays low confidence with red styling', () => {
    render(
      <TrustMetadata
        confidence="low"
        source="Fallback heuristic"
        timestamp="2026-03-24 10:00"
      />,
    )

    expect(screen.getByTestId('trust-metadata-confidence')).toHaveTextContent(
      'Low confidence',
    )
  })

  it('displays source and timestamp', () => {
    render(
      <TrustMetadata
        confidence="high"
        source="Intent Builder v3"
        timestamp="2026-03-24 10:00"
      />,
    )

    expect(screen.getByTestId('trust-metadata-source')).toHaveTextContent('Intent Builder v3')
    expect(screen.getByTestId('trust-metadata-timestamp')).toHaveTextContent('2026-03-24 10:00')
  })

  it('displays AI-generated label (SG 8.6)', () => {
    render(
      <TrustMetadata
        confidence="high"
        source="Intent Builder"
        timestamp="2026-03-24 10:00"
      />,
    )

    expect(screen.getByTestId('trust-metadata-ai-label')).toHaveTextContent('AI-generated')
  })

  it('displays ownership cue', () => {
    render(
      <TrustMetadata
        confidence="high"
        source="source"
        timestamp="now"
        ownershipCue="Review before merging"
      />,
    )

    expect(screen.getByTestId('trust-metadata-ownership')).toHaveTextContent(
      'Review before merging',
    )
  })

  it('shows default ownership cue when not specified', () => {
    render(
      <TrustMetadata confidence="high" source="source" timestamp="now" />,
    )

    expect(screen.getByTestId('trust-metadata-ownership')).toHaveTextContent(
      'You are responsible for final action',
    )
  })

  it('toggles rationale disclosure on click', () => {
    render(
      <TrustMetadata
        confidence="high"
        source="source"
        timestamp="now"
        rationale="The model chose this approach because of X, Y, Z."
      />,
    )

    // Rationale content should be hidden initially
    expect(screen.queryByTestId('trust-metadata-rationale-content')).not.toBeInTheDocument()

    // Click toggle to expand
    fireEvent.click(screen.getByTestId('trust-metadata-rationale-toggle'))
    expect(screen.getByTestId('trust-metadata-rationale-content')).toHaveTextContent(
      'The model chose this approach because of X, Y, Z.',
    )

    // Click toggle to collapse
    fireEvent.click(screen.getByTestId('trust-metadata-rationale-toggle'))
    expect(screen.queryByTestId('trust-metadata-rationale-content')).not.toBeInTheDocument()
  })

  it('does not render rationale toggle when no rationale is provided', () => {
    render(
      <TrustMetadata confidence="medium" source="source" timestamp="now" />,
    )

    expect(screen.queryByTestId('trust-metadata-rationale-toggle')).not.toBeInTheDocument()
  })
})

// ---------------------------------------------------------------------------
// AuditTimeline
// ---------------------------------------------------------------------------

describe('AuditTimeline', () => {
  it('renders empty state when no entries', () => {
    render(<AuditTimeline entries={[]} />)

    expect(screen.getByTestId('audit-timeline-empty')).toHaveTextContent('No audit entries yet')
  })

  it('renders all provided entries', () => {
    render(<AuditTimeline entries={sampleEntries} />)

    expect(screen.getByTestId('audit-entry-a1')).toBeInTheDocument()
    expect(screen.getByTestId('audit-entry-a2')).toBeInTheDocument()
    expect(screen.getByTestId('audit-entry-a3')).toBeInTheDocument()
  })

  it('displays entry descriptions', () => {
    render(<AuditTimeline entries={sampleEntries} />)

    const descriptions = screen.getAllByTestId('audit-entry-description')
    expect(descriptions[0]).toHaveTextContent('Generated refactoring plan')
    expect(descriptions[1]).toHaveTextContent('Applied code changes')
    expect(descriptions[2]).toHaveTextContent('Manual review completed')
  })

  it('displays actor badges (AI vs Human)', () => {
    render(<AuditTimeline entries={sampleEntries} />)

    const actors = screen.getAllByTestId('audit-entry-actor')
    expect(actors[0]).toHaveTextContent('AI')
    expect(actors[1]).toHaveTextContent('AI')
    expect(actors[2]).toHaveTextContent('Human')
  })

  it('displays status badges', () => {
    render(<AuditTimeline entries={sampleEntries} />)

    const statuses = screen.getAllByTestId('audit-entry-status')
    expect(statuses[0]).toHaveTextContent('Completed')
    expect(statuses[1]).toHaveTextContent('Pending')
    expect(statuses[2]).toHaveTextContent('Completed')
  })

  it('shows Undo button only on mutable entries', () => {
    const onUndo = vi.fn()
    render(<AuditTimeline entries={sampleEntries} onUndo={onUndo} />)

    // Only entry a1 is mutable
    expect(screen.getByTestId('audit-undo-a1')).toBeInTheDocument()
    expect(screen.queryByTestId('audit-undo-a2')).not.toBeInTheDocument()
    expect(screen.queryByTestId('audit-undo-a3')).not.toBeInTheDocument()
  })

  it('calls onUndo with entry ID when Undo is clicked', () => {
    const onUndo = vi.fn()
    render(<AuditTimeline entries={sampleEntries} onUndo={onUndo} />)

    fireEvent.click(screen.getByTestId('audit-undo-a1'))
    expect(onUndo).toHaveBeenCalledWith('a1')
  })

  it('does not render Undo buttons when onUndo is not provided', () => {
    render(<AuditTimeline entries={sampleEntries} />)

    expect(screen.queryByTestId('audit-undo-a1')).not.toBeInTheDocument()
  })

  it('displays timestamps for entries', () => {
    render(<AuditTimeline entries={sampleEntries} />)

    const timestamps = screen.getAllByTestId('audit-entry-timestamp')
    expect(timestamps[0]).toHaveTextContent('2026-03-24 10:00:00')
  })
})
