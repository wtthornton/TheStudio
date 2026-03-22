export interface FileHeatmapProps {
  /** scope from TaskPacketRead — null means data not yet available. */
  scope: {
    affected_files_estimate?: number
    components?: string[]
    file_references?: string[]
  } | null | undefined
}

/** Group file references by directory prefix. */
function groupByDirectory(
  files: string[],
): { directory: string; files: string[]; count: number }[] {
  const groups: Record<string, string[]> = {}

  for (const f of files) {
    const lastSlash = f.lastIndexOf('/')
    const dir = lastSlash > 0 ? f.slice(0, lastSlash) : '.'
    ;(groups[dir] ??= []).push(f)
  }

  return Object.entries(groups)
    .map(([directory, dirFiles]) => ({
      directory,
      files: dirFiles.sort(),
      count: dirFiles.length,
    }))
    .sort((a, b) => b.count - a.count)
}

function IntensityBar({ count, max }: { count: number; max: number }) {
  const pct = max > 0 ? Math.round((count / max) * 100) : 0
  const color =
    pct >= 66
      ? 'bg-red-500'
      : pct >= 33
        ? 'bg-amber-500'
        : 'bg-emerald-500'

  return (
    <div className="h-2 w-full rounded-full bg-gray-700">
      <div
        className={`h-2 rounded-full ${color}`}
        style={{ width: `${Math.max(pct, 8)}%` }}
      />
    </div>
  )
}

export default function FileHeatmap({ scope }: FileHeatmapProps) {
  if (scope == null) {
    return (
      <div className="rounded-lg border border-gray-700 bg-gray-800 p-3">
        <p className="text-xs font-semibold uppercase tracking-wider text-gray-500 mb-2">
          Scope
        </p>
        <p className="text-sm italic text-gray-600">Pending</p>
      </div>
    )
  }

  const fileCount = scope.affected_files_estimate ?? 0
  const components = scope.components ?? []
  const fileRefs = scope.file_references ?? []
  const grouped = groupByDirectory(fileRefs)
  const maxCount = grouped.length > 0 ? grouped[0].count : 1

  return (
    <div className="rounded-lg border border-gray-700 bg-gray-800 p-3">
      <p className="text-xs font-semibold uppercase tracking-wider text-gray-500 mb-3">
        Scope
      </p>

      {/* File count */}
      <p className="text-sm text-gray-300 mb-2">
        <span className="font-semibold text-gray-200">{fileCount}</span>{' '}
        file{fileCount !== 1 ? 's' : ''} affected (estimate)
      </p>

      {/* Components */}
      {components.length > 0 && (
        <div className="mb-3">
          <p className="text-xs text-gray-500 mb-1">Components</p>
          <div className="flex flex-wrap gap-1">
            {components.map((c) => (
              <span
                key={c}
                className="rounded bg-gray-700 px-2 py-0.5 text-xs text-gray-300"
              >
                {c}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* File references grouped by directory */}
      {grouped.length > 0 && (
        <div>
          <p className="text-xs text-gray-500 mb-1">File References</p>
          <ul className="space-y-2">
            {grouped.map(({ directory, files, count }) => (
              <li key={directory}>
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-xs font-mono text-gray-400 truncate">
                    {directory}/
                  </span>
                  <span className="text-xs text-gray-600">({count})</span>
                </div>
                <IntensityBar count={count} max={maxCount} />
                <ul className="mt-1 ml-3 space-y-0.5">
                  {files.map((f) => (
                    <li
                      key={f}
                      className="text-xs font-mono text-gray-500 truncate"
                    >
                      {f}
                    </li>
                  ))}
                </ul>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* No file refs but have count */}
      {grouped.length === 0 && fileCount > 0 && (
        <p className="text-xs text-gray-500 italic">
          No explicit file references detected
        </p>
      )}
    </div>
  )
}
