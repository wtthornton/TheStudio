/** Displays the last 20 SSE events in a scrollable list. */

import { usePipelineStore } from '../stores/pipeline-store'

function formatTime(ts: number): string {
  const d = new Date(ts)
  return d.toLocaleTimeString('en-US', { hour12: false })
}

function eventLabel(type: string): { text: string; className: string } {
  if (type.includes('gate.fail')) return { text: 'FAIL', className: 'text-red-400' }
  if (type.includes('gate.pass')) return { text: 'PASS', className: 'text-emerald-400' }
  if (type.includes('stage.enter')) return { text: 'ENTER', className: 'text-blue-400' }
  if (type.includes('stage.exit')) return { text: 'EXIT', className: 'text-amber-400' }
  if (type.includes('full_state')) return { text: 'SYNC', className: 'text-purple-400' }
  return { text: type.split('.').pop() ?? type, className: 'text-gray-400' }
}

export function EventLog() {
  const events = usePipelineStore((s) => s.events)

  return (
    <div
      className="rounded-lg border border-gray-800 bg-gray-900 p-3"
      data-testid="event-log"
    >
      <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-gray-500">
        Recent Events
      </h3>
      {events.length === 0 ? (
        <p className="text-xs text-gray-600" data-testid="event-log-empty">
          No events yet
        </p>
      ) : (
        <ul className="max-h-64 space-y-1 overflow-y-auto" data-testid="event-list">
          {events.map((ev) => {
            const badge = eventLabel(ev.type)
            return (
              <li
                key={ev.id}
                className="flex items-center gap-2 text-xs font-mono"
                data-testid="event-entry"
              >
                <span className="text-gray-600">{formatTime(ev.timestamp)}</span>
                <span className={`font-semibold ${badge.className}`}>{badge.text}</span>
                {ev.stage && <span className="text-gray-300">{ev.stage}</span>}
                {ev.taskpacketId && (
                  <span className="text-gray-500 truncate max-w-32">{ev.taskpacketId}</span>
                )}
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )
}
