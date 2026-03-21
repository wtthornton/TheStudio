import { render, screen } from '@testing-library/react'
import { describe, it, expect, beforeEach } from 'vitest'
import { PipelineStatus } from '../PipelineStatus'
import { usePipelineStore } from '../../stores/pipeline-store'
import { PIPELINE_STAGES } from '../../lib/constants'

describe('PipelineStatus', () => {
  beforeEach(() => {
    usePipelineStore.getState().reset()
  })

  it('renders all 9 stage nodes', () => {
    render(<PipelineStatus />)
    for (const stage of PIPELINE_STAGES) {
      expect(screen.getByTestId(`stage-${stage.id}`)).toBeInTheDocument()
    }
  })

  it('renders pipeline rail container', () => {
    render(<PipelineStatus />)
    expect(screen.getByTestId('pipeline-rail')).toBeInTheDocument()
  })

  it('renders 8 connecting arrows between 9 stages', () => {
    const { container } = render(<PipelineStatus />)
    const arrows = container.querySelectorAll('svg')
    expect(arrows).toHaveLength(8)
  })

  it('shows task count badge when stage has tasks', () => {
    usePipelineStore.getState().stageEnter('intake', 'task-1')
    render(<PipelineStatus />)
    const badge = screen.getByTestId('stage-count-intake')
    expect(badge).toHaveTextContent('1')
  })

  it('hides task count badge when stage has no tasks', () => {
    render(<PipelineStatus />)
    expect(screen.queryByTestId('stage-count-intake')).not.toBeInTheDocument()
  })

  it('reflects active status from store', () => {
    usePipelineStore.getState().stageEnter('context', 'task-2')
    render(<PipelineStatus />)
    const dot = screen.getByTestId('stage-dot-context')
    // active status → blue-500 (#3b82f6)
    expect(dot.style.backgroundColor).toBe('rgb(59, 130, 246)')
  })

  it('reflects failed status from store', () => {
    usePipelineStore.getState().stageEnter('verify', 'task-3')
    usePipelineStore.getState().stageExit('verify', 'task-3', false)
    render(<PipelineStatus />)
    const dot = screen.getByTestId('stage-dot-verify')
    // failed status → red-500 (#ef4444)
    expect(dot.style.backgroundColor).toBe('rgb(239, 68, 68)')
  })

  it('reflects passed status from store', () => {
    usePipelineStore.getState().stageEnter('qa', 'task-4')
    usePipelineStore.getState().stageExit('qa', 'task-4', true)
    render(<PipelineStatus />)
    const dot = screen.getByTestId('stage-dot-qa')
    // passed status → emerald-500 (#10b981)
    expect(dot.style.backgroundColor).toBe('rgb(16, 185, 129)')
  })
})
