import type { ReactNode } from 'react'

export interface MetricCardProps {
  label: string
  value: string | number | null | undefined
  icon?: ReactNode
  color?: 'green' | 'amber' | 'red' | 'gray'
}

const colorClasses: Record<string, string> = {
  green: 'text-emerald-400 border-emerald-700/50',
  amber: 'text-amber-400 border-amber-700/50',
  red: 'text-red-400 border-red-700/50',
  gray: 'text-gray-400 border-gray-700',
}

const iconBgClasses: Record<string, string> = {
  green: 'bg-emerald-900/40',
  amber: 'bg-amber-900/40',
  red: 'bg-red-900/40',
  gray: 'bg-gray-800',
}

export default function MetricCard({
  label,
  value,
  icon,
  color = 'gray',
}: MetricCardProps) {
  const border = colorClasses[color] ?? colorClasses.gray
  const iconBg = iconBgClasses[color] ?? iconBgClasses.gray

  const isPending = value == null

  return (
    <div
      className={`flex items-center gap-3 rounded-lg border bg-gray-800 p-3 ${border}`}
    >
      {icon && (
        <div
          className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-md ${iconBg}`}
        >
          {icon}
        </div>
      )}
      <div className="min-w-0">
        <p className="text-xs text-gray-500">{label}</p>
        {isPending ? (
          <p className="text-sm italic text-gray-600">Pending</p>
        ) : (
          <p className={`text-lg font-semibold ${colorClasses[color]?.split(' ')[0] ?? 'text-gray-300'}`}>
            {value}
          </p>
        )}
      </div>
    </div>
  )
}
