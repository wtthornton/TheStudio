/** ImportModal — Browse GitHub issues and batch-import them into the pipeline.
 *
 * Epic 38, Story 38.3.
 *
 * Features:
 *  - Repo selector populated from registered admin repos (GET /github/repos),
 *    with manual text-input fallback when no repos are registered.
 *  - Label / state filters and title search.
 *  - Issue list with per-row checkboxes and select-all.
 *  - Import mode toggle: Triage (hold for human review) vs Direct (start pipeline).
 *  - "Already in pipeline" detection: duplicates are highlighted after import.
 *  - Paginated "Load more" for repos with many issues.
 */

import { useState, useCallback, useEffect, useRef } from 'react'
import {
  fetchDashboardRepos,
  fetchGitHubIssues,
  importGitHubIssues,
  type GitHubIssue,
  type DashboardRepo,
  type ImportIssueResult,
} from '../../lib/api'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface ImportModalProps {
  open: boolean
  onClose: () => void
  /** Called after a successful import with the count of newly created tasks. */
  onImported?: (created: number) => void
}

type ImportMode = 'triage' | 'direct'
type StateFilter = 'open' | 'closed' | 'all'

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function ImportModal({ open, onClose, onImported }: ImportModalProps) {
  // --- Repo selection ---
  const [repos, setRepos] = useState<DashboardRepo[]>([])
  const [selectedRepo, setSelectedRepo] = useState('')
  const [repoInput, setRepoInput] = useState('') // manual fallback when no repos registered
  const [reposLoading, setReposLoading] = useState(false)

  // --- Filters ---
  const [stateFilter, setStateFilter] = useState<StateFilter>('open')
  const [labelFilter, setLabelFilter] = useState('')
  const [search, setSearch] = useState('')

  // --- Issues ---
  const [issues, setIssues] = useState<GitHubIssue[]>([])
  const [issuesLoading, setIssuesLoading] = useState(false)
  const [issuesError, setIssuesError] = useState<string | null>(null)
  const [currentPage, setCurrentPage] = useState(1)
  const [hasNext, setHasNext] = useState(false)

  // --- Selection ---
  const [selectedNumbers, setSelectedNumbers] = useState<Set<number>>(new Set())

  // --- Import mode ---
  const [importMode, setImportMode] = useState<ImportMode>('triage')

  // --- Import state ---
  const [importing, setImporting] = useState(false)
  const [importResults, setImportResults] = useState<ImportIssueResult[] | null>(null)
  const [importError, setImportError] = useState<string | null>(null)

  const searchRef = useRef<HTMLInputElement>(null)

  /** The effective repo string (selected from dropdown or typed manually). */
  const activeRepo = selectedRepo || repoInput

  // --- Reset when modal opens/closes ---
  const reset = useCallback(() => {
    setSelectedRepo('')
    setRepoInput('')
    setStateFilter('open')
    setLabelFilter('')
    setSearch('')
    setIssues([])
    setIssuesError(null)
    setCurrentPage(1)
    setHasNext(false)
    setSelectedNumbers(new Set())
    setImportMode('triage')
    setImporting(false)
    setImportResults(null)
    setImportError(null)
  }, [])

  // Load registered repos when modal opens
  useEffect(() => {
    if (!open) return
    reset()
    setReposLoading(true)
    fetchDashboardRepos()
      .then((data) => {
        setRepos(data.repos)
        // Auto-select if there's exactly one repo
        if (data.repos.length === 1) {
          setSelectedRepo(data.repos[0].full_name)
        }
      })
      .catch(() => {
        // Non-fatal: user can type the repo name manually
      })
      .finally(() => setReposLoading(false))
  }, [open, reset])

  // Escape key closes (when not importing)
  useEffect(() => {
    if (!open) return
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !importing) onClose()
    }
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [open, importing, onClose])

  // --- Load issues ---
  const loadIssues = useCallback(
    async (page: number) => {
      if (!activeRepo) return
      setIssuesLoading(true)
      setIssuesError(null)
      try {
        const data = await fetchGitHubIssues({
          repo: activeRepo,
          state: stateFilter,
          labels: labelFilter || undefined,
          search: search || undefined,
          page,
          per_page: 30,
        })
        if (page === 1) {
          setIssues(data.issues)
        } else {
          setIssues((prev) => [...prev, ...data.issues])
        }
        setHasNext(data.has_next)
        setCurrentPage(page)
        // Clear import results when refreshing the list
        if (page === 1) {
          setImportResults(null)
          setImportError(null)
        }
      } catch (err) {
        setIssuesError(err instanceof Error ? err.message : 'Failed to load issues')
      } finally {
        setIssuesLoading(false)
      }
    },
    [activeRepo, stateFilter, labelFilter, search],
  )

  // --- Backdrop click ---
  const handleBackdropClick = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      if (e.target === e.currentTarget && !importing) onClose()
    },
    [importing, onClose],
  )

  // --- Checkbox helpers ---
  const toggleIssue = useCallback((number: number) => {
    setSelectedNumbers((prev) => {
      const next = new Set(prev)
      if (next.has(number)) next.delete(number)
      else next.add(number)
      return next
    })
  }, [])

  const toggleAll = useCallback(() => {
    setSelectedNumbers((prev) =>
      prev.size === issues.length ? new Set() : new Set(issues.map((i) => i.number)),
    )
  }, [issues])

  // --- Repo / filter change helpers (reset issues + selection) ---
  const handleRepoChange = (value: string) => {
    setSelectedRepo(value)
    setIssues([])
    setCurrentPage(1)
    setSelectedNumbers(new Set())
    setImportResults(null)
    setImportError(null)
  }

  const handleRepoInputChange = (value: string) => {
    setRepoInput(value)
    setIssues([])
    setCurrentPage(1)
    setSelectedNumbers(new Set())
    setImportResults(null)
    setImportError(null)
  }

  const handleFilterChange = () => {
    setIssues([])
    setCurrentPage(1)
  }

  // --- Import ---
  const handleImport = async () => {
    if (!activeRepo || selectedNumbers.size === 0) return
    setImporting(true)
    setImportError(null)
    setImportResults(null)
    try {
      const selectedIssues = issues
        .filter((i) => selectedNumbers.has(i.number))
        .map((i) => ({
          number: i.number,
          title: i.title,
          body: i.body,
          labels: i.labels,
        }))
      const response = await importGitHubIssues({
        repo: activeRepo,
        issues: selectedIssues,
        triage_override: importMode === 'triage',
      })
      setImportResults(response.results)
      onImported?.(response.created)
    } catch (err) {
      setImportError(err instanceof Error ? err.message : 'Import failed')
    } finally {
      setImporting(false)
    }
  }

  if (!open) return null

  // ---------------------------------------------------------------------------
  // Derived state for the summary banner
  // ---------------------------------------------------------------------------
  const createdCount = importResults?.filter((r) => r.status === 'created').length ?? 0
  const duplicateCount = importResults?.filter((r) => r.status === 'duplicate').length ?? 0
  const errorCount = importResults?.filter((r) => r.status === 'error').length ?? 0

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60"
      onClick={handleBackdropClick}
    >
      <div className="flex max-h-[90vh] w-full max-w-3xl flex-col overflow-hidden rounded-lg border border-gray-700 bg-gray-900 shadow-2xl">
        {/* ------------------------------------------------------------------ */}
        {/* Header */}
        {/* ------------------------------------------------------------------ */}
        <div className="flex items-center justify-between border-b border-gray-700 px-6 py-4">
          <h2 className="text-base font-semibold text-gray-100">Import GitHub Issues</h2>
          <button
            onClick={onClose}
            disabled={importing}
            aria-label="Close"
            className="text-gray-400 hover:text-gray-200 disabled:opacity-50"
          >
            ✕
          </button>
        </div>

        {/* ------------------------------------------------------------------ */}
        {/* Filters */}
        {/* ------------------------------------------------------------------ */}
        <div className="flex flex-wrap items-end gap-3 border-b border-gray-700 px-6 py-3">
          {/* Repo selector */}
          <div className="flex min-w-52 flex-col gap-1">
            <label className="text-xs text-gray-400">Repository</label>
            {repos.length > 0 ? (
              <select
                value={selectedRepo}
                onChange={(e) => handleRepoChange(e.target.value)}
                disabled={importing}
                className="rounded border border-gray-600 bg-gray-800 px-2 py-1.5 text-sm text-gray-100 focus:border-blue-500 focus:outline-none"
              >
                <option value="">Select repo…</option>
                {repos.map((r) => (
                  <option key={r.full_name} value={r.full_name}>
                    {r.full_name}
                  </option>
                ))}
              </select>
            ) : (
              <input
                type="text"
                placeholder={reposLoading ? 'Loading…' : 'owner/repo'}
                value={repoInput}
                onChange={(e) => handleRepoInputChange(e.target.value)}
                disabled={importing || reposLoading}
                className="rounded border border-gray-600 bg-gray-800 px-2 py-1.5 text-sm text-gray-100 placeholder-gray-600 focus:border-blue-500 focus:outline-none"
              />
            )}
          </div>

          {/* State filter */}
          <div className="flex flex-col gap-1">
            <label className="text-xs text-gray-400">Status</label>
            <select
              value={stateFilter}
              onChange={(e) => {
                setStateFilter(e.target.value as StateFilter)
                handleFilterChange()
              }}
              disabled={importing}
              className="rounded border border-gray-600 bg-gray-800 px-2 py-1.5 text-sm text-gray-100 focus:border-blue-500 focus:outline-none"
            >
              <option value="open">Open</option>
              <option value="closed">Closed</option>
              <option value="all">All</option>
            </select>
          </div>

          {/* Labels filter */}
          <div className="flex flex-col gap-1">
            <label className="text-xs text-gray-400">Labels (comma-sep)</label>
            <input
              type="text"
              placeholder="bug,enhancement"
              value={labelFilter}
              onChange={(e) => {
                setLabelFilter(e.target.value)
                handleFilterChange()
              }}
              disabled={importing}
              className="w-40 rounded border border-gray-600 bg-gray-800 px-2 py-1.5 text-sm text-gray-100 placeholder-gray-600 focus:border-blue-500 focus:outline-none"
            />
          </div>

          {/* Search */}
          <div className="flex flex-1 flex-col gap-1">
            <label className="text-xs text-gray-400">Search title</label>
            <input
              ref={searchRef}
              type="text"
              placeholder="Search…"
              value={search}
              onChange={(e) => {
                setSearch(e.target.value)
                handleFilterChange()
              }}
              disabled={importing}
              className="rounded border border-gray-600 bg-gray-800 px-2 py-1.5 text-sm text-gray-100 placeholder-gray-600 focus:border-blue-500 focus:outline-none"
            />
          </div>

          {/* Load button */}
          <button
            onClick={() => loadIssues(1)}
            disabled={!activeRepo || issuesLoading || importing}
            className="rounded bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-500 disabled:opacity-50"
          >
            {issuesLoading ? 'Loading…' : 'Load Issues'}
          </button>
        </div>

        {/* ------------------------------------------------------------------ */}
        {/* Import mode toggle */}
        {/* ------------------------------------------------------------------ */}
        <div className="flex items-center gap-4 border-b border-gray-700 px-6 py-2">
          <span className="text-xs text-gray-400">Import mode:</span>
          <label className="flex cursor-pointer items-center gap-1.5 text-sm">
            <input
              type="radio"
              name="importMode"
              value="triage"
              checked={importMode === 'triage'}
              onChange={() => setImportMode('triage')}
              disabled={importing}
              className="accent-blue-500"
            />
            <span className="text-gray-200">Triage</span>
            <span className="text-xs text-gray-500">(hold for review)</span>
          </label>
          <label className="flex cursor-pointer items-center gap-1.5 text-sm">
            <input
              type="radio"
              name="importMode"
              value="direct"
              checked={importMode === 'direct'}
              onChange={() => setImportMode('direct')}
              disabled={importing}
              className="accent-blue-500"
            />
            <span className="text-gray-200">Direct</span>
            <span className="text-xs text-gray-500">(start pipeline immediately)</span>
          </label>
        </div>

        {/* ------------------------------------------------------------------ */}
        {/* Issue list */}
        {/* ------------------------------------------------------------------ */}
        <div className="flex-1 overflow-y-auto px-6 py-3">
          {/* Error banners */}
          {issuesError && (
            <div className="mb-3 rounded border border-red-700 bg-red-900/30 px-3 py-2 text-sm text-red-300">
              {issuesError}
            </div>
          )}
          {importError && (
            <div className="mb-3 rounded border border-red-700 bg-red-900/30 px-3 py-2 text-sm text-red-300">
              {importError}
            </div>
          )}

          {/* Import result summary */}
          {importResults && (
            <div className="mb-3 rounded border border-green-700 bg-green-900/20 px-3 py-2 text-sm">
              <span className="font-medium text-green-300">Import complete — </span>
              <span className="text-green-200">
                {createdCount} created
                {duplicateCount > 0 && `, ${duplicateCount} already in pipeline`}
                {errorCount > 0 && `, ${errorCount} error${errorCount !== 1 ? 's' : ''}`}
              </span>
            </div>
          )}

          {/* Empty state */}
          {issues.length === 0 && !issuesLoading && !issuesError && (
            <p className="py-12 text-center text-sm text-gray-500">
              {activeRepo
                ? 'Click "Load Issues" to browse GitHub issues.'
                : 'Select a repository to get started.'}
            </p>
          )}

          {/* Issue table */}
          {issues.length > 0 && (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-700">
                  <th className="pb-2 pr-3 text-left">
                    <input
                      type="checkbox"
                      checked={selectedNumbers.size === issues.length && issues.length > 0}
                      ref={(el) => {
                        if (el) {
                          el.indeterminate =
                            selectedNumbers.size > 0 && selectedNumbers.size < issues.length
                        }
                      }}
                      onChange={toggleAll}
                      disabled={importing}
                      className="accent-blue-500"
                      aria-label="Select all"
                    />
                  </th>
                  <th className="pb-2 pr-3 text-left text-xs font-medium text-gray-400">#</th>
                  <th className="pb-2 pr-3 text-left text-xs font-medium text-gray-400">Title</th>
                  <th className="pb-2 pr-3 text-left text-xs font-medium text-gray-400">Labels</th>
                  <th className="pb-2 text-left text-xs font-medium text-gray-400">Status</th>
                </tr>
              </thead>
              <tbody>
                {issues.map((issue) => {
                  const result = importResults?.find((r) => r.number === issue.number)
                  return (
                    <tr
                      key={issue.number}
                      className="cursor-pointer border-b border-gray-800 hover:bg-gray-800/50"
                      onClick={() => !importing && toggleIssue(issue.number)}
                    >
                      <td className="py-2 pr-3">
                        <input
                          type="checkbox"
                          checked={selectedNumbers.has(issue.number)}
                          onChange={() => toggleIssue(issue.number)}
                          onClick={(e) => e.stopPropagation()}
                          disabled={importing}
                          className="accent-blue-500"
                        />
                      </td>
                      <td className="py-2 pr-3 text-xs text-gray-400">#{issue.number}</td>
                      <td className="py-2 pr-3">
                        <a
                          href={issue.html_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          onClick={(e) => e.stopPropagation()}
                          className="text-gray-100 hover:text-blue-400 hover:underline"
                        >
                          {issue.title}
                        </a>
                        {issue.comments > 0 && (
                          <span className="ml-1.5 text-xs text-gray-500">
                            💬 {issue.comments}
                          </span>
                        )}
                      </td>
                      <td className="py-2 pr-3">
                        <div className="flex flex-wrap gap-1">
                          {issue.labels.map((label) => (
                            <span
                              key={label}
                              className="rounded bg-gray-700 px-1.5 py-0.5 text-xs text-gray-300"
                            >
                              {label}
                            </span>
                          ))}
                        </div>
                      </td>
                      <td className="py-2">
                        {result ? (
                          <span
                            className={`rounded px-1.5 py-0.5 text-xs font-medium ${
                              result.status === 'created'
                                ? 'bg-green-800 text-green-200'
                                : result.status === 'duplicate'
                                  ? 'bg-yellow-800 text-yellow-200'
                                  : 'bg-red-800 text-red-200'
                            }`}
                          >
                            {result.status === 'created'
                              ? '✓ Created'
                              : result.status === 'duplicate'
                                ? '↩ In pipeline'
                                : '✗ Error'}
                          </span>
                        ) : (
                          <span
                            className={`rounded px-1.5 py-0.5 text-xs ${
                              issue.state === 'open'
                                ? 'bg-green-900/40 text-green-400'
                                : 'bg-gray-700 text-gray-400'
                            }`}
                          >
                            {issue.state}
                          </span>
                        )}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          )}

          {/* Load more */}
          {hasNext && (
            <div className="mt-3 flex justify-center">
              <button
                onClick={() => loadIssues(currentPage + 1)}
                disabled={issuesLoading || importing}
                className="rounded border border-gray-600 px-4 py-1.5 text-sm text-gray-300 hover:bg-gray-700 disabled:opacity-50"
              >
                {issuesLoading ? 'Loading…' : 'Load more'}
              </button>
            </div>
          )}
        </div>

        {/* ------------------------------------------------------------------ */}
        {/* Footer */}
        {/* ------------------------------------------------------------------ */}
        <div className="flex items-center justify-between border-t border-gray-700 px-6 py-4">
          <span className="text-sm text-gray-400">
            {selectedNumbers.size > 0
              ? `${selectedNumbers.size} issue${selectedNumbers.size !== 1 ? 's' : ''} selected`
              : issues.length > 0
                ? 'No issues selected'
                : ''}
          </span>
          <div className="flex gap-3">
            <button
              onClick={onClose}
              disabled={importing}
              className="rounded border border-gray-600 px-4 py-1.5 text-sm text-gray-300 hover:bg-gray-700 disabled:opacity-50"
            >
              {importResults ? 'Close' : 'Cancel'}
            </button>
            {!importResults && (
              <button
                onClick={handleImport}
                disabled={selectedNumbers.size === 0 || importing || !activeRepo}
                className="rounded bg-blue-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-blue-500 disabled:opacity-50"
              >
                {importing
                  ? `Importing ${selectedNumbers.size}…`
                  : `Import ${selectedNumbers.size > 0 ? selectedNumbers.size + ' ' : ''}Issue${selectedNumbers.size !== 1 ? 's' : ''}`}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
