/**
 * RepoSettings — Epic 41, Stories 41.11 + 41.14.
 *
 * Per-repo configuration dashboard panel with fleet health summary.
 *
 * Sections:
 *   1. Fleet Health Table — per-repo: name, tier, status, active workflows,
 *      last task timestamp (GET /admin/repos/health — Story 41.14)
 *   2. Repo Configuration — select a repo from the list and edit its config
 *      using RepoConfigForm (PATCH /admin/repos/{id}/profile — Story 41.11)
 *
 * Accessible from the "Repos" tab added to App.tsx navigation.
 */

import { useEffect, useState, useCallback } from 'react'
import type { AdminRepoItem, AdminRepoDetail, RepoHealthItem } from '../lib/api'
import { fetchAdminRepos, fetchAdminRepoDetail, fetchReposHealth } from '../lib/api'
import { RepoConfigForm } from './RepoConfigForm'
import { EmptyState } from './EmptyState'

// Repo icon for empty state
function RepoIcon() {
  return (
    <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M9 19c-5 1.5-5-2.5-7-3m14 6v-3.87a3.37 3.37 0 0 0-.94-2.61c3.14-.35 6.44-1.54 6.44-7A5.44 5.44 0 0 0 20 4.77 5.07 5.07 0 0 0 19.91 1S18.73.65 16 2.48a13.38 13.38 0 0 0-7 0C6.27.65 5.09 1 5.09 1A5.07 5.07 0 0 0 5 4.77a5.44 5.44 0 0 0-1.5 3.78c0 5.42 3.3 6.61 6.44 7A3.37 3.37 0 0 0 9 18.13V22" />
    </svg>
  )
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function TierBadge({ tier }: { tier: string }) {
  const colors: Record<string, string> = {
    OBSERVE: 'bg-gray-700 text-gray-300',
    observe: 'bg-gray-700 text-gray-300',
    SUGGEST: 'bg-blue-900 text-blue-300',
    suggest: 'bg-blue-900 text-blue-300',
    EXECUTE: 'bg-green-900 text-green-300',
    execute: 'bg-green-900 text-green-300',
  }
  return (
    <span
      className={`inline-block rounded px-1.5 py-0.5 text-xs font-medium ${colors[tier] ?? 'bg-gray-700 text-gray-300'}`}
    >
      {tier.toUpperCase()}
    </span>
  )
}

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    ACTIVE: 'text-green-400',
    active: 'text-green-400',
    PAUSED: 'text-yellow-400',
    paused: 'text-yellow-400',
    DISABLED: 'text-red-400',
    disabled: 'text-red-400',
  }
  return (
    <span className={`text-xs font-medium ${colors[status] ?? 'text-gray-400'}`}>
      {status.toUpperCase()}
    </span>
  )
}

function HealthDot({ health }: { health: string }) {
  const colors: Record<string, string> = {
    ok: 'bg-green-500',
    degraded: 'bg-red-500',
    idle: 'bg-yellow-500',
  }
  return (
    <span
      className={`inline-block h-2 w-2 rounded-full ${colors[health] ?? 'bg-gray-500'}`}
      title={health}
    />
  )
}

function formatRelativeTime(isoStr: string | null): string {
  if (!isoStr) return '—'
  const date = new Date(isoStr)
  const diffMs = Date.now() - date.getTime()
  const diffMins = Math.floor(diffMs / 60_000)
  if (diffMins < 1) return 'just now'
  if (diffMins < 60) return `${diffMins}m ago`
  const diffHrs = Math.floor(diffMins / 60)
  if (diffHrs < 24) return `${diffHrs}h ago`
  const diffDays = Math.floor(diffHrs / 24)
  return `${diffDays}d ago`
}

// ---------------------------------------------------------------------------
// Fleet Health Table (41.14)
// ---------------------------------------------------------------------------

function FleetHealthTable({
  health,
  onSelectRepo,
  selectedRepoId,
}: {
  health: RepoHealthItem[]
  onSelectRepo: (id: string) => void
  selectedRepoId: string | null
}) {
  if (health.length === 0) {
    return (
      <EmptyState
        icon={<RepoIcon />}
        heading="No repositories registered"
        description="Connect a GitHub repository to start processing issues into evidence-backed draft PRs. You'll need your GitHub App installation ID."
        primaryAction={{ label: 'Register Repository', href: '/admin/ui/repos' }}
        secondaryAction={{ label: 'View onboarding guide', href: '/docs/onboarding-new-repo.md' }}
        data-testid="repos-empty"
      />
    )
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs">
        <thead>
          <tr className="border-b border-gray-700 text-gray-400">
            <th className="py-2 pr-4 text-left font-medium">Health</th>
            <th className="py-2 pr-4 text-left font-medium">Repository</th>
            <th className="py-2 pr-4 text-left font-medium">Tier</th>
            <th className="py-2 pr-4 text-left font-medium">Status</th>
            <th className="py-2 pr-4 text-right font-medium">Active</th>
            <th className="py-2 text-right font-medium">Last Task</th>
          </tr>
        </thead>
        <tbody>
          {health.map((repo) => (
            <tr
              key={repo.id}
              onClick={() => onSelectRepo(repo.id)}
              className={`cursor-pointer border-b border-gray-800 hover:bg-gray-800 transition-colors ${
                selectedRepoId === repo.id ? 'bg-gray-800' : ''
              }`}
            >
              <td className="py-2 pr-4">
                <HealthDot health={repo.health} />
              </td>
              <td className="py-2 pr-4 font-mono text-gray-200">
                {repo.full_name}
              </td>
              <td className="py-2 pr-4">
                <TierBadge tier={repo.tier} />
              </td>
              <td className="py-2 pr-4">
                <StatusBadge status={repo.status} />
              </td>
              <td className="py-2 pr-4 text-right text-gray-300">
                {repo.active_workflows}
              </td>
              <td className="py-2 text-right text-gray-400">
                {formatRelativeTime(repo.last_task_at)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main RepoSettings panel
// ---------------------------------------------------------------------------

export function RepoSettings() {
  const [repos, setRepos] = useState<AdminRepoItem[]>([])
  const [health, setHealth] = useState<RepoHealthItem[]>([])
  const [selectedRepoId, setSelectedRepoId] = useState<string | null>(null)
  const [selectedRepoDetail, setSelectedRepoDetail] = useState<AdminRepoDetail | null>(null)
  const [loadingHealth, setLoadingHealth] = useState(true)
  const [loadingDetail, setLoadingDetail] = useState(false)
  const [healthError, setHealthError] = useState<string | null>(null)

  const loadData = useCallback(async () => {
    setLoadingHealth(true)
    setHealthError(null)
    try {
      const [reposResp, healthResp] = await Promise.all([
        fetchAdminRepos(),
        fetchReposHealth(),
      ])
      setRepos(reposResp.repos)
      setHealth(healthResp.repos)
    } catch {
      setHealthError('Failed to load repository data.')
    } finally {
      setLoadingHealth(false)
    }
  }, [])

  useEffect(() => {
    void loadData()
  }, [loadData])

  useEffect(() => {
    if (!selectedRepoId) {
      setSelectedRepoDetail(null)
      return
    }
    setLoadingDetail(true)
    fetchAdminRepoDetail(selectedRepoId)
      .then((detail) => {
        setSelectedRepoDetail(detail)
        setLoadingDetail(false)
      })
      .catch(() => {
        setSelectedRepoDetail(null)
        setLoadingDetail(false)
      })
  }, [selectedRepoId])

  function handleSelectRepo(id: string) {
    setSelectedRepoId((prev) => (prev === id ? null : id))
  }

  async function handleSaved() {
    // Refresh health data after a config save
    await loadData()
    // Re-fetch detail for the selected repo
    if (selectedRepoId) {
      const detail = await fetchAdminRepoDetail(selectedRepoId)
      setSelectedRepoDetail(detail)
    }
  }

  return (
    <div className="mx-auto max-w-5xl px-6 py-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-100">Repository Settings</h2>
        <button
          onClick={() => void loadData()}
          className="rounded bg-gray-700 px-3 py-1.5 text-xs text-gray-300 hover:bg-gray-600"
        >
          ↺ Refresh
        </button>
      </div>

      {/* Fleet Health Table (Story 41.14) */}
      <div className="rounded-lg border border-gray-700 bg-gray-900 p-4">
        <h3 className="text-sm font-semibold text-gray-200 mb-3">Fleet Health</h3>
        <div className="mb-2 flex items-center gap-4 text-xs text-gray-500">
          <span><span className="inline-block h-2 w-2 rounded-full bg-green-500 mr-1" />ok — active with tasks</span>
          <span><span className="inline-block h-2 w-2 rounded-full bg-yellow-500 mr-1" />idle — no recent activity</span>
          <span><span className="inline-block h-2 w-2 rounded-full bg-red-500 mr-1" />degraded — paused or disabled</span>
        </div>
        {loadingHealth ? (
          <p className="text-xs text-gray-500">Loading…</p>
        ) : healthError ? (
          <p className="text-xs text-red-400">{healthError}</p>
        ) : (
          <FleetHealthTable
            health={health}
            onSelectRepo={handleSelectRepo}
            selectedRepoId={selectedRepoId}
          />
        )}
        {/* empty state rendered by FleetHealthTable when repos.length === 0 */}
      </div>

      {/* Per-repo config editor (Story 41.11) */}
      {selectedRepoId && (
        <div className="rounded-lg border border-gray-700 bg-gray-900 p-4">
          <h3 className="text-sm font-semibold text-gray-200 mb-3">
            Repo Configuration{' '}
            <span className="text-xs text-gray-500 font-normal">
              — click another row to switch repos
            </span>
          </h3>
          {loadingDetail ? (
            <p className="text-xs text-gray-500">Loading configuration…</p>
          ) : selectedRepoDetail ? (
            <RepoConfigForm repo={selectedRepoDetail} onSaved={handleSaved} />
          ) : (
            <p className="text-xs text-red-400">Failed to load repo configuration.</p>
          )}
        </div>
      )}

      {!selectedRepoId && repos.length > 0 && (
        <p className="text-xs text-gray-500 text-center">
          Click a repository row above to view and edit its configuration.
        </p>
      )}
    </div>
  )
}
