/**
 * ReputationSummaryCards -- Epic 39, Story 39.21.
 *
 * Four summary cards for the Reputation & Outcomes view:
 * - Success Rate (QA pass fraction) with trend
 * - Avg Loopbacks (rework count per task) with trend
 * - PR Merge Rate with trend
 * - Drift Score (low / moderate / high, no numeric trend)
 *
 * Reuses the visual pattern from SummaryCards (Slice 1) but consumes
 * the reputation summary endpoint with its own data shape.
 */

import { useEffect, useState } from 'react'
import type {
  ReputationSummaryResponse,
  ReputationSummaryCards as Cards,
  TrendDirection,
  DriftLevel,
} from '../../lib/api'
import { fetchReputationSummary } from '../../lib/api'

function trendArrow(trend: TrendDirection): { symbol: string; color: string } {
  switch (trend) {
    case 'up':
      return { symbol: '↑', color: 'text-green-400' }
    case 'down':
      return { symbol: '↓', color: 'text-red-400' }
    default:
      return { symbol: '→', color: 'text-gray-400' }
  }
}

function driftColor(score: DriftLevel): string {
  switch (score) {
    case 'high':
      return 'text-red-400'
    case 'moderate':
      return 'text-yellow-400'
    default:
      return 'text-green-400'
  }
}

function formatNumericCard(
  key: keyof Omit<Cards, 'drift_score'>,
  value: number,
): string {
  switch (key) {
    case 'success_rate':
    case 'pr_merge_rate':
      return `${(value * 100).toFixed(1)}%`
    case 'avg_loopbacks':
      return value.toFixed(2)
    default:
      return String(value)
  }
}

const CARD_LABELS: Record<string, string> = {
  success_rate: 'QA Success Rate',
  avg_loopbacks: 'Avg Loopbacks',
  pr_merge_rate: 'PR Merge Rate',
  drift_score: 'Drift Score',
}

export function ReputationSummaryCards() {
  const [data, setData] = useState<ReputationSummaryResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)

    fetchReputationSummary()
      .then((result) => { if (!cancelled) setData(result) })
      .catch((err: Error) => { if (!cancelled) setError(err.message) })
      .finally(() => { if (!cancelled) setLoading(false) })

    return () => { cancelled = true }
  }, [])

  if (loading) {
    return (
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="animate-pulse rounded-lg border border-gray-700 bg-gray-900 p-4 h-20" />
        ))}
      </div>
    )
  }

  if (error) {
    return <div className="text-sm text-red-400">Failed to load reputation summary: {error}</div>
  }

  if (!data) return null

  const cards = data.cards
  const numericKeys = ['success_rate', 'avg_loopbacks', 'pr_merge_rate'] as const

  return (
    <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
      {/* Three numeric cards with trend arrows */}
      {numericKeys.map((key) => {
        const card = cards[key]
        const { symbol, color } = trendArrow(card.trend)
        return (
          <div key={key} className="rounded-lg border border-gray-700 bg-gray-900 p-4">
            <div className="text-xs text-gray-400 uppercase tracking-wider">
              {CARD_LABELS[key]}
            </div>
            <div className="mt-1 flex items-baseline gap-2">
              <span className="text-2xl font-semibold text-gray-100">
                {formatNumericCard(key, card.value)}
              </span>
              <span className={`text-sm font-medium ${color}`}>{symbol}</span>
            </div>
          </div>
        )
      })}

      {/* Drift score card — categorical, no numeric trend */}
      <div className="rounded-lg border border-gray-700 bg-gray-900 p-4">
        <div className="text-xs text-gray-400 uppercase tracking-wider">
          {CARD_LABELS.drift_score}
        </div>
        <div className="mt-1 flex items-baseline gap-2">
          <span className={`text-2xl font-semibold capitalize ${driftColor(cards.drift_score.score)}`}>
            {cards.drift_score.value}
          </span>
        </div>
      </div>
    </div>
  )
}
