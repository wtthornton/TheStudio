/**
 * Epic 44.7 — Show LLM provider health during wizard setup.
 * GETs /admin/health, surfaces the router (LLM Router) service status and
 * interprets it as Anthropic API key reachability. Next is always enabled —
 * users can configure the key later in Admin → Settings → API Keys.
 */

import { useCallback, useEffect, useState } from 'react'
import { useWizardNav } from './WizardShell'

type ProbeState = 'pending' | 'ok' | 'degraded' | 'fail'

interface ServiceStatus {
  name: string
  status: string
  latency_ms: number | null
  error: string | null
}

interface HealthPayload {
  temporal: ServiceStatus
  jetstream: ServiceStatus
  postgres: ServiceStatus
  router: ServiceStatus
  overall_status: string
  checked_at: string
}

function toProbeState(status: string): ProbeState {
  switch (status.toLowerCase()) {
    case 'ok':
      return 'ok'
    case 'degraded':
      return 'degraded'
    default:
      return 'fail'
  }
}

function statusLabel(state: ProbeState): string {
  switch (state) {
    case 'ok':
      return 'Connected'
    case 'degraded':
      return 'Degraded'
    case 'fail':
      return 'Unreachable'
    default:
      return 'Checking…'
  }
}

function statusColor(state: ProbeState): string {
  switch (state) {
    case 'ok':
      return 'text-emerald-400'
    case 'degraded':
      return 'text-yellow-400'
    case 'fail':
      return 'text-red-400'
    default:
      return 'text-gray-500'
  }
}

function StatusRow({
  label,
  state,
  latency,
  testId,
}: {
  label: string
  state: ProbeState
  latency?: number | null
  testId: string
}) {
  return (
    <div className="flex items-center justify-between rounded-lg border border-gray-800 bg-gray-950/80 px-3 py-2 text-sm">
      <span className="text-gray-300">{label}</span>
      <span className={`flex items-center gap-2 font-medium ${statusColor(state)}`} data-testid={testId}>
        {statusLabel(state)}
        {state === 'ok' && latency != null ? (
          <span className="text-xs font-normal text-gray-500">{latency.toFixed(0)} ms</span>
        ) : null}
      </span>
    </div>
  )
}

export function LLMProviderStep() {
  const { setNextDisabled } = useWizardNav()

  const [fetchState, setFetchState] = useState<'pending' | 'done' | 'error'>('pending')
  const [routerState, setRouterState] = useState<ProbeState>('pending')
  const [routerLatency, setRouterLatency] = useState<number | null>(null)
  const [routerError, setRouterError] = useState<string | null>(null)
  const [overallOk, setOverallOk] = useState(false)

  const runCheck = useCallback(async () => {
    setFetchState('pending')
    setRouterState('pending')
    setRouterLatency(null)
    setRouterError(null)

    try {
      const res = await fetch('/admin/health', { method: 'GET' })
      if (!res.ok) {
        setRouterState('fail')
        setFetchState('error')
        return
      }
      const data = (await res.json()) as HealthPayload
      const probe = toProbeState(data.router.status)
      setRouterState(probe)
      setRouterLatency(data.router.latency_ms)
      setRouterError(data.router.error ?? null)
      setOverallOk(data.overall_status.toLowerCase() === 'ok')
      setFetchState('done')
    } catch {
      setRouterState('fail')
      setFetchState('error')
    }
  }, [])

  useEffect(() => {
    void runCheck()
  }, [runCheck])

  // Next is always enabled — key can be configured after wizard
  useEffect(() => {
    setNextDisabled(false)
  }, [setNextDisabled])

  const keyConfigured = routerState === 'ok'

  return (
    <div className="space-y-5" data-testid="wizard-step-llm-provider">
      <p className="text-sm text-gray-400">
        TheStudio uses the{' '}
        <strong className="text-gray-300">Anthropic API</strong> to process issues. We probe the
        LLM Router to confirm your API key is reachable. You can configure the key in{' '}
        <strong className="text-gray-300">Admin → Settings → API Keys</strong> if this check fails.
      </p>

      {/* Status rows */}
      <div className="space-y-2">
        {fetchState === 'pending' ? (
          <div
            className="rounded-lg border border-gray-800 bg-gray-950/80 px-3 py-2 text-sm text-gray-500"
            data-testid="wizard-llm-checking"
          >
            Checking LLM Router…
          </div>
        ) : (
          <StatusRow
            label="LLM Router (Anthropic)"
            state={routerState}
            latency={routerLatency}
            testId="wizard-llm-router-status"
          />
        )}
      </div>

      {/* Key configured badge */}
      {fetchState === 'done' && (
        <div
          className={[
            'flex items-start gap-2 rounded-lg border px-3 py-2 text-sm',
            keyConfigured
              ? 'border-emerald-800 bg-emerald-950/40 text-emerald-300'
              : 'border-yellow-800 bg-yellow-950/40 text-yellow-300',
          ].join(' ')}
          role="status"
          data-testid="wizard-llm-key-status"
        >
          <span aria-hidden="true" className="mt-0.5 shrink-0">
            {keyConfigured ? '✓' : '⚠'}
          </span>
          <span>
            {keyConfigured
              ? 'Anthropic API key is configured and the LLM Router is reachable.'
              : 'LLM Router is unreachable. Set ANTHROPIC_API_KEY in your environment or via Admin → Settings → API Keys, then click Check again.'}
          </span>
        </div>
      )}

      {/* Router-level error detail */}
      {routerError && fetchState === 'done' ? (
        <div
          className="rounded-lg border border-red-900 bg-red-950/40 px-3 py-2 text-xs text-red-400"
          role="alert"
          data-testid="wizard-llm-router-error"
        >
          {routerError}
        </div>
      ) : null}

      {/* Fetch-level error */}
      {fetchState === 'error' ? (
        <div
          className="rounded-lg border border-red-900 bg-red-950/40 px-3 py-2 text-xs text-red-400"
          role="alert"
          data-testid="wizard-llm-fetch-error"
        >
          Could not reach <code className="font-mono">/admin/health</code>. Make sure the server is
          running.
        </div>
      ) : null}

      {/* Recheck link */}
      <button
        type="button"
        onClick={() => void runCheck()}
        className="text-sm text-blue-400 underline-offset-2 hover:text-blue-300 hover:underline"
        data-testid="wizard-llm-recheck"
      >
        Check again
      </button>

      {/* Info callout */}
      <div className="rounded-lg border border-gray-800 bg-gray-900/60 px-3 py-2 text-xs text-gray-400">
        <strong className="text-gray-300">Note:</strong> If you are running in{' '}
        <span className="font-mono text-gray-300">llm_provider=mock</span> mode, the LLM Router
        will report as unreachable — this is expected. Set{' '}
        <span className="font-mono text-gray-300">llm_provider=anthropic</span> in your config to
        enable real processing.
        {overallOk && !keyConfigured ? null : null}
      </div>
    </div>
  )
}
