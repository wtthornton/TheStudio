/** Hook that fetches tasks and stage metrics on mount to populate store before SSE events. */

import { useEffect } from 'react'
import { usePipelineStore } from '../stores/pipeline-store'
import { fetchTasks, fetchStageMetrics } from '../lib/api'
import type { StageId } from '../lib/constants'
import { PIPELINE_STAGES } from '../lib/constants'

const VALID_STAGES = new Set<string>(PIPELINE_STAGES.map((s) => s.id))

export function useInitialLoad(): void {
  const { stageEnter, setStageMetrics, setTasksLoading, setMetricsLoading } = usePipelineStore()

  useEffect(() => {
    let cancelled = false

    // Fetch tasks to populate active stage counts
    async function loadTasks() {
      setTasksLoading(true)
      try {
        const { items } = await fetchTasks({ limit: 100, status: 'IN_PROGRESS' })
        if (cancelled) return
        for (const task of items) {
          if (task.stage_timings) {
            // Find the last stage with a start but no end — that's the active stage
            const activeStage = Object.entries(task.stage_timings)
              .filter(([, timing]) => timing.start && !timing.end)
              .map(([stage]) => stage)
              .pop()
            if (activeStage && VALID_STAGES.has(activeStage)) {
              stageEnter(activeStage as StageId, task.id)
            }
          }
        }
      } catch {
        // Silently fail — SSE will populate state
      } finally {
        if (!cancelled) setTasksLoading(false)
      }
    }

    // Fetch stage metrics
    async function loadMetrics() {
      setMetricsLoading(true)
      try {
        const response = await fetchStageMetrics(24)
        if (cancelled) return
        const metrics: Record<string, { passRate: number | null; avgDuration: number | null; throughput: number }> = {}
        for (const m of response.stages) {
          metrics[m.stage] = {
            passRate: m.pass_rate,
            avgDuration: m.avg_duration_seconds,
            throughput: m.throughput,
          }
        }
        setStageMetrics(metrics)
      } catch {
        // Silently fail — metrics are optional
      } finally {
        if (!cancelled) setMetricsLoading(false)
      }
    }

    void loadTasks()
    void loadMetrics()

    return () => {
      cancelled = true
    }
  }, [stageEnter, setStageMetrics, setTasksLoading, setMetricsLoading])
}
