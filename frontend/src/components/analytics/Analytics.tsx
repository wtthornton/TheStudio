/**
 * Analytics -- Epic 39, Story 39.6 (main container).
 * Updated Epic 41, Story 41.12 -- repo filter from RepoContext.
 * Updated Epic 46.5 -- empty state when no data yet.
 *
 * Orchestrates the Analytics tab with:
 *   - PeriodSelector (39.11)
 *   - SummaryCards (39.10)
 *   - ThroughputChart (39.6)
 *   - BottleneckBars (39.7)
 *   - CategoryBreakdown (39.8)
 *   - FailureAnalysis (39.9)
 *
 * All child components receive the shared `period` and `repo` state.
 * When a specific repo is selected via RepoSelector, analytics data is
 * scoped to that repo. When "All Repos" is selected (repo=null), data
 * is aggregate across all repositories.
 */

import { useState, useEffect } from 'react'
import type { AnalyticsPeriod } from '../../lib/api'
import { fetchAnalyticsSummary } from '../../lib/api'
import { PeriodSelector } from './PeriodSelector'
import { SummaryCards } from './SummaryCards'
import { ThroughputChart } from './ThroughputChart'
import { BottleneckBars } from './BottleneckBars'
import { CategoryBreakdown } from './CategoryBreakdown'
import { FailureAnalysis } from './FailureAnalysis'
import { ExpertTable } from './ExpertTable'
import { useRepoContext } from '../../contexts/RepoContext'
import { EmptyState } from '../EmptyState'

// ---------------------------------------------------------------------------
// Empty state icon
// ---------------------------------------------------------------------------

function AnalyticsIcon() {
  return (
    <svg
      width="48"
      height="48"
      viewBox="0 0 48 48"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
    >
      <rect x="6" y="28" width="8" height="14" rx="2" fill="#374151" />
      <rect x="20" y="18" width="8" height="24" rx="2" fill="#374151" />
      <rect x="34" y="10" width="8" height="32" rx="2" fill="#374151" />
      <path
        d="M6 26 L20 16 L34 8"
        stroke="#4B5563"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeDasharray="3 3"
      />
    </svg>
  )
}

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface AnalyticsProps {
  /** Called when user clicks "Go to Pipeline" in the empty state. */
  onNavigateToPipeline?: () => void
}

export function Analytics({ onNavigateToPipeline }: AnalyticsProps) {
  const [period, setPeriod] = useState<AnalyticsPeriod>('30d')
  const { selectedRepo } = useRepoContext()
  /** null = loading, true = no data, false = has data */
  const [isEmpty, setIsEmpty] = useState<boolean | null>(null)

  useEffect(() => {
    let cancelled = false
    fetchAnalyticsSummary(period, selectedRepo)
      .then((data) => {
        if (cancelled) return
        const tasksCompleted = data.cards?.tasks_completed?.value ?? 0
        const totalSpend = data.cards?.total_spend_usd?.value ?? 0
        setIsEmpty(tasksCompleted === 0 && totalSpend === 0)
      })
      .catch(() => {
        // On error fall through to showing analytics normally
        if (!cancelled) setIsEmpty(false)
      })
    return () => {
      cancelled = true
    }
  }, [period, selectedRepo])

  if (isEmpty === true) {
    return (
      <div className="mx-auto max-w-6xl px-6 py-16">
        <EmptyState
          icon={<AnalyticsIcon />}
          heading="No analytics data yet"
          description="Start processing GitHub issues through the pipeline to see operational metrics, throughput charts, and bottleneck analysis here."
          primaryAction={
            onNavigateToPipeline
              ? { label: 'Go to Pipeline', onClick: onNavigateToPipeline }
              : { label: 'Go to Pipeline', href: '#' }
          }
          secondaryAction={{ label: 'Learn about analytics', href: 'https://docs.thestudio.ai/analytics' }}
          data-testid="analytics-empty-state"
        />
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-6xl px-6 py-6 space-y-6">
      {/* Header row — data-tour target for period selector step */}
      <div className="flex items-center justify-between" data-tour="analytics-period">
        <div>
          <h2 className="text-lg font-semibold text-gray-100">Operational Analytics</h2>
          {selectedRepo && (
            <p className="text-xs text-gray-500 mt-0.5">
              Showing data for <span className="text-gray-400 font-mono">{selectedRepo}</span>
            </p>
          )}
        </div>
        <PeriodSelector period={period} onChange={setPeriod} />
      </div>

      {/* Summary cards — data-tour target for KPIs step */}
      <div data-tour="analytics-kpis">
        <SummaryCards period={period} repo={selectedRepo} />
      </div>

      {/* Charts row */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* data-tour target for throughput step */}
        <div data-tour="analytics-throughput">
          <ThroughputChart period={period} repo={selectedRepo} />
        </div>
        {/* data-tour target for bottleneck step */}
        <div data-tour="analytics-bottleneck">
          <BottleneckBars period={period} repo={selectedRepo} />
        </div>
      </div>

      {/* Detail row */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <CategoryBreakdown period={period} repo={selectedRepo} />
        <FailureAnalysis period={period} repo={selectedRepo} />
      </div>

      {/* Expert reputation table — data-tour target for expert table step */}
      <div data-tour="analytics-expert-table">
        <ExpertTable onSelectExpert={() => {}} />
      </div>
    </div>
  )
}
