/**
 * Epic 44.6 — Let the user pick a trust tier during wizard setup.
 * Fetches registered repos, shows Observe/Suggest/Execute dropdown with
 * descriptions, and PATCHes /admin/repos/{id}/tier on Apply.
 */

import { useEffect, useState } from 'react'
import { fetchAdminRepos, changeAdminRepoTier } from '../../lib/api'
import type { AdminRepoItem } from '../../lib/api'
import { useWizardNav } from './WizardShell'

type Tier = 'observe' | 'suggest' | 'execute'
type ApplyState = 'idle' | 'applying' | 'success' | 'error'

interface TierOption {
  value: Tier
  label: string
  badge: string
  description: string
  badgeClass: string
}

const TIER_OPTIONS: TierOption[] = [
  {
    value: 'observe',
    label: 'Observe',
    badge: 'Read-only',
    description:
      'TheStudio reads your issues and proposes draft PRs for manual review. No automated writes.',
    badgeClass: 'bg-gray-800 text-gray-300 ring-gray-700',
  },
  {
    value: 'suggest',
    label: 'Suggest',
    badge: 'Draft PRs',
    description:
      'TheStudio opens draft PRs automatically after verification passes. You merge manually.',
    badgeClass: 'bg-blue-950 text-blue-300 ring-blue-800',
  },
  {
    value: 'execute',
    label: 'Execute',
    badge: 'Auto-merge',
    description:
      'TheStudio promotes PRs to ready-for-review and can auto-merge when all checks pass.',
    badgeClass: 'bg-purple-950 text-purple-300 ring-purple-800',
  },
]

export function TrustTierStep() {
  const { setNextDisabled } = useWizardNav()

  const [repos, setRepos] = useState<AdminRepoItem[]>([])
  const [loadError, setLoadError] = useState<string | null>(null)
  const [selectedTier, setSelectedTier] = useState<Tier>('observe')
  const [applyState, setApplyState] = useState<ApplyState>('idle')
  const [applyError, setApplyError] = useState<string | null>(null)

  // Load repos on mount
  useEffect(() => {
    let cancelled = false
    async function load() {
      try {
        const data = await fetchAdminRepos()
        if (!cancelled) {
          setRepos(data.repos)
          // Pre-select the tier from the first registered repo, if any
          if (data.repos.length > 0 && data.repos[0].tier) {
            const existingTier = data.repos[0].tier.toLowerCase() as Tier
            if (['observe', 'suggest', 'execute'].includes(existingTier)) {
              setSelectedTier(existingTier)
            }
          }
        }
      } catch {
        if (!cancelled) {
          setLoadError('Could not load repositories. You can skip this step.')
        }
      }
    }
    void load()
    return () => {
      cancelled = true
    }
  }, [])

  // Next is always enabled — tier selection is optional during wizard
  useEffect(() => {
    setNextDisabled(false)
  }, [setNextDisabled])

  async function handleApply() {
    if (repos.length === 0) return

    setApplyState('applying')
    setApplyError(null)

    let anyFailed = false
    for (const repo of repos) {
      const result = await changeAdminRepoTier(repo.id, selectedTier)
      if (!result) {
        anyFailed = true
      }
    }

    if (anyFailed) {
      setApplyError('One or more repos could not be updated. Check permissions and try again.')
      setApplyState('error')
    } else {
      setApplyState('success')
    }
  }

  const selectedOption = TIER_OPTIONS.find((o) => o.value === selectedTier) ?? TIER_OPTIONS[0]

  return (
    <div className="space-y-5" data-testid="wizard-step-trust-tier">
      <p className="text-sm text-gray-400">
        Choose how much autonomy TheStudio has when processing issues. You can change this at any
        time in the{' '}
        <strong className="text-gray-300">Configuration → Trust Tiers</strong> tab.
      </p>

      {loadError ? (
        <div
          className="rounded-lg border border-yellow-800 bg-yellow-950/60 px-3 py-2 text-sm text-yellow-400"
          role="alert"
          data-testid="wizard-trust-tier-load-error"
        >
          {loadError}
        </div>
      ) : null}

      {/* Tier selector */}
      <div className="space-y-2" role="radiogroup" aria-label="Trust tier">
        {TIER_OPTIONS.map((option) => {
          const isSelected = selectedTier === option.value
          return (
            <label
              key={option.value}
              className={[
                'flex cursor-pointer items-start gap-3 rounded-lg border px-3 py-3 transition-colors',
                isSelected
                  ? 'border-blue-600 bg-blue-950/30'
                  : 'border-gray-700 bg-gray-900/40 hover:border-gray-600',
              ].join(' ')}
              data-testid={`wizard-trust-tier-option-${option.value}`}
            >
              <input
                type="radio"
                name="trust-tier"
                value={option.value}
                checked={isSelected}
                onChange={() => {
                  setSelectedTier(option.value)
                  setApplyState('idle')
                }}
                className="mt-0.5 h-4 w-4 cursor-pointer accent-blue-500"
                aria-label={option.label}
              />
              <div className="min-w-0 flex-1 space-y-0.5">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-gray-100">{option.label}</span>
                  <span
                    className={[
                      'rounded-full px-2 py-0.5 text-xs font-medium ring-1',
                      option.badgeClass,
                    ].join(' ')}
                  >
                    {option.badge}
                  </span>
                </div>
                <p className="text-xs text-gray-400">{option.description}</p>
              </div>
            </label>
          )
        })}
      </div>

      {/* Apply button + status */}
      {repos.length > 0 ? (
        <div className="flex flex-wrap items-center gap-3">
          <button
            type="button"
            onClick={() => void handleApply()}
            disabled={applyState === 'applying' || applyState === 'success'}
            data-testid="wizard-trust-tier-apply"
            className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-40"
          >
            {applyState === 'applying'
              ? 'Applying…'
              : applyState === 'success'
                ? `Applied — ${selectedOption.label}`
                : `Apply ${selectedOption.label} tier`}
          </button>

          {applyState === 'success' && (
            <span
              className="flex items-center gap-1 text-sm text-emerald-400"
              data-testid="wizard-trust-tier-success"
              role="status"
            >
              <span aria-hidden="true">✓</span>
              {repos.length === 1
                ? `${repos[0].owner}/${repos[0].repo} updated.`
                : `${repos.length} repos updated.`}
            </span>
          )}

          {applyState === 'error' && applyError ? (
            <span
              className="text-sm text-red-400"
              data-testid="wizard-trust-tier-error"
              role="alert"
            >
              {applyError}
            </span>
          ) : null}
        </div>
      ) : (
        !loadError && (
          <p className="text-xs text-gray-500" data-testid="wizard-trust-tier-no-repos">
            No repositories registered yet — complete the previous step first.
          </p>
        )
      )}

      {/* Info callout */}
      <div className="rounded-lg border border-gray-800 bg-gray-900/60 px-3 py-2 text-xs text-gray-400">
        <strong className="text-gray-300">Tip:</strong> Start with{' '}
        <span className="font-medium text-gray-200">Observe</span> and promote when you're
        confident in the pipeline output. Execute tier requires a compliance check to activate.
      </div>
    </div>
  )
}
