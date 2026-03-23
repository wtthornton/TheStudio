/**
 * ExpertDetail -- Epic 39, Story 39.18.
 *
 * Detail view for a single expert.  Shows:
 * - Context key breakdown (all contexts tracked for this expert)
 * - Weight trend sparkline (from weight_history array)
 * - Per-context trust tier, confidence, drift signal
 *
 * Rendered as a slide-in panel when a row in ExpertTable is clicked.
 */

import { useEffect, useState } from 'react'
import type {
  ExpertDetailResponse,
  ExpertContextRow,
  DriftSignal,
  TrustTier,
} from '../../lib/api'
import { fetchExpertDetail } from '../../lib/api'

interface ExpertDetailProps {
  expertId: string
  onClose: () => void
}

function tierBadge(tier: TrustTier): string {
  switch (tier) {
    case 'trusted':
      return 'bg-green-900/50 text-green-300 border-green-700'
    case 'probation':
      return 'bg-yellow-900/50 text-yellow-300 border-yellow-700'
    default:
      return 'bg-gray-800 text-gray-400 border-gray-600'
  }
}

function driftIcon(signal: DriftSignal): { symbol: string; color: string } {
  switch (signal) {
    case 'improving':
      return { symbol: '↑', color: 'text-green-400' }
    case 'declining':
      return { symbol: '↓', color: 'text-red-400' }
    default:
      return { symbol: '→', color: 'text-gray-400' }
  }
}

/** Minimal SVG sparkline from a weight_history array. */
function WeightSparkline({ history }: { history: number[] }) {
  if (history.length < 2) {
    return (
      <span className="text-xs text-gray-500">
        {history.length === 1 ? `${(history[0] * 100).toFixed(1)}%` : 'No history'}
      </span>
    )
  }

  const width = 120
  const height = 32
  const max = Math.max(...history, 0.01)
  const min = Math.min(...history)
  const range = max - min || 0.01
  const step = width / (history.length - 1)

  const points = history
    .map((v, i) => {
      const x = i * step
      const y = height - ((v - min) / range) * (height - 4) - 2
      return `${x.toFixed(1)},${y.toFixed(1)}`
    })
    .join(' ')

  return (
    <svg
      width={width}
      height={height}
      className="overflow-visible"
      aria-label="Weight history sparkline"
    >
      <polyline
        points={points}
        fill="none"
        stroke="#6366f1"
        strokeWidth="1.5"
        strokeLinejoin="round"
        strokeLinecap="round"
      />
      {/* Last point dot */}
      {history.length > 0 && (
        <circle
          cx={(history.length - 1) * step}
          cy={height - ((history[history.length - 1] - min) / range) * (height - 4) - 2}
          r={2.5}
          fill="#818cf8"
        />
      )}
    </svg>
  )
}

function ContextRow({ ctx }: { ctx: ExpertContextRow }) {
  const drift = driftIcon(ctx.drift_signal)
  return (
    <div className="rounded border border-gray-700 bg-gray-800/50 p-3">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="font-mono text-xs text-gray-300 truncate" title={ctx.context_key}>
            {ctx.context_key}
          </div>
          <div className="mt-1 flex flex-wrap gap-3 text-xs text-gray-400">
            <span>Weight: <span className="text-gray-200">{(ctx.weight * 100).toFixed(1)}%</span></span>
            <span>Samples: <span className="text-gray-200">{ctx.sample_count}</span></span>
            <span>Confidence: <span className="text-gray-200">{(ctx.confidence * 100).toFixed(0)}%</span></span>
            <span className={drift.color}>{drift.symbol} {ctx.drift_signal}</span>
          </div>
        </div>
        <div className="flex flex-col items-end gap-1 shrink-0">
          <span
            className={`rounded border px-1.5 py-0.5 text-xs capitalize ${tierBadge(ctx.trust_tier)}`}
          >
            {ctx.trust_tier}
          </span>
          <WeightSparkline history={ctx.weight_history} />
        </div>
      </div>
    </div>
  )
}

export function ExpertDetail({ expertId, onClose }: ExpertDetailProps) {
  const [data, setData] = useState<ExpertDetailResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)

    fetchExpertDetail(expertId)
      .then((result) => { if (!cancelled) setData(result) })
      .catch((err: Error) => { if (!cancelled) setError(err.message) })
      .finally(() => { if (!cancelled) setLoading(false) })

    return () => { cancelled = true }
  }, [expertId])

  return (
    <div className="rounded-lg border border-gray-700 bg-gray-900 p-4">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-sm font-medium text-gray-300">Expert Detail</h3>
          <p className="font-mono text-xs text-gray-500 mt-0.5">{expertId}</p>
        </div>
        <button
          onClick={onClose}
          className="rounded px-2 py-1 text-xs text-gray-400 hover:bg-gray-800 hover:text-gray-200"
        >
          ← Back to table
        </button>
      </div>

      {loading && (
        <div className="space-y-2">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-16 animate-pulse rounded bg-gray-800" />
          ))}
        </div>
      )}

      {error && (
        <div className="text-sm text-red-400">Failed to load expert detail: {error}</div>
      )}

      {!loading && !error && data && (
        <div className="space-y-2">
          <p className="text-xs text-gray-500 mb-3">
            {data.contexts.length} context
            {data.contexts.length !== 1 ? 's' : ''} tracked for this expert.
            Sparklines show weight history (most recent on the right).
          </p>
          {data.contexts.map((ctx) => (
            <ContextRow key={ctx.context_key} ctx={ctx} />
          ))}
        </div>
      )}
    </div>
  )
}
