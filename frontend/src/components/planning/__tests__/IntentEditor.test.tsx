/** IntentEditor tests — 15 test cases covering core flows (Epic 36, 36.11g). */

import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, beforeEach, vi } from 'vitest'
import IntentEditor from '../IntentEditor'
import { useIntentStore } from '../../../stores/intent-store'
import type { IntentSpecRead, TaskPacketRead } from '../../../lib/api'

// --- Fixtures ---

const specV1: IntentSpecRead = {
  id: 'spec-1',
  taskpacket_id: 'task-1',
  version: 1,
  goal: 'Implement login feature',
  constraints: ['Must use OAuth', 'No plaintext passwords'],
  acceptance_criteria: ['User can login', 'User can logout'],
  non_goals: ['Password reset'],
  source: 'auto',
  created_at: '2026-03-01T12:00:00Z',
}

const specV2: IntentSpecRead = {
  id: 'spec-2',
  taskpacket_id: 'task-1',
  version: 2,
  goal: 'Implement login and signup features',
  constraints: ['Must use OAuth', 'Rate limit attempts'],
  acceptance_criteria: ['User can login', 'User can logout', 'User can signup'],
  non_goals: ['Password reset', 'Social login'],
  source: 'developer',
  created_at: '2026-03-02T12:00:00Z',
}

const mockTask: TaskPacketRead = {
  id: 'task-1',
  repo: 'owner/repo',
  issue_id: 42,
  status: 'intent_review',
  created_at: '2026-03-01T10:00:00Z',
  updated_at: '2026-03-01T12:00:00Z',
  issue_title: 'Add login feature',
  issue_body: 'We need a login system',
  scope: null,
  risk_flags: null,
  complexity_index: null,
}

// --- Mocks ---

const mockFetchTaskDetail = vi.fn()
const mockFetchIntent = vi.fn()
const mockApproveIntent = vi.fn()
const mockRejectIntent = vi.fn()
const mockEditIntent = vi.fn()
const mockRefineIntent = vi.fn()

vi.mock('../../../lib/api', () => ({
  fetchTaskDetail: (...args: unknown[]) => mockFetchTaskDetail(...args),
  fetchIntent: (...args: unknown[]) => mockFetchIntent(...args),
  approveIntent: (...args: unknown[]) => mockApproveIntent(...args),
  rejectIntent: (...args: unknown[]) => mockRejectIntent(...args),
  editIntent: (...args: unknown[]) => mockEditIntent(...args),
  refineIntent: (...args: unknown[]) => mockRefineIntent(...args),
}))

function setupStore(overrides: Partial<ReturnType<typeof useIntentStore.getState>> = {}) {
  useIntentStore.setState({
    taskId: 'task-1',
    current: specV2,
    versions: [specV1, specV2],
    selectedVersion: 2,
    loading: false,
    error: null,
    mode: 'view',
    refineModalOpen: false,
    saving: false,
    ...overrides,
  })
}

describe('IntentEditor', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockFetchTaskDetail.mockResolvedValue(mockTask)
    mockFetchIntent.mockResolvedValue({ current: specV2, versions: [specV1, specV2] })
    mockApproveIntent.mockResolvedValue({})
    mockRejectIntent.mockResolvedValue({})
    mockEditIntent.mockResolvedValue({})
    mockRefineIntent.mockResolvedValue({})
  })

  // 1. Loading state
  it('shows loading state while fetching', () => {
    useIntentStore.setState({ loading: true, current: null, versions: [], taskId: null, selectedVersion: null, error: null, mode: 'view', refineModalOpen: false, saving: false })
    render(<IntentEditor taskId="task-1" />)
    expect(screen.getByText(/loading intent review/i)).toBeInTheDocument()
  })

  // 2. Split pane layout
  it('renders split pane with source context and intent spec', async () => {
    setupStore()
    render(<IntentEditor taskId="task-1" />)
    await waitFor(() => {
      expect(screen.getByText('Implement login and signup features')).toBeInTheDocument()
    })
    // Should show goal from current spec
    expect(screen.getByText('Implement login and signup features')).toBeInTheDocument()
  })

  // 3. Sections visible
  it('displays constraints, acceptance criteria, and non-goals sections', async () => {
    setupStore()
    render(<IntentEditor taskId="task-1" />)
    await waitFor(() => {
      expect(screen.getByText('Must use OAuth')).toBeInTheDocument()
    })
    expect(screen.getByText('Rate limit attempts')).toBeInTheDocument()
    expect(screen.getByText('User can signup')).toBeInTheDocument()
    expect(screen.getByText('Social login')).toBeInTheDocument()
  })

  // 4. Source badge
  it('shows source badge for current version', async () => {
    setupStore()
    render(<IntentEditor taskId="task-1" />)
    await waitFor(() => {
      expect(screen.getByText('developer')).toBeInTheDocument()
    })
  })

  // 5. Version selector
  it('renders version selector with all versions', async () => {
    setupStore()
    render(<IntentEditor taskId="task-1" />)
    await waitFor(() => {
      const selector = screen.getByRole('combobox')
      expect(selector).toBeInTheDocument()
      expect(selector.querySelectorAll('option')).toHaveLength(2)
    })
  })

  // 6. Approve action
  it('calls approve when Approve button is clicked', async () => {
    setupStore()
    render(<IntentEditor taskId="task-1" />)
    await waitFor(() => {
      expect(screen.getByText('Approve')).toBeInTheDocument()
    })
    fireEvent.click(screen.getByText('Approve'))
    await waitFor(() => {
      expect(mockApproveIntent).toHaveBeenCalledWith('task-1')
    })
  })

  // 7. Reject flow
  it('shows reject confirmation with reason input', async () => {
    setupStore()
    render(<IntentEditor taskId="task-1" />)
    await waitFor(() => {
      expect(screen.getByText('Reject')).toBeInTheDocument()
    })
    fireEvent.click(screen.getByText('Reject'))
    const input = screen.getByPlaceholderText(/rejection reason/i)
    expect(input).toBeInTheDocument()
  })

  // 8. Edit mode
  it('switches to edit mode when Edit is clicked', async () => {
    setupStore()
    render(<IntentEditor taskId="task-1" />)
    await waitFor(() => {
      expect(screen.getByText('Edit')).toBeInTheDocument()
    })
    fireEvent.click(screen.getByText('Edit'))
    // Store mode should be 'edit' — component should render IntentEditMode
    await waitFor(() => {
      expect(useIntentStore.getState().mode).toBe('edit')
    })
  })

  // 9. Refine button opens modal
  it('opens refinement modal when Refine is clicked', async () => {
    setupStore()
    render(<IntentEditor taskId="task-1" />)
    await waitFor(() => {
      expect(screen.getByText('Refine')).toBeInTheDocument()
    })
    fireEvent.click(screen.getByText('Refine'))
    expect(useIntentStore.getState().refineModalOpen).toBe(true)
  })

  // 10. Compare Versions toggle appears
  it('shows Compare Versions button when multiple versions exist', async () => {
    setupStore()
    render(<IntentEditor taskId="task-1" />)
    await waitFor(() => {
      expect(screen.getByTestId('compare-toggle')).toBeInTheDocument()
      expect(screen.getByTestId('compare-toggle')).toHaveTextContent('Compare Versions')
    })
  })

  // 11. Compare Versions toggle hidden for single version
  it('hides Compare Versions button when only one version exists', async () => {
    // Override mock to return only v1 so the API fetch won't replace store state with v2
    mockFetchIntent.mockResolvedValue({ current: specV1, versions: [specV1] })
    setupStore({ versions: [specV1], current: specV1, selectedVersion: 1 })
    render(<IntentEditor taskId="task-1" />)
    await waitFor(() => {
      expect(screen.getByText('Implement login feature')).toBeInTheDocument()
    })
    expect(screen.queryByTestId('compare-toggle')).not.toBeInTheDocument()
  })

  // 12. Diff view shows when toggled
  it('shows version diff when Compare Versions is toggled on', async () => {
    setupStore()
    render(<IntentEditor taskId="task-1" />)
    await waitFor(() => {
      expect(screen.getByTestId('compare-toggle')).toBeInTheDocument()
    })
    fireEvent.click(screen.getByTestId('compare-toggle'))
    await waitFor(() => {
      expect(screen.getByTestId('version-diff')).toBeInTheDocument()
    })
  })

  // 13. Diff highlights added/removed items
  it('shows added and removed items in diff view', async () => {
    setupStore()
    render(<IntentEditor taskId="task-1" />)
    await waitFor(() => {
      expect(screen.getByTestId('compare-toggle')).toBeInTheDocument()
    })
    fireEvent.click(screen.getByTestId('compare-toggle'))
    await waitFor(() => {
      expect(screen.getByTestId('version-diff')).toBeInTheDocument()
    })
    // "No plaintext passwords" was removed (in v1 but not v2)
    // "Rate limit attempts" was added (in v2 but not v1)
    // "User can signup" was added
    // Check the diff container exists and has content
    const diffEl = screen.getByTestId('version-diff')
    expect(diffEl).toHaveTextContent('Rate limit attempts')
    expect(diffEl).toHaveTextContent('No plaintext passwords')
    expect(diffEl).toHaveTextContent('User can signup')
  })

  // 14. Error state
  it('shows error message when intent fails to load', async () => {
    // Simulate API failure so the component itself sets the error state
    mockFetchIntent.mockRejectedValue(new Error('Network error'))
    setupStore({ current: null, error: null })
    render(<IntentEditor taskId="task-1" />)
    await waitFor(() => {
      expect(screen.getByText('Network error')).toBeInTheDocument()
    })
  })

  // 15. No intent state
  it('shows no-intent message when current is null with no error', async () => {
    // API returns no current intent
    mockFetchIntent.mockResolvedValue({ current: null, versions: [] })
    setupStore({ current: null, error: null, versions: [] })
    render(<IntentEditor taskId="task-1" />)
    await waitFor(() => {
      expect(screen.getByText(/no intent specification yet/i)).toBeInTheDocument()
    })
  })
})

// Separate describe for VersionDiff unit tests
describe('diffList', () => {
  it('classifies added, removed, and unchanged items', async () => {
    const { diffList } = await import('../VersionDiff')
    const result = diffList(['a', 'b', 'c'], ['b', 'c', 'd'])
    expect(result).toEqual([
      { value: 'a', status: 'removed' },
      { value: 'b', status: 'unchanged' },
      { value: 'c', status: 'unchanged' },
      { value: 'd', status: 'added' },
    ])
  })
})
