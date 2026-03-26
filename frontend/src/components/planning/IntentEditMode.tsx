/** IntentEditMode — edit form replacing right panel (Epic 36, 36.11e). */

import { useState, useCallback, useMemo } from 'react'
import { useIntentStore } from '../../stores/intent-store'
import type { IntentSpecRead } from '../../lib/api'

/* ------------------------------------------------------------------ */
/*  EditableList — reusable add/remove list editor                     */
/* ------------------------------------------------------------------ */

interface EditableListProps {
  label: string
  items: string[]
  onChange: (items: string[]) => void
  placeholder?: string
}

export function EditableList({ label, items, onChange, placeholder }: EditableListProps) {
  const [draft, setDraft] = useState('')

  const handleAdd = useCallback(() => {
    const trimmed = draft.trim()
    if (!trimmed) return
    onChange([...items, trimmed])
    setDraft('')
  }, [draft, items, onChange])

  const handleRemove = useCallback(
    (index: number) => {
      onChange(items.filter((_, i) => i !== index))
    },
    [items, onChange],
  )

  const handleUpdate = useCallback(
    (index: number, value: string) => {
      const next = [...items]
      next[index] = value
      onChange(next)
    },
    [items, onChange],
  )

  return (
    <section>
      <h4 className="mb-1 text-xs font-semibold uppercase tracking-wider text-gray-500">
        {label}
      </h4>
      <ul className="space-y-1">
        {items.map((item, i) => (
          <li key={i} className="flex items-center gap-1">
            <input
              type="text"
              value={item}
              onChange={(e) => handleUpdate(i, e.target.value)}
              className="flex-1 rounded border border-gray-600 bg-gray-800 px-2 py-1 text-sm text-gray-200 focus:border-blue-500 focus:outline-none"
            />
            <button
              type="button"
              onClick={() => handleRemove(i)}
              className="rounded px-1.5 py-0.5 text-xs text-red-400 hover:bg-red-900/30 hover:text-red-300"
              aria-label={`Remove ${label} item ${i + 1}`}
            >
              ✕
            </button>
          </li>
        ))}
      </ul>
      <div className="mt-1 flex items-center gap-1">
        <input
          type="text"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder={placeholder ?? `Add ${label.toLowerCase()}…`}
          className="flex-1 rounded border border-gray-700 bg-gray-800/60 px-2 py-1 text-sm text-gray-300 placeholder-gray-600 focus:border-blue-500 focus:outline-none"
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              e.preventDefault()
              handleAdd()
            }
          }}
        />
        <button
          type="button"
          onClick={handleAdd}
          disabled={!draft.trim()}
          className="rounded bg-gray-700 px-2 py-1 text-xs text-gray-300 hover:bg-gray-600 disabled:opacity-40"
        >
          Add
        </button>
      </div>
    </section>
  )
}

/* ------------------------------------------------------------------ */
/*  IntentEditMode — main edit form                                    */
/* ------------------------------------------------------------------ */

interface IntentEditModeProps {
  spec: IntentSpecRead
}

export default function IntentEditMode({ spec }: IntentEditModeProps) {
  const { saveEdit, setMode, saving } = useIntentStore()

  // Local edit state seeded from current spec
  const [goal, setGoal] = useState(spec.goal)
  const [constraints, setConstraints] = useState<string[]>([...spec.constraints])
  const [acceptanceCriteria, setAcceptanceCriteria] = useState<string[]>([
    ...spec.acceptance_criteria,
  ])
  const [nonGoals, setNonGoals] = useState<string[]>([...spec.non_goals])

  // Determine if anything changed (for save-disabled check)
  const unchanged = useMemo(() => {
    if (goal !== spec.goal) return false
    const arrEq = (a: string[], b: string[]) =>
      a.length === b.length && a.every((v, i) => v === b[i])
    if (!arrEq(constraints, spec.constraints)) return false
    if (!arrEq(acceptanceCriteria, spec.acceptance_criteria)) return false
    if (!arrEq(nonGoals, spec.non_goals)) return false
    return true
  }, [goal, constraints, acceptanceCriteria, nonGoals, spec])

  const handleSave = useCallback(async () => {
    // Filter out empty strings
    const filtered = {
      goal: goal.trim(),
      constraints: constraints.map((s) => s.trim()).filter(Boolean),
      acceptance_criteria: acceptanceCriteria.map((s) => s.trim()).filter(Boolean),
      non_goals: nonGoals.map((s) => s.trim()).filter(Boolean),
    }
    await saveEdit(filtered)
    // saveEdit sets mode back to 'view' on success
  }, [goal, constraints, acceptanceCriteria, nonGoals, saveEdit])

  const handleCancel = useCallback(() => {
    setMode('view')
  }, [setMode])

  return (
    <div className="flex flex-col gap-4 overflow-y-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-300">Edit Intent Specification</h3>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={handleSave}
            disabled={saving || unchanged || !goal.trim()}
            className="rounded bg-blue-600 px-3 py-1 text-xs font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {saving ? 'Saving…' : 'Save'}
          </button>
          <button
            type="button"
            onClick={handleCancel}
            disabled={saving}
            className="rounded px-3 py-1 text-xs text-gray-400 hover:text-gray-200"
          >
            Cancel
          </button>
        </div>
      </div>

      {/* Goal */}
      <section>
        <h4 className="mb-1 text-xs font-semibold uppercase tracking-wider text-gray-500">
          Goal
        </h4>
        <textarea
          value={goal}
          onChange={(e) => setGoal(e.target.value)}
          rows={3}
          className="w-full resize-y rounded border border-gray-600 bg-gray-800 px-3 py-2 text-sm text-gray-200 focus:border-blue-500 focus:outline-none"
        />
      </section>

      {/* Constraints */}
      <EditableList
        label="Constraints"
        items={constraints}
        onChange={setConstraints}
        placeholder="Add constraint…"
      />

      {/* Acceptance Criteria */}
      <EditableList
        label="Acceptance Criteria"
        items={acceptanceCriteria}
        onChange={setAcceptanceCriteria}
        placeholder="Add acceptance criterion…"
      />

      {/* Non-Goals */}
      <EditableList
        label="Non-Goals"
        items={nonGoals}
        onChange={setNonGoals}
        placeholder="Add non-goal…"
      />
    </div>
  )
}
