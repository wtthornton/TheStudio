/**
 * ExecutionModeSelector — Segmented control for draft/suggest/execute trust tiers.
 *
 * Per SG 8.3 "Autonomy Dial": explicit mode indicator and switch when permissions allow.
 * "execute" mode shows a warning indicator per SG 8.5 (appropriate friction).
 *
 * Epic 55.2
 */

import type { PromptObject } from './PromptObject'

type ExecutionMode = PromptObject['mode']

interface ModeOption {
  value: ExecutionMode
  label: string
  description: string
  /** Tailwind classes for the selected state */
  selectedClassName: string
  warning?: boolean
}

const MODE_OPTIONS: ModeOption[] = [
  {
    value: 'draft',
    label: 'Draft',
    description: 'AI generates a preview. No changes are applied.',
    selectedClassName: 'border-gray-500 bg-gray-800 text-gray-100',
  },
  {
    value: 'suggest',
    label: 'Suggest',
    description: 'AI proposes changes for your review before applying.',
    selectedClassName: 'border-blue-600 bg-blue-900/40 text-blue-200',
  },
  {
    value: 'execute',
    label: 'Execute',
    description: 'AI applies changes directly. Use with caution.',
    selectedClassName: 'border-purple-600 bg-purple-900/40 text-purple-200',
    warning: true,
  },
]

interface ExecutionModeSelectorProps {
  value: ExecutionMode
  onChange: (mode: ExecutionMode) => void
  /** Per-mode disabled state — e.g. user lacks permission for execute */
  disabledModes?: Partial<Record<ExecutionMode, boolean>>
}

export function ExecutionModeSelector({
  value,
  onChange,
  disabledModes = {},
}: ExecutionModeSelectorProps) {
  return (
    <fieldset
      aria-label="Execution mode"
      className="space-y-2"
      data-testid="execution-mode-selector"
    >
      <legend className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-500">
        Execution Mode
      </legend>

      <div className="space-y-1.5">
        {MODE_OPTIONS.map((option) => {
          const isSelected = value === option.value
          const isDisabled = !!disabledModes[option.value]

          return (
            <label
              key={option.value}
              className={`flex cursor-pointer items-start gap-3 rounded-lg border px-4 py-3 transition-colors ${
                isDisabled
                  ? 'cursor-not-allowed border-gray-800 bg-gray-900/50 opacity-50'
                  : isSelected
                    ? option.selectedClassName
                    : 'border-gray-700 bg-gray-900 hover:border-gray-600'
              }`}
              data-testid={`mode-option-${option.value}`}
            >
              <input
                type="radio"
                name="execution-mode"
                value={option.value}
                checked={isSelected}
                disabled={isDisabled}
                onChange={() => onChange(option.value)}
                className="mt-0.5 accent-blue-500"
                aria-describedby={`mode-desc-${option.value}`}
              />
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <span
                    className={`text-sm font-medium ${
                      isDisabled ? 'text-gray-500' : isSelected ? '' : 'text-gray-300'
                    }`}
                  >
                    {option.label}
                  </span>
                  {option.warning && (
                    <span
                      className="rounded bg-amber-900/50 px-1.5 py-0.5 text-xs font-medium text-amber-400"
                      aria-label="Warning: high-impact mode"
                      data-testid="execute-warning"
                    >
                      High impact
                    </span>
                  )}
                </div>
                <p
                  id={`mode-desc-${option.value}`}
                  className={`mt-0.5 text-xs ${isDisabled ? 'text-gray-600' : 'text-gray-400'}`}
                >
                  {option.description}
                </p>
              </div>
            </label>
          )
        })}
      </div>
    </fieldset>
  )
}
