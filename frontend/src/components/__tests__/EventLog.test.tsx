import { render, screen } from '@testing-library/react'
import { describe, it, expect, beforeEach } from 'vitest'
import { EventLog } from '../EventLog'
import { usePipelineStore } from '../../stores/pipeline-store'

describe('EventLog', () => {
  beforeEach(() => {
    usePipelineStore.getState().reset()
  })

  it('shows empty message when no events', () => {
    render(<EventLog />)
    expect(screen.getByTestId('event-log-empty')).toHaveTextContent('No events yet')
  })

  it('renders events after pushEvent', () => {
    usePipelineStore.getState().pushEvent('pipeline.stage.enter', 'intake', 'tp-1')
    render(<EventLog />)
    const entries = screen.getAllByTestId('event-entry')
    expect(entries).toHaveLength(1)
    expect(entries[0]).toHaveTextContent('ENTER')
    expect(entries[0]).toHaveTextContent('intake')
  })

  it('shows gate fail with red styling', () => {
    usePipelineStore.getState().pushEvent('pipeline.gate.fail', 'verify')
    render(<EventLog />)
    const entry = screen.getByTestId('event-entry')
    expect(entry).toHaveTextContent('FAIL')
  })

  it('limits to 20 events', () => {
    const store = usePipelineStore.getState()
    for (let i = 0; i < 25; i++) {
      store.pushEvent(`pipeline.stage.enter`, 'intake', `tp-${i}`)
    }
    render(<EventLog />)
    const entries = screen.getAllByTestId('event-entry')
    expect(entries).toHaveLength(20)
  })
})
