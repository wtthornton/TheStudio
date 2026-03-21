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

  it('renders idle icons for all stages by default', () => {
    render(<PipelineStatus />)
    const idleIcons = screen.getAllByTestId('icon-idle')
    expect(idleIcons).toHaveLength(9)
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

  it('shows active icon when stage has active tasks', () => {
    usePipelineStore.getState().stageEnter('context', 'task-2')
    render(<PipelineStatus />)
    expect(screen.getByTestId('icon-active')).toBeInTheDocument()
    // Other 8 stages still idle
    expect(screen.getAllByTestId('icon-idle')).toHaveLength(8)
  })

  it('shows failed icon when stage fails', () => {
    usePipelineStore.getState().stageEnter('verify', 'task-3')
    usePipelineStore.getState().stageExit('verify', 'task-3', false)
    render(<PipelineStatus />)
    expect(screen.getByTestId('icon-failed')).toBeInTheDocument()
  })

  it('shows passed icon when stage passes', () => {
    usePipelineStore.getState().stageEnter('qa', 'task-4')
    usePipelineStore.getState().stageExit('qa', 'task-4', true)
    render(<PipelineStatus />)
    expect(screen.getByTestId('icon-passed')).toBeInTheDocument()
  })
})
