/**
 * SteeringActivityLog — Epic 37 Slice 5 (37.28).
 *
 * Settings activity log page. Shows a paginated, filterable table of all
 * pipeline steering actions across all tasks (pause, resume, abort, redirect,
 * retry, trust tier assignments).
 *
 * Data source: GET /api/v1/dashboard/steering/audit
 */

import { useEffect, useState, useCallback } from 'react'
import { EmptyState } from './EmptyState'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type SteeringAction =
  | 'pause'
  | 'resume'
  | 'abort'
  | 'redirect'
  | 'retry'
  | 'trust_tier_assigned'
  | 'trust_tier_overridden'

interface AuditEntry {
  id: string
  task_id: string
  action: SteeringAction
  from_stage: string | null
  to_stage: string | null
  reason: string | null
  timestamp: string
  actor: string
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const PAGE_SIZE = 50

const ACTION_LABELS: Record<SteeringAction, string> = {
  pause: 'Pause',
  resume: 'Resume',
  abort: 'Abort',
  redirect: 'Redirect',
  retry: 'Retry',
  trust_tier_assigned: 'Trust Assigned',
  trust_tier_overridden: 'Trust Override',
}

const ACTION_COLORS: Record<SteeringAction, string> = {
  pause: 'bg-amber-900 text-amber-300',
  resume: 'bg-green-900 text-green-300',
  abort: 'bg-red-900 text-red-300',
  redirect: 'bg-violet-900 text-violet-300',
  retry: 'bg-blue-900 text-blue-300',
  trust_tier_assigned: 'bg-teal-900 text-teal-300',
  trust_tier_overridden: 'bg-orange-900 text-orange-300',
}

const ACTION_ICONS: Record<SteeringAction, string> = {
  pause: '⏸',
  resume: '▶',
  abort: '✕',
  redirect: '↩',
  retry: '↺',
  trust_tier_assigned: '🔒',
  trust_tier_overridden: '🔓',
}

const ALL_ACTIONS: SteeringAction[] = [
  'pause',
  'resume',
  'abort',
  'redirect',
  'retry',
  'trust_tier_assigned',
  'trust_tier_overridden',
]

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatRelativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime()
  const seconds = Math.floor(diff / 1000)
  if (seconds < 60) return `${seconds}s ago`
  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return `${minutes}m ago`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.floor(hours / 24)
  return `${days}d ago`
}

function formatAbsoluteTime(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}

function shortId(id: string): string {
  return id.slice(0, 8) + '…'
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

interface ActionBadgeProps {
  action: SteeringAction
}

function ActionBadge({ action }: ActionBadgeProps) {
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${ACTION_COLORS[action]}`}
    >
      <span>{ACTION_ICONS[action]}</span>
      <span>{ACTION_LABELS[action]}</span>
    </span>
  )
}

// ---------------------------------------------------------------------------
// Filter Bar
// ---------------------------------------------------------------------------

interface FilterBarProps {
  actionFilter: SteeringAction | ''
  onActionChange: (action: SteeringAction | '') => void
  onRefresh: () => void
  loading: boolean
}

function FilterBar({ actionFilter, onActionChange, onRefresh, loading }: FilterBarProps) {
  return (
    <div className="flex flex-wrap items-center gap-3">
      <label className="text-sm text-gray-400">Filter by action:</label>
      <select
        value={actionFilter}
        onChange={(e) => onActionChange(e.target.value as SteeringAction | '')}
        className="rounded border border-gray-700 bg-gray-800 px-3 py-1.5 text-sm text-gray-200 focus:border-indigo-500 focus:outline-none"
      >
        <option value="">All actions</option>
        {ALL_ACTIONS.map((a) => (
          <option key={a} value={a}>
            {ACTION_LABELS[a]}
          </option>
        ))}
      </select>

      <button
        onClick={onRefresh}
        disabled={loading}
        className="ml-auto rounded border border-gray-700 bg-gray-800 px-3 py-1.5 text-sm text-gray-300 hover:bg-gray-700 disabled:opacity-50"
      >
        {loading ? 'Loading…' : '↻ Refresh'}
      </button>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Audit Table
// ---------------------------------------------------------------------------

interface AuditTableProps {
  entries: AuditEntry[]
  loading: boolean
  error: string | null
}

function AuditTable({ entries, loading, error }: AuditTableProps) {
  if (loading) {
    return (
      <div className="flex items-center justify-center py-16 text-gray-500">
        <div className="h-5 w-5 animate-spin rounded-full border-2 border-gray-600 border-t-indigo-500 mr-3" />
        Loading activity log…
      </div>
    )
  }

  if (error) {
    return (
      <div className="rounded-md border border-red-800 bg-red-950/30 px-4 py-3 text-sm text-red-400">
        {error}
      </div>
    )
  }

  if (entries.length === 0) {
    return (
      <EmptyState
        icon={<span className="text-4xl">🔧</span>}
        heading="No steering actions yet"
        description="Steering actions (pause, resume, abort, redirect, retry, trust tier changes) will appear here once the pipeline is active."
        data-testid="activity-log-empty-state"
      />
    )
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-gray-800">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-800 bg-gray-900/60">
            <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-gray-500">
              Time
            </th>
            <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-gray-500">
              Task ID
            </th>
            <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-gray-500">
              Action
            </th>
            <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-gray-500">
              From Stage
            </th>
            <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-gray-500">
              To Stage
            </th>
            <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-gray-500">
              Reason
            </th>
            <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-gray-500">
              Actor
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-800">
          {entries.map((entry) => (
            <tr
              key={entry.id}
              className="bg-gray-900 transition-colors hover:bg-gray-800/50"
            >
              <td className="whitespace-nowrap px-4 py-3 text-gray-400" title={formatAbsoluteTime(entry.timestamp)}>
                {formatRelativeTime(entry.timestamp)}
              </td>
              <td className="px-4 py-3">
                <span
                  className="cursor-help font-mono text-xs text-indigo-400"
                  title={entry.task_id}
                >
                  {shortId(entry.task_id)}
                </span>
              </td>
              <td className="px-4 py-3">
                <ActionBadge action={entry.action} />
              </td>
              <td className="px-4 py-3 text-gray-400">
                {entry.from_stage ? (
                  <span className="rounded bg-gray-800 px-1.5 py-0.5 font-mono text-xs">
                    {entry.from_stage}
                  </span>
                ) : (
                  <span className="text-gray-600">—</span>
                )}
              </td>
              <td className="px-4 py-3 text-gray-400">
                {entry.to_stage ? (
                  <span className="rounded bg-gray-800 px-1.5 py-0.5 font-mono text-xs">
                    {entry.to_stage}
                  </span>
                ) : (
                  <span className="text-gray-600">—</span>
                )}
              </td>
              <td className="max-w-xs px-4 py-3 text-gray-300">
                {entry.reason ? (
                  <span className="line-clamp-2" title={entry.reason}>
                    {entry.reason}
                  </span>
                ) : (
                  <span className="text-gray-600">—</span>
                )}
              </td>
              <td className="px-4 py-3 text-gray-400">
                <span className="rounded bg-gray-800 px-1.5 py-0.5 text-xs">{entry.actor}</span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Pagination Controls
// ---------------------------------------------------------------------------

interface PaginationProps {
  page: number
  hasMore: boolean
  total: number
  onPrev: () => void
  onNext: () => void
  loading: boolean
}

function Pagination({ page, hasMore, total, onPrev, onNext, loading }: PaginationProps) {
  const start = page * PAGE_SIZE + 1
  const end = page * PAGE_SIZE + total

  return (
    <div className="flex items-center justify-between text-sm text-gray-500">
      <span>
        {total === 0 ? 'No entries' : `Showing ${start}–${end}`}
        {hasMore ? '+' : ''}
      </span>
      <div className="flex gap-2">
        <button
          onClick={onPrev}
          disabled={page === 0 || loading}
          className="rounded border border-gray-700 bg-gray-800 px-3 py-1.5 text-gray-300 hover:bg-gray-700 disabled:cursor-not-allowed disabled:opacity-40"
        >
          ← Previous
        </button>
        <button
          onClick={onNext}
          disabled={!hasMore || loading}
          className="rounded border border-gray-700 bg-gray-800 px-3 py-1.5 text-gray-300 hover:bg-gray-700 disabled:cursor-not-allowed disabled:opacity-40"
        >
          Next →
        </button>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------

export function SteeringActivityLog() {
  const [entries, setEntries] = useState<AuditEntry[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [page, setPage] = useState(0)
  const [actionFilter, setActionFilter] = useState<SteeringAction | ''>('')
  const [hasMore, setHasMore] = useState(false)

  const fetchEntries = useCallback(
    async (p: number, filter: SteeringAction | '') => {
      setLoading(true)
      setError(null)
      try {
        const params = new URLSearchParams({
          limit: String(PAGE_SIZE),
          offset: String(p * PAGE_SIZE),
        })
        if (filter) params.set('action', filter)

        const res = await fetch(`/api/v1/dashboard/steering/audit?${params}`)
        if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`)

        const data: AuditEntry[] = await res.json()
        setEntries(data)
        // If we got a full page, there may be more
        setHasMore(data.length === PAGE_SIZE)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load audit log')
      } finally {
        setLoading(false)
      }
    },
    [],
  )

  // Fetch on mount and whenever page/filter changes
  useEffect(() => {
    fetchEntries(page, actionFilter)
  }, [fetchEntries, page, actionFilter])

  const handleActionChange = useCallback((action: SteeringAction | '') => {
    setActionFilter(action)
    setPage(0)
  }, [])

  const handleRefresh = useCallback(() => {
    fetchEntries(page, actionFilter)
  }, [fetchEntries, page, actionFilter])

  const handlePrev = useCallback(() => setPage((p) => Math.max(0, p - 1)), [])
  const handleNext = useCallback(() => setPage((p) => p + 1), [])

  return (
    <div className="mx-auto max-w-7xl px-6 py-6 space-y-6" data-component="SteeringActivityLog">
      {/* Page header */}
      <div className="flex items-center gap-3">
        <span className="text-2xl">🔧</span>
        <div>
          <h2 className="text-xl font-semibold text-gray-100">Steering Activity Log</h2>
          <p className="text-sm text-gray-500 mt-0.5">
            Full history of all pipeline steering actions — pause, resume, abort, redirect, retry,
            and trust tier changes.
          </p>
        </div>
      </div>

      {/* Filter bar */}
      <FilterBar
        actionFilter={actionFilter}
        onActionChange={handleActionChange}
        onRefresh={handleRefresh}
        loading={loading}
      />

      {/* Audit table */}
      <AuditTable entries={entries} loading={loading} error={error} />

      {/* Pagination */}
      {!loading && !error && (
        <Pagination
          page={page}
          hasMore={hasMore}
          total={entries.length}
          onPrev={handlePrev}
          onNext={handleNext}
          loading={loading}
        />
      )}
    </div>
  )
}
