/**
 * Epic 44.4 — Register a GitHub repo during wizard setup.
 * POSTs to /admin/repos, handles 201 (created) and 409 (already registered).
 */

import { useEffect, useState } from 'react'
import { useWizardNav } from './WizardShell'

type SubmitState = 'idle' | 'submitting' | 'success' | 'conflict' | 'error'

interface FormFields {
  owner: string
  repo: string
  installation_id: string
}

interface FieldError {
  owner?: string
  repo?: string
  installation_id?: string
}

function validate(fields: FormFields): FieldError {
  const errors: FieldError = {}
  if (!fields.owner.trim()) errors.owner = 'Owner is required.'
  if (!fields.repo.trim()) errors.repo = 'Repository name is required.'
  const id = fields.installation_id.trim()
  if (!id) {
    errors.installation_id = 'Installation ID is required.'
  } else if (!/^\d+$/.test(id)) {
    errors.installation_id = 'Installation ID must be a positive integer.'
  }
  return errors
}

export function RepoRegistrationStep() {
  const { setNextDisabled } = useWizardNav()

  const [fields, setFields] = useState<FormFields>({
    owner: '',
    repo: '',
    installation_id: '',
  })
  const [fieldErrors, setFieldErrors] = useState<FieldError>({})
  const [submitState, setSubmitState] = useState<SubmitState>('idle')
  const [serverError, setServerError] = useState<string | null>(null)

  // Next is enabled once registration succeeds (201 or 409)
  useEffect(() => {
    const done = submitState === 'success' || submitState === 'conflict'
    setNextDisabled(!done)
  }, [submitState, setNextDisabled])

  function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
    const { name, value } = e.target
    setFields((prev) => ({ ...prev, [name]: value }))
    // Clear per-field error on change
    setFieldErrors((prev) => ({ ...prev, [name]: undefined }))
    // Reset submission state so user can resubmit
    if (submitState !== 'idle') setSubmitState('idle')
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const errors = validate(fields)
    if (Object.keys(errors).length > 0) {
      setFieldErrors(errors)
      return
    }

    setSubmitState('submitting')
    setServerError(null)

    try {
      const res = await fetch('/admin/repos', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          owner: fields.owner.trim(),
          repo: fields.repo.trim(),
          installation_id: parseInt(fields.installation_id.trim(), 10),
        }),
      })

      if (res.status === 201) {
        setSubmitState('success')
      } else if (res.status === 409) {
        setSubmitState('conflict')
      } else {
        let detail = `Unexpected response: ${res.status}`
        try {
          const body = (await res.json()) as { detail?: string }
          if (body.detail) detail = body.detail
        } catch {
          /* ignore parse error */
        }
        setServerError(detail)
        setSubmitState('error')
      }
    } catch {
      setServerError('Network error — check that the API is running.')
      setSubmitState('error')
    }
  }

  const isRegistered = submitState === 'success' || submitState === 'conflict'

  return (
    <div className="space-y-4" data-testid="wizard-step-repo-registration">
      <p className="text-sm text-gray-400">
        Register your first GitHub repository. You'll need your GitHub App installation ID — find
        it in{' '}
        <a
          href="https://github.com/settings/installations"
          target="_blank"
          rel="noopener noreferrer"
          className="text-blue-400 underline-offset-2 hover:text-blue-300 hover:underline"
        >
          GitHub → Settings → Installations
        </a>
        .
      </p>

      <form onSubmit={(e) => void handleSubmit(e)} noValidate className="space-y-3">
        <div>
          <label htmlFor="wizard-owner" className="mb-1 block text-sm font-medium text-gray-300">
            Owner
          </label>
          <input
            id="wizard-owner"
            name="owner"
            type="text"
            autoComplete="off"
            placeholder="e.g. acme-org"
            value={fields.owner}
            onChange={handleChange}
            disabled={isRegistered}
            data-testid="wizard-repo-owner"
            className="w-full rounded-lg border border-gray-700 bg-gray-950 px-3 py-2 text-sm text-gray-100 placeholder-gray-600 focus:border-blue-500 focus:outline-none disabled:opacity-50"
          />
          {fieldErrors.owner ? (
            <p className="mt-1 text-xs text-red-400" data-testid="wizard-repo-owner-error">
              {fieldErrors.owner}
            </p>
          ) : null}
        </div>

        <div>
          <label htmlFor="wizard-repo" className="mb-1 block text-sm font-medium text-gray-300">
            Repository
          </label>
          <input
            id="wizard-repo"
            name="repo"
            type="text"
            autoComplete="off"
            placeholder="e.g. my-service"
            value={fields.repo}
            onChange={handleChange}
            disabled={isRegistered}
            data-testid="wizard-repo-name"
            className="w-full rounded-lg border border-gray-700 bg-gray-950 px-3 py-2 text-sm text-gray-100 placeholder-gray-600 focus:border-blue-500 focus:outline-none disabled:opacity-50"
          />
          {fieldErrors.repo ? (
            <p className="mt-1 text-xs text-red-400" data-testid="wizard-repo-name-error">
              {fieldErrors.repo}
            </p>
          ) : null}
        </div>

        <div>
          <label
            htmlFor="wizard-installation-id"
            className="mb-1 block text-sm font-medium text-gray-300"
          >
            Installation ID
          </label>
          <input
            id="wizard-installation-id"
            name="installation_id"
            type="text"
            inputMode="numeric"
            autoComplete="off"
            placeholder="e.g. 12345678"
            value={fields.installation_id}
            onChange={handleChange}
            disabled={isRegistered}
            data-testid="wizard-repo-installation-id"
            className="w-full rounded-lg border border-gray-700 bg-gray-950 px-3 py-2 text-sm text-gray-100 placeholder-gray-600 focus:border-blue-500 focus:outline-none disabled:opacity-50"
          />
          {fieldErrors.installation_id ? (
            <p
              className="mt-1 text-xs text-red-400"
              data-testid="wizard-repo-installation-id-error"
            >
              {fieldErrors.installation_id}
            </p>
          ) : null}
        </div>

        {!isRegistered && (
          <button
            type="submit"
            disabled={submitState === 'submitting'}
            data-testid="wizard-repo-submit"
            className="mt-1 min-h-[44px] rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-40"
          >
            {submitState === 'submitting' ? 'Registering…' : 'Register Repository'}
          </button>
        )}
      </form>

      {submitState === 'success' && (
        <div
          className="flex items-center gap-2 rounded-lg border border-emerald-800 bg-emerald-950/60 px-3 py-2 text-sm text-emerald-400"
          data-testid="wizard-repo-success"
          role="status"
        >
          <span aria-hidden="true">✓</span>
          <span>
            Repository <strong>{fields.owner}/{fields.repo}</strong> registered successfully.
          </span>
        </div>
      )}

      {submitState === 'conflict' && (
        <div
          className="flex items-center gap-2 rounded-lg border border-yellow-800 bg-yellow-950/60 px-3 py-2 text-sm text-yellow-400"
          data-testid="wizard-repo-conflict"
          role="status"
        >
          <span aria-hidden="true">⚠</span>
          <span>
            Repository <strong>{fields.owner}/{fields.repo}</strong> is already registered — you
            can continue.
          </span>
        </div>
      )}

      {submitState === 'error' && serverError && (
        <div
          className="flex items-center gap-2 rounded-lg border border-red-800 bg-red-950/60 px-3 py-2 text-sm text-red-400"
          data-testid="wizard-repo-error"
          role="alert"
        >
          <span aria-hidden="true">✕</span>
          <span>{serverError}</span>
        </div>
      )}
    </div>
  )
}
