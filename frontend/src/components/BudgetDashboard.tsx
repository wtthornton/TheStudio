/**
 * BudgetDashboard — Epic 37 Slice 4 (37.22).
 *
 * Components:
 *   - Period selector (1d / 7d / 30d)
 *   - SummaryCards — total cost, calls, cache hit rate
 *   - SpendChart — stacked bar (Chart.js) of daily spend
 *   - CostBreakdown — horizontal bar charts by stage and by model
 *   - BudgetAlertConfig — threshold inputs + action toggles
 */

import { useEffect, useState, useCallback } from 'react'
import { EmptyState } from './EmptyState'
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
import { useBudgetStore } from '../stores/budget-store'
import type { Period } from '../stores/budget-store'
import type { BudgetConfigUpdate } from '../lib/api'

// Register Chart.js components
ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend)

// ---------------------------------------------------------------------------
// Period Selector
// ---------------------------------------------------------------------------

interface PeriodSelectorProps {
  value: Period
  onChange: (p: Period) => void
}

function PeriodSelector({ value, onChange }: PeriodSelectorProps) {
  const options: { label: string; value: Period }[] = [
    { label: '1d', value: '1d' },
    { label: '7d', value: '7d' },
    { label: '30d', value: '30d' },
  ]
  return (
    <div className="flex gap-1 rounded-md border border-gray-700 bg-gray-800 p-1">
      {options.map((opt) => (
        <button
          key={opt.value}
          onClick={() => onChange(opt.value)}
          className={`rounded px-3 py-1 text-sm font-medium transition-colors ${
            value === opt.value
              ? 'bg-indigo-600 text-white'
              : 'text-gray-400 hover:text-gray-200'
          }`}
        >
          {opt.label}
        </button>
      ))}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Summary Cards
// ---------------------------------------------------------------------------

function SummaryCards() {
  const summary = useBudgetStore((s) => s.summary)
  const config = useBudgetStore((s) => s.config)

  if (!summary) return null

  const weeklyCapPct =
    config?.weekly_budget_cap && summary.total_cost > 0
      ? Math.min(100, (summary.total_cost / config.weekly_budget_cap) * 100)
      : null

  const cards = [
    {
      label: 'Total Spend',
      value: `$${summary.total_cost.toFixed(4)}`,
      sub: config?.weekly_budget_cap
        ? `Cap: $${config.weekly_budget_cap.toFixed(2)}`
        : undefined,
      accent:
        weeklyCapPct !== null && weeklyCapPct >= 90
          ? 'text-red-400'
          : weeklyCapPct !== null && weeklyCapPct >= 75
            ? 'text-yellow-400'
            : 'text-indigo-400',
    },
    {
      label: 'Total API Calls',
      value: summary.total_calls.toLocaleString(),
      sub: undefined,
      accent: 'text-blue-400',
    },
    {
      label: 'Cache Hit Rate',
      value: `${(summary.cache_hit_rate * 100).toFixed(1)}%`,
      sub: undefined,
      accent: 'text-green-400',
    },
  ]

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
      {cards.map((card) => (
        <div key={card.label} className="rounded-lg border border-gray-700 bg-gray-900 p-4">
          <p className="text-xs text-gray-400">{card.label}</p>
          <p className={`mt-1 text-2xl font-semibold ${card.accent}`}>{card.value}</p>
          {card.sub && <p className="mt-0.5 text-xs text-gray-500">{card.sub}</p>}
        </div>
      ))}
    </div>
  )
}

// ---------------------------------------------------------------------------
// SpendChart — stacked bar (daily spend over the period)
// ---------------------------------------------------------------------------

const MODEL_COLORS = [
  'rgba(99, 102, 241, 0.8)',   // indigo
  'rgba(16, 185, 129, 0.8)',   // emerald
  'rgba(245, 158, 11, 0.8)',   // amber
  'rgba(239, 68, 68, 0.8)',    // red
  'rgba(59, 130, 246, 0.8)',   // blue
  'rgba(168, 85, 247, 0.8)',   // purple
  'rgba(20, 184, 166, 0.8)',   // teal
  'rgba(249, 115, 22, 0.8)',   // orange
]

function SpendChart() {
  const history = useBudgetStore((s) => s.history)

  if (!history || history.by_day.length === 0) {
    return (
      <div className="flex h-48 items-center justify-center rounded-lg border border-gray-700 bg-gray-900 text-sm text-gray-500">
        No spend data for this period
      </div>
    )
  }

  // Build datasets: one dataset per model, distributed proportionally across days
  // by_day gives total per day; by_model gives total per model across window.
  // We distribute each day's cost proportionally by model share.
  const totalCost = history.total_cost
  const models = history.by_model.slice(0, 8) // cap at 8 colours
  const days = history.by_day

  const datasets =
    models.length > 0 && totalCost > 0
      ? models.map((model, idx) => {
          const modelShare = model.total_cost / totalCost
          return {
            label: model.key,
            data: days.map((d) => parseFloat((d.total_cost * modelShare).toFixed(6))),
            backgroundColor: MODEL_COLORS[idx % MODEL_COLORS.length],
            stack: 'stack0',
          }
        })
      : [
          {
            label: 'Cost ($)',
            data: days.map((d) => d.total_cost),
            backgroundColor: MODEL_COLORS[0],
            stack: 'stack0',
          },
        ]

  const chartData = {
    labels: days.map((d) => d.key),
    datasets,
  }

  const options = {
    responsive: true,
    maintainAspectRatio: true,
    plugins: {
      legend: {
        display: models.length > 1,
        labels: { color: '#9ca3af', boxWidth: 12, padding: 8 },
      },
      tooltip: {
        callbacks: {
          label: (ctx: { dataset: { label?: string }; raw: unknown }) =>
            ` ${ctx.dataset.label ?? ''}: $${Number(ctx.raw).toFixed(4)}`,
        },
      },
    },
    scales: {
      x: {
        stacked: true,
        ticks: { color: '#6b7280', maxRotation: 45 },
        grid: { color: 'rgba(75,85,99,0.2)' },
      },
      y: {
        stacked: true,
        ticks: {
          color: '#6b7280',
          callback: (val: string | number) => `$${Number(val).toFixed(2)}`,
        },
        grid: { color: 'rgba(75,85,99,0.2)' },
      },
    },
  }

  return (
    <div className="rounded-lg border border-gray-700 bg-gray-900 p-4">
      <h3 className="mb-3 text-sm font-medium text-gray-300">Daily Spend</h3>
      <Bar data={chartData} options={options} />
    </div>
  )
}

// ---------------------------------------------------------------------------
// Horizontal bar chart helper
// ---------------------------------------------------------------------------

interface HBarChartProps {
  title: string
  entries: { key: string; total_cost: number; call_count: number }[]
  colorStart?: string
}

function HBarChart({ title, entries, colorStart = 'rgba(99,102,241,0.75)' }: HBarChartProps) {
  if (entries.length === 0) {
    return (
      <div className="flex h-32 items-center justify-center rounded-lg border border-gray-700 bg-gray-900 text-sm text-gray-500">
        No data
      </div>
    )
  }

  const sorted = [...entries].sort((a, b) => b.total_cost - a.total_cost).slice(0, 12)

  const chartData = {
    labels: sorted.map((e) => e.key),
    datasets: [
      {
        label: 'Cost ($)',
        data: sorted.map((e) => e.total_cost),
        backgroundColor: colorStart,
        borderRadius: 3,
      },
    ],
  }

  const options = {
    indexAxis: 'y' as const,
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      tooltip: {
        callbacks: {
          label: (ctx: { raw: unknown }) => ` $${Number(ctx.raw).toFixed(4)}`,
        },
      },
    },
    scales: {
      x: {
        ticks: {
          color: '#6b7280',
          callback: (val: string | number) => `$${Number(val).toFixed(2)}`,
        },
        grid: { color: 'rgba(75,85,99,0.2)' },
      },
      y: {
        ticks: { color: '#9ca3af' },
        grid: { display: false },
      },
    },
  }

  const height = Math.max(120, sorted.length * 28)

  return (
    <div className="rounded-lg border border-gray-700 bg-gray-900 p-4">
      <h3 className="mb-3 text-sm font-medium text-gray-300">{title}</h3>
      <div style={{ height }}>
        <Bar data={chartData} options={options} />
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// CostBreakdown — by stage + by model horizontal bars
// ---------------------------------------------------------------------------

function CostBreakdown() {
  const byStage = useBudgetStore((s) => s.byStage)
  const byModel = useBudgetStore((s) => s.byModel)

  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
      <HBarChart
        title="Cost by Pipeline Stage"
        entries={byStage?.by_stage ?? []}
        colorStart="rgba(16,185,129,0.75)"
      />
      <HBarChart
        title="Cost by Model"
        entries={byModel?.by_model ?? []}
        colorStart="rgba(99,102,241,0.75)"
      />
    </div>
  )
}

// ---------------------------------------------------------------------------
// BudgetAlertConfig — thresholds + action toggles
// ---------------------------------------------------------------------------

function BudgetAlertConfig() {
  const config = useBudgetStore((s) => s.config)
  const saving = useBudgetStore((s) => s.saving)
  const error = useBudgetStore((s) => s.error)
  const saveConfig = useBudgetStore((s) => s.saveConfig)
  const clearError = useBudgetStore((s) => s.clearError)

  const [form, setForm] = useState<BudgetConfigUpdate>({})
  const [dirty, setDirty] = useState(false)

  // Initialise form from config
  useEffect(() => {
    if (config) {
      setForm({
        daily_spend_warning: config.daily_spend_warning,
        weekly_budget_cap: config.weekly_budget_cap,
        per_task_warning: config.per_task_warning,
        pause_on_budget_exceeded: config.pause_on_budget_exceeded,
        model_downgrade_on_approach: config.model_downgrade_on_approach,
        downgrade_threshold_percent: config.downgrade_threshold_percent,
      })
      setDirty(false)
    }
  }, [config])

  const handleNumberChange = useCallback(
    (field: keyof BudgetConfigUpdate, value: string) => {
      const num = parseFloat(value)
      if (!isNaN(num)) {
        setForm((f) => ({ ...f, [field]: num }))
        setDirty(true)
      }
    },
    [],
  )

  const handleToggle = useCallback((field: keyof BudgetConfigUpdate, checked: boolean) => {
    setForm((f) => ({ ...f, [field]: checked }))
    setDirty(true)
  }, [])

  const handleSave = useCallback(async () => {
    await saveConfig(form)
    setDirty(false)
  }, [form, saveConfig])

  if (!config) return null

  const numberFields: {
    key: keyof BudgetConfigUpdate
    label: string
    unit: string
    help: string
  }[] = [
    {
      key: 'daily_spend_warning',
      label: 'Daily Spend Warning',
      unit: '$',
      help: 'Alert when daily spend exceeds this amount',
    },
    {
      key: 'weekly_budget_cap',
      label: 'Weekly Budget Cap',
      unit: '$',
      help: 'Maximum weekly spend before auto-pause (if enabled)',
    },
    {
      key: 'per_task_warning',
      label: 'Per-Task Cost Warning',
      unit: '$',
      help: 'Alert when a single task exceeds this cost',
    },
    {
      key: 'downgrade_threshold_percent',
      label: 'Downgrade Threshold',
      unit: '%',
      help: 'Switch to cheaper model when this % of cap is reached',
    },
  ]

  const toggleFields: {
    key: 'pause_on_budget_exceeded' | 'model_downgrade_on_approach'
    label: string
    help: string
  }[] = [
    {
      key: 'pause_on_budget_exceeded',
      label: 'Pause on Budget Exceeded',
      help: 'Automatically pause all active workflows when weekly cap is breached',
    },
    {
      key: 'model_downgrade_on_approach',
      label: 'Downgrade Model on Approach',
      help: 'Switch to cheaper model when spend approaches the downgrade threshold',
    },
  ]

  return (
    <div className="rounded-lg border border-gray-700 bg-gray-900 p-6">
      <h3 className="mb-4 text-sm font-semibold text-gray-200">Budget Alert Configuration</h3>

      {error && (
        <div className="mb-4 flex items-center justify-between rounded border border-red-700 bg-red-900/30 px-3 py-2">
          <span className="text-xs text-red-300">{error}</span>
          <button onClick={clearError} className="ml-4 text-xs text-red-400 hover:text-red-200">
            ✕
          </button>
        </div>
      )}

      {/* Number inputs */}
      <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-2">
        {numberFields.map((field) => (
          <div key={field.key}>
            <label className="mb-1 block text-xs font-medium text-gray-300">
              {field.label}
              <span className="ml-1 text-gray-500">({field.unit})</span>
            </label>
            <input
              type="number"
              step={field.unit === '%' ? '1' : '0.01'}
              min={0}
              max={field.unit === '%' ? 100 : undefined}
              value={
                (form[field.key] as number | undefined) ??
                (config[field.key as keyof typeof config] as number)
              }
              onChange={(e) => handleNumberChange(field.key, e.target.value)}
              className="w-full rounded border border-gray-600 bg-gray-800 px-3 py-1.5 text-sm text-gray-100 focus:border-indigo-500 focus:outline-none"
            />
            <p className="mt-0.5 text-xs text-gray-500">{field.help}</p>
          </div>
        ))}
      </div>

      {/* Toggle fields */}
      <div className="mb-6 space-y-3">
        {toggleFields.map((field) => (
          <div key={field.key} className="flex items-start gap-3">
            <button
              role="switch"
              aria-checked={
                (form[field.key] as boolean | undefined) ??
                (config[field.key as keyof typeof config] as boolean)
              }
              onClick={() =>
                handleToggle(
                  field.key,
                  !(
                    (form[field.key] as boolean | undefined) ??
                    (config[field.key as keyof typeof config] as boolean)
                  ),
                )
              }
              className={`mt-0.5 flex h-5 w-9 shrink-0 cursor-pointer rounded-full transition-colors focus:outline-none ${
                ((form[field.key] as boolean | undefined) ??
                  (config[field.key as keyof typeof config] as boolean))
                  ? 'bg-indigo-600'
                  : 'bg-gray-600'
              }`}
            >
              <span
                className={`h-5 w-5 rounded-full bg-white shadow transition-transform ${
                  ((form[field.key] as boolean | undefined) ??
                    (config[field.key as keyof typeof config] as boolean))
                    ? 'translate-x-4'
                    : 'translate-x-0'
                }`}
              />
            </button>
            <div>
              <p className="text-sm text-gray-200">{field.label}</p>
              <p className="text-xs text-gray-500">{field.help}</p>
            </div>
          </div>
        ))}
      </div>

      {/* Actions */}
      <div className="flex items-center gap-3">
        <button
          onClick={handleSave}
          disabled={saving || !dirty}
          className="rounded bg-indigo-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {saving ? 'Saving…' : 'Save Configuration'}
        </button>
        {config.updated_at && (
          <span className="text-xs text-gray-500">
            Last updated: {new Date(config.updated_at).toLocaleString()}
          </span>
        )}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// BudgetDashboard — main export
// ---------------------------------------------------------------------------

export function BudgetDashboard() {
  const period = useBudgetStore((s) => s.period)
  const loading = useBudgetStore((s) => s.loading)
  const error = useBudgetStore((s) => s.error)
  const summary = useBudgetStore((s) => s.summary)
  const loadAll = useBudgetStore((s) => s.loadAll)
  const setPeriod = useBudgetStore((s) => s.setPeriod)
  const clearError = useBudgetStore((s) => s.clearError)

  useEffect(() => {
    void loadAll()
  }, [loadAll])

  return (
    <div className="mx-auto max-w-6xl px-6 py-6">
      {/* Header row */}
      <div className="mb-6 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-100">Budget Dashboard</h2>
        <div className="flex items-center gap-3">
          {loading && <span className="text-xs text-gray-400">Loading…</span>}
          <PeriodSelector value={period} onChange={setPeriod} />
          <button
            onClick={() => void loadAll()}
            disabled={loading}
            className="rounded border border-gray-700 px-2 py-1 text-xs text-gray-400 hover:border-gray-500 hover:text-gray-200 disabled:opacity-50"
            title="Refresh"
          >
            ↻
          </button>
        </div>
      </div>

      {error && (
        <div className="mb-4 flex items-center justify-between rounded border border-red-700 bg-red-900/30 px-3 py-2">
          <span className="text-sm text-red-300">{error}</span>
          <button onClick={clearError} className="ml-4 text-xs text-red-400 hover:text-red-200">
            ✕
          </button>
        </div>
      )}

      {/* Empty state — no budget data yet and not loading */}
      {!loading && !error && summary === null && (
        <EmptyState
          icon={
            <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <rect x="2" y="7" width="20" height="14" rx="2" />
              <path d="M16 3H8a2 2 0 0 0-2 2v2h12V5a2 2 0 0 0-2-2z" />
              <circle cx="12" cy="14" r="2" />
            </svg>
          }
          heading="No spend data yet"
          description="Budget metrics will appear here once tasks start processing. Configure alerts and spending caps to keep LLM costs in check."
          primaryAction={{ label: 'Configure Budget Alerts', href: '/admin/ui/settings' }}
          secondaryAction={{ label: 'View Admin Console', href: '/admin/ui/' }}
          data-testid="budget-empty"
          className="py-16"
        />
      )}

      <div className="space-y-6">
        {/* Summary KPIs */}
        <SummaryCards />

        {/* SpendChart — stacked bar */}
        <SpendChart />

        {/* CostBreakdown — by stage + by model */}
        <CostBreakdown />

        {/* BudgetAlertConfig */}
        <BudgetAlertConfig />
      </div>
    </div>
  )
}
