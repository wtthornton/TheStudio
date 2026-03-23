/**
 * ThroughputChart -- Epic 39, Story 39.6.
 *
 * Bar chart showing completed tasks per day/week.
 * Uses Chart.js (react-chartjs-2) which is already installed.
 */

import { useEffect, useState } from 'react'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js'
import { Bar } from 'react-chartjs-2'
import type { AnalyticsPeriod, ThroughputResponse } from '../../lib/api'
import { fetchAnalyticsThroughput } from '../../lib/api'

// Register Chart.js components
ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend)

interface ThroughputChartProps {
  period: AnalyticsPeriod
  repo?: string | null
}

export function ThroughputChart({ period, repo }: ThroughputChartProps) {
  const [data, setData] = useState<ThroughputResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)

    fetchAnalyticsThroughput(period, 'day', repo)
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
        <div className="h-64 animate-pulse bg-gray-800 rounded" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="rounded-lg border border-gray-700 bg-gray-900 p-4">
        <div className="text-sm text-red-400">Failed to load throughput: {error}</div>
      </div>
    )
  }

  if (!data || data.data.length === 0) {
    return (
      <div className="rounded-lg border border-gray-700 bg-gray-900 p-4">
        <h3 className="text-sm font-medium text-gray-300 mb-2">Throughput</h3>
        <div className="flex items-center justify-center h-48 text-gray-500 text-sm">
          No completed tasks in this period
        </div>
      </div>
    )
  }

  const chartData = {
    labels: data.data.map((d) => d.date),
    datasets: [
      {
        label: 'Tasks completed',
        data: data.data.map((d) => d.count),
        backgroundColor: 'rgba(99, 102, 241, 0.7)',
        borderColor: 'rgba(99, 102, 241, 1)',
        borderWidth: 1,
        borderRadius: 3,
      },
    ],
  }

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      title: { display: false },
    },
    scales: {
      x: {
        ticks: { color: '#9ca3af', maxRotation: 45 },
        grid: { color: 'rgba(75, 85, 99, 0.3)' },
      },
      y: {
        beginAtZero: true,
        ticks: {
          color: '#9ca3af',
          stepSize: 1,
          callback: (value: string | number) => Math.floor(Number(value)) === Number(value) ? value : null,
        },
        grid: { color: 'rgba(75, 85, 99, 0.3)' },
      },
    },
  }

  return (
    <div className="rounded-lg border border-gray-700 bg-gray-900 p-4">
      <h3 className="text-sm font-medium text-gray-300 mb-3">Throughput</h3>
      <div className="h-64">
        <Bar data={chartData} options={options} />
      </div>
    </div>
  )
}
