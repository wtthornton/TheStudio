import { describe, it, expect, beforeEach } from 'vitest'
import { usePipelineStore } from '../pipeline-store'

describe('pipeline-store', () => {
  beforeEach(() => {
    usePipelineStore.getState().reset()
    usePipelineStore.setState({ connected: false, lastEventId: null })
  })

  it('initializes 9 stages as idle', () => {
    const { stages } = usePipelineStore.getState()
    const ids = Object.keys(stages)
    expect(ids).toHaveLength(9)
    for (const id of ids) {
      const stage = stages[id as keyof typeof stages]
      expect(stage.status).toBe('idle')
      expect(stage.taskCount).toBe(0)
      expect(stage.activeTasks).toEqual([])
    }
  })

  it('stageEnter sets active and increments taskCount', () => {
    const { stageEnter } = usePipelineStore.getState()
    stageEnter('intake', 'tp-1')

    const stage = usePipelineStore.getState().stages.intake
    expect(stage.status).toBe('active')
    expect(stage.taskCount).toBe(1)
    expect(stage.activeTasks).toEqual(['tp-1'])
  })

  it('stageEnter does not duplicate task IDs', () => {
    const { stageEnter } = usePipelineStore.getState()
    stageEnter('intake', 'tp-1')
    usePipelineStore.getState().stageEnter('intake', 'tp-1')

    const stage = usePipelineStore.getState().stages.intake
    expect(stage.activeTasks).toEqual(['tp-1'])
  })

  it('stageExit removes task and sets passed when success', () => {
    const { stageEnter } = usePipelineStore.getState()
    stageEnter('verify', 'tp-1')
    usePipelineStore.getState().stageExit('verify', 'tp-1', true)

    const stage = usePipelineStore.getState().stages.verify
    expect(stage.status).toBe('passed')
    expect(stage.activeTasks).toEqual([])
  })

  it('stageExit sets failed when not success', () => {
    const { stageEnter } = usePipelineStore.getState()
    stageEnter('qa', 'tp-1')
    usePipelineStore.getState().stageExit('qa', 'tp-1', false)

    const stage = usePipelineStore.getState().stages.qa
    expect(stage.status).toBe('failed')
  })

  it('stageExit keeps active if other tasks remain', () => {
    const store = usePipelineStore.getState()
    store.stageEnter('intent', 'tp-1')
    usePipelineStore.getState().stageEnter('intent', 'tp-2')
    usePipelineStore.getState().stageExit('intent', 'tp-1', true)

    const stage = usePipelineStore.getState().stages.intent
    expect(stage.status).toBe('active')
    expect(stage.activeTasks).toEqual(['tp-2'])
  })

  it('gateResult sets passed/failed status', () => {
    const { gateResult } = usePipelineStore.getState()
    gateResult('verify', true)
    expect(usePipelineStore.getState().stages.verify.status).toBe('passed')

    usePipelineStore.getState().gateResult('verify', false)
    expect(usePipelineStore.getState().stages.verify.status).toBe('failed')
  })

  it('setLastEventId updates lastEventId', () => {
    usePipelineStore.getState().setLastEventId(42)
    expect(usePipelineStore.getState().lastEventId).toBe(42)
  })

  it('setConnected updates connected flag', () => {
    usePipelineStore.getState().setConnected(true)
    expect(usePipelineStore.getState().connected).toBe(true)
  })

  it('reset restores initial state', () => {
    const store = usePipelineStore.getState()
    store.stageEnter('intake', 'tp-1')
    store.setLastEventId(99)
    usePipelineStore.getState().reset()

    const { stages, lastEventId } = usePipelineStore.getState()
    expect(stages.intake.status).toBe('idle')
    expect(stages.intake.activeTasks).toEqual([])
    expect(lastEventId).toBeNull()
  })
})
