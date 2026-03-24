/**
 * Epic 44.10 — Vitest tests for wizard components and gate logic.
 * Covers: wizardStorage, WizardShell, IncompleteBanner, wizard gate in App.
 */

import { render, screen, fireEvent, act } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

// ---------------------------------------------------------------------------
// Mock react-use-wizard so WizardShell renders without its internals
// ---------------------------------------------------------------------------
vi.mock('react-use-wizard', () => {
  const useWizardMock = vi.fn(() => ({
    activeStep: 0,
    stepCount: 2,
    isFirstStep: true,
    isLastStep: false,
    isLoading: false,
    nextStep: vi.fn().mockResolvedValue(undefined),
    previousStep: vi.fn().mockResolvedValue(undefined),
  }))

  const WizardMock = ({
    children,
    header,
    footer,
  }: {
    children: React.ReactNode
    header?: React.ReactNode
    footer?: React.ReactNode
    onStepChange?: () => void
  }) => (
    <div data-testid="wizard-mock">
      {header}
      {/* render only the first child step */}
      {Array.isArray(children) ? children[0] : children}
      {footer}
    </div>
  )

  return { Wizard: WizardMock, useWizard: useWizardMock }
})

// ---------------------------------------------------------------------------
// Imports after mocks
// ---------------------------------------------------------------------------
import {
  isSetupWizardComplete,
  isSetupWizardSkipped,
  markSetupWizardComplete,
  markSetupWizardSkipped,
  clearSetupWizardSkipped,
  SETUP_WIZARD_COMPLETE_KEY,
  SETUP_WIZARD_SKIPPED_KEY,
} from '../components/wizard/wizardStorage'
import { WizardShell } from '../components/wizard/WizardShell'
import { IncompleteBanner } from '../components/wizard/IncompleteBanner'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
function clearWizardStorage() {
  localStorage.removeItem(SETUP_WIZARD_COMPLETE_KEY)
  localStorage.removeItem(SETUP_WIZARD_SKIPPED_KEY)
}

// ===========================================================================
// wizardStorage
// ===========================================================================
describe('wizardStorage', () => {
  beforeEach(() => {
    clearWizardStorage()
  })

  it('isSetupWizardComplete() returns false when key is absent', () => {
    expect(isSetupWizardComplete()).toBe(false)
  })

  it('isSetupWizardComplete() returns true after markSetupWizardComplete()', () => {
    markSetupWizardComplete()
    expect(isSetupWizardComplete()).toBe(true)
  })

  it('isSetupWizardSkipped() returns false when key is absent', () => {
    expect(isSetupWizardSkipped()).toBe(false)
  })

  it('isSetupWizardSkipped() returns true after markSetupWizardSkipped()', () => {
    markSetupWizardSkipped()
    expect(isSetupWizardSkipped()).toBe(true)
  })

  it('clearSetupWizardSkipped() removes the skipped flag', () => {
    markSetupWizardSkipped()
    expect(isSetupWizardSkipped()).toBe(true)
    clearSetupWizardSkipped()
    expect(isSetupWizardSkipped()).toBe(false)
  })

  it('markSetupWizardComplete() persists across re-reads', () => {
    markSetupWizardComplete()
    // Read directly from localStorage to verify persistence
    expect(localStorage.getItem(SETUP_WIZARD_COMPLETE_KEY)).toBe('true')
  })

  it('markSetupWizardSkipped() persists across re-reads', () => {
    markSetupWizardSkipped()
    expect(localStorage.getItem(SETUP_WIZARD_SKIPPED_KEY)).toBe('true')
  })

  it('complete and skipped flags are independent', () => {
    markSetupWizardComplete()
    expect(isSetupWizardSkipped()).toBe(false)
    markSetupWizardSkipped()
    expect(isSetupWizardComplete()).toBe(true)
    expect(isSetupWizardSkipped()).toBe(true)
  })
})

// ===========================================================================
// WizardShell
// ===========================================================================
describe('WizardShell', () => {
  it('renders the wizard container', () => {
    render(
      <WizardShell onComplete={vi.fn()}>
        <div>Step 1</div>
        <div>Step 2</div>
      </WizardShell>,
    )
    expect(screen.getByTestId('wizard-shell')).toBeInTheDocument()
  })

  it('renders the title', () => {
    render(
      <WizardShell title="My Setup" onComplete={vi.fn()}>
        <div>Step 1</div>
      </WizardShell>,
    )
    expect(screen.getByText('My Setup')).toBeInTheDocument()
  })

  it('renders default title when none provided', () => {
    render(
      <WizardShell onComplete={vi.fn()}>
        <div>Step 1</div>
      </WizardShell>,
    )
    expect(screen.getByText('Welcome to TheStudio')).toBeInTheDocument()
  })

  it('renders child step content', () => {
    render(
      <WizardShell onComplete={vi.fn()}>
        <div data-testid="step-content">Health Check</div>
      </WizardShell>,
    )
    expect(screen.getByTestId('step-content')).toBeInTheDocument()
  })

  it('renders Skip button when onSkip is provided', () => {
    render(
      <WizardShell onComplete={vi.fn()} onSkip={vi.fn()}>
        <div>Step 1</div>
      </WizardShell>,
    )
    expect(screen.getByTestId('wizard-skip')).toBeInTheDocument()
  })

  it('does not render Skip button when onSkip is absent', () => {
    render(
      <WizardShell onComplete={vi.fn()}>
        <div>Step 1</div>
      </WizardShell>,
    )
    expect(screen.queryByTestId('wizard-skip')).not.toBeInTheDocument()
  })

  it('calls onSkip when Skip button is clicked', () => {
    const onSkip = vi.fn()
    render(
      <WizardShell onComplete={vi.fn()} onSkip={onSkip}>
        <div>Step 1</div>
      </WizardShell>,
    )
    fireEvent.click(screen.getByTestId('wizard-skip'))
    expect(onSkip).toHaveBeenCalledOnce()
  })

  it('renders the wizard-header progress area', () => {
    render(
      <WizardShell onComplete={vi.fn()}>
        <div>Step 1</div>
      </WizardShell>,
    )
    expect(screen.getByTestId('wizard-header')).toBeInTheDocument()
  })

  it('renders Next button in footer', () => {
    render(
      <WizardShell onComplete={vi.fn()}>
        <div>Step 1</div>
      </WizardShell>,
    )
    expect(screen.getByTestId('wizard-next')).toBeInTheDocument()
  })

  it('Back button not shown on first step', () => {
    render(
      <WizardShell onComplete={vi.fn()}>
        <div>Step 1</div>
      </WizardShell>,
    )
    // useWizard mock returns isFirstStep: true
    expect(screen.queryByTestId('wizard-back')).not.toBeInTheDocument()
  })
})

// ===========================================================================
// IncompleteBanner
// ===========================================================================
describe('IncompleteBanner', () => {
  beforeEach(() => {
    clearWizardStorage()
  })

  it('does not render when neither flag is set', () => {
    render(<IncompleteBanner onResume={vi.fn()} />)
    expect(screen.queryByTestId('incomplete-banner')).not.toBeInTheDocument()
  })

  it('does not render when setup is complete (even if skipped)', () => {
    markSetupWizardComplete()
    markSetupWizardSkipped()
    render(<IncompleteBanner onResume={vi.fn()} />)
    expect(screen.queryByTestId('incomplete-banner')).not.toBeInTheDocument()
  })

  it('renders when wizard was skipped but not complete', async () => {
    markSetupWizardSkipped()
    render(<IncompleteBanner onResume={vi.fn()} />)
    // Effect runs after mount
    await act(async () => {})
    expect(screen.getByTestId('incomplete-banner')).toBeInTheDocument()
  })

  it('calls onResume when Resume Setup button is clicked', async () => {
    markSetupWizardSkipped()
    const onResume = vi.fn()
    render(<IncompleteBanner onResume={onResume} />)
    await act(async () => {})
    fireEvent.click(screen.getByTestId('incomplete-banner-resume'))
    expect(onResume).toHaveBeenCalledOnce()
  })

  it('dismisses (hides) when ✕ button is clicked', async () => {
    markSetupWizardSkipped()
    render(<IncompleteBanner onResume={vi.fn()} />)
    await act(async () => {})
    expect(screen.getByTestId('incomplete-banner')).toBeInTheDocument()
    fireEvent.click(screen.getByTestId('incomplete-banner-dismiss'))
    expect(screen.queryByTestId('incomplete-banner')).not.toBeInTheDocument()
  })
})

// ===========================================================================
// Wizard gate logic (storage-level)
// ===========================================================================
describe('wizard gate logic', () => {
  beforeEach(() => {
    clearWizardStorage()
  })

  it('wizard should show when no flags set (fresh install)', () => {
    // Simulate gate logic from App.tsx
    const shouldShow = !isSetupWizardComplete() && !isSetupWizardSkipped()
    expect(shouldShow).toBe(true)
  })

  it('wizard should hide after completion', () => {
    markSetupWizardComplete()
    const shouldShow = !isSetupWizardComplete() && !isSetupWizardSkipped()
    expect(shouldShow).toBe(false)
  })

  it('wizard should hide after skip', () => {
    markSetupWizardSkipped()
    const shouldShow = !isSetupWizardComplete() && !isSetupWizardSkipped()
    expect(shouldShow).toBe(false)
  })

  it('clearing skipped flag re-enables wizard to show', () => {
    markSetupWizardSkipped()
    clearSetupWizardSkipped()
    const shouldShow = !isSetupWizardComplete() && !isSetupWizardSkipped()
    expect(shouldShow).toBe(true)
  })

  it('re-launch (clearSkipped + setState) works even when previously complete', () => {
    // Complete, then re-launch: we clear skipped but still mark complete.
    // Gate: isComplete || isSkipped → hide. Resume always forces show.
    // This test validates resume callback contracts.
    markSetupWizardComplete()
    clearSetupWizardSkipped() // resume does this
    // After resume the App forcibly sets showSetupWizard = true regardless of flags
    const storageComplete = isSetupWizardComplete()
    expect(storageComplete).toBe(true) // flag unchanged — wizard shows via state override
  })
})
