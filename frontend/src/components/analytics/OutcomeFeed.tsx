/**
 * OutcomeFeed -- Epic 39, Story 39.19.
 *
 * Chronological feed of recent TaskPacket outcome signals.
 * Each entry shows:
 * - Outcome badge (success / failure / loopback)
 * - Signal type (qa_passed, qa_defect, etc.)
 * - Task reference (repo#issue_id or task_id truncated)
 * - Relative timestamp
 * - Learnings extracted from failure payloads
 */

import { useEffect, useState } from 'react'
import type { OutcomeEntry, OutcomesResponse } from '../../lib/api'
import { fetchReputationOutcomes } from '../../lib/api'

function outcomeBadge(type: OutcomeEntry['outcome_type']): {
  label: string
  bg: string
  text: string
} {
  switch (type) {
    case 'success':
      return { label: 'Success', bg: 'bg-green-900/50', text: 'text-green-300' }
    case 'failure':
      return { label: 'Failure', bg: 'bg-red-900/50', text: 'text-red-300' }
    case 'loopback':
      return { label: 'Loopback', bg: 'bg-yellow-900/50', text: 'text-yellow-300' }
    default:
      return { label: 'Unknown', bg: 'bg-gray-800', text: 'text-gray-400' }
  }
}

function relativeTime(isoString: string | null): string {
  if (!isoString) return 'unknown time'
  const diff = Date.now() - new Date(isoString).getTime()
  const mins = Math.floor(diff / 60_000)
  const hours = Math.floor(mins / 60)
  const days = Math.floor(hours / 24)
  if (days > 0) return `${days}d ago`
  if (hours > 0) return `${hours}h ago`
  if (mins > 0) return `${mins}m ago`
  return 'just now'
}

function taskRef(entry: OutcomeEntry): string {
  if (entry.repo && entry.issue_id) return `${entry.repo}#${entry.issue_id}`
  if (entry.task_id) return entry.task_id.slice(0, 8) + '…'
  return 'unknown task'
}

function OutcomeItem({ entry }: { entry: OutcomeEntry }) {
  const badge = outcomeBadge(entry.outcome_type)
  return (
    <div className="flex items-start gap-3 py-3 border-b border-gray-800 last:border-0">
      <span
        className={`mt-0.5 shrink-0 rounded px-1.5 py-0.5 text-xs font-medium ${badge.bg} ${badge.text}`}
      >
        {badge.label}
      </span>
      <div className="min-w-0 flex-1">
        <div className="flex items-baseline gap-2">
          <span className="text-xs font-mono text-gray-300">{taskRef(entry)}</span>
          <span className="text-xs text-gray-500">{entry.signal_type.replace(/_/g, ' ')}</span>
          <span className="ml-auto shrink-0 text-xs text-gray-600">
            {relativeTime(entry.signal_at)}
          </span>
        </div>
        {entry.learnings && (
          <p className="mt-0.5 text-xs text-gray-400 truncate" title={String(entry.learnings)}>
            {String(entry.learnings)}
          </p>
        )}
      </div>
    </div>
  )
}

export function OutcomeFeed() {
  const [data, setData] = useState<OutcomesResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)

    fetchReputationOutcomes(50)
      .then((result) => { if (!cancelled) setData(result) })
      .catch((err: Error) => { if (!cancelled) setError(err.message) })
      .finally(() => { if (!cancelled) setLoading(false) })

    return () => { cancelled = true }
  }, [])

  if (loading) {
    return (
      <div className="rounded-lg border border-gray-700 bg-gray-900 p-4">
        <div className="space-y-3">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-10 animate-pulse rounded bg-gray-800" />
          ))}
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="rounded-lg border border-gray-700 bg-gray-900 p-4">
        <div className="text-sm text-red-400">Failed to load outcomes: {error}</div>
      </div>
    )
  }

  if (!data || data.outcomes.length === 0) {
    return (
      <div className="rounded-lg border border-gray-700 bg-gray-900 p-4">
        <h3 className="text-sm font-medium text-gray-300 mb-2">Outcome Signals</h3>
        <div className="flex items-center justify-center h-32 text-gray-500 text-sm">
          No outcome signals recorded yet
        </div>
      </div>
    )
  }

  return (
    <div className="rounded-lg border border-gray-700 bg-gray-900 p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-medium text-gray-300">Outcome Signals</h3>
        <span className="text-xs text-gray-500">{data.total} total</span>
      </div>
      <div>
        {data.outcomes.map((entry) => (
          <OutcomeItem key={entry.id} entry={entry} />
        ))}
      </div>
    </div>
  )
}
