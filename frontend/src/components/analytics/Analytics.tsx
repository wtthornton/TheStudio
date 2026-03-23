/**
 * Analytics -- Epic 39, Story 39.6 (main container).
 * Updated Epic 41, Story 41.12 -- repo filter from RepoContext.
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

import { useState } from 'react'
import type { AnalyticsPeriod } from '../../lib/api'
import { PeriodSelector } from './PeriodSelector'
import { SummaryCards } from './SummaryCards'
import { ThroughputChart } from './ThroughputChart'
import { BottleneckBars } from './BottleneckBars'
import { CategoryBreakdown } from './CategoryBreakdown'
import { FailureAnalysis } from './FailureAnalysis'
import { useRepoContext } from '../../contexts/RepoContext'

export function Analytics() {
  const [period, setPeriod] = useState<AnalyticsPeriod>('30d')
  const { selectedRepo } = useRepoContext()

  return (
    <div className="mx-auto max-w-6xl px-6 py-6 space-y-6">
      {/* Header row */}
      <div className="flex items-center justify-between">
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

      {/* Summary cards */}
      <SummaryCards period={period} repo={selectedRepo} />

      {/* Charts row */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <ThroughputChart period={period} repo={selectedRepo} />
        <BottleneckBars period={period} repo={selectedRepo} />
      </div>

      {/* Detail row */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <CategoryBreakdown period={period} repo={selectedRepo} />
        <FailureAnalysis period={period} repo={selectedRepo} />
      </div>
    </div>
  )
}
