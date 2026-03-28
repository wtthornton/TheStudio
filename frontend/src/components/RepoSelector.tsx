/** RepoSelector — dropdown to filter the dashboard by repository (Epic 41, Story 41.4).
 *
 * Fetches the list of registered repos from GET /admin/repos and renders a
 * <select> with an "All Repos" option at the top. The selected value is stored
 * in RepoContext so all dashboard tabs can read it.
 *
 * Falls back gracefully if the admin API is unavailable (e.g. in tests or
 * before a second repo is registered).
 */

import { useEffect, useState } from 'react'
import { fetchAdminRepos } from '../lib/api'
import type { AdminRepoItem } from '../lib/api'
import { useRepoContext } from '../contexts/RepoContext'

export function RepoSelector() {
  const { selectedRepo, setSelectedRepo } = useRepoContext()
  const [repos, setRepos] = useState<AdminRepoItem[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    fetchAdminRepos()
      .then((data) => {
        if (!cancelled) {
          setRepos(data.repos)
          setLoading(false)
        }
      })
      .catch(() => {
        if (!cancelled) setLoading(false)
      })
    return () => { cancelled = true }
  }, [])

  // Don't render if only 0 or 1 repos (no switching needed)
  if (loading || repos.length <= 1) return null

  return (
    <div className="flex items-center gap-1.5" data-testid="repo-selector">
      <span className="text-xs text-gray-500 shrink-0">Repo:</span>
      <select
        value={selectedRepo ?? ''}
        onChange={(e) => setSelectedRepo(e.target.value || null)}
        className="rounded border border-gray-700 bg-gray-800 px-2 py-1 text-xs text-gray-300 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:ring-offset-gray-950"
        data-testid="repo-selector-dropdown"
      >
        <option value="">All Repos</option>
        {repos.map((r) => {
          const fullName = `${r.owner}/${r.repo}`
          return (
            <option key={r.id} value={fullName}>
              {fullName}
              {r.status !== 'ACTIVE' ? ` (${r.status.toLowerCase()})` : ''}
            </option>
          )
        })}
      </select>
    </div>
  )
}
