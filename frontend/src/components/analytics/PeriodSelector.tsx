/**
 * PeriodSelector -- Epic 39, Story 39.11.
 *
 * Button group for selecting analytics time period (7d, 30d, 90d).
 * Selected button is highlighted with bg-gray-700 to match the
 * existing dashboard nav styling.
 */

import type { AnalyticsPeriod } from '../../lib/api'

interface PeriodSelectorProps {
  period: AnalyticsPeriod
  onChange: (p: AnalyticsPeriod) => void
}

const OPTIONS: { label: string; value: AnalyticsPeriod }[] = [
  { label: '7d', value: '7d' },
  { label: '30d', value: '30d' },
  { label: '90d', value: '90d' },
]

export function PeriodSelector({ period, onChange }: PeriodSelectorProps) {
  return (
    <div className="flex gap-1 rounded-md border border-gray-700 bg-gray-800 p-1">
      {OPTIONS.map((opt) => (
        <button
          key={opt.value}
          onClick={() => onChange(opt.value)}
          className={`rounded px-3 py-1 text-sm font-medium transition-colors ${
            period === opt.value
              ? 'bg-gray-700 text-gray-100'
              : 'text-gray-400 hover:text-gray-200'
          }`}
        >
          {opt.label}
        </button>
      ))}
    </div>
  )
}
