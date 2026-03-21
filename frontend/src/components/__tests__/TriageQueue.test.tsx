import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { TriageQueue } from '../planning/TriageQueue'
import { useTriageStore } from '../../stores/triage-store'
import type { TriageTask } from '../../lib/api'

const mockTask = (overrides: Partial<TriageTask> = {}): TriageTask => ({
  id: 'task-1',
  repo: 'owner/repo',
  issue_id: 42,
  status: 'triage',
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
  issue_title: 'Fix the login bug',
  issue_body: 'Users cannot log in when using Firefox',
  triage_enrichment: {
    file_count_estimate: 3,
    complexity_hint: 'medium',
    cost_estimate_range: { min: 0.10, max: 0.40 },
  },
  rejection_reason: null,
  ...overrides,
})

// Mock the API to return tasks when called
const mockFetchTriageTasks = vi.fn()
const mockAcceptTriageTask = vi.fn()
const mockRejectTriageTask = vi.fn()
const mockEditTriageTask = vi.fn()

vi.mock('../../lib/api', () => ({
  fetchTriageTasks: (...args: unknown[]) => mockFetchTriageTasks(...args),
  acceptTriageTask: (...args: unknown[]) => mockAcceptTriageTask(...args),
  rejectTriageTask: (...args: unknown[]) => mockRejectTriageTask(...args),
  editTriageTask: (...args: unknown[]) => mockEditTriageTask(...args),
}))

describe('TriageQueue', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // Default: API returns empty
    mockFetchTriageTasks.mockResolvedValue({ items: [], total: 0 })
    mockAcceptTriageTask.mockResolvedValue({ task: {}, workflow_started: true })
    mockRejectTriageTask.mockResolvedValue({})
    mockEditTriageTask.mockResolvedValue({})
    // Reset store
    useTriageStore.setState({ tasks: [], loading: false, error: null })
  })

  it('shows empty state when API returns no tasks', async () => {
    render(<TriageQueue />)
    await waitFor(() => {
      expect(screen.getByText(/no issues awaiting triage/i)).toBeInTheDocument()
    })
  })

  it('renders task cards from API response', async () => {
    mockFetchTriageTasks.mockResolvedValue({
      items: [
        mockTask(),
        mockTask({ id: 'task-2', issue_id: 43, issue_title: 'Another bug' }),
      ],
      total: 2,
    })
    render(<TriageQueue />)
    await waitFor(() => {
      expect(screen.getByText('Fix the login bug')).toBeInTheDocument()
      expect(screen.getByText('Another bug')).toBeInTheDocument()
    })
  })

  it('shows task count in header', async () => {
    mockFetchTriageTasks.mockResolvedValue({
      items: [mockTask(), mockTask({ id: 'task-2' })],
      total: 2,
    })
    render(<TriageQueue />)
    await waitFor(() => {
      expect(screen.getByText('(2)')).toBeInTheDocument()
    })
  })

  it('shows complexity badge from enrichment', async () => {
    mockFetchTriageTasks.mockResolvedValue({ items: [mockTask()], total: 1 })
    render(<TriageQueue />)
    await waitFor(() => {
      expect(screen.getByText('medium')).toBeInTheDocument()
    })
  })

  it('shows file count from enrichment', async () => {
    mockFetchTriageTasks.mockResolvedValue({ items: [mockTask()], total: 1 })
    render(<TriageQueue />)
    await waitFor(() => {
      expect(screen.getByText(/~3 files/)).toBeInTheDocument()
    })
  })

  it('shows accept button', async () => {
    mockFetchTriageTasks.mockResolvedValue({ items: [mockTask()], total: 1 })
    render(<TriageQueue />)
    await waitFor(() => {
      expect(screen.getByText('Accept & Plan')).toBeInTheDocument()
    })
  })

  it('shows reject reasons on reject button click', async () => {
    mockFetchTriageTasks.mockResolvedValue({ items: [mockTask()], total: 1 })
    render(<TriageQueue />)
    await waitFor(() => {
      expect(screen.getByText('Reject')).toBeInTheDocument()
    })
    fireEvent.click(screen.getByText('Reject'))
    expect(screen.getByText('Duplicate')).toBeInTheDocument()
    expect(screen.getByText('Out of Scope')).toBeInTheDocument()
    expect(screen.getByText('Needs Info')).toBeInTheDocument()
    expect(screen.getByText("Won't Fix")).toBeInTheDocument()
  })

  it('shows edit button', async () => {
    mockFetchTriageTasks.mockResolvedValue({ items: [mockTask()], total: 1 })
    render(<TriageQueue />)
    await waitFor(() => {
      expect(screen.getByText('Edit')).toBeInTheDocument()
    })
  })

  it('shows error with retry button on API failure', async () => {
    mockFetchTriageTasks.mockRejectedValue(new Error('Network error'))
    render(<TriageQueue />)
    await waitFor(() => {
      expect(screen.getByText(/network error/i)).toBeInTheDocument()
      expect(screen.getByText(/retry/i)).toBeInTheDocument()
    })
  })
})
