import { describe, it, expect, beforeEach, vi, type Mock } from 'vitest'
import { renderHook } from '@testing-library/react'
import { usePipelineStore } from '../../stores/pipeline-store'
import { useSSE } from '../useSSE'

// Mock EventSource
class MockEventSource {
  static instances: MockEventSource[] = []
  url: string
  onopen: ((ev: Event) => void) | null = null
  onerror: ((ev: Event) => void) | null = null
  onmessage: ((ev: MessageEvent) => void) | null = null
  close: Mock

  constructor(url: string) {
    this.url = url
    this.close = vi.fn()
    MockEventSource.instances.push(this)
  }

  /** Simulate receiving an SSE message. */
  simulateMessage(data: string, lastEventId = '') {
    this.onmessage?.({
      data,
      lastEventId,
    } as MessageEvent)
  }

  simulateOpen() {
    this.onopen?.({} as Event)
  }

  simulateError() {
    this.onerror?.({} as Event)
  }
}

// Install mock globally
vi.stubGlobal('EventSource', MockEventSource)

describe('useSSE', () => {
  beforeEach(() => {
    MockEventSource.instances = []
    usePipelineStore.getState().reset()
    usePipelineStore.setState({ connected: false, lastEventId: null })
  })

  it('creates EventSource on mount', () => {
    renderHook(() => useSSE())
    expect(MockEventSource.instances).toHaveLength(1)
    expect(MockEventSource.instances[0].url).toBe('/api/v1/dashboard/events/stream')
  })

  it('includes lastEventId in URL when set', () => {
    usePipelineStore.setState({ lastEventId: 42 })
    renderHook(() => useSSE())
    expect(MockEventSource.instances[0].url).toContain('lastEventId=42')
  })

  it('sets connected on open', () => {
    renderHook(() => useSSE())
    MockEventSource.instances[0].simulateOpen()
    expect(usePipelineStore.getState().connected).toBe(true)
  })

  it('sets disconnected on error', () => {
    renderHook(() => useSSE())
    MockEventSource.instances[0].simulateOpen()
    MockEventSource.instances[0].simulateError()
    expect(usePipelineStore.getState().connected).toBe(false)
  })

  it('dispatches stage.enter event', () => {
    renderHook(() => useSSE())
    const es = MockEventSource.instances[0]
    es.simulateMessage(JSON.stringify({
      type: 'pipeline.stage.enter',
      data: { stage: 'intake', taskpacket_id: 'tp-1' },
    }), '1')

    const stage = usePipelineStore.getState().stages.intake
    expect(stage.status).toBe('active')
    expect(stage.activeTasks).toContain('tp-1')
  })

  it('dispatches stage.exit event', () => {
    // First enter, then exit
    usePipelineStore.getState().stageEnter('verify', 'tp-2')
    renderHook(() => useSSE())
    const es = MockEventSource.instances[0]
    es.simulateMessage(JSON.stringify({
      type: 'pipeline.stage.exit',
      data: { stage: 'verify', taskpacket_id: 'tp-2', success: true },
    }))

    expect(usePipelineStore.getState().stages.verify.status).toBe('passed')
  })

  it('dispatches gate.pass event', () => {
    renderHook(() => useSSE())
    MockEventSource.instances[0].simulateMessage(JSON.stringify({
      type: 'pipeline.gate.pass',
      data: { stage: 'qa' },
    }))

    expect(usePipelineStore.getState().stages.qa.status).toBe('passed')
  })

  it('dispatches gate.fail event', () => {
    renderHook(() => useSSE())
    MockEventSource.instances[0].simulateMessage(JSON.stringify({
      type: 'pipeline.gate.fail',
      data: { stage: 'verify' },
    }))

    expect(usePipelineStore.getState().stages.verify.status).toBe('failed')
  })

  it('handles system.full_state by resetting', () => {
    usePipelineStore.getState().stageEnter('intake', 'tp-1')
    renderHook(() => useSSE())
    MockEventSource.instances[0].simulateMessage(JSON.stringify({
      type: 'system.full_state',
      data: {},
    }))

    expect(usePipelineStore.getState().stages.intake.status).toBe('idle')
  })

  it('updates lastEventId from SSE message', () => {
    renderHook(() => useSSE())
    MockEventSource.instances[0].simulateMessage(JSON.stringify({
      type: 'pipeline.stage.enter',
      data: { stage: 'intent', taskpacket_id: 'tp-3' },
    }), '55')

    expect(usePipelineStore.getState().lastEventId).toBe(55)
  })

  it('ignores invalid stage IDs', () => {
    renderHook(() => useSSE())
    MockEventSource.instances[0].simulateMessage(JSON.stringify({
      type: 'pipeline.stage.enter',
      data: { stage: 'bogus', taskpacket_id: 'tp-1' },
    }))

    // No stage should change
    const stages = usePipelineStore.getState().stages
    for (const s of Object.values(stages)) {
      expect(s.status).toBe('idle')
    }
  })

  it('ignores unparseable messages', () => {
    renderHook(() => useSSE())
    MockEventSource.instances[0].simulateMessage('not-json')

    // No crash, no state change
    expect(usePipelineStore.getState().stages.intake.status).toBe('idle')
  })

  it('closes EventSource on unmount', () => {
    const { unmount } = renderHook(() => useSSE())
    const es = MockEventSource.instances[0]
    unmount()
    expect(es.close).toHaveBeenCalled()
  })
})
