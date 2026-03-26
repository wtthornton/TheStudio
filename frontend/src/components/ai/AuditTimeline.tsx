/**
 * AuditTimeline — Vertical timeline of AI action entries with undo affordances.
 *
 * Per SG 8.3 "Action Audit + Undo": show what changed and enable reversal.
 * Most recent entry at top. Entries marked as AI or human actor.
 * SG 8.6: AI labeling on AI-actor entries.
 *
 * Epic 55.4
 */

export interface AuditEntry {
  id: string
  timestamp: string
  description: string
  actor: 'ai' | 'human'
  status: 'completed' | 'pending' | 'reverted' | 'failed'
  /** Whether this entry can be undone/reverted */
  mutable?: boolean
}

const STATUS_STYLES: Record<AuditEntry['status'], { label: string; className: string }> = {
  completed: { label: 'Completed', className: 'bg-[rgba(22,163,74,0.2)] text-green-500' },
  pending: { label: 'Pending', className: 'bg-[rgba(59,130,246,0.2)] text-blue-500' },
  reverted: { label: 'Reverted', className: 'bg-gray-800 text-gray-400' },
  failed: { label: 'Failed', className: 'bg-[rgba(239,68,68,0.2)] text-red-500' },
}

const ACTOR_LABELS: Record<AuditEntry['actor'], string> = {
  ai: 'AI',
  human: 'Human',
}

interface AuditTimelineProps {
  entries: AuditEntry[]
  onUndo?: (entryId: string) => void
}

export function AuditTimeline({ entries, onUndo }: AuditTimelineProps) {
  // Empty state
  if (entries.length === 0) {
    return (
      <section
        aria-label="Audit timeline"
        className="rounded-lg border border-gray-700 bg-gray-900 p-6 text-center"
        data-testid="audit-timeline"
      >
        <p className="text-sm text-gray-500" data-testid="audit-timeline-empty">
          No audit entries yet
        </p>
      </section>
    )
  }

  return (
    <section
      aria-label="Audit timeline"
      className="rounded-lg border border-gray-700 bg-gray-900 p-4"
      data-testid="audit-timeline"
    >
      <h3 className="mb-3 text-xs font-semibold uppercase tracking-wide text-gray-500">
        Audit Trail
      </h3>

      <ol className="relative space-y-0 border-l border-gray-700 ml-2">
        {entries.map((entry) => {
          const statusStyle = STATUS_STYLES[entry.status]

          return (
            <li
              key={entry.id}
              className="relative pb-4 pl-6 last:pb-0"
              data-testid={`audit-entry-${entry.id}`}
            >
              {/* Timeline dot */}
              <span
                className={`absolute -left-1.5 top-1 h-3 w-3 rounded-full border-2 border-gray-900 ${
                  entry.status === 'completed'
                    ? 'bg-emerald-500'
                    : entry.status === 'pending'
                      ? 'bg-blue-500'
                      : entry.status === 'failed'
                        ? 'bg-red-500'
                        : 'bg-gray-600'
                }`}
                aria-hidden="true"
              />

              {/* Entry content */}
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0 flex-1">
                  {/* Timestamp + actor */}
                  <div className="flex flex-wrap items-center gap-2 text-xs">
                    <time className="text-gray-500 tabular-nums" data-testid="audit-entry-timestamp">
                      {entry.timestamp}
                    </time>
                    <span
                      className={`rounded px-1.5 py-0.5 text-xs font-medium ${
                        entry.actor === 'ai'
                          ? 'bg-purple-900/40 text-purple-400'
                          : 'bg-gray-700 text-gray-300'
                      }`}
                      data-testid="audit-entry-actor"
                    >
                      {ACTOR_LABELS[entry.actor]}
                    </span>
                    {/* SG 8.6: AI label */}
                    {entry.actor === 'ai' && (
                      <span className="text-xs text-gray-600">AI-generated</span>
                    )}
                  </div>

                  {/* Description */}
                  <p
                    className="mt-1 text-sm text-gray-200"
                    data-testid="audit-entry-description"
                  >
                    {entry.description}
                  </p>
                </div>

                {/* Status badge + undo */}
                <div className="flex shrink-0 items-center gap-2">
                  <span
                    className={`rounded-full px-2 py-0.5 text-xs font-medium ${statusStyle.className}`}
                    data-testid="audit-entry-status"
                  >
                    {statusStyle.label}
                  </span>

                  {entry.mutable && onUndo && (
                    <button
                      type="button"
                      onClick={() => onUndo(entry.id)}
                      className="rounded px-2 py-1 text-xs text-gray-400 hover:text-gray-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-amber-500"
                      aria-label={`Undo: ${entry.description}`}
                      data-testid={`audit-undo-${entry.id}`}
                    >
                      Undo
                    </button>
                  )}
                </div>
              </div>
            </li>
          )
        })}
      </ol>
    </section>
  )
}
