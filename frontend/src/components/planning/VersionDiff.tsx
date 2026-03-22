/** VersionDiff — field-level comparison between two intent spec versions (Epic 36, 36.11g). */

import type { IntentSpecRead } from '../../lib/api'

interface VersionDiffProps {
  left: IntentSpecRead
  right: IntentSpecRead
}

/** Classify each item as added, removed, or unchanged using Set-based exact match. */
function diffList(
  leftItems: string[],
  rightItems: string[],
): { value: string; status: 'added' | 'removed' | 'unchanged' }[] {
  const leftSet = new Set(leftItems)
  const rightSet = new Set(rightItems)

  const result: { value: string; status: 'added' | 'removed' | 'unchanged' }[] = []

  // Removed items (in left but not in right)
  for (const item of leftItems) {
    if (!rightSet.has(item)) {
      result.push({ value: item, status: 'removed' })
    }
  }

  // Unchanged items (in both)
  for (const item of rightItems) {
    if (leftSet.has(item)) {
      result.push({ value: item, status: 'unchanged' })
    }
  }

  // Added items (in right but not in left)
  for (const item of rightItems) {
    if (!leftSet.has(item)) {
      result.push({ value: item, status: 'added' })
    }
  }

  return result
}

const STATUS_CLASSES: Record<string, string> = {
  added: 'bg-emerald-900/40 text-emerald-300',
  removed: 'bg-red-900/40 text-red-300 line-through',
  unchanged: 'text-gray-300',
}

function DiffListSection({
  label,
  items,
}: {
  label: string
  items: { value: string; status: 'added' | 'removed' | 'unchanged' }[]
}) {
  if (items.length === 0) return null

  return (
    <section>
      <h4 className="mb-1 text-xs font-semibold uppercase tracking-wider text-gray-500">
        {label}
      </h4>
      <ul className="space-y-1 pl-5">
        {items.map((item, i) => (
          <li key={`${item.status}-${i}`} className={`text-sm ${STATUS_CLASSES[item.status]}`}>
            {item.status === 'added' && <span className="mr-1 text-emerald-400">+</span>}
            {item.status === 'removed' && <span className="mr-1 text-red-400">−</span>}
            {item.value}
          </li>
        ))}
      </ul>
    </section>
  )
}

export default function VersionDiff({ left, right }: VersionDiffProps) {
  const goalChanged = left.goal !== right.goal

  return (
    <div className="flex flex-col gap-4 overflow-y-auto" data-testid="version-diff">
      {/* Header */}
      <div className="flex items-center gap-2 text-xs text-gray-500">
        <span>Comparing v{left.version}</span>
        <span>→</span>
        <span>v{right.version}</span>
      </div>

      {/* Goal diff */}
      <section>
        <h4 className="mb-1 text-xs font-semibold uppercase tracking-wider text-gray-500">
          Goal
        </h4>
        {goalChanged ? (
          <div className="space-y-1">
            <p className="text-sm bg-red-900/40 text-red-300 line-through">{left.goal}</p>
            <p className="text-sm bg-emerald-900/40 text-emerald-300">{right.goal}</p>
          </div>
        ) : (
          <p className="text-sm text-gray-300">{right.goal}</p>
        )}
      </section>

      {/* Constraints diff */}
      <DiffListSection
        label="Constraints"
        items={diffList(left.constraints, right.constraints)}
      />

      {/* Acceptance Criteria diff */}
      <DiffListSection
        label="Acceptance Criteria"
        items={diffList(left.acceptance_criteria, right.acceptance_criteria)}
      />

      {/* Non-Goals diff */}
      <DiffListSection
        label="Non-Goals"
        items={diffList(left.non_goals, right.non_goals)}
      />
    </div>
  )
}

export { diffList }
