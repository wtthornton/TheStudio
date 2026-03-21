import { render, screen } from '@testing-library/react'
import { describe, it, expect, beforeEach } from 'vitest'
import { ConnectionIndicator } from '../ConnectionIndicator'
import { usePipelineStore } from '../../stores/pipeline-store'

describe('ConnectionIndicator', () => {
  beforeEach(() => {
    usePipelineStore.getState().reset()
    usePipelineStore.getState().setConnected(false)
  })

  it('shows disconnected state by default', () => {
    render(<ConnectionIndicator />)
    expect(screen.getByTestId('connection-label')).toHaveTextContent('Disconnected')
    expect(screen.getByTestId('connection-dot')).toHaveClass('bg-red-500')
  })

  it('shows connected state when store is connected', () => {
    usePipelineStore.getState().setConnected(true)
    render(<ConnectionIndicator />)
    expect(screen.getByTestId('connection-label')).toHaveTextContent('Connected')
    expect(screen.getByTestId('connection-dot')).toHaveClass('bg-emerald-500')
  })

  it('shows pulse animation when disconnected', () => {
    render(<ConnectionIndicator />)
    expect(screen.getByTestId('connection-dot')).toHaveClass('animate-pulse')
  })

  it('does not pulse when connected', () => {
    usePipelineStore.getState().setConnected(true)
    render(<ConnectionIndicator />)
    expect(screen.getByTestId('connection-dot')).not.toHaveClass('animate-pulse')
  })
})
