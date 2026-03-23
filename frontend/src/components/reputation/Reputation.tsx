/**
 * Reputation -- Epic 39, Story 39.17 (main container).
 *
 * Orchestrates the Reputation & Outcomes tab with:
 *   - ReputationSummaryCards (39.21) — 4 summary cards
 *   - ExpertTable (39.17) — sortable expert performance table
 *   - ExpertDetail (39.18) — click-to-expand expert view
 *   - OutcomeFeed (39.19) — chronological outcome signals
 *   - DriftAlerts (39.20) — drift detection panel
 *
 * Story 39.21: Reuses the SummaryCards pattern from Slice 1 with the
 * reputation data shape (success_rate, avg_loopbacks, pr_merge_rate,
 * drift_score).
 */

import { useState } from 'react'
import { ExpertTable } from '../analytics/ExpertTable'
import { ExpertDetail } from '../analytics/ExpertDetail'
import { OutcomeFeed } from '../analytics/OutcomeFeed'
import { DriftAlerts } from '../analytics/DriftAlerts'
import { ReputationSummaryCards } from './ReputationSummaryCards'

export function Reputation() {
  const [selectedExpertId, setSelectedExpertId] = useState<string | null>(null)

  return (
    <div className="mx-auto max-w-6xl px-6 py-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-100">Reputation & Outcomes</h2>
        <p className="text-xs text-gray-500">14-day rolling window</p>
      </div>

      {/* Summary cards (Story 39.21) */}
      <ReputationSummaryCards />

      {/* Top row: Expert performance + Drift alerts */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div>
          {selectedExpertId ? (
            <ExpertDetail
              expertId={selectedExpertId}
              onClose={() => setSelectedExpertId(null)}
            />
          ) : (
            <ExpertTable onSelectExpert={setSelectedExpertId} />
          )}
        </div>
        <DriftAlerts />
      </div>

      {/* Outcome signals feed */}
      <OutcomeFeed />
    </div>
  )
}
