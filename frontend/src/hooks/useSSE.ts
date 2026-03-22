/** Hook that connects to the pipeline SSE endpoint and dispatches to the store. */

import { useEffect, useRef } from 'react'
import { usePipelineStore } from '../stores/pipeline-store'
import { useTriageStore } from '../stores/triage-store'
import { useSteeringStore } from '../stores/steering-store'
import type { StageId } from '../lib/constants'
import { PIPELINE_STAGES } from '../lib/constants'

const SSE_URL = '/api/v1/dashboard/events/stream'
const VALID_STAGES = new Set<string>(PIPELINE_STAGES.map((s) => s.id))

function isStageId(value: string): value is StageId {
  return VALID_STAGES.has(value)
}

interface SSEEventData {
  type?: string
  data?: {
    stage?: string
    taskpacket_id?: string
    task_id?: string
    success?: boolean
    cost_delta?: number
    total_cost?: number
    model?: string
    from_stage?: string
    to_stage?: string
    reason?: string
    attempt?: number
    max_attempts?: number
    outcome?: string
    activity_type?: string
    content?: string
    subphase?: string
    detail?: string
    action?: string
    new_status?: string
  }
}

export function useSSE(): void {
  const esRef = useRef<EventSource | null>(null)
  const { stageEnter, stageExit, gateResult, costUpdate, setLastEventId, setConnected, pushEvent, reset } =
    usePipelineStore()
  const setSteeringStatus = useSteeringStore((s) => s.setSteeringStatus)

  useEffect(() => {
    const lastId = usePipelineStore.getState().lastEventId
    const url = lastId != null ? `${SSE_URL}?lastEventId=${lastId}` : SSE_URL
    const es = new EventSource(url)
    esRef.current = es

    es.onopen = () => {
      setConnected(true)
    }

    es.onerror = () => {
      setConnected(false)
    }

    es.onmessage = (event: MessageEvent) => {
      // Update last event ID for reconnection
      if (event.lastEventId) {
        const id = parseInt(event.lastEventId, 10)
        if (!Number.isNaN(id)) {
          setLastEventId(id)
        }
      }

      let parsed: SSEEventData
      try {
        parsed = JSON.parse(event.data as string) as SSEEventData
      } catch {
        return // ignore unparseable messages (heartbeats, etc.)
      }

      const eventType = parsed.type
      const data = parsed.data
      if (!eventType || !data) return

      const stage = data.stage
      const taskId = data.taskpacket_id ?? ''

      // Log every parsed event for the EventLog component
      pushEvent(eventType, stage ?? undefined, taskId || undefined)

      if (eventType === 'pipeline.stage.enter' && stage && isStageId(stage)) {
        stageEnter(stage, taskId)
      } else if (eventType === 'pipeline.stage.exit' && stage && isStageId(stage)) {
        stageExit(stage, taskId, data.success !== false)
      } else if (eventType === 'pipeline.gate.pass' && stage && isStageId(stage)) {
        gateResult(stage, true)
      } else if (eventType === 'pipeline.gate.fail' && stage && isStageId(stage)) {
        gateResult(stage, false)
      } else if (eventType === 'pipeline.cost_update' && data.task_id != null) {
        costUpdate(data.task_id, data.cost_delta ?? 0, data.total_cost ?? 0)
      } else if (eventType === 'system.full_state') {
        reset()
      } else if (eventType === 'pipeline.triage.created' && data.task_id) {
        // Reload triage queue when a new task enters triage
        void useTriageStore.getState().loadTasks()
      } else if (eventType === 'pipeline.triage.accepted' && data.task_id) {
        useTriageStore.getState().removeTask(data.task_id)
      } else if (eventType === 'pipeline.triage.rejected' && data.task_id) {
        useTriageStore.getState().removeTask(data.task_id)
      } else if (eventType === 'pipeline.steering.action' && data.task_id) {
        // Update steering status for the currently-viewed task
        const action = data.action
        const currentTaskId = useSteeringStore.getState().taskId
        if (currentTaskId === data.task_id) {
          if (action === 'pause') setSteeringStatus('paused')
          else if (action === 'resume') setSteeringStatus('running')
          else if (action === 'abort') setSteeringStatus('aborted')
        }
      }
    }

    return () => {
      es.close()
      esRef.current = null
    }
  }, [stageEnter, stageExit, gateResult, costUpdate, setLastEventId, setConnected, pushEvent, reset, setSteeringStatus])
}
