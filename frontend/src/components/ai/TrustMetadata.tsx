/**
 * TrustMetadata — Compact metadata block for AI trust and safety signals.
 *
 * Per SG 8.4: confidence indicator, provenance/evidence link, timestamp, ownership cue.
 * Per SG 8.6: AI labeling rule — visibly marks AI-generated content.
 * Color-coding uses text labels alongside color (never color-only per cross-surface rules).
 *
 * Epic 55.3
 */

import { useState } from 'react'

export type ConfidenceLevel = 'high' | 'medium' | 'low'

const CONFIDENCE_STYLES: Record<
  ConfidenceLevel,
  { label: string; textClass: string; bgClass: string }
> = {
  high: {
    label: 'High confidence',
    textClass: 'text-emerald-400',
    bgClass: 'bg-emerald-900/40',
  },
  medium: {
    label: 'Medium confidence',
    textClass: 'text-amber-400',
    bgClass: 'bg-amber-900/40',
  },
  low: {
    label: 'Low confidence',
    textClass: 'text-red-400',
    bgClass: 'bg-red-900/40',
  },
}

interface TrustMetadataProps {
  confidence: ConfidenceLevel
  source: string
  timestamp: string
  /** Optional expanded rationale text (SG 8.3: "rationale on demand") */
  rationale?: string
  /** Ownership cue shown to the user (SG 8.4) */
  ownershipCue?: string
}

export function TrustMetadata({
  confidence,
  source,
  timestamp,
  rationale,
  ownershipCue = 'You are responsible for final action',
}: TrustMetadataProps) {
  const [rationaleExpanded, setRationaleExpanded] = useState(false)
  const style = CONFIDENCE_STYLES[confidence]

  return (
    <aside
      aria-label="Trust and provenance metadata"
      className="rounded-lg border border-gray-700 bg-gray-900 px-4 py-3"
      data-testid="trust-metadata"
    >
      {/* SG 8.6: AI label */}
      <p
        className="mb-2 text-xs font-medium text-gray-500"
        data-testid="trust-metadata-ai-label"
      >
        AI-generated
      </p>

      {/* Metadata row */}
      <div className="flex flex-wrap items-center gap-3 text-xs">
        {/* Confidence */}
        <span
          className={`inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 font-medium ${style.bgClass} ${style.textClass}`}
          data-testid="trust-metadata-confidence"
        >
          <span
            className={`inline-block h-1.5 w-1.5 rounded-full ${
              confidence === 'high'
                ? 'bg-emerald-400'
                : confidence === 'medium'
                  ? 'bg-amber-400'
                  : 'bg-red-400'
            }`}
            aria-hidden="true"
          />
          {style.label}
        </span>

        {/* Source / provenance */}
        <span className="text-gray-400" data-testid="trust-metadata-source">
          Source: <span className="text-gray-300">{source}</span>
        </span>

        {/* Timestamp */}
        <span className="text-gray-500" data-testid="trust-metadata-timestamp">
          {timestamp}
        </span>
      </div>

      {/* Ownership cue (SG 8.4) */}
      <p
        className="mt-2 text-xs italic text-gray-500"
        data-testid="trust-metadata-ownership"
      >
        {ownershipCue}
      </p>

      {/* Rationale disclosure (SG 8.3) */}
      {rationale && (
        <div className="mt-3 border-t border-gray-800 pt-2">
          <button
            type="button"
            onClick={() => setRationaleExpanded((prev) => !prev)}
            className="flex items-center gap-1.5 text-xs font-medium text-gray-400 hover:text-gray-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
            aria-expanded={rationaleExpanded}
            aria-controls="trust-rationale-content"
            data-testid="trust-metadata-rationale-toggle"
          >
            <span className="text-gray-500">{rationaleExpanded ? '\u25BE' : '\u25B8'}</span>
            Rationale
          </button>
          {rationaleExpanded && (
            <div
              id="trust-rationale-content"
              className="mt-2 rounded border border-gray-800 bg-gray-800/50 px-3 py-2 text-xs text-gray-300 whitespace-pre-wrap"
              data-testid="trust-metadata-rationale-content"
            >
              {rationale}
            </div>
          )}
        </div>
      )}
    </aside>
  )
}
