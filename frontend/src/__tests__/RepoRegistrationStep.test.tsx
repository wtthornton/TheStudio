/**
 * Epic 44.4 — Repo registration wizard step: helper copy and installation-ID link.
 */

import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { RepoRegistrationStep } from '../components/wizard/RepoRegistrationStep'
import { WizardShell } from '../components/wizard/WizardShell'

function renderStep() {
  return render(
    <WizardShell onComplete={vi.fn()}>
      <RepoRegistrationStep />
    </WizardShell>,
  )
}

describe('RepoRegistrationStep', () => {
  it('renders per-field helper text for owner, repository, and installation ID', () => {
    renderStep()

    expect(screen.getByTestId('wizard-step-repo-registration')).toBeInTheDocument()

    expect(
      screen.getByText('GitHub org or username that owns the repo.'),
    ).toBeInTheDocument()
    expect(
      screen.getByText('Repository name only (do not include owner or URL).'),
    ).toBeInTheDocument()
    expect(
      screen.getByText(/Numeric GitHub App installation ID from/i),
    ).toBeInTheDocument()
  })

  it('includes the GitHub installations URL on intro and field helper links', () => {
    renderStep()

    const installLinks = screen
      .getAllByRole('link')
      .filter(
        (a) => a.getAttribute('href') === 'https://github.com/settings/installations',
      )

    expect(installLinks.length).toBeGreaterThanOrEqual(2)

    const intro = screen.getByRole('link', { name: /GitHub → Settings → Installations/i })
    expect(intro).toHaveAttribute('href', 'https://github.com/settings/installations')
    expect(intro).toHaveAttribute('target', '_blank')
    expect(intro).toHaveAttribute('rel', 'noopener noreferrer')

    const fieldHelper = screen.getByRole('link', {
      name: /GitHub Settings → Installations/i,
    })
    expect(fieldHelper).toHaveAttribute('href', 'https://github.com/settings/installations')
  })
})
