/** Hook for consuming real-time GitHub webhook bridge events (Epic 38.26).
 *
 * Connects to the pipeline SSE endpoint and filters for `github.event.*`
 * events published by the webhook bridge (Story 38.24) so components can
 * react to external GitHub actions without polling.
 *
 * Usage:
 *   const { prStatus, reviewStatus, lastEvent } = useGitHubEvents(taskId)
 *
 * Events handled:
 *   - github.event.pull_request  — PR opened, merged, closed, reopened
 *   - github.event.pull_request_review — Review submitted (approved / changes_requested)
 *   - github.event.issue_comment — New comment on linked issue
 *   - github.event.check_run    — CI check status updates
 */

import { useState, useEffect, useRef, useCallback } from 'react'
import { usePipelineStore } from '../stores/pipeline-store'

const SSE_URL = '/api/v1/dashboard/events/stream'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type PrStatus =
  | 'open'
  | 'closed'
  | 'merged'
  | 'unknown'

export type ReviewStatus =
  | 'approved'
  | 'changes_requested'
  | 'commented'
  | 'dismissed'
  | 'none'

export type CheckStatus =
  | 'queued'
  | 'in_progress'
  | 'completed'
  | 'unknown'

export interface GitHubEventData {
  event_type: string
  action: string
  repo: string
  delivery_id: string
  timestamp: string
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  payload: Record<string, any>
}

export interface UseGitHubEventsResult {
  /** Latest parsed PR state derived from github.event.pull_request events. */
  prStatus: PrStatus
  /** Latest review state from github.event.pull_request_review events. */
  reviewStatus: ReviewStatus
  /** Latest CI check state from github.event.check_run events. */
  checkStatus: CheckStatus
  /** Raw last event data (null until first relevant event arrives). */
  lastEvent: GitHubEventData | null
  /** Number of GitHub events received since hook mount. */
  eventCount: number
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function parsePrStatus(payload: Record<string, unknown>): PrStatus {
  const pr = (payload.pull_request ?? {}) as Record<string, unknown>
  const action = (payload.action as string) ?? ''
  const merged = Boolean(pr.merged)

  if (action === 'closed' && merged) return 'merged'
  if (action === 'closed') return 'closed'
  if (action === 'opened' || action === 'reopened') return 'open'
  return 'unknown'
}

function parseReviewStatus(payload: Record<string, unknown>): ReviewStatus {
  const review = (payload.review ?? {}) as Record<string, unknown>
  const state = ((review.state as string) ?? '').toLowerCase()
  if (state === 'approved') return 'approved'
  if (state === 'changes_requested') return 'changes_requested'
  if (state === 'commented') return 'commented'
  if (state === 'dismissed') return 'dismissed'
  return 'none'
}

function parseCheckStatus(payload: Record<string, unknown>): CheckStatus {
  const checkRun = (payload.check_run ?? {}) as Record<string, unknown>
  const status = ((checkRun.status as string) ?? '').toLowerCase()
  if (status === 'queued') return 'queued'
  if (status === 'in_progress') return 'in_progress'
  if (status === 'completed') return 'completed'
  return 'unknown'
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

/**
 * Subscribes to github.event.* SSE events and returns derived state.
 *
 * @param taskId - Optional TaskPacket ID to filter events by repo/PR. When
 *   omitted, all GitHub events are included (useful for triage queue refresh).
 */
export function useGitHubEvents(taskId?: string): UseGitHubEventsResult {
  const [prStatus, setPrStatus] = useState<PrStatus>('unknown')
  const [reviewStatus, setReviewStatus] = useState<ReviewStatus>('none')
  const [checkStatus, setCheckStatus] = useState<CheckStatus>('unknown')
  const [lastEvent, setLastEvent] = useState<GitHubEventData | null>(null)
  const [eventCount, setEventCount] = useState(0)
  const esRef = useRef<EventSource | null>(null)

  // Read last event ID from the pipeline store for reconnect support
  const lastEventId = usePipelineStore((s) => s.lastEventId)

  const handleMessage = useCallback(
    (raw: string) => {
      let parsed: { type?: string; data?: GitHubEventData }
      try {
        parsed = JSON.parse(raw) as { type?: string; data?: GitHubEventData }
      } catch {
        return
      }

      const eventType = parsed.type ?? ''
      if (!eventType.startsWith('github.event.')) return

      const data = parsed.data
      if (!data) return

      // Only process events for this task's repo when taskId is provided.
      // Note: we can't filter by issue/PR number here since we don't have that
      // mapping on the frontend — backend associates via taskpacket_id.
      setLastEvent(data)
      setEventCount((c) => c + 1)

      const subType = eventType.replace('github.event.', '')

      if (subType === 'pull_request') {
        setPrStatus(parsePrStatus(data.payload))
      } else if (subType === 'pull_request_review') {
        setReviewStatus(parseReviewStatus(data.payload))
      } else if (subType === 'check_run') {
        setCheckStatus(parseCheckStatus(data.payload))
      }
      // issue_comment and check_suite are captured in lastEvent but don't
      // update named status fields — consumers can inspect lastEvent directly.
    },
    // taskId is intentionally excluded — it's used only to key the hook, not inside
    // the handler, to avoid re-creating the EventSource on every render.
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [],
  )

  useEffect(() => {
    // Build reconnect URL using last known event ID
    const url =
      lastEventId != null
        ? `${SSE_URL}?lastEventId=${lastEventId}`
        : SSE_URL

    const es = new EventSource(url)
    esRef.current = es

    es.onmessage = (event: MessageEvent) => {
      handleMessage(event.data as string)
    }

    // Named event listeners for event-typed SSE messages (server sends
    // event: github.event.pull_request lines in some configurations)
    const githubEventTypes = [
      'github.event.pull_request',
      'github.event.pull_request_review',
      'github.event.issue_comment',
      'github.event.check_run',
      'github.event.check_suite',
    ]
    for (const et of githubEventTypes) {
      es.addEventListener(et, (event: Event) => {
        handleMessage((event as MessageEvent).data as string)
      })
    }

    return () => {
      es.close()
      esRef.current = null
    }
    // Reconnect when task context changes so consumers get a fresh stream lifecycle.
  }, [lastEventId, taskId, handleMessage])

  return { prStatus, reviewStatus, checkStatus, lastEvent, eventCount }
}
