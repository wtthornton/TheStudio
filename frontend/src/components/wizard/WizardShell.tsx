/**
 * Epic 44.1 — Setup wizard chrome: progress, step nav, skip.
 * Uses react-use-wizard; footer/header sit inside Wizard so useWizard() works.
 */

import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import { Wizard, useWizard } from 'react-use-wizard'

const WizardNavContext = createContext<{
  setNextDisabled: (value: boolean) => void
} | null>(null)

export function useWizardNav(): { setNextDisabled: (value: boolean) => void } {
  const ctx = useContext(WizardNavContext)
  if (!ctx) {
    throw new Error('useWizardNav must be used inside WizardShell')
  }
  return ctx
}

function WizardProgressHeader({ title }: { title: string }) {
  const { activeStep, stepCount } = useWizard()
  const pct = stepCount > 0 ? ((activeStep + 1) / stepCount) * 100 : 0

  return (
    <div className="mb-6 space-y-3" data-testid="wizard-header">
      <h2 id="setup-wizard-title" className="text-lg font-semibold text-gray-100">
        {title}
      </h2>
      <div className="h-2 overflow-hidden rounded-full bg-gray-800">
        <div
          className="h-full rounded-full bg-blue-600 transition-all duration-300 ease-out"
          style={{ width: `${pct}%` }}
          data-testid="wizard-progress-bar"
        />
      </div>
      <p className="text-xs text-gray-500">
        Step {activeStep + 1} of {stepCount}
      </p>
    </div>
  )
}

interface WizardFooterProps {
  nextDisabled: boolean
  onComplete: () => void
  onSkip?: () => void
}

function WizardFooter({ nextDisabled, onComplete, onSkip }: WizardFooterProps) {
  const { nextStep, previousStep, isFirstStep, isLastStep, isLoading } = useWizard()

  const handleNext = async () => {
    if (isLastStep) {
      onComplete()
      return
    }
    await nextStep()
  }

  return (
    <div
      className="mt-8 flex flex-wrap items-center justify-between gap-3 border-t border-gray-800 pt-6"
      data-testid="wizard-footer"
    >
      <div>
        {onSkip ? (
          <button
            type="button"
            onClick={onSkip}
            className="text-sm text-gray-500 underline-offset-2 hover:text-gray-300 hover:underline"
            data-testid="wizard-skip"
          >
            Skip setup
          </button>
        ) : (
          <span />
        )}
      </div>
      <div className="flex gap-2">
        {!isFirstStep ? (
          <button
            type="button"
            onClick={previousStep}
            className="rounded-lg border border-gray-600 px-4 py-2 text-sm font-medium text-gray-200 hover:bg-gray-800"
            data-testid="wizard-back"
          >
            Back
          </button>
        ) : null}
        <button
          type="button"
          disabled={nextDisabled || isLoading}
          onClick={() => void handleNext()}
          className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-40"
          data-testid="wizard-next"
        >
          {isLastStep ? 'Finish' : 'Next'}
        </button>
      </div>
    </div>
  )
}

export interface WizardShellProps {
  /** Shown above the progress bar */
  title?: string
  children: ReactNode
  onComplete: () => void
  onSkip?: () => void
}

export function WizardShell({
  title = 'Welcome to TheStudio',
  children,
  onComplete,
  onSkip,
}: WizardShellProps) {
  const [nextDisabled, setNextDisabledState] = useState(false)

  const setNextDisabled = useCallback((value: boolean) => {
    setNextDisabledState(value)
  }, [])

  const navValue = useMemo(() => ({ setNextDisabled }), [setNextDisabled])

  const handleStepChange = useCallback(() => {
    setNextDisabledState(false)
  }, [])

  return (
    <div
      className="w-full max-w-lg rounded-xl border border-gray-700 bg-gray-900 p-6 shadow-xl"
      data-testid="wizard-shell"
    >
      {/* Provider wraps Wizard so step components remain direct children of Wizard (stepCount). */}
      <WizardNavContext.Provider value={navValue}>
        <Wizard
          header={<WizardProgressHeader title={title} />}
          footer={
            <WizardFooter
              nextDisabled={nextDisabled}
              onComplete={onComplete}
              onSkip={onSkip}
            />
          }
          onStepChange={handleStepChange}
        >
          {children}
        </Wizard>
      </WizardNavContext.Provider>
    </div>
  )
}
