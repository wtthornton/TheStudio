/** RoutingPreview tests — 13 test cases (Epic 36, Story 36.15c). */

import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, beforeEach, vi } from 'vitest'
import RoutingPreview from '../RoutingPreview'
import { useRoutingStore } from '../../../stores/routing-store'
import type { RoutingResultRead } from '../../../lib/api'

// --- Fixtures ---

const selectionMandatory = {
  expert_id: 'exp-1',
  expert_class: 'SecurityExpert',
  pattern: 'auth/*',
  reputation_weight: 0.9,
  reputation_confidence: 0.85,
  selection_score: 0.88,
  selection_reason: 'MANDATORY',
}

const selectionAuto = {
  expert_id: 'exp-2',
  expert_class: 'TestExpert',
  pattern: 'tests/*',
  reputation_weight: 0.6,
  reputation_confidence: 0.75,
  selection_score: 0.65,
  selection_reason: 'AUTO',
}

const routingResult: RoutingResultRead = {
  taskpacket_id: 'task-1',
  selections: [selectionMandatory, selectionAuto],
  rationale: 'Security review required. Tests need coverage.',
  budget_remaining: 1,
}

// --- Mocks ---

const mockLoadRouting = vi.fn()
const mockApprove = vi.fn()
const mockOverride = vi.fn()
const mockReset = vi.fn()

vi.mock('../../../lib/api', () => ({
  fetchRouting: vi.fn(),
  approveRouting: vi.fn(),
  overrideRouting: vi.fn(),
}))

function setupStore(
  overrides: Partial<ReturnType<typeof useRoutingStore.getState>> = {},
) {
  useRoutingStore.setState({
    taskId: 'task-1',
    routing: routingResult,
    loading: false,
    error: null,
    saving: false,
    loadRouting: mockLoadRouting,
    approve: mockApprove,
    override: mockOverride,
    reset: mockReset,
    ...overrides,
  })
}

beforeEach(() => {
  vi.clearAllMocks()
})

// --- Tests ---

describe('RoutingPreview', () => {
  it('1. shows loading spinner when loading is true', () => {
    setupStore({ loading: true, routing: null })
    render(<RoutingPreview taskId="task-1" />)
    expect(screen.getByText(/loading routing data/i)).toBeInTheDocument()
  })

  it('2. shows error message when error is set', () => {
    setupStore({ error: 'Network error', routing: null })
    render(<RoutingPreview taskId="task-1" />)
    expect(screen.getByText('Network error')).toBeInTheDocument()
  })

  it('3. error state shows Retry button', () => {
    setupStore({ error: 'Network error', routing: null })
    render(<RoutingPreview taskId="task-1" />)
    expect(screen.getByRole('button', { name: /retry/i })).toBeInTheDocument()
  })

  it('4. clicking Retry calls loadRouting', () => {
    setupStore({ error: 'Network error', routing: null })
    render(<RoutingPreview taskId="task-1" />)
    fireEvent.click(screen.getByRole('button', { name: /retry/i }))
    expect(mockLoadRouting).toHaveBeenCalledWith('task-1')
  })

  it('5. shows empty-state message when routing is null', () => {
    setupStore({ routing: null })
    render(<RoutingPreview taskId="task-1" />)
    expect(
      screen.getByText(/no routing data available/i),
    ).toBeInTheDocument()
  })

  it('6. renders rationale section when routing has rationale', () => {
    setupStore()
    render(<RoutingPreview taskId="task-1" />)
    expect(
      screen.getByText('Security review required. Tests need coverage.'),
    ).toBeInTheDocument()
  })

  it('7. renders expert cards for each selection', () => {
    setupStore()
    render(<RoutingPreview taskId="task-1" />)
    expect(screen.getByText('SecurityExpert')).toBeInTheDocument()
    expect(screen.getByText('TestExpert')).toBeInTheDocument()
  })

  it('8. shows "no experts selected" when selections is empty', () => {
    setupStore({
      routing: { ...routingResult, selections: [] },
    })
    render(<RoutingPreview taskId="task-1" />)
    expect(screen.getByText(/no experts selected/i)).toBeInTheDocument()
  })

  it('9. shows budget remaining', () => {
    setupStore()
    render(<RoutingPreview taskId="task-1" />)
    expect(screen.getByText(/budget.*1.*slot remaining/i)).toBeInTheDocument()
  })

  it('10. Approve Routing button calls store approve', () => {
    setupStore()
    render(<RoutingPreview taskId="task-1" />)
    fireEvent.click(screen.getByRole('button', { name: /approve routing/i }))
    expect(mockApprove).toHaveBeenCalledOnce()
  })

  it('11. shows "Approving…" label while saving', () => {
    setupStore({ saving: true })
    render(<RoutingPreview taskId="task-1" />)
    expect(screen.getByText(/approving…/i)).toBeInTheDocument()
  })

  it('12. removing an AUTO expert calls override with remove reason', () => {
    setupStore()
    render(<RoutingPreview taskId="task-1" />)
    // TestExpert is AUTO — has a Remove button
    fireEvent.click(screen.getByRole('button', { name: /remove/i }))
    expect(mockOverride).toHaveBeenCalledWith('remove:TestExpert')
  })

  it('13. AddExpertDropdown excludes already-selected classes and calls override on selection', () => {
    setupStore()
    render(<RoutingPreview taskId="task-1" />)
    const dropdown = screen.getByRole('combobox', { name: /add expert/i })
    // SecurityExpert and TestExpert are already selected — should NOT appear
    const options = Array.from(dropdown.querySelectorAll('option')).map(
      (o) => (o as HTMLOptionElement).value,
    )
    expect(options).not.toContain('SecurityExpert')
    expect(options).not.toContain('TestExpert')
    // Pick DatabaseExpert
    fireEvent.change(dropdown, { target: { value: 'DatabaseExpert' } })
    expect(mockOverride).toHaveBeenCalledWith('add:DatabaseExpert')
  })
})
