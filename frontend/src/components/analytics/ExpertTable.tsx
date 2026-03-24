/**
 * ExpertTable -- Epic 39, Story 39.17.
 *
 * Sortable table of expert reputation weights.  Clicking a row opens
 * the ExpertDetail view for that expert.
 *
 * Columns: Expert ID (truncated), Trust Tier, Avg Weight, Samples,
 *          Confidence, Trend (drift signal).
 */

import { useEffect, useState } from 'react'
import type { ExpertsResponse, DriftSignal, TrustTier } from '../../lib/api'
import { fetchReputationExperts } from '../../lib/api'

type SortKey = 'avg_weight' | 'total_samples' | 'avg_confidence' | 'trust_tier'

interface ExpertTableProps {
  onSelectExpert: (expertId: string) => void
}

function tierColor(tier: TrustTier): string {
  switch (tier) {
    case 'trusted':
      return 'text-green-400'
    case 'probation':
      return 'text-yellow-400'
    default:
      return 'text-gray-400'
  }
}

function driftBadge(signal: DriftSignal): { label: string; color: string } {
  switch (signal) {
    case 'improving':
      return { label: '↑ Improving', color: 'text-green-400' }
    case 'declining':
      return { label: '↓ Declining', color: 'text-red-400' }
    default:
      return { label: '→ Stable', color: 'text-gray-400' }
  }
}

function tierOrder(tier: TrustTier): number {
  return tier === 'trusted' ? 2 : tier === 'probation' ? 1 : 0
}

export function ExpertTable({ onSelectExpert }: ExpertTableProps) {
  const [data, setData] = useState<ExpertsResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [sortKey, setSortKey] = useState<SortKey>('avg_weight')
  const [sortAsc, setSortAsc] = useState(false)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)

    fetchReputationExperts()
      .then((result) => { if (!cancelled) setData(result) })
      .catch((err: Error) => { if (!cancelled) setError(err.message) })
      .finally(() => { if (!cancelled) setLoading(false) })

    return () => { cancelled = true }
  }, [])

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
        <div className="text-sm text-red-400">Failed to load experts: {error}</div>
      </div>
    )
  }

  if (!data || data.experts.length === 0) {
    return (
      <div className="rounded-lg border border-gray-700 bg-gray-900 p-4">
        <h3 className="text-sm font-medium text-gray-300 mb-2">Expert Performance</h3>
        <div className="flex items-center justify-center h-32 text-gray-500 text-sm">
          No expert reputation data available
        </div>
      </div>
    )
  }

  const sorted = [...data.experts].sort((a, b) => {
    let av: number, bv: number
    if (sortKey === 'trust_tier') {
      av = tierOrder(a.trust_tier)
      bv = tierOrder(b.trust_tier)
    } else {
      av = a[sortKey] as number
      bv = b[sortKey] as number
    }
    return sortAsc ? av - bv : bv - av
  })

  function toggleSort(key: SortKey) {
    if (sortKey === key) {
      setSortAsc((p) => !p)
    } else {
      setSortKey(key)
      setSortAsc(false)
    }
  }

  function colHeader(key: SortKey, label: string) {
    const active = sortKey === key
    return (
      <th
        className="px-3 py-2 text-left text-xs font-medium text-gray-400 uppercase tracking-wider cursor-pointer select-none hover:text-gray-200"
        onClick={() => toggleSort(key)}
      >
        {label}
        {active && (
          <span className="ml-1 text-indigo-400">{sortAsc ? '↑' : '↓'}</span>
        )}
      </th>
    )
  }

  return (
    <div className="rounded-lg border border-gray-700 bg-gray-900 p-4">
      <h3 className="text-sm font-medium text-gray-300 mb-3">Expert Performance</h3>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-700">
              <th className="px-3 py-2 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                Expert
              </th>
              {colHeader('trust_tier', 'Tier')}
              {colHeader('avg_weight', 'Weight')}
              {colHeader('total_samples', 'Samples')}
              {colHeader('avg_confidence', 'Confidence')}
              <th className="px-3 py-2 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                Trend
              </th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((expert) => {
              const drift = driftBadge(expert.drift_signal)
              return (
                <tr
                  key={expert.expert_id}
                  className="border-b border-gray-800 hover:bg-gray-800/50 cursor-pointer transition-colors"
                  onClick={() => onSelectExpert(expert.expert_id)}
                >
                  <td className="px-3 py-2 font-mono text-xs text-gray-300">
                    {expert.expert_id.slice(0, 8)}…
                  </td>
                  <td className={`px-3 py-2 text-xs font-medium capitalize ${tierColor(expert.trust_tier)}`}>
                    {expert.trust_tier}
                  </td>
                  <td className="px-3 py-2 text-xs text-gray-200">
                    {(expert.avg_weight * 100).toFixed(1)}%
                  </td>
                  <td className="px-3 py-2 text-xs text-gray-400">
                    {expert.total_samples}
                  </td>
                  <td className="px-3 py-2 text-xs text-gray-400">
                    {(expert.avg_confidence * 100).toFixed(0)}%
                  </td>
                  <td className={`px-3 py-2 text-xs font-medium ${drift.color}`}>
                    {drift.label}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
      <p className="mt-2 text-xs text-gray-500">
        Click a row to view expert details. {data.experts.length} expert
        {data.experts.length !== 1 ? 's' : ''} tracked.
      </p>
    </div>
  )
}
