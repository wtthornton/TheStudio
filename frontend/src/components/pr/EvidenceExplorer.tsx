/** EvidenceExplorer — Tabbed viewer for PR evidence JSON.
 *
 * Epic 38, Story 38.8.
 *
 * Tabs:
 *  - Evidence  — Task summary (status, tier, PR link, loopbacks, files changed)
 *  - Intent    — Goal, acceptance criteria, constraints, non-goals
 *  - Gates     — Verification / QA gate results and defect summary
 *  - Cost      — Token and USD cost breakdown by stage
 *  - Diff      — Link out to GitHub PR diff (or placeholder when no PR)
 *
 * Consumes GET /api/v1/dashboard/tasks/:id/evidence (EvidencePayload).
 * Loading states, error handling, and empty states are all handled.
 */

import { useState, useEffect, useCallback } from 'react'
import {
  fetchTaskEvidence,
  type EvidencePayload,
  type EvidenceGateResult,
  type EvidenceCostEntry,
  type EvidenceProvenanceEntry,
} from '../../lib/api'
import { useGitHubEvents, type PrStatus, type ReviewStatus, type CheckStatus } from '../../hooks/useGitHubEvents'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface EvidenceExplorerProps {
  taskId: string
  /** Called when the user dismisses or closes the explorer (optional). */
  onClose?: () => void
}

type Tab = 'evidence' | 'intent' | 'gates' | 'cost' | 'diff'

// ---------------------------------------------------------------------------
// Small helper components
// ---------------------------------------------------------------------------

function EmptyState({ label }: { label: string }) {
  return (
    <div className="py-12 text-center text-gray-500 text-sm">
      {label}
    </div>
  )
}

function Field({ label, value }: { label: string; value: string | number | null | undefined }) {
  return (
    <div className="flex gap-2 text-sm">
      <span className="text-gray-400 shrink-0 w-36">{label}</span>
      <span className="text-gray-100 break-all">{value ?? <span className="text-gray-600">—</span>}</span>
    </div>
  )
}

function Badge({ text, color }: { text: string; color: 'green' | 'red' | 'yellow' | 'blue' | 'gray' }) {
  const colors: Record<string, string> = {
    green: 'bg-green-900 text-green-300',
    red: 'bg-red-900 text-red-300',
    yellow: 'bg-yellow-900 text-yellow-300',
    blue: 'bg-blue-900 text-blue-300',
    gray: 'bg-gray-700 text-gray-300',
  }
  return (
    <span className={`rounded px-1.5 py-0.5 text-xs font-medium ${colors[color]}`}>
      {text}
    </span>
  )
}

function SectionTitle({ children }: { children: React.ReactNode }) {
  return <h3 className="text-xs uppercase tracking-widest text-gray-500 mb-3">{children}</h3>
}

// ---------------------------------------------------------------------------
// Tab panels
// ---------------------------------------------------------------------------

function EvidenceTab({ payload }: { payload: EvidencePayload }) {
  const s = payload.task_summary

  const tierColor: Record<string, 'blue' | 'yellow' | 'green'> = {
    observe: 'blue',
    suggest: 'yellow',
    execute: 'green',
  }

  return (
    <div className="space-y-6">
      {/* Task summary */}
      <div>
        <SectionTitle>Task Summary</SectionTitle>
        <div className="space-y-2">
          <Field label="Task ID" value={s.taskpacket_id} />
          <Field label="Correlation ID" value={s.correlation_id} />
          <Field label="Repository" value={s.repo} />
          <Field label="Issue" value={s.issue_title ? `#${s.issue_id} — ${s.issue_title}` : `#${s.issue_id}`} />
          <div className="flex gap-2 text-sm">
            <span className="text-gray-400 shrink-0 w-36">Status</span>
            <Badge text={s.status} color="gray" />
          </div>
          {s.trust_tier && (
            <div className="flex gap-2 text-sm">
              <span className="text-gray-400 shrink-0 w-36">Trust tier</span>
              <Badge text={s.trust_tier} color={tierColor[s.trust_tier] ?? 'gray'} />
            </div>
          )}
          <Field label="Loopbacks" value={s.loopback_count} />
          <Field label="Created" value={s.created_at ? new Date(s.created_at).toLocaleString() : null} />
          <Field label="Updated" value={s.updated_at ? new Date(s.updated_at).toLocaleString() : null} />
        </div>
      </div>

      {/* PR link */}
      {s.pr_number && (
        <div>
          <SectionTitle>Pull Request</SectionTitle>
          <div className="space-y-2">
            <Field label="PR number" value={`#${s.pr_number}`} />
            {s.pr_url && (
              <div className="flex gap-2 text-sm">
                <span className="text-gray-400 shrink-0 w-36">PR URL</span>
                <a
                  href={s.pr_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-400 hover:text-blue-300 hover:underline break-all"
                >
                  {s.pr_url}
                </a>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Files changed */}
      <div>
        <SectionTitle>Files Changed ({payload.files_changed.length})</SectionTitle>
        {payload.files_changed.length === 0 ? (
          <EmptyState label="No files recorded yet." />
        ) : (
          <ul className="space-y-1">
            {payload.files_changed.map((f) => (
              <li key={f} className="text-sm font-mono text-gray-300 bg-gray-800 rounded px-2 py-1">
                {f}
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* Schema metadata */}
      <div className="text-xs text-gray-600 border-t border-gray-700 pt-3 space-y-1">
        <div>Schema version: {payload.schema_version}</div>
        {payload.generated_at && (
          <div>Generated: {new Date(payload.generated_at).toLocaleString()}</div>
        )}
      </div>
    </div>
  )
}

function IntentTab({ payload }: { payload: EvidencePayload }) {
  const intent = payload.intent
  if (!intent) {
    return <EmptyState label="Intent specification not available for this task." />
  }

  return (
    <div className="space-y-6">
      <div>
        <SectionTitle>Goal (v{intent.version})</SectionTitle>
        <p className="text-sm text-gray-200 leading-relaxed">{intent.goal}</p>
      </div>

      {intent.acceptance_criteria.length > 0 && (
        <div>
          <SectionTitle>Acceptance Criteria</SectionTitle>
          <ul className="space-y-1 list-disc list-inside text-sm text-gray-300">
            {intent.acceptance_criteria.map((c, i) => (
              <li key={i}>{c}</li>
            ))}
          </ul>
        </div>
      )}

      {intent.constraints.length > 0 && (
        <div>
          <SectionTitle>Constraints</SectionTitle>
          <ul className="space-y-1 list-disc list-inside text-sm text-gray-300">
            {intent.constraints.map((c, i) => (
              <li key={i}>{c}</li>
            ))}
          </ul>
        </div>
      )}

      {intent.non_goals.length > 0 && (
        <div>
          <SectionTitle>Non-Goals</SectionTitle>
          <ul className="space-y-1 list-disc list-inside text-sm text-gray-400">
            {intent.non_goals.map((g, i) => (
              <li key={i}>{g}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}

function GatesTab({ payload }: { payload: EvidencePayload }) {
  const gates = payload.gate_results
  if (!gates) {
    return <EmptyState label="Gate results not available for this task." />
  }

  return (
    <div className="space-y-6">
      {/* Overall result */}
      <div>
        <SectionTitle>Overall</SectionTitle>
        <div className="flex flex-wrap gap-3">
          <div className="flex items-center gap-2 text-sm">
            <span className="text-gray-400">Verification</span>
            <Badge
              text={gates.verification_passed ? 'PASS' : 'FAIL'}
              color={gates.verification_passed ? 'green' : 'red'}
            />
          </div>
          {gates.qa_passed !== null && (
            <div className="flex items-center gap-2 text-sm">
              <span className="text-gray-400">QA</span>
              <Badge
                text={gates.qa_passed ? 'PASS' : 'FAIL'}
                color={gates.qa_passed ? 'green' : 'red'}
              />
            </div>
          )}
          {gates.defect_count > 0 && (
            <div className="flex items-center gap-2 text-sm">
              <span className="text-gray-400">Defects</span>
              <Badge text={String(gates.defect_count)} color="red" />
            </div>
          )}
        </div>

        {gates.defect_categories.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1">
            {gates.defect_categories.map((cat) => (
              <Badge key={cat} text={cat} color="yellow" />
            ))}
          </div>
        )}
      </div>

      {/* Per-check results */}
      {gates.checks.length > 0 && (
        <div>
          <SectionTitle>Checks ({gates.checks.length})</SectionTitle>
          <div className="space-y-2">
            {gates.checks.map((check: EvidenceGateResult, i: number) => (
              <div key={i} className="bg-gray-800 rounded p-3 space-y-1">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-200">{check.name}</span>
                  <Badge text={check.passed ? 'PASS' : 'FAIL'} color={check.passed ? 'green' : 'red'} />
                </div>
                {check.details && (
                  <p className="text-xs text-gray-400">{check.details}</p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {gates.checks.length === 0 && (
        <EmptyState label="No individual gate checks recorded." />
      )}
    </div>
  )
}

function CostTab({ payload }: { payload: EvidencePayload }) {
  const cost = payload.cost_breakdown
  const provenance = payload.provenance

  if (!cost && !provenance) {
    return <EmptyState label="Cost and provenance data not available for this task." />
  }

  return (
    <div className="space-y-6">
      {/* Cost summary */}
      {cost && (
        <div>
          <SectionTitle>Cost Summary</SectionTitle>
          <div className="grid grid-cols-3 gap-3 mb-4">
            <div className="bg-gray-800 rounded p-3 text-center">
              <div className="text-lg font-semibold text-gray-100">
                ${cost.total_cost_usd.toFixed(4)}
              </div>
              <div className="text-xs text-gray-400 mt-1">Total cost</div>
            </div>
            <div className="bg-gray-800 rounded p-3 text-center">
              <div className="text-lg font-semibold text-gray-100">
                {cost.total_tokens_in.toLocaleString()}
              </div>
              <div className="text-xs text-gray-400 mt-1">Tokens in</div>
            </div>
            <div className="bg-gray-800 rounded p-3 text-center">
              <div className="text-lg font-semibold text-gray-100">
                {cost.total_tokens_out.toLocaleString()}
              </div>
              <div className="text-xs text-gray-400 mt-1">Tokens out</div>
            </div>
          </div>

          {/* Per-entry breakdown */}
          {cost.entries.length > 0 && (
            <div>
              <SectionTitle>By Stage / Model</SectionTitle>
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-xs text-gray-500 border-b border-gray-700">
                    <th className="pb-2 font-medium">Label</th>
                    <th className="pb-2 font-medium text-right">Tokens in</th>
                    <th className="pb-2 font-medium text-right">Tokens out</th>
                    <th className="pb-2 font-medium text-right">Cost (USD)</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-800">
                  {cost.entries.map((entry: EvidenceCostEntry, i: number) => (
                    <tr key={i} className="text-gray-300">
                      <td className="py-2">{entry.label}</td>
                      <td className="py-2 text-right font-mono">{entry.tokens_in.toLocaleString()}</td>
                      <td className="py-2 text-right font-mono">{entry.tokens_out.toLocaleString()}</td>
                      <td className="py-2 text-right font-mono">${entry.cost_usd.toFixed(4)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Provenance */}
      {provenance && (
        <div>
          <SectionTitle>Provenance</SectionTitle>
          <div className="space-y-2">
            {provenance.agent_model && (
              <Field label="Agent model" value={provenance.agent_model} />
            )}
            {provenance.loopback_stages.length > 0 && (
              <div className="flex gap-2 text-sm flex-wrap">
                <span className="text-gray-400 shrink-0 w-36">Loopback stages</span>
                <div className="flex flex-wrap gap-1">
                  {provenance.loopback_stages.map((s) => (
                    <Badge key={s} text={s} color="yellow" />
                  ))}
                </div>
              </div>
            )}
          </div>

          {provenance.experts_consulted.length > 0 && (
            <div className="mt-4">
              <SectionTitle>Experts Consulted ({provenance.experts_consulted.length})</SectionTitle>
              <div className="space-y-2">
                {provenance.experts_consulted.map((exp: EvidenceProvenanceEntry, i: number) => (
                  <div key={i} className="bg-gray-800 rounded p-3 space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="text-sm text-gray-200 font-medium">{exp.name}</span>
                      {exp.version && <span className="text-xs text-gray-500">v{exp.version}</span>}
                      {exp.role && <Badge text={exp.role} color="blue" />}
                    </div>
                    {exp.policy_triggers.length > 0 && (
                      <div className="flex flex-wrap gap-1 mt-1">
                        {exp.policy_triggers.map((t) => (
                          <Badge key={t} text={t} color="gray" />
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function DiffTab({ payload }: { payload: EvidencePayload }) {
  const s = payload.task_summary

  if (!s.pr_url) {
    return (
      <div className="py-12 text-center space-y-3">
        <p className="text-gray-500 text-sm">No pull request available for this task.</p>
        <p className="text-gray-600 text-xs">
          A PR link will appear here once the agent publishes a draft pull request.
        </p>
      </div>
    )
  }

  const diffUrl = `${s.pr_url}/files`

  return (
    <div className="space-y-4">
      <div className="bg-gray-800 rounded p-4 space-y-3">
        <div className="flex items-center justify-between">
          <span className="text-sm text-gray-300">
            Pull Request <span className="font-semibold text-gray-100">#{s.pr_number}</span>
          </span>
          <a
            href={s.pr_url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs text-blue-400 hover:text-blue-300 hover:underline"
          >
            Open on GitHub ↗
          </a>
        </div>
        {payload.files_changed.length > 0 && (
          <p className="text-xs text-gray-400">
            {payload.files_changed.length} file{payload.files_changed.length !== 1 ? 's' : ''} changed
          </p>
        )}
      </div>

      <div className="flex gap-3">
        <a
          href={diffUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="flex-1 text-center py-2.5 rounded bg-gray-700 hover:bg-gray-600 text-sm text-gray-200 transition-colors"
        >
          View Diff on GitHub ↗
        </a>
        <a
          href={s.pr_url}
          target="_blank"
          rel="noopener noreferrer"
          className="flex-1 text-center py-2.5 rounded bg-gray-700 hover:bg-gray-600 text-sm text-gray-200 transition-colors"
        >
          View PR on GitHub ↗
        </a>
      </div>

      <p className="text-xs text-gray-600 text-center">
        Inline diff rendering is not available — diffs open in GitHub.
      </p>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Live PR status strip (rendered when GitHub events have arrived)
// ---------------------------------------------------------------------------

const PR_STATUS_COLOR: Record<PrStatus, string> = {
  open: 'bg-green-900 text-green-300',
  merged: 'bg-purple-900 text-purple-300',
  closed: 'bg-red-900 text-red-300',
  unknown: 'bg-gray-700 text-gray-400',
}

const REVIEW_STATUS_COLOR: Record<ReviewStatus, string> = {
  approved: 'bg-green-900 text-green-300',
  changes_requested: 'bg-orange-900 text-orange-300',
  commented: 'bg-blue-900 text-blue-300',
  dismissed: 'bg-gray-700 text-gray-400',
  none: '',
}

const CHECK_STATUS_COLOR: Record<CheckStatus, string> = {
  queued: 'bg-gray-700 text-gray-400',
  in_progress: 'bg-yellow-900 text-yellow-300',
  completed: 'bg-green-900 text-green-300',
  unknown: 'bg-gray-700 text-gray-400',
}

interface LivePrStatusProps {
  prStatus: PrStatus
  reviewStatus: ReviewStatus
  checkStatus: CheckStatus
  eventCount: number
}

function LivePrStatus({ prStatus, reviewStatus, checkStatus, eventCount }: LivePrStatusProps) {
  if (eventCount === 0) return null

  return (
    <div
      className="flex items-center gap-2 px-4 py-2 bg-gray-800 border-b border-gray-700 text-xs shrink-0"
      aria-label="Live GitHub PR status"
      data-testid="live-pr-status"
    >
      <span className="text-gray-500 shrink-0">Live:</span>

      {prStatus !== 'unknown' && (
        <span className={`rounded px-1.5 py-0.5 font-medium ${PR_STATUS_COLOR[prStatus]}`}>
          PR {prStatus}
        </span>
      )}

      {reviewStatus !== 'none' && (
        <span className={`rounded px-1.5 py-0.5 font-medium ${REVIEW_STATUS_COLOR[reviewStatus]}`}>
          {reviewStatus.replace('_', ' ')}
        </span>
      )}

      {checkStatus !== 'unknown' && (
        <span className={`rounded px-1.5 py-0.5 font-medium ${CHECK_STATUS_COLOR[checkStatus]}`}>
          CI {checkStatus.replace('_', ' ')}
        </span>
      )}

      <span className="ml-auto text-gray-600">{eventCount} event{eventCount !== 1 ? 's' : ''}</span>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export default function EvidenceExplorer({ taskId, onClose }: EvidenceExplorerProps) {
  const [activeTab, setActiveTab] = useState<Tab>('evidence')
  const [payload, setPayload] = useState<EvidencePayload | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Real-time GitHub event state via webhook bridge (Story 38.26)
  const { prStatus, reviewStatus, checkStatus, lastEvent, eventCount } = useGitHubEvents(taskId)

  const loadEvidence = useCallback(() => {
    if (!taskId) return
    setLoading(true)
    setError(null)
    fetchTaskEvidence(taskId)
      .then((data) => {
        setPayload(data)
        setLoading(false)
      })
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : 'Unknown error')
        setLoading(false)
      })
  }, [taskId])

  useEffect(() => {
    setPayload(null)
    loadEvidence()
  }, [loadEvidence])

  // Auto-refresh evidence payload when PR is merged or closed so the
  // Evidence tab (pr_number, pr_url) reflects the latest persisted state.
  useEffect(() => {
    if (lastEvent && (prStatus === 'merged' || prStatus === 'closed')) {
      loadEvidence()
    }
  }, [lastEvent, prStatus, loadEvidence])

  const tabs: { id: Tab; label: string }[] = [
    { id: 'evidence', label: 'Evidence' },
    { id: 'intent', label: 'Intent' },
    { id: 'gates', label: 'Gates' },
    { id: 'cost', label: 'Cost' },
    { id: 'diff', label: 'Diff' },
  ]

  return (
    <div className="bg-gray-900 border border-gray-700 rounded-lg overflow-hidden flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-700 shrink-0">
        <h2 className="text-sm font-semibold text-gray-100">PR Evidence Explorer</h2>
        {onClose && (
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-300 text-xs"
            aria-label="Close"
          >
            ✕
          </button>
        )}
      </div>

      {/* Tab bar */}
      <div className="flex gap-1 px-3 pt-2 border-b border-gray-700 shrink-0">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-3 py-1.5 text-sm rounded-t transition-colors ${
              activeTab === tab.id
                ? 'bg-gray-700 text-gray-100 border-b-2 border-blue-500'
                : 'text-gray-400 hover:text-gray-200'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Live PR status strip — only shown when GitHub events have arrived */}
      <LivePrStatus
        prStatus={prStatus}
        reviewStatus={reviewStatus}
        checkStatus={checkStatus}
        eventCount={eventCount}
      />

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4">
        {/* Loading state */}
        {loading && (
          <div className="py-12 text-center">
            <div className="inline-block w-6 h-6 border-2 border-gray-600 border-t-blue-500 rounded-full animate-spin mb-3" />
            <p className="text-gray-500 text-sm">Loading evidence…</p>
          </div>
        )}

        {/* Error state */}
        {!loading && error && (
          <div className="border border-red-700 bg-red-950 rounded p-4 text-sm text-red-300 space-y-1">
            <p className="font-medium">Failed to load evidence</p>
            <p className="text-red-400">{error}</p>
          </div>
        )}

        {/* Loaded state */}
        {!loading && !error && payload && (
          <>
            {activeTab === 'evidence' && <EvidenceTab payload={payload} />}
            {activeTab === 'intent' && <IntentTab payload={payload} />}
            {activeTab === 'gates' && <GatesTab payload={payload} />}
            {activeTab === 'cost' && <CostTab payload={payload} />}
            {activeTab === 'diff' && <DiffTab payload={payload} />}
          </>
        )}
      </div>
    </div>
  )
}
