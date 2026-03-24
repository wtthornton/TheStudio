/**
 * Epic 47.8 — Vitest tests for guided tours.
 *
 * Covers:
 *  1. TOUR_REGISTRY — 4 tours with expected ids, labels, storageKeys
 *  2. Registry helper functions — isTourCompleted, markTourCompleted,
 *     resetTourCompletion, resetAllTours, getTourMeta
 *  3. HelpMenu with 4 guided tour replay links from TOUR_REGISTRY
 *  4. TourBeacon — renders when not completed, hidden when completed
 */

// ---------------------------------------------------------------------------
// Mock react-joyride so TourProvider renders without a DOM paint engine
// ---------------------------------------------------------------------------
vi.mock('react-joyride', () => {
  const Joyride = () => null
  const STATUS = { FINISHED: 'finished', SKIPPED: 'skipped' }
  return { default: Joyride, Joyride, STATUS }
})

import { render, screen, fireEvent } from '@testing-library/react'
import { beforeEach, afterEach, describe, expect, it, vi } from 'vitest'
import {
  TOUR_REGISTRY,
  getTourMeta,
  isTourCompleted,
  markTourCompleted,
  resetTourCompletion,
  resetAllTours,
  type TourId,
} from '../components/tours/registry'
import { HelpMenu } from '../components/help/HelpMenu'
import { TourProvider } from '../components/tours/TourProvider'
import { TourBeacon } from '../components/tours/TourBeacon'
import type { Step } from 'react-joyride'

// ---------------------------------------------------------------------------
// localStorage helpers
// ---------------------------------------------------------------------------
function clearTourStorage() {
  for (const tour of TOUR_REGISTRY) {
    localStorage.removeItem(tour.storageKey)
  }
}

// ===========================================================================
// 1. TOUR_REGISTRY
// ===========================================================================
describe('TOUR_REGISTRY', () => {
  it('contains exactly 4 tours', () => {
    expect(TOUR_REGISTRY).toHaveLength(4)
  })

  it('has the expected tour ids in order', () => {
    const ids = TOUR_REGISTRY.map((t) => t.id)
    expect(ids).toEqual(['pipeline', 'triage', 'analytics', 'repo-trust'])
  })

  it('each tour has a non-empty label', () => {
    for (const tour of TOUR_REGISTRY) {
      expect(tour.label.length).toBeGreaterThan(0)
    }
  })

  it('each tour has a non-empty description', () => {
    for (const tour of TOUR_REGISTRY) {
      expect(tour.description.length).toBeGreaterThan(0)
    }
  })

  it('each tour has a unique storageKey', () => {
    const keys = TOUR_REGISTRY.map((t) => t.storageKey)
    const unique = new Set(keys)
    expect(unique.size).toBe(TOUR_REGISTRY.length)
  })

  it('all storageKeys follow the studio:tour:*:completed pattern', () => {
    for (const tour of TOUR_REGISTRY) {
      expect(tour.storageKey).toMatch(/^studio:tour:.+:completed$/)
    }
  })
})

// ===========================================================================
// 2. Registry helper functions
// ===========================================================================
describe('getTourMeta', () => {
  it('returns the correct meta for a known tour id', () => {
    const meta = getTourMeta('pipeline')
    expect(meta).toBeDefined()
    expect(meta!.id).toBe('pipeline')
  })

  it('returns undefined for an unknown tour id', () => {
    // Cast to force the call with an unregistered id
    expect(getTourMeta('unknown' as TourId)).toBeUndefined()
  })
})

describe('isTourCompleted / markTourCompleted / resetTourCompletion', () => {
  beforeEach(() => clearTourStorage())
  afterEach(() => clearTourStorage())

  it('isTourCompleted returns false when key is absent', () => {
    const { storageKey } = TOUR_REGISTRY[0]
    expect(isTourCompleted(storageKey)).toBe(false)
  })

  it('markTourCompleted sets key to "true"', () => {
    const { storageKey } = TOUR_REGISTRY[0]
    markTourCompleted(storageKey)
    expect(localStorage.getItem(storageKey)).toBe('true')
    expect(isTourCompleted(storageKey)).toBe(true)
  })

  it('resetTourCompletion removes the key', () => {
    const { storageKey } = TOUR_REGISTRY[0]
    markTourCompleted(storageKey)
    resetTourCompletion(storageKey)
    expect(localStorage.getItem(storageKey)).toBeNull()
    expect(isTourCompleted(storageKey)).toBe(false)
  })
})

describe('resetAllTours', () => {
  beforeEach(() => {
    // Mark all tours as completed before each test
    for (const tour of TOUR_REGISTRY) {
      markTourCompleted(tour.storageKey)
    }
  })
  afterEach(() => clearTourStorage())

  it('clears all 4 tour completion flags', () => {
    resetAllTours()
    for (const tour of TOUR_REGISTRY) {
      expect(isTourCompleted(tour.storageKey)).toBe(false)
    }
  })
})

// ===========================================================================
// 3. HelpMenu — 4 guided tour replay links
// ===========================================================================
describe('HelpMenu — guided tours with TOUR_REGISTRY', () => {
  // Build the tours array that App.tsx will pass (same shape as TOUR_REGISTRY)
  const tours = TOUR_REGISTRY.map((t) => ({
    id: t.id,
    label: t.label,
    description: t.description,
  }))

  function renderWithTours(onStartTour = vi.fn()) {
    return render(
      <HelpMenu
        onOpenHelpPanel={vi.fn()}
        onOpenWizard={vi.fn()}
        onOpenApiDocs={vi.fn()}
        onStartTour={onStartTour}
        tours={tours}
      />,
    )
  }

  it('renders all 4 tour buttons when dropdown is open', () => {
    renderWithTours()
    fireEvent.click(screen.getByTestId('help-menu-trigger'))
    for (const tour of tours) {
      expect(screen.getByTestId(`help-menu-tour-${tour.id}`)).toBeInTheDocument()
    }
  })

  it('shows each tour label in the dropdown', () => {
    renderWithTours()
    fireEvent.click(screen.getByTestId('help-menu-trigger'))
    for (const tour of tours) {
      expect(screen.getByText(tour.label)).toBeInTheDocument()
    }
  })

  it('shows each tour description in the dropdown', () => {
    renderWithTours()
    fireEvent.click(screen.getByTestId('help-menu-trigger'))
    for (const tour of tours) {
      expect(screen.getByText(tour.description!)).toBeInTheDocument()
    }
  })

  it('clicking each tour calls onStartTour with the correct id', () => {
    const onStartTour = vi.fn()
    renderWithTours(onStartTour)
    fireEvent.click(screen.getByTestId('help-menu-trigger'))
    for (const tour of tours) {
      fireEvent.click(screen.getByTestId(`help-menu-tour-${tour.id}`))
      expect(onStartTour).toHaveBeenCalledWith(tour.id)
      // Re-open the menu for the next iteration
      if (tour.id !== tours[tours.length - 1].id) {
        fireEvent.click(screen.getByTestId('help-menu-trigger'))
      }
    }
    expect(onStartTour).toHaveBeenCalledTimes(4)
  })

  it('clicking a tour item closes the dropdown', () => {
    renderWithTours()
    fireEvent.click(screen.getByTestId('help-menu-trigger'))
    fireEvent.click(screen.getByTestId('help-menu-tour-pipeline'))
    expect(screen.queryByTestId('help-menu-dropdown')).not.toBeInTheDocument()
  })

  it('does NOT render the placeholder "Guided Tours" button', () => {
    renderWithTours()
    fireEvent.click(screen.getByTestId('help-menu-trigger'))
    expect(screen.queryByTestId('help-menu-tours')).not.toBeInTheDocument()
  })

  it('shows "Guided Tours" section header', () => {
    renderWithTours()
    fireEvent.click(screen.getByTestId('help-menu-trigger'))
    expect(screen.getByText('Guided Tours')).toBeInTheDocument()
  })
})

// ===========================================================================
// 4. TourBeacon
// ===========================================================================
const DUMMY_STEPS: Step[] = [{ target: 'body', content: 'Hello' }]

function renderBeacon(props: { tourId: TourId; completed?: boolean }) {
  // Prime localStorage before render
  const meta = getTourMeta(props.tourId)!
  if (props.completed) {
    markTourCompleted(meta.storageKey)
  } else {
    resetTourCompletion(meta.storageKey)
  }

  return render(
    <TourProvider>
      <TourBeacon tourId={props.tourId} steps={DUMMY_STEPS} label="Test tour" />
    </TourProvider>,
  )
}

describe('TourBeacon', () => {
  afterEach(() => clearTourStorage())

  it('renders the beacon button when tour is not completed', () => {
    renderBeacon({ tourId: 'pipeline', completed: false })
    expect(screen.getByTestId('tour-beacon-pipeline')).toBeInTheDocument()
  })

  it('renders null (no button) when tour is already completed', () => {
    renderBeacon({ tourId: 'pipeline', completed: true })
    expect(screen.queryByTestId('tour-beacon-pipeline')).not.toBeInTheDocument()
  })

  it('shows the provided label on the beacon button', () => {
    renderBeacon({ tourId: 'triage', completed: false })
    expect(screen.getByTestId('tour-beacon-triage')).toHaveTextContent('Test tour')
  })

  it('has the correct aria-label', () => {
    renderBeacon({ tourId: 'analytics', completed: false })
    expect(screen.getByTestId('tour-beacon-analytics')).toHaveAttribute(
      'aria-label',
      'Start guided tour: Test tour',
    )
  })
})
