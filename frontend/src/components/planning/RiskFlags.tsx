export interface RiskFlagsProps {
  /** risk_flags from TaskPacketRead — maps flag name to active boolean. null = pending. */
  flags: Record<string, boolean> | null | undefined
}

function CheckIcon() {
  return (
    <svg className="h-4 w-4 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
    </svg>
  )
}

function XIcon() {
  return (
    <svg className="h-4 w-4 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
    </svg>
  )
}

function formatFlagName(key: string): string {
  return key
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase())
}

export default function RiskFlags({ flags }: RiskFlagsProps) {
  if (flags == null) {
    return (
      <div className="rounded-lg border border-gray-700 bg-gray-800 p-3">
        <p className="text-xs font-semibold uppercase tracking-wider text-gray-500 mb-2">
          Risk Flags
        </p>
        <p className="text-sm italic text-gray-600">Pending</p>
      </div>
    )
  }

  const entries = Object.entries(flags)

  if (entries.length === 0) {
    return (
      <div className="rounded-lg border border-gray-700 bg-gray-800 p-3">
        <p className="text-xs font-semibold uppercase tracking-wider text-gray-500 mb-2">
          Risk Flags
        </p>
        <p className="text-sm text-gray-500">No risk flags detected</p>
      </div>
    )
  }

  return (
    <div className="rounded-lg border border-gray-700 bg-gray-800 p-3">
      <p className="text-xs font-semibold uppercase tracking-wider text-gray-500 mb-2">
        Risk Flags
      </p>
      <ul className="space-y-1">
        {entries.map(([key, active]) => (
          <li key={key} className="flex items-center gap-2 text-sm">
            {active ? <XIcon /> : <CheckIcon />}
            <span className={active ? 'text-red-300' : 'text-gray-400'}>
              {formatFlagName(key)}
            </span>
          </li>
        ))}
      </ul>
    </div>
  )
}
