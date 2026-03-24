/**
 * Epic 44.5 — Display the webhook URL and let the user confirm it is configured.
 * Shows the payload URL to copy, a copy-to-clipboard button, and a manual
 * confirmation checkbox that enables the Next button.
 */

import { useEffect, useState } from 'react'
import { useWizardNav } from './WizardShell'

/** Derive the webhook URL from the current origin. */
function getWebhookUrl(): string {
  return `${window.location.origin}/webhook/github`
}

type CopyState = 'idle' | 'copied' | 'error'

export function WebhookConfigStep() {
  const { setNextDisabled } = useWizardNav()
  const [confirmed, setConfirmed] = useState(false)
  const [copyState, setCopyState] = useState<CopyState>('idle')

  const webhookUrl = getWebhookUrl()

  // Next is enabled only once the user ticks the checkbox
  useEffect(() => {
    setNextDisabled(!confirmed)
  }, [confirmed, setNextDisabled])

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(webhookUrl)
      setCopyState('copied')
      setTimeout(() => setCopyState('idle'), 2000)
    } catch {
      setCopyState('error')
      setTimeout(() => setCopyState('idle'), 2000)
    }
  }

  return (
    <div className="space-y-5" data-testid="wizard-step-webhook">
      <p className="text-sm text-gray-400">
        Add this URL as a webhook in your GitHub repository (
        <a
          href="https://docs.github.com/en/webhooks/using-webhooks/creating-webhooks"
          target="_blank"
          rel="noopener noreferrer"
          className="text-blue-400 underline-offset-2 hover:text-blue-300 hover:underline"
        >
          Settings → Webhooks → Add webhook
        </a>
        ). Set the content type to <code className="text-gray-200">application/json</code>.
      </p>

      {/* Webhook URL display + copy button */}
      <div className="flex items-center gap-2 rounded-lg border border-gray-700 bg-gray-950 px-3 py-2">
        <span
          className="flex-1 truncate font-mono text-sm text-gray-200"
          data-testid="wizard-webhook-url"
        >
          {webhookUrl}
        </span>
        <button
          type="button"
          onClick={() => void handleCopy()}
          data-testid="wizard-webhook-copy"
          aria-label="Copy webhook URL"
          className="shrink-0 rounded-md px-2.5 py-1 text-xs font-medium text-blue-400 ring-1 ring-gray-700 hover:bg-gray-800 hover:text-blue-300 focus:outline-none focus:ring-blue-500"
        >
          {copyState === 'copied' ? 'Copied!' : copyState === 'error' ? 'Failed' : 'Copy'}
        </button>
      </div>

      {/* Events hint */}
      <div className="rounded-lg border border-gray-800 bg-gray-900/60 px-3 py-2 text-xs text-gray-400">
        <strong className="text-gray-300">Required events:</strong> Select{' '}
        <span className="font-mono text-gray-200">Issues</span> and{' '}
        <span className="font-mono text-gray-200">Issue comments</span>.
      </div>

      {/* Manual confirmation checkbox */}
      <label
        className="flex cursor-pointer items-start gap-3 rounded-lg border border-gray-700 bg-gray-900/40 px-3 py-3 hover:border-gray-600"
        data-testid="wizard-webhook-confirm-label"
      >
        <input
          type="checkbox"
          checked={confirmed}
          onChange={(e) => setConfirmed(e.target.checked)}
          data-testid="wizard-webhook-confirm"
          className="mt-0.5 h-4 w-4 cursor-pointer accent-blue-500"
        />
        <span className="text-sm text-gray-300">
          I have added the webhook URL to GitHub and selected the required events.
        </span>
      </label>
    </div>
  )
}
