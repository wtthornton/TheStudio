/**
 * IntentPreview — Displays a structured preview of a PromptObject.
 *
 * Per SG 8.1 step 2: "system restates what it will do (scope, constraints, assumptions)".
 * Shows each field in a card layout with mode badge and action buttons.
 *
 * Epic 55.1
 */

import type { PromptObject } from './PromptObject'

const MODE_BADGE: Record<PromptObject['mode'], { label: string; className: string }> = {
  draft: {
    label: 'Draft',
    className: 'bg-gray-700 text-gray-300',
  },
  suggest: {
    label: 'Suggest',
    className: 'bg-blue-900/60 text-blue-300',
  },
  execute: {
    label: 'Execute',
    className: 'bg-purple-900/60 text-purple-300',
  },
}

interface IntentPreviewProps {
  prompt: PromptObject
  onEdit: () => void
  onConfirm: () => void
}

interface FieldCardProps {
  label: string
  value: string
  testId: string
}

function FieldCard({ label, value, testId }: FieldCardProps) {
  return (
    <div
      className="rounded-lg border border-gray-700 bg-gray-800/60 px-4 py-3"
      data-testid={testId}
    >
      <dt className="mb-1 text-xs font-semibold uppercase tracking-wide text-gray-500">
        {label}
      </dt>
      <dd className="text-sm text-gray-200 whitespace-pre-wrap">{value}</dd>
    </div>
  )
}

export function IntentPreview({ prompt, onEdit, onConfirm }: IntentPreviewProps) {
  const badge = MODE_BADGE[prompt.mode]

  return (
    <section
      aria-label="Intent preview"
      className="rounded-lg border border-gray-700 bg-gray-900 p-5"
      data-testid="intent-preview"
    >
      {/* Header: title + mode badge */}
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-100">Intent Preview</h3>
        <span
          className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${badge.className}`}
          data-testid="intent-preview-mode-badge"
        >
          {badge.label}
        </span>
      </div>

      {/* SG 8.6: AI labeling */}
      <p className="mb-4 text-xs text-gray-500" data-testid="intent-preview-ai-label">
        AI-generated intent summary
      </p>

      {/* Field cards */}
      <dl className="grid gap-3 sm:grid-cols-2">
        <FieldCard label="Goal" value={prompt.goal} testId="intent-field-goal" />
        <FieldCard label="Context" value={prompt.context} testId="intent-field-context" />
        <FieldCard
          label="Constraints"
          value={prompt.constraints}
          testId="intent-field-constraints"
        />
        <FieldCard
          label="Success Criteria"
          value={prompt.success_criteria}
          testId="intent-field-success-criteria"
        />
      </dl>

      {/* Action buttons */}
      <div className="mt-5 flex items-center justify-end gap-3">
        <button
          type="button"
          onClick={onEdit}
          className="rounded px-3 py-1.5 text-xs font-medium text-gray-400 hover:text-gray-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
          data-testid="intent-preview-edit-btn"
        >
          Edit
        </button>
        <button
          type="button"
          onClick={onConfirm}
          className="rounded bg-blue-700 px-4 py-1.5 text-xs font-medium text-blue-100 hover:bg-blue-600 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-400"
          data-testid="intent-preview-confirm-btn"
        >
          Confirm
        </button>
      </div>
    </section>
  )
}
