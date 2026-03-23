/**
 * RepoConfigForm — Epic 41, Story 41.11.
 *
 * Form for viewing and editing per-repo configuration fields:
 * - default_branch
 * - required_checks (comma-separated)
 * - tool_allowlist (comma-separated)
 * - poll_enabled / poll_interval_minutes
 *
 * Submits to PATCH /admin/repos/{id}/profile.
 * Tier change submits to PATCH /admin/repos/{id}/tier.
 */

import { useState, useEffect } from 'react'
import type { AdminRepoDetail, RepoProfileUpdateRequest } from '../lib/api'
import { updateAdminRepoProfile, changeAdminRepoTier } from '../lib/api'

interface RepoConfigFormProps {
  repo: AdminRepoDetail
  onSaved?: () => void
}

export function RepoConfigForm({ repo, onSaved }: RepoConfigFormProps) {
  const [defaultBranch, setDefaultBranch] = useState(repo.default_branch || 'main')
  const [requiredChecks, setRequiredChecks] = useState(
    (repo.required_checks || []).join(', ')
  )
  const [toolAllowlist, setToolAllowlist] = useState(
    (repo.tool_allowlist || []).join(', ')
  )
  const [pollEnabled, setPollEnabled] = useState(repo.poll_enabled || false)
  const [pollInterval, setPollInterval] = useState(
    repo.poll_interval_minutes?.toString() || ''
  )
  const [tier, setTier] = useState(repo.tier || 'OBSERVE')

  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  // Sync state when repo prop changes (e.g., parent re-fetches)
  useEffect(() => {
    setDefaultBranch(repo.default_branch || 'main')
    setRequiredChecks((repo.required_checks || []).join(', '))
    setToolAllowlist((repo.tool_allowlist || []).join(', '))
    setPollEnabled(repo.poll_enabled || false)
    setPollInterval(repo.poll_interval_minutes?.toString() || '')
    setTier(repo.tier || 'OBSERVE')
  }, [repo])

  async function handleSave(e: React.FormEvent) {
    e.preventDefault()
    setSaving(true)
    setMessage(null)
    setError(null)

    const update: RepoProfileUpdateRequest = {
      default_branch: defaultBranch.trim() || undefined,
      required_checks: requiredChecks
        .split(',')
        .map((s) => s.trim())
        .filter(Boolean),
      tool_allowlist: toolAllowlist
        .split(',')
        .map((s) => s.trim())
        .filter(Boolean),
      poll_enabled: pollEnabled,
      poll_interval_minutes: pollEnabled && pollInterval
        ? parseInt(pollInterval, 10)
        : undefined,
    }

    const result = await updateAdminRepoProfile(repo.id, update)

    // Also update tier if changed
    if (tier !== repo.tier) {
      const tierResult = await changeAdminRepoTier(repo.id, tier.toLowerCase())
      if (!tierResult) {
        setError('Profile saved but tier change failed.')
        setSaving(false)
        return
      }
    }

    if (result) {
      setMessage('Configuration saved.')
      onSaved?.()
    } else {
      setError('Failed to save configuration.')
    }
    setSaving(false)
  }

  return (
    <form onSubmit={handleSave} className="space-y-4 text-sm">
      {/* Repo identifier (read-only) */}
      <div>
        <label className="block text-xs font-medium text-gray-400 mb-1">Repository</label>
        <div className="rounded bg-gray-800 px-3 py-2 text-gray-200 font-mono text-xs">
          {repo.owner}/{repo.repo}
        </div>
      </div>

      {/* Tier */}
      <div>
        <label className="block text-xs font-medium text-gray-400 mb-1">Trust Tier</label>
        <select
          value={tier}
          onChange={(e) => setTier(e.target.value)}
          className="w-full rounded border border-gray-700 bg-gray-800 px-3 py-2 text-gray-200 text-xs"
        >
          <option value="OBSERVE">Observe</option>
          <option value="SUGGEST">Suggest</option>
          <option value="EXECUTE">Execute</option>
        </select>
      </div>

      {/* Default branch */}
      <div>
        <label className="block text-xs font-medium text-gray-400 mb-1">Default Branch</label>
        <input
          type="text"
          value={defaultBranch}
          onChange={(e) => setDefaultBranch(e.target.value)}
          placeholder="main"
          className="w-full rounded border border-gray-700 bg-gray-800 px-3 py-2 text-gray-200 text-xs placeholder-gray-600"
        />
      </div>

      {/* Required checks */}
      <div>
        <label className="block text-xs font-medium text-gray-400 mb-1">
          Required Checks <span className="text-gray-600">(comma-separated)</span>
        </label>
        <input
          type="text"
          value={requiredChecks}
          onChange={(e) => setRequiredChecks(e.target.value)}
          placeholder="ci/tests, ci/lint"
          className="w-full rounded border border-gray-700 bg-gray-800 px-3 py-2 text-gray-200 text-xs placeholder-gray-600"
        />
      </div>

      {/* Tool allowlist */}
      <div>
        <label className="block text-xs font-medium text-gray-400 mb-1">
          Tool Allowlist <span className="text-gray-600">(comma-separated)</span>
        </label>
        <input
          type="text"
          value={toolAllowlist}
          onChange={(e) => setToolAllowlist(e.target.value)}
          placeholder="bash, python, git"
          className="w-full rounded border border-gray-700 bg-gray-800 px-3 py-2 text-gray-200 text-xs placeholder-gray-600"
        />
      </div>

      {/* Poll settings */}
      <div>
        <label className="flex items-center gap-2 text-xs font-medium text-gray-400">
          <input
            type="checkbox"
            checked={pollEnabled}
            onChange={(e) => setPollEnabled(e.target.checked)}
            className="rounded border-gray-700 bg-gray-800"
          />
          Enable Issue Polling
        </label>
        {pollEnabled && (
          <div className="mt-2 ml-5">
            <label className="block text-xs text-gray-500 mb-1">Poll Interval (minutes)</label>
            <input
              type="number"
              value={pollInterval}
              onChange={(e) => setPollInterval(e.target.value)}
              min={1}
              max={1440}
              placeholder="60"
              className="w-24 rounded border border-gray-700 bg-gray-800 px-2 py-1 text-gray-200 text-xs"
            />
          </div>
        )}
      </div>

      {/* Feedback */}
      {message && (
        <p className="text-xs text-green-400">{message}</p>
      )}
      {error && (
        <p className="text-xs text-red-400">{error}</p>
      )}

      <button
        type="submit"
        disabled={saving}
        className="rounded bg-blue-700 px-4 py-1.5 text-xs font-medium text-white hover:bg-blue-600 disabled:opacity-50"
      >
        {saving ? 'Saving…' : 'Save Configuration'}
      </button>
    </form>
  )
}
