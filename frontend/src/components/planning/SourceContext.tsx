import type { TaskPacketRead } from '../../lib/api'

interface SourceContextProps {
  task: TaskPacketRead
}

function ComplexityBar({ value }: { value: number }) {
  const pct = Math.min(Math.max(value, 0), 100)
  const color =
    pct >= 70 ? 'bg-red-500' : pct >= 40 ? 'bg-amber-500' : 'bg-emerald-500'
  return (
    <div className="flex items-center gap-2">
      <div className="h-2 flex-1 rounded-full bg-gray-700">
        <div
          className={`h-2 rounded-full ${color}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-xs text-gray-400">{pct}</span>
    </div>
  )
}

function RiskFlagsList({ flags }: { flags: Record<string, boolean> }) {
  const entries = Object.entries(flags)
  if (entries.length === 0) return <span className="text-xs text-gray-500">No risk flags</span>
  return (
    <ul className="space-y-1">
      {entries.map(([flag, active]) => (
        <li key={flag} className="flex items-center gap-2 text-sm">
          <span className={active ? 'text-red-400' : 'text-emerald-400'}>
            {active ? '✗' : '✓'}
          </span>
          <span className="text-gray-300">{flag.replace(/_/g, ' ')}</span>
        </li>
      ))}
    </ul>
  )
}

function ScopeSection({ scope }: { scope: Record<string, unknown> }) {
  const files = (scope.files as string[] | undefined) ?? []
  const components = (scope.components as string[] | undefined) ?? []
  const fileCount = (scope.file_count as number | undefined) ?? files.length

  // Group files by directory
  const grouped: Record<string, string[]> = {}
  for (const f of files) {
    const parts = f.split('/')
    const dir = parts.length > 1 ? parts.slice(0, -1).join('/') : '.'
    const name = parts[parts.length - 1]
    if (!grouped[dir]) grouped[dir] = []
    grouped[dir].push(name)
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2 text-sm text-gray-300">
        <span className="text-gray-500">Files:</span>
        <span>{fileCount}</span>
      </div>
      {components.length > 0 && (
        <div className="space-y-1">
          <span className="text-xs text-gray-500">Components</span>
          <div className="flex flex-wrap gap-1">
            {components.map((c) => (
              <span
                key={c}
                className="rounded bg-gray-800 px-2 py-0.5 text-xs text-gray-300"
              >
                {c}
              </span>
            ))}
          </div>
        </div>
      )}
      {Object.keys(grouped).length > 0 && (
        <div className="space-y-1">
          <span className="text-xs text-gray-500">File references</span>
          {Object.entries(grouped).map(([dir, names]) => (
            <div key={dir} className="ml-2">
              <span className="text-xs font-mono text-gray-500">{dir}/</span>
              <ul className="ml-3">
                {names.map((n) => (
                  <li key={n} className="text-xs font-mono text-gray-400">
                    {n}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default function SourceContext({ task }: SourceContextProps) {
  const complexityScore =
    task.complexity_index != null
      ? (task.complexity_index as Record<string, unknown>).score as number | undefined
      : undefined

  return (
    <div className="flex flex-col gap-4 overflow-y-auto">
      {/* Issue title + body */}
      <section>
        <h3 className="mb-2 text-sm font-semibold text-gray-100">
          {task.issue_title ?? `Issue #${task.issue_id}`}
        </h3>
        {task.issue_body ? (
          <pre className="whitespace-pre-wrap break-words rounded border border-gray-700 bg-gray-800 p-3 text-sm text-gray-300">
            {task.issue_body}
          </pre>
        ) : (
          <p className="text-sm text-gray-500 italic">No description provided</p>
        )}
      </section>

      {/* Enrichment section */}
      <section className="space-y-3">
        <h4 className="text-xs font-semibold uppercase tracking-wider text-gray-500">
          Enrichment
        </h4>

        {/* Complexity score */}
        <div>
          <span className="text-xs text-gray-500">Complexity</span>
          {complexityScore != null ? (
            <ComplexityBar value={complexityScore} />
          ) : (
            <p className="text-xs text-gray-500 italic">Pending</p>
          )}
        </div>

        {/* Risk flags */}
        <div>
          <span className="text-xs text-gray-500">Risk Flags</span>
          {task.risk_flags != null ? (
            <RiskFlagsList flags={task.risk_flags} />
          ) : (
            <p className="text-xs text-gray-500 italic">Pending</p>
          )}
        </div>

        {/* Scope / files */}
        <div>
          <span className="text-xs text-gray-500">Scope</span>
          {task.scope != null ? (
            <ScopeSection scope={task.scope} />
          ) : (
            <p className="text-xs text-gray-500 italic">Pending</p>
          )}
        </div>
      </section>
    </div>
  )
}
