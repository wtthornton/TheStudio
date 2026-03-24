/** localStorage keys for Epic 44 — Setup Wizard (see docs/epics/epic-44-setup-wizard.md AC1/AC3). */

export const SETUP_WIZARD_COMPLETE_KEY = 'thestudio_setup_complete'
export const SETUP_WIZARD_SKIPPED_KEY = 'thestudio_setup_skipped'

export function isSetupWizardComplete(): boolean {
  try {
    return localStorage.getItem(SETUP_WIZARD_COMPLETE_KEY) === 'true'
  } catch {
    return false
  }
}

export function isSetupWizardSkipped(): boolean {
  try {
    return localStorage.getItem(SETUP_WIZARD_SKIPPED_KEY) === 'true'
  } catch {
    return false
  }
}

export function markSetupWizardComplete(): void {
  try {
    localStorage.setItem(SETUP_WIZARD_COMPLETE_KEY, 'true')
  } catch {
    /* ignore quota / private mode */
  }
}

export function markSetupWizardSkipped(): void {
  try {
    localStorage.setItem(SETUP_WIZARD_SKIPPED_KEY, 'true')
  } catch {
    /* ignore */
  }
}
