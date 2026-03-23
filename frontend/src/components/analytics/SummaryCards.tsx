/**
 * SummaryCards -- Epic 39, Story 39.10.
 *
 * Four summary cards: Tasks Completed, Avg Pipeline Time, PR Merge Rate,
 * Total Spend.  Each shows value + trend arrow.
 *
 * Trend arrows:  up = green, down = red, stable = gray.
 */

import { useEffect, useState } from 'react'
import type { AnalyticsPeriod, SummaryResponse, SummaryCardValue, TrendDirection } from '../../lib/api'
import { fetchAnalyticsSummary } from '../../lib/api'

interface SummaryCardsProps {
  period: AnalyticsPeriod
  repo?: string | null
}

function trendArrow(trend: TrendDirection): { symbol: string; color: string } {
  switch (trend) {
    case 'up':
      return { symbol: '\u2191', color: 'text-green-400' }
    case 'down':
      return { symbol: '\u2193', color: 'text-red-400' }
    default:
      return { symbol: '\u2192', color: 'text-gray-400' }
  }
}

function formatValue(key: string, card: SummaryCardValue): string {
  switch (key) {
    case 'tasks_completed':
      return String(card.value)
    case 'avg_pipeline_seconds':
      if (card.value < 60) return `${card.value.toFixed(1)}s`
      return `${(card.value / 60).toFixed(1)}m`
    case 'pr_merge_rate':
      return `${(card.value * 100).toFixed(1)}%`
    case 'total_spend_usd':
      return `$${card.value.toFixed(4)}`
    default:
      return String(card.value)
  }
}

const CARD_LABELS: Record<string, string> = {
  tasks_completed: 'Tasks Completed',
  avg_pipeline_seconds: 'Avg Pipeline Time',
  pr_merge_rate: 'PR Merge Rate',
  total_spend_usd: 'Total Spend',
}

export function SummaryCards({ period, repo }: SummaryCardsProps) {
  const [data, setData] = useState<SummaryResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)

    fetchAnalyticsSummary(period, repo)
      .then((result) => {
        if (!cancelled) setData(result)
      })
      .catch((err: Error) => {
        if (!cancelled) setError(err.message)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => { cancelled = true }
  }, [period, repo])

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
    return <div className="text-sm text-red-400">Failed to load summary: {error}</div>
  }

  if (!data) return null

  const cardKeys = ['tasks_completed', 'avg_pipeline_seconds', 'pr_merge_rate', 'total_spend_usd'] as const

  return (
    <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
      {cardKeys.map((key) => {
        const card = data.cards[key]
        const { symbol, color } = trendArrow(card.trend)
        return (
          <div key={key} className="rounded-lg border border-gray-700 bg-gray-900 p-4">
            <div className="text-xs text-gray-400 uppercase tracking-wider">
              {CARD_LABELS[key]}
            </div>
            <div className="mt-1 flex items-baseline gap-2">
              <span className="text-2xl font-semibold text-gray-100">
                {formatValue(key, card)}
              </span>
              <span className={`text-sm font-medium ${color}`}>{symbol}</span>
            </div>
          </div>
        )
      })}
    </div>
  )
}
