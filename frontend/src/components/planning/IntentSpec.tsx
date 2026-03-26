import type { IntentSpecRead } from '../../lib/api'

interface IntentSpecProps {
  spec: IntentSpecRead
}

const SOURCE_COLORS: Record<string, string> = {
  auto: 'bg-[rgba(59,130,246,0.2)] text-blue-500',
  developer: 'bg-[rgba(22,163,74,0.2)] text-green-500',
  refinement: 'bg-purple-900 text-purple-300',
}

function SourceBadge({ source }: { source: string }) {
  const color = SOURCE_COLORS[source] ?? 'bg-gray-700 text-gray-300'
  return (
    <span className={`rounded px-2 py-0.5 text-xs font-medium ${color}`}>
      {source}
    </span>
  )
}

export default function IntentSpec({ spec }: IntentSpecProps) {
  const timestamp = new Date(spec.created_at).toLocaleString()

  return (
    <div className="flex flex-col gap-4 overflow-y-auto">
      {/* Header: source badge + version + timestamp */}
      <div className="flex items-center gap-3">
        <SourceBadge source={spec.source} />
        <span className="text-xs text-gray-500">v{spec.version}</span>
        <span className="text-xs text-gray-500">{timestamp}</span>
      </div>

      {/* Goal */}
      <section>
        <h4 className="mb-1 text-xs font-semibold uppercase tracking-wider text-gray-500">
          Goal
        </h4>
        <p className="text-sm text-gray-200">{spec.goal}</p>
      </section>

      {/* Constraints */}
      {spec.constraints.length > 0 && (
        <section>
          <h4 className="mb-1 text-xs font-semibold uppercase tracking-wider text-gray-500">
            Constraints
          </h4>
          <ul className="list-disc space-y-1 pl-5">
            {spec.constraints.map((c, i) => (
              <li key={i} className="text-sm text-gray-300">
                {c}
              </li>
            ))}
          </ul>
        </section>
      )}

      {/* Acceptance Criteria */}
      {spec.acceptance_criteria.length > 0 && (
        <section>
          <h4 className="mb-1 text-xs font-semibold uppercase tracking-wider text-gray-500">
            Acceptance Criteria
          </h4>
          <ol className="list-decimal space-y-1 pl-5">
            {spec.acceptance_criteria.map((ac, i) => (
              <li key={i} className="text-sm text-gray-300">
                {ac}
              </li>
            ))}
          </ol>
        </section>
      )}

      {/* Non-Goals */}
      {spec.non_goals.length > 0 && (
        <section>
          <h4 className="mb-1 text-xs font-semibold uppercase tracking-wider text-gray-500">
            Non-Goals
          </h4>
          <ul className="space-y-1 pl-5">
            {spec.non_goals.map((ng, i) => (
              <li key={i} className="text-sm text-gray-400 line-through">
                {ng}
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  )
}
