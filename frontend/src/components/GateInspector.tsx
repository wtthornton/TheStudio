/** Gate Inspector — chronological gate transitions with filtering and health metrics.
 * S2.F7: List view, S2.F8: Detail view, S2.F9: Filter bar, S2.F10: Health metrics
 */

import { useState, useEffect, useCallback } from 'react'
import { PIPELINE_STAGES } from '../lib/constants'
import { fetchGates, fetchGateMetrics } from '../lib/api'
import type { GateEvidenceRead, GateMetrics } from '../lib/api'
import { useRepoContext } from '../contexts/RepoContext'

// --- Filter Bar (S2.F9) ---

interface FilterState {
  result: string // '' | 'pass' | 'fail'
  stage: string
  taskId: string
}

function GateFilterBar({ filters, onChange }: { filters: FilterState; onChange: (f: FilterState) => void }) {
  return (
    <div className="flex flex-wrap items-center gap-2 border-b border-gray-700 px-4 py-2" data-testid="gate-filter-bar">
      {/* Pass/Fail toggle */}
      <div className="flex rounded border border-gray-600 text-xs">
        <button
          className={`px-2 py-1 ${filters.result === '' ? 'bg-gray-700 text-gray-200' : 'text-gray-400'}`}
          onClick={() => onChange({ ...filters, result: '' })}
        >All</button>
        <button
          className={`px-2 py-1 ${filters.result === 'pass' ? 'bg-[rgba(22,163,74,0.2)] text-green-500' : 'text-gray-400'}`}
          onClick={() => onChange({ ...filters, result: 'pass' })}
        >Pass</button>
        <button
          className={`px-2 py-1 ${filters.result === 'fail' ? 'bg-[rgba(239,68,68,0.2)] text-red-500' : 'text-gray-400'}`}
          onClick={() => onChange({ ...filters, result: 'fail' })}
        >Fail</button>
      </div>

      {/* Stage selector */}
      <select
        className="rounded border border-gray-600 bg-gray-800 px-2 py-1 text-xs text-gray-300"
        value={filters.stage}
        onChange={(e) => onChange({ ...filters, stage: e.target.value })}
      >
        <option value="">All stages</option>
        {PIPELINE_STAGES.map((s) => (
          <option key={s.id} value={s.id}>{s.label}</option>
        ))}
      </select>

      {/* Task ID filter */}
      <input
        type="text"
        placeholder="Task ID…"
        className="rounded border border-gray-600 bg-gray-800 px-2 py-1 text-xs text-gray-300 placeholder-gray-500 w-32"
        value={filters.taskId}
        onChange={(e) => onChange({ ...filters, taskId: e.target.value })}
      />
    </div>
  )
}

// --- Health Metrics Panel (S2.F10) ---

function GateHealthMetrics({ metrics }: { metrics: GateMetrics | null }) {
  if (!metrics) return null

  return (
    <div className="grid grid-cols-4 gap-3 border-b border-gray-700 px-4 py-3" data-testid="gate-health-metrics">
      <div className="text-center">
        <div className="text-xs text-gray-500">Pass Rate</div>
        <div className="text-sm font-medium text-emerald-400">
          {metrics.pass_rate != null ? `${Math.round(metrics.pass_rate * 100)}%` : '—'}
        </div>
      </div>
      <div className="text-center">
        <div className="text-xs text-gray-500">Avg Issues</div>
        <div className="text-sm font-medium text-amber-400">
          {metrics.avg_issues != null ? metrics.avg_issues.toFixed(1) : '—'}
        </div>
      </div>
      <div className="text-center">
        <div className="text-xs text-gray-500">Top Failure</div>
        <div className="text-sm font-medium text-red-400 truncate">
          {metrics.top_failure_type ?? '—'}
        </div>
      </div>
      <div className="text-center">
        <div className="text-xs text-gray-500">Loopback Rate</div>
        <div className="text-sm font-medium text-purple-400">
          {metrics.loopback_rate != null ? `${Math.round(metrics.loopback_rate * 100)}%` : '—'}
        </div>
      </div>
    </div>
  )
}

// --- Gate Detail View (S2.F8) ---

function GateDetail({ gate }: { gate: GateEvidenceRead }) {
  const checks = Array.isArray(gate.checks) ? gate.checks : []

  return (
    <div className="space-y-2 border-t border-gray-700 px-4 py-3 bg-gray-800/50" data-testid="gate-detail">
      <div className="grid grid-cols-2 gap-2 text-xs">
        <div>
          <span className="text-gray-500">Stage:</span>{' '}
          <span className="text-gray-300">{gate.stage}</span>
        </div>
        <div>
          <span className="text-gray-500">Result:</span>{' '}
          <span className={gate.result === 'pass' ? 'text-emerald-400' : 'text-red-400'}>
            {gate.result.toUpperCase()}
          </span>
        </div>
        {gate.defect_category && (
          <div>
            <span className="text-gray-500">Defect:</span>{' '}
            <span className="text-amber-400">{gate.defect_category}</span>
          </div>
        )}
        <div>
          <span className="text-gray-500">Time:</span>{' '}
          <span className="text-gray-300">{new Date(gate.created_at).toLocaleString()}</span>
        </div>
      </div>

      {/* Checks */}
      {checks.length > 0 && (
        <div className="space-y-1">
          <div className="text-xs font-medium text-gray-400">Checks ({checks.length})</div>
          {checks.map((check, i) => (
            <div key={i} className="flex items-start gap-2 rounded bg-gray-900 px-2 py-1 text-xs">
              <span className={String(check.result) === 'passed' ? 'text-emerald-400' : 'text-red-400'}>
                {String(check.result) === 'passed' ? '✓' : '✗'}
              </span>
              <div className="flex-1">
                <span className="text-gray-300">{String(check.name ?? `Check ${i + 1}`)}</span>
                {check.details != null && (
                  <div className="text-gray-500 mt-0.5">{String(check.details)}</div>
                )}
              </div>
              {check.duration_ms != null && (
                <span className="text-gray-600">{Number(check.duration_ms)}ms</span>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Evidence artifact */}
      {gate.evidence_artifact && (
        <div>
          <div className="text-xs font-medium text-gray-400 mb-1">Evidence</div>
          <pre className="rounded bg-gray-900 p-2 text-xs text-gray-400 overflow-x-auto max-h-40">
            {JSON.stringify(gate.evidence_artifact, null, 2)}
          </pre>
        </div>
      )}
    </div>
  )
}

// --- Main Gate Inspector ---

export function GateInspector() {
  const { selectedRepo } = useRepoContext()
  const [gates, setGates] = useState<GateEvidenceRead[]>([])
  const [metrics, setMetrics] = useState<GateMetrics | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [filters, setFilters] = useState<FilterState>({ result: '', stage: '', taskId: '' })
  const [page, setPage] = useState(0)
  const PAGE_SIZE = 20

  const loadData = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [gateData, metricData] = await Promise.all([
        fetchGates({
          offset: page * PAGE_SIZE,
          limit: PAGE_SIZE,
          result: filters.result || undefined,
          stage: filters.stage || undefined,
          task_id: filters.taskId || undefined,
          repo: selectedRepo,
        }),
        fetchGateMetrics(24, selectedRepo).catch(() => null),
      ])
      setGates(gateData.items)
      setMetrics(metricData)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load gates')
    } finally {
      setLoading(false)
    }
  }, [page, filters, selectedRepo])

  useEffect(() => { void loadData() }, [loadData])

  return (
    <div className="rounded-lg border border-gray-700 bg-gray-900" data-testid="gate-inspector" data-tour="gate-inspector" data-component="GateInspector">
      <div className="flex items-center justify-between border-b border-gray-700 px-4 py-2">
        <h3 className="text-sm font-semibold">Gate Inspector</h3>
        <button onClick={loadData} className="text-xs text-blue-400 hover:underline">Refresh</button>
      </div>

      <GateHealthMetrics metrics={metrics} />
      <GateFilterBar filters={filters} onChange={(f) => { setFilters(f); setPage(0) }} />

      {loading ? (
        <div className="flex items-center justify-center py-8">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-gray-600 border-t-blue-400" />
        </div>
      ) : error ? (
        <div className="px-4 py-4 text-center text-sm text-red-400">
          {error}
          <button onClick={loadData} className="ml-2 text-blue-400 hover:underline">Retry</button>
        </div>
      ) : gates.length === 0 ? (
        <div className="px-4 py-8 text-center text-sm text-gray-500" data-testid="gate-inspector-empty">
          No gate events found
        </div>
      ) : (
        <div>
          {/* S2.F7: List view */}
          <ul data-testid="gate-list">
            {gates.map((gate) => {
              const isExpanded = expandedId === gate.id
              const issueCount = Array.isArray(gate.checks)
                ? gate.checks.filter((c) => String(c.result) !== 'passed').length
                : 0

              return (
                <li key={gate.id}>
                  <button
                    className="flex w-full items-center gap-3 px-4 py-2 text-left hover:bg-gray-800/50 transition-colors"
                    onClick={() => setExpandedId(isExpanded ? null : gate.id)}
                    data-testid="gate-list-item"
                  >
                    {/* Pass/Fail icon */}
                    <span className={`shrink-0 text-sm ${gate.result === 'pass' ? 'text-emerald-400' : 'text-red-400'}`}>
                      {gate.result === 'pass' ? '✓' : '✗'}
                    </span>

                    {/* Task ID */}
                    <span className="w-20 truncate text-xs text-gray-300 font-mono">
                      {gate.task_id.slice(0, 8)}
                    </span>

                    {/* Stage transition */}
                    <span className="text-xs text-gray-400">{gate.stage}</span>

                    {/* Timestamp */}
                    <span className="ml-auto text-xs text-gray-500">
                      {new Date(gate.created_at).toLocaleTimeString('en-US', { hour12: false })}
                    </span>

                    {/* Issue count */}
                    {issueCount > 0 && (
                      <span className="rounded bg-[rgba(239,68,68,0.2)] px-1.5 py-0.5 text-xs text-red-500">
                        {issueCount} issues
                      </span>
                    )}

                    <span className="text-gray-600 text-xs">{isExpanded ? '▾' : '▸'}</span>
                  </button>

                  {/* S2.F8: Expanded detail */}
                  {isExpanded && <GateDetail gate={gate} />}
                </li>
              )
            })}
          </ul>

          {/* Pagination */}
          <div className="flex items-center justify-between border-t border-gray-700 px-4 py-2">
            <button
              onClick={() => setPage((p) => Math.max(0, p - 1))}
              disabled={page === 0}
              className="text-xs text-blue-400 disabled:text-gray-600"
            >Previous</button>
            <span className="text-xs text-gray-500">Page {page + 1}</span>
            <button
              onClick={() => setPage((p) => p + 1)}
              disabled={gates.length < PAGE_SIZE}
              className="text-xs text-blue-400 disabled:text-gray-600"
            >Next</button>
          </div>
        </div>
      )}
    </div>
  )
}
