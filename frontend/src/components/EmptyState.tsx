/** Reusable empty state component — Epic 46.1
 * Provides icon/illustration slot, heading, description,
 * primary CTA button (onClick or href), and optional secondary link.
 * Dark theme styling consistent with the pipeline dashboard.
 */

import type { ReactNode } from 'react'

interface PrimaryAction {
  label: string
  /** If provided, renders an <a> tag instead of a <button>. */
  href?: string
  onClick?: () => void
}

interface SecondaryAction {
  label: string
  href?: string
  onClick?: () => void
}

interface EmptyStateProps {
  /** Icon or illustration to display above the heading. */
  icon?: ReactNode
  /** Main heading text. */
  heading: string
  /** Descriptive body text shown below the heading. */
  description?: string
  /** Primary call-to-action button or link. */
  primaryAction?: PrimaryAction
  /** Optional secondary link (e.g. "Learn more" or "Configure later"). */
  secondaryAction?: SecondaryAction
  /** Additional Tailwind classes for the wrapper div. */
  className?: string
  /** data-testid for targeted testing. */
  'data-testid'?: string
}

export function EmptyState({
  icon,
  heading,
  description,
  primaryAction,
  secondaryAction,
  className = '',
  'data-testid': testId = 'empty-state',
}: EmptyStateProps) {
  return (
    <div
      className={`flex flex-col items-center gap-4 py-12 px-6 text-center ${className}`}
      data-testid={testId}
    >
      {icon && (
        <div className="text-gray-500" data-testid={`${testId}-icon`}>
          {icon}
        </div>
      )}

      <div className="flex flex-col gap-2 max-w-xs">
        <h3 className="text-base font-semibold text-gray-200" data-testid={`${testId}-heading`}>
          {heading}
        </h3>
        {description && (
          <p className="text-sm text-gray-400" data-testid={`${testId}-description`}>
            {description}
          </p>
        )}
      </div>

      {(primaryAction || secondaryAction) && (
        <div className="flex flex-col items-center gap-2 mt-1">
          {primaryAction &&
            (primaryAction.href ? (
              <a
                href={primaryAction.href}
                className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-500 transition-colors"
                data-testid={`${testId}-primary-action`}
              >
                {primaryAction.label}
              </a>
            ) : (
              <button
                onClick={primaryAction.onClick}
                className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-500 transition-colors"
                data-testid={`${testId}-primary-action`}
              >
                {primaryAction.label}
              </button>
            ))}

          {secondaryAction &&
            (secondaryAction.href ? (
              <a
                href={secondaryAction.href}
                className="text-sm text-gray-400 hover:text-gray-200 underline underline-offset-2 transition-colors"
                data-testid={`${testId}-secondary-action`}
              >
                {secondaryAction.label}
              </a>
            ) : (
              <button
                onClick={secondaryAction.onClick}
                className="text-sm text-gray-400 hover:text-gray-200 underline underline-offset-2 transition-colors"
                data-testid={`${testId}-secondary-action`}
              >
                {secondaryAction.label}
              </button>
            ))}
        </div>
      )}
    </div>
  )
}
