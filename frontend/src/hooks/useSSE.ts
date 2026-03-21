/** Hook that connects to the pipeline SSE endpoint and dispatches to the store. */

import { useEffect, useRef } from 'react'
import { usePipelineStore } from '../stores/pipeline-store'
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
    success?: boolean
  }
}

export function useSSE(): void {
  const esRef = useRef<EventSource | null>(null)
  const { stageEnter, stageExit, gateResult, setLastEventId, setConnected, reset } =
    usePipelineStore()

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

      if (eventType === 'pipeline.stage.enter' && stage && isStageId(stage)) {
        stageEnter(stage, taskId)
      } else if (eventType === 'pipeline.stage.exit' && stage && isStageId(stage)) {
        stageExit(stage, taskId, data.success !== false)
      } else if (eventType === 'pipeline.gate.pass' && stage && isStageId(stage)) {
        gateResult(stage, true)
      } else if (eventType === 'pipeline.gate.fail' && stage && isStageId(stage)) {
        gateResult(stage, false)
      } else if (eventType === 'system.full_state') {
        reset()
      }
    }

    return () => {
      es.close()
      esRef.current = null
    }
  }, [stageEnter, stageExit, gateResult, setLastEventId, setConnected, reset])
}
