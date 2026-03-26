/**
 * TriageAcceptModal — Prompt-first confirmation flow for triage task acceptance.
 *
 * Story 54.3: Prompt-First Planning and Control Flows.
 *
 * Implements steps 2-3 of the SG §13.1 five-step prompt-first sequence before
 * a triage task enters the pipeline:
 *
 *   Step 2 — Intent preview: system restates what it will do (scope, mode, assumptions)
 *   Step 3 — Mode choice:    user selects observe (draft) / suggest / execute
 *   Step 5 — Human decision: user approves, edits, or rejects
 *
 * Step 1 (intent capture) is the triage task itself; step 4 (evidence output)
 * is delivered post-pipeline via TrustMetadata / AuditTimeline.
 */

import { useState, useEffect, useRef, useCallback } from 'react'
import { useFocusTrap } from '../../hooks/useFocusTrap'
import { ExecutionModeSelector } from '../ai/ExecutionModeSelector'
import type { PromptObject } from '../ai/PromptObject'
import type { TriageTask } from '../../lib/api'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type TriageAcceptMode = PromptObject['mode']

export interface TriageAcceptModalProps {
  /** The triage task being accepted. */
  task: TriageTask
  /** Called when the user confirms acceptance with a chosen mode. */
  onConfirm: (taskId: string, mode: TriageAcceptMode) => void
  /** Called when the user chooses to edit the task first. */
  onEdit: (taskId: string) => void
  /** Called when the user cancels or dismisses. */
  onClose: () => void
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Build a plain-language summary of what the pipeline will do. */
function buildPipelineSummary(mode: TriageAcceptMode): string {
  switch (mode) {
    case 'draft':
      return 'Pipeline will analyse and produce a draft plan. No changes will be applied — all outputs are read-only for human review.'
    case 'suggest':
      return 'Pipeline will propose changes for your review. You will approve or reject each suggestion before anything is applied.'
    case 'execute':
      return 'Pipeline will analyse, plan, and apply changes autonomously. You will review the result and can roll back if needed.'
  }
}

/** AI label per SG §13.5. */
function AiLabel() {
  return (
    <span className="inline-flex items-center gap-1 text-xs text-gray-500" aria-label="AI-generated">
      <svg
        className="h-3 w-3"
        viewBox="0 0 12 12"
        fill="none"
        aria-hidden="true"
      >
        <circle cx="6" cy="6" r="5" stroke="currentColor" strokeWidth="1.5" />
        <path d="M4 6h4M6 4v4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
      </svg>
      AI-generated intent summary
    </span>
  )
}

// ---------------------------------------------------------------------------
// Step progress indicator
// ---------------------------------------------------------------------------

/** Compact progress bar — shows which prompt-first steps are active. */
function StepProgress({ currentStep }: { currentStep: 2 | 3 }) {
  const steps = [
    { n: 1, label: 'Intent capture', done: true },
    { n: 2, label: 'Intent preview', done: currentStep >= 2 },
    { n: 3, label: 'Mode choice', done: currentStep >= 3 },
    { n: 4, label: 'Evidence output', done: false },
    { n: 5, label: 'Human decision', done: false },
  ]

  return (
    <ol
      className="flex items-center gap-0"
      aria-label="Prompt-first flow progress"
      data-testid="prompt-first-steps"
    >
      {steps.map((step, idx) => (
        <li key={step.n} className="flex items-center">
          <div
            className={`flex h-5 w-5 items-center justify-center rounded-full text-[10px] font-semibold transition-colors ${
              step.done
                ? 'bg-blue-700 text-blue-100'
                : 'bg-gray-800 text-gray-600'
            }`}
            aria-current={step.n === currentStep ? 'step' : undefined}
            title={step.label}
          >
            {step.n}
          </div>
          {idx < steps.length - 1 && (
            <div
              className={`h-px w-5 transition-colors ${
                step.done && steps[idx + 1].done ? 'bg-blue-700' : 'bg-gray-700'
              }`}
            />
          )}
        </li>
      ))}
    </ol>
  )
}

// ---------------------------------------------------------------------------
// TriageAcceptModal
// ---------------------------------------------------------------------------

export function TriageAcceptModal({
  task,
  onConfirm,
  onEdit,
  onClose,
}: TriageAcceptModalProps) {
  const [mode, setMode] = useState<TriageAcceptMode>('suggest')
  const [step, setStep] = useState<2 | 3>(2)

  const dialogRef = useRef<HTMLDivElement>(null)
  useFocusTrap(dialogRef, true)

  // Keyboard: Escape dismisses
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [onClose])

  const handleBackdropClick = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      if (e.target === e.currentTarget) onClose()
    },
    [onClose],
  )

  const handleConfirm = useCallback(() => {
    onConfirm(task.id, mode)
  }, [onConfirm, task.id, mode])

  const handleEdit = useCallback(() => {
    onEdit(task.id)
  }, [onEdit, task.id])

  // Advance from step 2 → 3 when user scrolls past intent preview
  const handleContinue = useCallback(() => {
    setStep(3)
  }, [])

  const enrichment = task.triage_enrichment

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
      onClick={handleBackdropClick}
      data-testid="triage-accept-backdrop"
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="triage-accept-title"
        className="flex w-full max-w-2xl flex-col rounded-lg border border-gray-700 bg-gray-900 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
        data-testid="triage-accept-modal"
      >
        {/* ── Header ── */}
        <div className="flex items-start justify-between border-b border-gray-800 px-6 py-4">
          <div className="flex-1 min-w-0">
            <div className="mb-2 flex items-center gap-3">
              <span className="text-xs font-semibold uppercase tracking-wide text-blue-400">
                Accept &amp; Plan
              </span>
              <StepProgress currentStep={step} />
            </div>
            <h2
              id="triage-accept-title"
              className="truncate text-sm font-semibold text-gray-100"
            >
              {task.issue_title || `Issue #${task.issue_id}`}
            </h2>
            {task.issue_id && (
              <p className="mt-0.5 text-xs text-gray-500">Issue #{task.issue_id}</p>
            )}
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="ml-4 shrink-0 rounded p-1 text-gray-500 hover:text-gray-300 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
            data-testid="triage-accept-close"
          >
            <svg className="h-4 w-4" viewBox="0 0 16 16" fill="none" aria-hidden="true">
              <path d="M4 4l8 8M12 4l-8 8" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
            </svg>
          </button>
        </div>

        {/* ── Body ── */}
        <div className="flex-1 overflow-y-auto px-6 py-5">
          {/* Step 2 — Intent preview */}
          <section
            aria-label="Intent preview"
            className="mb-5 rounded-lg border border-gray-700 bg-gray-800/50 p-4"
            data-testid="triage-intent-preview"
          >
            <div className="mb-3 flex items-center justify-between">
              <h3 className="text-xs font-semibold uppercase tracking-wide text-gray-400">
                Intent Preview
              </h3>
              <AiLabel />
            </div>

            {/* Planned action */}
            <div className="mb-3">
              <dt className="mb-1 text-xs font-medium text-gray-500">Planned action</dt>
              <dd
                className="text-sm text-gray-200"
                data-testid="intent-planned-action"
              >
                Process issue{task.issue_id ? ` #${task.issue_id}` : ''} through the TheStudio
                delivery pipeline. The pipeline will analyse context, build an intent specification,
                route to expert agents, implement, verify, and submit a draft PR.
              </dd>
            </div>

            {/* Scope estimate from enrichment */}
            {enrichment && (
              <dl className="grid grid-cols-3 gap-3">
                <div
                  className="rounded border border-gray-700 bg-gray-900 px-3 py-2"
                  data-testid="intent-complexity"
                >
                  <dt className="text-[10px] font-semibold uppercase tracking-wide text-gray-500">
                    Complexity
                  </dt>
                  <dd className="mt-0.5 text-sm capitalize text-gray-200">
                    {enrichment.complexity_hint}
                  </dd>
                </div>
                <div
                  className="rounded border border-gray-700 bg-gray-900 px-3 py-2"
                  data-testid="intent-files"
                >
                  <dt className="text-[10px] font-semibold uppercase tracking-wide text-gray-500">
                    Est. files
                  </dt>
                  <dd className="mt-0.5 text-sm text-gray-200">
                    ~{enrichment.file_count_estimate}
                  </dd>
                </div>
                <div
                  className="rounded border border-gray-700 bg-gray-900 px-3 py-2"
                  data-testid="intent-cost"
                >
                  <dt className="text-[10px] font-semibold uppercase tracking-wide text-gray-500">
                    Est. cost
                  </dt>
                  <dd className="mt-0.5 text-sm text-gray-200">
                    ${enrichment.cost_estimate_range.min.toFixed(2)}–$
                    {enrichment.cost_estimate_range.max.toFixed(2)}
                  </dd>
                </div>
              </dl>
            )}

            {/* Pipeline summary — driven by current mode */}
            <p
              className="mt-3 text-xs text-gray-400"
              data-testid="intent-pipeline-summary"
            >
              {buildPipelineSummary(mode)}
            </p>

            {step === 2 && (
              <div className="mt-4 flex justify-end">
                <button
                  type="button"
                  onClick={handleContinue}
                  className="rounded bg-blue-700 px-4 py-1.5 text-xs font-medium text-blue-100 hover:bg-blue-600 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-400"
                  data-testid="intent-preview-continue"
                >
                  Continue to Mode Selection →
                </button>
              </div>
            )}
          </section>

          {/* Step 3 — Mode choice (shown after user advances past step 2) */}
          {step >= 3 && (
            <section
              aria-label="Execution mode selection"
              className="rounded-lg border border-gray-700 bg-gray-800/50 p-4"
              data-testid="triage-mode-selector"
            >
              <div className="mb-3">
                <h3 className="text-xs font-semibold uppercase tracking-wide text-gray-400">
                  Step 3 — Choose Execution Mode
                </h3>
                <p className="mt-1 text-xs text-gray-500">
                  Select how much autonomy the pipeline should have for this task.
                </p>
              </div>

              <ExecutionModeSelector value={mode} onChange={setMode} />
            </section>
          )}
        </div>

        {/* ── Footer — Decision controls (Step 5) ── */}
        <div className="flex items-center justify-between border-t border-gray-800 px-6 py-4">
          <p className="text-xs text-gray-500" data-testid="ownership-notice">
            You are responsible for the final outcome of this action.
          </p>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={handleEdit}
              className="rounded border border-blue-700 px-3 py-1.5 text-xs font-medium text-blue-400 hover:bg-blue-900/40 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 focus-visible:ring-offset-gray-900"
              data-testid="triage-accept-edit-btn"
            >
              Edit First
            </button>
            <button
              type="button"
              onClick={onClose}
              className="rounded px-3 py-1.5 text-xs text-gray-400 hover:text-gray-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 focus-visible:ring-offset-gray-900"
              data-testid="triage-accept-cancel-btn"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleConfirm}
              disabled={step < 3}
              className="rounded bg-blue-600 px-4 py-1.5 text-xs font-medium text-white hover:bg-blue-700 disabled:opacity-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 focus-visible:ring-offset-gray-900"
              data-testid="triage-accept-confirm-btn"
            >
              Accept &amp; Start Pipeline
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
