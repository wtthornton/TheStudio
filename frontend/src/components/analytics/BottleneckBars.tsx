/**
 * BottleneckBars -- Epic 39, Story 39.7.
 *
 * Horizontal bar chart showing average time per pipeline stage.
 * Highlights the slowest stage (bg-red-500) and annotates the
 * most variable stage with a star indicator.
 */

import { useEffect, useState } from 'react'
import type { AnalyticsPeriod, BottleneckResponse, BottleneckStage } from '../../lib/api'
import { fetchAnalyticsBottlenecks } from '../../lib/api'

interface BottleneckBarsProps {
  period: AnalyticsPeriod
  repo?: string | null
}

function formatDuration(seconds: number): string {
  if (seconds < 1) return `${(seconds * 1000).toFixed(0)}ms`
  if (seconds < 60) return `${seconds.toFixed(1)}s`
  return `${(seconds / 60).toFixed(1)}m`
}

function StageBar({ stage, maxAvg }: { stage: BottleneckStage; maxAvg: number }) {
  const widthPct = maxAvg > 0 ? Math.max(2, (stage.avg_seconds / maxAvg) * 100) : 0
  const barColor = stage.is_slowest ? 'bg-red-500' : 'bg-indigo-500'

  return (
    <div className="flex items-center gap-3 py-1.5">
      <div className="w-24 text-xs text-gray-400 text-right shrink-0 capitalize">
        {stage.stage}
      </div>
      <div className="flex-1 flex items-center gap-2">
        <div className="flex-1 bg-gray-800 rounded-full h-5 overflow-hidden">
          <div
            className={`h-full rounded-full ${barColor} transition-all duration-500`}
            style={{ width: `${widthPct}%` }}
          />
        </div>
        <div className="w-20 text-xs text-gray-300 shrink-0">
          {formatDuration(stage.avg_seconds)}
          {stage.is_most_variable && (
            <span className="ml-1 text-yellow-400" title="Most variable stage">
              &#9733;
            </span>
          )}
        </div>
      </div>
    </div>
  )
}

export function BottleneckBars({ period, repo }: BottleneckBarsProps) {
  const [data, setData] = useState<BottleneckResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)

    fetchAnalyticsBottlenecks(period, repo)
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
        <div className="text-sm text-red-400">Failed to load bottlenecks: {error}</div>
      </div>
    )
  }

  if (!data || data.stages.length === 0) {
    return (
      <div className="rounded-lg border border-gray-700 bg-gray-900 p-4">
        <h3 className="text-sm font-medium text-gray-300 mb-2">Pipeline Bottlenecks</h3>
        <div className="flex items-center justify-center h-32 text-gray-500 text-sm">
          No stage timing data available
        </div>
      </div>
    )
  }

  const maxAvg = Math.max(...data.stages.map((s) => s.avg_seconds))

  return (
    <div className="rounded-lg border border-gray-700 bg-gray-900 p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-medium text-gray-300">Pipeline Bottlenecks</h3>
        <div className="flex gap-3 text-xs text-gray-500">
          <span><span className="inline-block w-2 h-2 rounded bg-red-500 mr-1" />Slowest</span>
          <span><span className="text-yellow-400 mr-1">&#9733;</span>Most variable</span>
        </div>
      </div>
      <div>
        {data.stages.map((stage) => (
          <StageBar key={stage.stage} stage={stage} maxAvg={maxAvg} />
        ))}
      </div>
    </div>
  )
}
