/** Pipeline stage definitions with display names and colors. */

export const PIPELINE_STAGES = [
  { id: 'intake', label: 'Intake', color: '#3b82f6' },       // blue-500
  { id: 'context', label: 'Context', color: '#6366f1' },     // indigo-500
  { id: 'intent', label: 'Intent', color: '#8b5cf6' },       // violet-500
  { id: 'router', label: 'Router', color: '#a855f7' },       // purple-500
  { id: 'assembler', label: 'Assembler', color: '#d946ef' }, // fuchsia-500
  { id: 'implement', label: 'Implement', color: '#ec4899' }, // pink-500
  { id: 'verify', label: 'Verify', color: '#f59e0b' },       // amber-500
  { id: 'qa', label: 'QA', color: '#10b981' },               // emerald-500
  { id: 'publish', label: 'Publish', color: '#06b6d4' },     // cyan-500
] as const

export type StageId = (typeof PIPELINE_STAGES)[number]['id']

export const STAGE_COUNT = PIPELINE_STAGES.length // 9

/** Status colors for stage nodes — align with SG 3.1 cross-surface semantics. */
export const STATUS_COLORS = {
  idle: '#4b5563',     // gray-600 — neutral / unknown
  active: '#2563eb',   // blue-600 — in progress / running / info
  review: '#ca8a04',   // yellow-600 — warning / review / degraded
  passed: '#16a34a',   // green-600 — success
  failed: '#dc2626',   // red-600 — error / failed
} as const
