/**
 * Epic 45.10 — Vitest tests for HelpMenu.
 * Covers: render, open/close, keyboard, outside-click, all menu item callbacks,
 * guided tours (enabled/disabled), aria attributes.
 */

import { render, screen, fireEvent } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { HelpMenu } from '../components/help/HelpMenu'

// ---------------------------------------------------------------------------
// Shared defaults
// ---------------------------------------------------------------------------
function renderMenu(props: Partial<React.ComponentProps<typeof HelpMenu>> = {}) {
  const defaults = {
    onOpenHelpPanel: vi.fn(),
    onOpenWizard: vi.fn(),
    onOpenApiDocs: vi.fn(),
  }
  return render(<HelpMenu {...defaults} {...props} />)
}

// ===========================================================================
// Render
// ===========================================================================
describe('HelpMenu — render', () => {
  it('renders the trigger button', () => {
    renderMenu()
    expect(screen.getByTestId('help-menu-trigger')).toBeInTheDocument()
  })

  it('has aria-label "Help menu" on trigger', () => {
    renderMenu()
    expect(screen.getByTestId('help-menu-trigger')).toHaveAttribute('aria-label', 'Help menu')
  })

  it('dropdown is hidden initially', () => {
    renderMenu()
    expect(screen.queryByTestId('help-menu-dropdown')).not.toBeInTheDocument()
  })

  it('wraps in data-testid="help-menu"', () => {
    renderMenu()
    expect(screen.getByTestId('help-menu')).toBeInTheDocument()
  })
})

// ===========================================================================
// Open / close
// ===========================================================================
describe('HelpMenu — open / close', () => {
  it('opens dropdown when trigger is clicked', () => {
    renderMenu()
    fireEvent.click(screen.getByTestId('help-menu-trigger'))
    expect(screen.getByTestId('help-menu-dropdown')).toBeInTheDocument()
  })

  it('closes dropdown when trigger is clicked again', () => {
    renderMenu()
    const trigger = screen.getByTestId('help-menu-trigger')
    fireEvent.click(trigger)
    fireEvent.click(trigger)
    expect(screen.queryByTestId('help-menu-dropdown')).not.toBeInTheDocument()
  })

  it('closes on Escape key', () => {
    renderMenu()
    fireEvent.click(screen.getByTestId('help-menu-trigger'))
    expect(screen.getByTestId('help-menu-dropdown')).toBeInTheDocument()
    fireEvent.keyDown(document, { key: 'Escape' })
    expect(screen.queryByTestId('help-menu-dropdown')).not.toBeInTheDocument()
  })

  it('closes when clicking outside the menu', () => {
    render(
      <div>
        <HelpMenu
          onOpenHelpPanel={vi.fn()}
          onOpenWizard={vi.fn()}
          onOpenApiDocs={vi.fn()}
        />
        <div data-testid="outside">outside element</div>
      </div>,
    )
    fireEvent.click(screen.getByTestId('help-menu-trigger'))
    expect(screen.getByTestId('help-menu-dropdown')).toBeInTheDocument()
    fireEvent.mouseDown(screen.getByTestId('outside'))
    expect(screen.queryByTestId('help-menu-dropdown')).not.toBeInTheDocument()
  })

  it('sets aria-expanded="false" when closed', () => {
    renderMenu()
    expect(screen.getByTestId('help-menu-trigger')).toHaveAttribute('aria-expanded', 'false')
  })

  it('sets aria-expanded="true" when open', () => {
    renderMenu()
    fireEvent.click(screen.getByTestId('help-menu-trigger'))
    expect(screen.getByTestId('help-menu-trigger')).toHaveAttribute('aria-expanded', 'true')
  })
})

// ===========================================================================
// Menu item callbacks
// ===========================================================================
describe('HelpMenu — menu item callbacks', () => {
  beforeEach(() => {
    // pre-open the menu for each test
  })

  it('Help Panel item calls onOpenHelpPanel and closes menu', () => {
    const onOpenHelpPanel = vi.fn()
    renderMenu({ onOpenHelpPanel })
    fireEvent.click(screen.getByTestId('help-menu-trigger'))
    fireEvent.click(screen.getByTestId('help-menu-help-panel'))
    expect(onOpenHelpPanel).toHaveBeenCalledOnce()
    expect(screen.queryByTestId('help-menu-dropdown')).not.toBeInTheDocument()
  })

  it('Setup Wizard item calls onOpenWizard and closes menu', () => {
    const onOpenWizard = vi.fn()
    renderMenu({ onOpenWizard })
    fireEvent.click(screen.getByTestId('help-menu-trigger'))
    fireEvent.click(screen.getByTestId('help-menu-wizard'))
    expect(onOpenWizard).toHaveBeenCalledOnce()
    expect(screen.queryByTestId('help-menu-dropdown')).not.toBeInTheDocument()
  })

  it('API Docs item calls onOpenApiDocs and closes menu', () => {
    const onOpenApiDocs = vi.fn()
    renderMenu({ onOpenApiDocs })
    fireEvent.click(screen.getByTestId('help-menu-trigger'))
    fireEvent.click(screen.getByTestId('help-menu-api-docs'))
    expect(onOpenApiDocs).toHaveBeenCalledOnce()
    expect(screen.queryByTestId('help-menu-dropdown')).not.toBeInTheDocument()
  })
})

// ===========================================================================
// Guided Tours — placeholder state (no onStartTour provided)
// ===========================================================================
describe('HelpMenu — guided tours placeholder', () => {
  it('renders Guided Tours item as disabled when onStartTour not provided', () => {
    renderMenu()
    fireEvent.click(screen.getByTestId('help-menu-trigger'))
    const toursBtn = screen.getByTestId('help-menu-tours')
    expect(toursBtn).toBeDisabled()
  })

  it('shows "Coming soon" subtext when tours not available', () => {
    renderMenu()
    fireEvent.click(screen.getByTestId('help-menu-trigger'))
    expect(screen.getByText(/coming soon/i)).toBeInTheDocument()
  })
})

// ===========================================================================
// Guided Tours — enabled state (onStartTour + tours provided)
// ===========================================================================
describe('HelpMenu — guided tours enabled', () => {
  const tours = [
    { id: 'pipeline', label: 'Pipeline Tour' },
    { id: 'triage', label: 'Triage Tour' },
  ]

  it('renders individual tour items when tours and onStartTour are provided', () => {
    const onStartTour = vi.fn()
    renderMenu({ onStartTour, tours })
    fireEvent.click(screen.getByTestId('help-menu-trigger'))
    expect(screen.getByTestId('help-menu-tour-pipeline')).toBeInTheDocument()
    expect(screen.getByTestId('help-menu-tour-triage')).toBeInTheDocument()
  })

  it('shows tour labels', () => {
    const onStartTour = vi.fn()
    renderMenu({ onStartTour, tours })
    fireEvent.click(screen.getByTestId('help-menu-trigger'))
    expect(screen.getByText('Pipeline Tour')).toBeInTheDocument()
    expect(screen.getByText('Triage Tour')).toBeInTheDocument()
  })

  it('clicking a tour item calls onStartTour with the tour id', () => {
    const onStartTour = vi.fn()
    renderMenu({ onStartTour, tours })
    fireEvent.click(screen.getByTestId('help-menu-trigger'))
    fireEvent.click(screen.getByTestId('help-menu-tour-pipeline'))
    expect(onStartTour).toHaveBeenCalledWith('pipeline')
  })

  it('clicking a tour item closes the dropdown', () => {
    const onStartTour = vi.fn()
    renderMenu({ onStartTour, tours })
    fireEvent.click(screen.getByTestId('help-menu-trigger'))
    fireEvent.click(screen.getByTestId('help-menu-tour-triage'))
    expect(screen.queryByTestId('help-menu-dropdown')).not.toBeInTheDocument()
  })

  it('does not render placeholder "Coming soon" when real tours exist', () => {
    const onStartTour = vi.fn()
    renderMenu({ onStartTour, tours })
    fireEvent.click(screen.getByTestId('help-menu-trigger'))
    expect(screen.queryByText(/coming soon/i)).not.toBeInTheDocument()
  })
})

// ===========================================================================
// Dropdown content
// ===========================================================================
describe('HelpMenu — dropdown content', () => {
  it('dropdown has role="menu"', () => {
    renderMenu()
    fireEvent.click(screen.getByTestId('help-menu-trigger'))
    expect(screen.getByTestId('help-menu-dropdown')).toHaveAttribute('role', 'menu')
  })

  it('shows Help Panel menu item text', () => {
    renderMenu()
    fireEvent.click(screen.getByTestId('help-menu-trigger'))
    expect(screen.getByText('Help Panel')).toBeInTheDocument()
  })

  it('shows Setup Wizard menu item text', () => {
    renderMenu()
    fireEvent.click(screen.getByTestId('help-menu-trigger'))
    expect(screen.getByText('Setup Wizard')).toBeInTheDocument()
  })

  it('shows API Docs menu item text', () => {
    renderMenu()
    fireEvent.click(screen.getByTestId('help-menu-trigger'))
    expect(screen.getByText('API Docs')).toBeInTheDocument()
  })
})
