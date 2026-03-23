/**
 * FailureAnalysis -- Epic 39, Story 39.9.
 *
 * Gate failure types grouped by pipeline stage.
 * Trend badge:  increasing = red, decreasing = green, stable = gray.
 */

import { useEffect, useState } from 'react'
import type { AnalyticsPeriod, FailureResponse, FailureStage } from '../../lib/api'
import { fetchAnalyticsFailures } from '../../lib/api'

interface FailureAnalysisProps {
  period: AnalyticsPeriod
  repo?: string | null
}

function TrendBadge({ trend }: { trend: 'increasing' | 'decreasing' | 'stable' }) {
  const config = {
    increasing: { symbol: '\u25b2', color: 'text-red-400', bg: 'bg-red-900/30' },
    decreasing: { symbol: '\u25bc', color: 'text-green-400', bg: 'bg-green-900/30' },
    stable: { symbol: '\u2192', color: 'text-gray-400', bg: 'bg-gray-800' },
  }
  const c = config[trend]

  return (
    <span className={`inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-xs ${c.color} ${c.bg}`}>
      {c.symbol} {trend}
    </span>
  )
}

function StageGroup({ stageData }: { stageData: FailureStage }) {
  return (
    <div className="mb-4 last:mb-0">
      <div className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2 capitalize">
        {stageData.stage}
      </div>
      <div className="space-y-1.5">
        {stageData.failures.map((f) => (
          <div
            key={f.type}
            className="flex items-center justify-between rounded bg-gray-800/50 px-3 py-2"
          >
            <div className="flex items-center gap-3">
              <span className="text-sm text-gray-200">{f.type}</span>
              <span className="text-xs text-gray-400">({f.count})</span>
            </div>
            <TrendBadge trend={f.trend} />
          </div>
        ))}
      </div>
    </div>
  )
}

export function FailureAnalysis({ period, repo }: FailureAnalysisProps) {
  const [data, setData] = useState<FailureResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)

    fetchAnalyticsFailures(period, repo)
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
      <div className="rounded-lg border border-gray-700 bg-gray-900 p-4">
        <div className="h-48 animate-pulse bg-gray-800 rounded" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="rounded-lg border border-gray-700 bg-gray-900 p-4">
        <div className="text-sm text-red-400">Failed to load failures: {error}</div>
      </div>
    )
  }

  if (!data || data.by_stage.length === 0) {
    return (
      <div className="rounded-lg border border-gray-700 bg-gray-900 p-4">
        <h3 className="text-sm font-medium text-gray-300 mb-2">Failure Analysis</h3>
        <div className="flex items-center justify-center h-32 text-gray-500 text-sm">
          No gate failures in this period
        </div>
      </div>
    )
  }

  return (
    <div className="rounded-lg border border-gray-700 bg-gray-900 p-4">
      <h3 className="text-sm font-medium text-gray-300 mb-3">Failure Analysis</h3>
      {data.by_stage.map((stageData) => (
        <StageGroup key={stageData.stage} stageData={stageData} />
      ))}
    </div>
  )
}
