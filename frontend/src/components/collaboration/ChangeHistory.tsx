/**
 * ChangeHistory — Epic 56.4
 *
 * Timeline of changes to an artifact, most recent first.
 */

export interface ChangeEntry {
  id: string
  actor: string
  timestamp: string // ISO 8601
  description: string
}

export interface ChangeHistoryProps {
  changes: ChangeEntry[]
}

export function ChangeHistory({ changes }: ChangeHistoryProps) {
  // Sort most recent first (defensive copy)
  const sorted = [...changes].sort(
    (a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime(),
  )

  return (
    <section
      className="rounded-lg border border-gray-800 bg-gray-900 p-4"
      data-testid="change-history"
      aria-label="Change History"
    >
      <h3 className="mb-3 text-sm font-semibold text-gray-100">Change History</h3>

      {sorted.length === 0 ? (
        <p className="py-4 text-center text-sm text-gray-500" data-testid="change-history-empty">
          No changes recorded
        </p>
      ) : (
        <ol className="space-y-2" data-testid="change-history-list">
          {sorted.map((entry) => (
            <li
              key={entry.id}
              className="flex items-start gap-3 rounded border border-gray-800 bg-gray-950 px-3 py-2"
              data-testid={`change-entry-${entry.id}`}
            >
              {/* Timeline dot */}
              <div
                className="mt-1.5 h-2 w-2 flex-shrink-0 rounded-full bg-indigo-500"
                aria-hidden="true"
              />
              <div className="min-w-0 flex-1">
                <div className="mb-0.5 flex items-center gap-2 text-xs text-gray-500">
                  <span className="font-medium text-gray-300" data-testid="change-actor">
                    {entry.actor}
                  </span>
                  <time dateTime={entry.timestamp} data-testid="change-time">
                    {new Date(entry.timestamp).toLocaleString()}
                  </time>
                </div>
                <p className="text-sm text-gray-200" data-testid="change-description">
                  {entry.description}
                </p>
              </div>
            </li>
          ))}
        </ol>
      )}
    </section>
  )
}
