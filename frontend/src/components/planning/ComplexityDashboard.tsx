import type { TaskPacketRead } from '../../lib/api'
import MetricCard from './MetricCard'
import RiskFlags from './RiskFlags'
import FileHeatmap from './FileHeatmap'

/* ── helpers ─────────────────────────────────────────────────── */

type Band = 'low' | 'medium' | 'high'

interface ComplexityData {
  score?: number
  band?: Band
  dimensions?: {
    scope_breadth?: number
    risk_flag_count?: number
    dependency_count?: number
    lines_estimate?: number
    expert_coverage?: number
  }
}

function bandColor(band: Band | undefined): 'green' | 'amber' | 'red' {
  if (band === 'low') return 'green'
  if (band === 'medium') return 'amber'
  return 'red'
}

function expertCoverageColor(count: number | null | undefined): 'green' | 'amber' | 'red' {
  if (count == null) return 'gray' as never // will show pending via MetricCard
  if (count >= 2) return 'green'
  if (count === 1) return 'amber'
  return 'red'
}

function riskFlagActiveCount(flags: Record<string, boolean> | null | undefined): number | null {
  if (flags == null) return null
  return Object.values(flags).filter(Boolean).length
}

function filesAffected(scope: Record<string, unknown> | null | undefined): number | null {
  if (scope == null) return null
  const est = scope.affected_files_estimate
  return typeof est === 'number' ? est : null
}

/* ── score bar ───────────────────────────────────────────────── */

function ScoreBar({ score, band }: { score: number | null; band: Band | undefined }) {
  if (score == null) {
    return (
      <div className="rounded-lg border border-gray-700 bg-gray-800 p-3">
        <p className="text-xs font-semibold uppercase tracking-wider text-gray-500 mb-2">
          Complexity Score
        </p>
        <p className="text-sm italic text-gray-600">Pending</p>
      </div>
    )
  }

  const color = bandColor(band)
  const barColorClass =
    color === 'green'
      ? 'bg-emerald-500'
      : color === 'amber'
        ? 'bg-amber-500'
        : 'bg-red-500'

  const textColorClass =
    color === 'green'
      ? 'text-emerald-400'
      : color === 'amber'
        ? 'text-amber-400'
        : 'text-red-400'

  const pct = Math.min(Math.max(score, 0), 100)

  return (
    <div className="rounded-lg border border-gray-700 bg-gray-800 p-3">
      <div className="flex items-center justify-between mb-2">
        <p className="text-xs font-semibold uppercase tracking-wider text-gray-500">
          Complexity Score
        </p>
        <span className={`text-lg font-bold ${textColorClass}`}>
          {Math.round(score)}
        </span>
      </div>
      <div className="h-2 w-full rounded-full bg-gray-700">
        <div
          className={`h-2 rounded-full transition-all ${barColorClass}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <p className={`mt-1 text-xs capitalize ${textColorClass}`}>{band ?? 'unknown'}</p>
    </div>
  )
}

/* ── icons (inline SVG to avoid dependency) ──────────────────── */

function FilesIcon() {
  return (
    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
    </svg>
  )
}

function FlagIcon() {
  return (
    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M3 21v-4m0 0V5a2 2 0 012-2h6.5l1 1H21l-3 6 3 6h-8.5l-1-1H5a2 2 0 00-2 2z" />
    </svg>
  )
}

function ExpertIcon() {
  return (
    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" />
    </svg>
  )
}

/* ── main component ──────────────────────────────────────────── */

export interface ComplexityDashboardProps {
  task: TaskPacketRead
}

export default function ComplexityDashboard({ task }: ComplexityDashboardProps) {
  const cx = task.complexity_index as ComplexityData | null | undefined
  const score = cx?.score ?? null
  const band = cx?.band as Band | undefined
  const dims = cx?.dimensions

  const fileCount = filesAffected(task.scope)
  const riskCount = riskFlagActiveCount(task.risk_flags)
  const expertCoverage = dims?.expert_coverage ?? null

  return (
    <div className="space-y-3">
      {/* Score bar */}
      <ScoreBar score={score} band={band} />

      {/* Metric cards row */}
      <div className="grid grid-cols-3 gap-3">
        <MetricCard
          label="Files Affected"
          value={fileCount}
          icon={<FilesIcon />}
          color={fileCount == null ? 'gray' : fileCount <= 5 ? 'green' : fileCount <= 15 ? 'amber' : 'red'}
        />
        <MetricCard
          label="Risk Flags"
          value={riskCount}
          icon={<FlagIcon />}
          color={riskCount == null ? 'gray' : riskCount === 0 ? 'green' : riskCount <= 2 ? 'amber' : 'red'}
        />
        <MetricCard
          label="Expert Coverage"
          value={expertCoverage}
          icon={<ExpertIcon />}
          color={expertCoverage == null ? 'gray' : expertCoverageColor(expertCoverage)}
        />
      </div>

      {/* Bottom row: heatmap + risk flags */}
      <div className="grid grid-cols-2 gap-3">
        <FileHeatmap scope={task.scope as { affected_files_estimate?: number; components?: string[]; file_references?: string[] } | null} />
        <RiskFlags flags={task.risk_flags} />
      </div>
    </div>
  )
}
