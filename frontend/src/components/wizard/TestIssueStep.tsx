/**
 * Epic 44.8 — Wizard step: trigger a test issue through the pipeline,
 * poll the resulting TaskPacket until it reaches a meaningful stage,
 * and show a success animation on completion.
 *
 * POST /api/v1/dashboard/tasks  (skip_triage: true) → task_id
 * GET  /api/v1/dashboard/tasks/{task_id}            → poll status
 *
 * Next is enabled as soon as the task is created and the pipeline is running.
 */

import { useCallback, useEffect, useRef, useState } from 'react'
import { useWizardNav } from './WizardShell'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface TaskPacketRead {
  id: string
  status: string
  issue_title: string
}

interface CreateTaskResponse {
  task: TaskPacketRead
  workflow_started: boolean
}

type FlowState =
  | 'idle'        // nothing started yet
  | 'creating'    // POST in flight
  | 'polling'     // task created; polling for progress
  | 'success'     // terminal success state reached
  | 'failed'      // pipeline or network failure

/** Status values that represent meaningful forward progress worth stopping the poll. */
const SUCCESS_STATUSES = new Set([
  'published',
  'verification_passed',
  'awaiting_approval',
  'in_progress',
  'intent_built',
  'enriched',
])

/** Status values that represent a terminal failure. */
const FAILURE_STATUSES = new Set(['failed', 'aborted', 'rejected'])

const POLL_INTERVAL_MS = 3_000
const MAX_POLL_ATTEMPTS = 40 // ~2 minutes

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function humanStatus(status: string): string {
  return status
    .split('_')
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ')
}

function statusColor(status: string): string {
  if (SUCCESS_STATUSES.has(status)) return 'text-emerald-400'
  if (FAILURE_STATUSES.has(status)) return 'text-red-400'
  if (status === 'triage' || status === 'received') return 'text-blue-400'
  return 'text-yellow-400'
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function SuccessAnimation() {
  return (
    <div
      className="flex flex-col items-center gap-3 py-4 text-center"
      data-testid="test-issue-success-animation"
      role="status"
      aria-live="polite"
    >
      {/* Pulsing checkmark ring */}
      <div className="relative flex h-16 w-16 items-center justify-center">
        <span
          className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-30"
          aria-hidden="true"
        />
        <span className="relative inline-flex h-12 w-12 items-center justify-center rounded-full bg-emerald-600 text-2xl text-white">
          ✓
        </span>
      </div>
      <p className="text-sm font-semibold text-emerald-300">Issue received — pipeline is running!</p>
      <p className="text-xs text-gray-400">
        Your test issue was picked up and is moving through the pipeline. You can monitor progress on
        the Pipeline tab.
      </p>
    </div>
  )
}

interface StatusBadgeProps {
  status: string
}

function StatusBadge({ status }: StatusBadgeProps) {
  return (
    <span
      className={`rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset ${statusColor(status)} ring-current/30`}
      data-testid="test-issue-status-badge"
    >
      {humanStatus(status)}
    </span>
  )
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export function TestIssueStep() {
  const { setNextDisabled } = useWizardNav()

  const [flow, setFlow] = useState<FlowState>('idle')
  const [taskId, setTaskId] = useState<string | null>(null)
  const [taskStatus, setTaskStatus] = useState<string | null>(null)
  const [pollAttempts, setPollAttempts] = useState(0)
  const [error, setError] = useState<string | null>(null)

  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null)

  // Stop the polling interval on unmount
  useEffect(() => {
    return () => {
      if (pollingRef.current) clearInterval(pollingRef.current)
    }
  }, [])

  // Enable Next once the pipeline is confirmed running
  useEffect(() => {
    setNextDisabled(flow === 'idle' || flow === 'creating')
  }, [flow, setNextDisabled])

  // ---------------------------------------------------------------------------
  // Poll for task status
  // ---------------------------------------------------------------------------
  const stopPolling = useCallback(() => {
    if (pollingRef.current) {
      clearInterval(pollingRef.current)
      pollingRef.current = null
    }
  }, [])

  const pollTask = useCallback(
    async (id: string, attempt: number) => {
      if (attempt >= MAX_POLL_ATTEMPTS) {
        stopPolling()
        // Don't mark as failed — the pipeline may just be slow. Leave in polling state.
        return
      }

      try {
        const res = await fetch(`/api/v1/dashboard/tasks/${id}`)
        if (!res.ok) return

        const data = (await res.json()) as TaskPacketRead
        setTaskStatus(data.status)
        setPollAttempts(attempt + 1)

        if (SUCCESS_STATUSES.has(data.status)) {
          stopPolling()
          setFlow('success')
        } else if (FAILURE_STATUSES.has(data.status)) {
          stopPolling()
          setFlow('failed')
          setError(`Pipeline ended with status: ${humanStatus(data.status)}`)
        }
      } catch {
        // Network blip — keep polling silently
      }
    },
    [stopPolling],
  )

  // ---------------------------------------------------------------------------
  // Trigger test issue
  // ---------------------------------------------------------------------------
  const triggerTestIssue = useCallback(async () => {
    stopPolling()
    setFlow('creating')
    setError(null)
    setTaskId(null)
    setTaskStatus(null)
    setPollAttempts(0)

    try {
      const res = await fetch('/api/v1/dashboard/tasks', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: 'Wizard test issue — smoke test',
          description:
            'This is an automatically generated test issue created by the Setup Wizard to verify that the pipeline is functioning correctly. You may safely ignore or delete it.',
          category: 'test',
          priority: 'low',
          skip_triage: true,
        }),
      })

      if (!res.ok) {
        const text = await res.text()
        throw new Error(`Server returned ${res.status}: ${text}`)
      }

      const data = (await res.json()) as CreateTaskResponse
      const id = data.task.id
      setTaskId(id)
      setTaskStatus(data.task.status)

      if (!data.workflow_started) {
        // Workflow didn't start (Temporal may be down). Still let user proceed.
        setFlow('polling')
        return
      }

      setFlow('polling')

      // Start polling
      let attempt = 0
      pollingRef.current = setInterval(() => {
        attempt += 1
        void pollTask(id, attempt)
      }, POLL_INTERVAL_MS)
    } catch (err) {
      setFlow('failed')
      setError(err instanceof Error ? err.message : 'Unknown error')
    }
  }, [pollTask, stopPolling])

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  return (
    <div className="space-y-5" data-testid="wizard-step-test-issue">
      <p className="text-sm text-gray-400">
        Send a{' '}
        <strong className="text-gray-300">test issue</strong> through the pipeline to verify
        end-to-end processing. TheStudio will create a synthetic task, run it through Intake →
        Context → Intent, and report back when it is picked up.
      </p>

      {/* Trigger button */}
      {flow === 'idle' || flow === 'failed' ? (
        <button
          type="button"
          onClick={() => void triggerTestIssue()}
          className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
          data-testid="test-issue-trigger"
        >
          Send Test Issue
        </button>
      ) : null}

      {/* Creating spinner */}
      {flow === 'creating' ? (
        <div
          className="flex items-center gap-2 text-sm text-gray-400"
          role="status"
          data-testid="test-issue-creating"
        >
          <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-blue-500 border-t-transparent" />
          Creating test issue…
        </div>
      ) : null}

      {/* Polling status */}
      {(flow === 'polling' || flow === 'success' || flow === 'failed') && taskId ? (
        <div
          className="rounded-lg border border-gray-800 bg-gray-950/80 p-3 text-sm"
          data-testid="test-issue-task-info"
        >
          <div className="flex items-center justify-between gap-2">
            <span className="font-mono text-xs text-gray-500">Task ID</span>
            <span
              className="max-w-[12rem] truncate font-mono text-xs text-gray-300"
              title={taskId}
              data-testid="test-issue-task-id"
            >
              {taskId}
            </span>
          </div>
          {taskStatus ? (
            <div className="mt-1.5 flex items-center justify-between gap-2">
              <span className="text-xs text-gray-500">Status</span>
              <StatusBadge status={taskStatus} />
            </div>
          ) : null}
          {flow === 'polling' ? (
            <div className="mt-2 flex items-center gap-2 text-xs text-gray-500">
              <span className="inline-block h-3 w-3 animate-spin rounded-full border border-blue-500 border-t-transparent" />
              Polling… ({pollAttempts}/{MAX_POLL_ATTEMPTS})
            </div>
          ) : null}
        </div>
      ) : null}

      {/* Success animation */}
      {flow === 'success' ? <SuccessAnimation /> : null}

      {/* Error */}
      {flow === 'failed' && error ? (
        <div
          className="rounded-lg border border-red-900 bg-red-950/40 px-3 py-2 text-xs text-red-400"
          role="alert"
          data-testid="test-issue-error"
        >
          {error}
        </div>
      ) : null}

      {/* Retry link (after failure or long poll) */}
      {(flow === 'failed' || (flow === 'polling' && pollAttempts >= MAX_POLL_ATTEMPTS)) ? (
        <button
          type="button"
          onClick={() => void triggerTestIssue()}
          className="text-sm text-blue-400 underline-offset-2 hover:text-blue-300 hover:underline"
          data-testid="test-issue-retry"
        >
          Try again
        </button>
      ) : null}

      {/* Skip hint */}
      <p className="text-xs text-gray-600">
        You can skip this step if the pipeline is not fully configured yet.
      </p>
    </div>
  )
}
