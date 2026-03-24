/**
 * Epic 44.3 — Probe liveness and readiness before continuing setup.
 */

import { useCallback, useEffect, useState } from 'react'
import { useWizardNav } from './WizardShell'

type ProbeState = 'pending' | 'ok' | 'fail'

function statusRow(label: string, state: ProbeState, testId: string) {
  const color =
    state === 'ok' ? 'text-emerald-400' : state === 'fail' ? 'text-red-400' : 'text-gray-500'
  const text =
    state === 'ok' ? 'OK' : state === 'fail' ? 'Failed' : 'Checking…'
  return (
    <div className="flex items-center justify-between rounded-lg border border-gray-800 bg-gray-950/80 px-3 py-2 text-sm">
      <span className="text-gray-300">{label}</span>
      <span className={`font-medium ${color}`} data-testid={testId}>
        {text}
      </span>
    </div>
  )
}

export function HealthCheckStep() {
  const { setNextDisabled } = useWizardNav()
  const [healthz, setHealthz] = useState<ProbeState>('pending')
  const [readyz, setReadyz] = useState<ProbeState>('pending')

  const runChecks = useCallback(async () => {
    setHealthz('pending')
    setReadyz('pending')

    try {
      const res = await fetch('/healthz', { method: 'GET' })
      let status: string | undefined
      try {
        const body = (await res.json()) as { status?: string }
        status = body.status
      } catch {
        status = undefined
      }
      setHealthz(res.ok && status === 'ok' ? 'ok' : 'fail')
    } catch {
      setHealthz('fail')
    }

    try {
      const res = await fetch('/readyz', { method: 'GET' })
      let status: string | undefined
      try {
        const body = (await res.json()) as { status?: string }
        status = body.status
      } catch {
        status = undefined
      }
      setReadyz(res.ok && status === 'ready' ? 'ok' : 'fail')
    } catch {
      setReadyz('fail')
    }
  }, [])

  useEffect(() => {
    void runChecks()
  }, [runChecks])

  useEffect(() => {
    const bothOk = healthz === 'ok' && readyz === 'ok'
    setNextDisabled(!bothOk)
  }, [healthz, readyz, setNextDisabled])

  return (
    <div className="space-y-4" data-testid="wizard-step-health">
      <p className="text-sm text-gray-400">
        We check that the API is running and the database is reachable. Both must pass before you
        continue.
      </p>
      <div className="space-y-2">
        {statusRow('Liveness (/healthz)', healthz, 'wizard-healthz-status')}
        {statusRow('Readiness (/readyz)', readyz, 'wizard-readyz-status')}
      </div>
      <button
        type="button"
        onClick={() => void runChecks()}
        className="text-sm text-blue-400 underline-offset-2 hover:text-blue-300 hover:underline"
        data-testid="health-recheck"
      >
        Check again
      </button>
    </div>
  )
}
