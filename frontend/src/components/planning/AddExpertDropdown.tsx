/** AddExpertDropdown — add an expert to the routing plan (Epic 36, Story 36.15c). */

import type { ChangeEvent } from 'react'

/** Canonical list of expert classes available in the routing system. */
export const AVAILABLE_EXPERT_CLASSES = [
  'SecurityExpert',
  'TestExpert',
  'DatabaseExpert',
  'FrontendExpert',
  'BackendExpert',
  'DevOpsExpert',
  'AccessibilityExpert',
  'PerformanceExpert',
] as const

export type ExpertClass = (typeof AVAILABLE_EXPERT_CLASSES)[number]

export interface AddExpertDropdownProps {
  /** Expert classes already present in the routing plan — excluded from the dropdown. */
  selectedClasses: string[]
  /** Called with the chosen expert class when the user selects one. */
  onAdd: (expertClass: string) => void
  /** Disable the control while a save is in progress. */
  disabled?: boolean
}

/* ── component ───────────────────────────────────────────────── */

export default function AddExpertDropdown({
  selectedClasses,
  onAdd,
  disabled = false,
}: AddExpertDropdownProps) {
  const available = AVAILABLE_EXPERT_CLASSES.filter(
    (cls) => !selectedClasses.includes(cls),
  )

  const handleChange = (e: ChangeEvent<HTMLSelectElement>) => {
    const value = e.target.value
    if (!value) return
    onAdd(value)
    // Reset the select back to the placeholder so it's ready for the next pick
    e.target.value = ''
  }

  if (available.length === 0) {
    return (
      <span className="text-xs text-gray-500 italic">All experts added</span>
    )
  }

  return (
    <select
      onChange={handleChange}
      disabled={disabled}
      defaultValue=""
      className="border border-blue-700 bg-gray-900 text-blue-400 text-sm px-3 py-1.5 rounded disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer hover:border-blue-500 transition-colors"
      aria-label="Add expert"
    >
      <option value="" disabled>
        + Add Expert
      </option>
      {available.map((cls) => (
        <option key={cls} value={cls} className="text-gray-200 bg-gray-900">
          {cls}
        </option>
      ))}
    </select>
  )
}
