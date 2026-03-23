/**
 * DriftAlerts -- Epic 39, Story 39.20.
 *
 * Drift detection alerts panel.  Shows:
 * - Composite drift score badge (low / moderate / high)
 * - List of active drift alerts (metric, direction, magnitude, possible cause)
 * - "Insufficient data" state when < 20 tasks in the 14-day window
 *
 * Data comes from GET /api/v1/dashboard/reputation/drift.
 */

import { useEffect, useState } from 'react'
import type { DriftAlert, DriftLevel, DriftResponse } from '../../lib/api'
import { fetchReputationDrift } from '../../lib/api'

function driftScoreBadge(score: DriftLevel): { bg: string; text: string; label: string } {
  switch (score) {
    case 'high':
      return { bg: 'bg-red-900/60', text: 'text-red-300', label: 'High Drift' }
    case 'moderate':
      return { bg: 'bg-yellow-900/60', text: 'text-yellow-300', label: 'Moderate Drift' }
    default:
      return { bg: 'bg-green-900/50', text: 'text-green-300', label: 'Low Drift' }
  }
}

function metricLabel(metric: string): string {
  const labels: Record<string, string> = {
    gate_pass_rate: 'Gate Pass Rate',
    expert_weights: 'Expert Weights',
    model_cost: 'Model Cost',
    loopback_rate: 'Loopback Rate',
  }
  return labels[metric] ?? metric.replace(/_/g, ' ')
}

function AlertCard({ alert }: { alert: DriftAlert }) {
  const directionColor = alert.direction === 'up' ? 'text-red-400' : 'text-red-400'
  const directionSymbol = alert.direction === 'up' ? '↑' : '↓'
  const pct = (alert.magnitude * 100).toFixed(1)

  return (
    <div className="rounded border border-gray-700 bg-gray-800/50 p-3">
      <div className="flex items-start justify-between gap-2">
        <div className="font-medium text-xs text-gray-200">{metricLabel(alert.metric)}</div>
        <span className={`shrink-0 text-xs font-semibold ${directionColor}`}>
          {directionSymbol} {pct}%
        </span>
      </div>
      <p className="mt-1 text-xs text-gray-400 leading-relaxed">{alert.possible_cause}</p>
      {alert.current_value !== null && alert.previous_value !== null && (
        <div className="mt-1.5 flex gap-3 text-xs text-gray-500">
          <span>Current: <span className="text-gray-300">{alert.current_value.toFixed(3)}</span></span>
          <span>Previous: <span className="text-gray-300">{alert.previous_value.toFixed(3)}</span></span>
        </div>
      )}
    </div>
  )
}

export function DriftAlerts() {
  const [data, setData] = useState<DriftResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)

    fetchReputationDrift()
      .then((result) => { if (!cancelled) setData(result) })
      .catch((err: Error) => { if (!cancelled) setError(err.message) })
      .finally(() => { if (!cancelled) setLoading(false) })

    return () => { cancelled = true }
  }, [])

  if (loading) {
    return (
      <div className="rounded-lg border border-gray-700 bg-gray-900 p-4">
        <div className="h-32 animate-pulse bg-gray-800 rounded" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="rounded-lg border border-gray-700 bg-gray-900 p-4">
        <div className="text-sm text-red-400">Failed to load drift data: {error}</div>
      </div>
    )
  }

  if (!data) return null

  const badge = driftScoreBadge(data.drift_score)

  return (
    <div className="rounded-lg border border-gray-700 bg-gray-900 p-4">
      {/* Header row with composite score */}
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-medium text-gray-300">Drift Detection</h3>
        <span className={`rounded px-2 py-0.5 text-xs font-semibold ${badge.bg} ${badge.text}`}>
          {badge.label}
        </span>
      </div>

      <p className="text-xs text-gray-500 mb-3">
        14-day rolling window · {data.task_count} task
        {data.task_count !== 1 ? 's' : ''} completed
      </p>

      {data.insufficient_data ? (
        <div className="flex flex-col items-center justify-center py-6 text-center">
          <p className="text-sm text-gray-400">Insufficient data for drift analysis</p>
          <p className="mt-1 text-xs text-gray-500">
            Requires at least {data.min_tasks_required ?? 20} completed tasks in the last{' '}
            {data.window_days} days ({data.task_count} found).
          </p>
        </div>
      ) : data.alerts.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-6 text-center">
          <p className="text-sm text-green-400">No drift detected</p>
          <p className="mt-1 text-xs text-gray-500">
            All tracked metrics are within normal ranges.
          </p>
        </div>
      ) : (
        <div className="space-y-2">
          {data.alerts.map((alert) => (
            <AlertCard key={alert.metric} alert={alert} />
          ))}
        </div>
      )}

      <div className="mt-3 pt-3 border-t border-gray-800 flex items-center justify-between text-xs text-gray-600">
        <span>Composite score: {(data.composite_score * 100).toFixed(0)}%</span>
        <span>{data.window_days}-day window</span>
      </div>
    </div>
  )
}
