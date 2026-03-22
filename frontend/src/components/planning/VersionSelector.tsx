import type { IntentSpecRead } from '../../lib/api'

interface VersionSelectorProps {
  versions: IntentSpecRead[]
  selectedVersion: number | null
  onSelect: (version: number) => void
}

export default function VersionSelector({
  versions,
  selectedVersion,
  onSelect,
}: VersionSelectorProps) {
  if (versions.length === 0) return null

  return (
    <select
      value={selectedVersion ?? ''}
      onChange={(e) => onSelect(Number(e.target.value))}
      className="rounded border border-gray-600 bg-gray-800 px-2 py-1 text-xs text-gray-300 focus:border-blue-500 focus:outline-none"
    >
      {versions.map((v) => (
        <option key={v.version} value={v.version}>
          v{v.version} — {v.source} — {new Date(v.created_at).toLocaleDateString()}
        </option>
      ))}
    </select>
  )
}
