/**
 * CategoryBreakdown -- Epic 39, Story 39.8.
 *
 * Table showing completed tasks grouped by triage category.
 * Columns: Category, Count, Merge Rate, Avg Cost, Avg Time.
 * Low-sample warning for categories with < 3 tasks.
 */

import { useEffect, useState } from 'react'
import type { AnalyticsPeriod, CategoryResponse } from '../../lib/api'
import { fetchAnalyticsCategories } from '../../lib/api'

interface CategoryBreakdownProps {
  period: AnalyticsPeriod
  repo?: string | null
}

function formatTime(seconds: number): string {
  if (seconds < 60) return `${seconds.toFixed(1)}s`
  if (seconds < 3600) return `${(seconds / 60).toFixed(1)}m`
  return `${(seconds / 3600).toFixed(1)}h`
}

export function CategoryBreakdown({ period, repo }: CategoryBreakdownProps) {
  const [data, setData] = useState<CategoryResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)

    fetchAnalyticsCategories(period, repo)
      .then((result) => {
        if (!cancelled) setData(result)
      })
      .catch((err: Error) => {
        if (!cancelled) setError(err.message)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => { cancelled = true }
  }, [period, repo])

  if (loading) {
    return (
      <div className="rounded-lg border border-gray-700 bg-gray-900 p-4">
        <div className="h-48 animate-pulse bg-gray-800 rounded" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="rounded-lg border border-gray-700 bg-gray-900 p-4">
        <div className="text-sm text-red-400">Failed to load categories: {error}</div>
      </div>
    )
  }

  if (!data || data.categories.length === 0) {
    return (
      <div className="rounded-lg border border-gray-700 bg-gray-900 p-4">
        <h3 className="text-sm font-medium text-gray-300 mb-2">Category Breakdown</h3>
        <div className="flex items-center justify-center h-32 text-gray-500 text-sm">
          No category data available
        </div>
      </div>
    )
  }

  return (
    <div className="rounded-lg border border-gray-700 bg-gray-900 p-4">
      <h3 className="text-sm font-medium text-gray-300 mb-3">Category Breakdown</h3>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-xs text-gray-400 uppercase tracking-wider border-b border-gray-700">
              <th className="text-left py-2 pr-4">Category</th>
              <th className="text-right py-2 px-3">Count</th>
              <th className="text-right py-2 px-3">Merge Rate</th>
              <th className="text-right py-2 px-3">Avg Cost</th>
              <th className="text-right py-2 pl-3">Avg Time</th>
            </tr>
          </thead>
          <tbody>
            {data.categories.map((cat) => (
              <tr key={cat.category} className="border-b border-gray-800 hover:bg-gray-800/50">
                <td className="py-2 pr-4 text-gray-200 capitalize">
                  {cat.category}
                  {cat.low_sample && (
                    <span
                      className="ml-2 inline-flex items-center rounded bg-yellow-900/40 px-1.5 py-0.5 text-xs text-yellow-400"
                      title="Fewer than 3 tasks — metrics may not be representative"
                    >
                      low sample
                    </span>
                  )}
                </td>
                <td className="py-2 px-3 text-right text-gray-300">{cat.count}</td>
                <td className="py-2 px-3 text-right text-gray-300">
                  {(cat.merge_rate * 100).toFixed(1)}%
                </td>
                <td className="py-2 px-3 text-right text-gray-300">
                  ${cat.avg_cost_usd.toFixed(4)}
                </td>
                <td className="py-2 pl-3 text-right text-gray-300">
                  {formatTime(cat.avg_pipeline_seconds)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
