/** Minimap bottom bar — persistent horizontal cards showing active TaskPackets.
 * S4.F6: Card rendering, S4.F7: Click-to-navigate, S4.F8: Horizontal scroll,
 * S4.F9: Collapse/expand toggle
 */

import { useState, useRef, useCallback, useEffect } from 'react'
import { usePipelineStore } from '../stores/pipeline-store'
import { PIPELINE_STAGES, STATUS_COLORS } from '../lib/constants'
import type { StageId } from '../lib/constants'

interface MinimapCard {
  taskId: string
  stage: StageId
  status: string
  progress: number
}

function getActiveCards(stages: Record<StageId, { activeTasks: string[]; status: string }>): MinimapCard[] {
  const cards: MinimapCard[] = []
  for (const s of PIPELINE_STAGES) {
    const state = stages[s.id]
    for (const taskId of state.activeTasks) {
      cards.push({
        taskId,
        stage: s.id,
        status: state.status,
        progress: (PIPELINE_STAGES.findIndex((p) => p.id === s.id) + 1) / 9 * 100,
      })
    }
  }
  return cards
}

interface MinimapProps {
  activeTaskId?: string
  onTaskClick: (taskId: string) => void
}

export function Minimap({ activeTaskId, onTaskClick }: MinimapProps) {
  const stages = usePipelineStore((s) => s.stages)
  const totalCost = usePipelineStore((s) => s.totalCost)
  const scrollRef = useRef<HTMLDivElement>(null)
  const [isDragging, setIsDragging] = useState(false)
  const dragStartRef = useRef({ x: 0, scrollLeft: 0 })

  // S4.F9: Collapse/expand from localStorage
  const [collapsed, setCollapsed] = useState(() => {
    try { return localStorage.getItem('minimap-collapsed') === 'true' } catch { return false }
  })

  const toggleCollapse = useCallback(() => {
    setCollapsed((prev) => {
      const next = !prev
      try { localStorage.setItem('minimap-collapsed', String(next)) } catch { /* localStorage unavailable */ }
      return next
    })
  }, [])

  const cards = getActiveCards(stages)

  // S4.F8: Mouse wheel horizontal scroll
  useEffect(() => {
    const el = scrollRef.current
    if (!el) return
    function onWheel(e: WheelEvent) {
      if (Math.abs(e.deltaY) > Math.abs(e.deltaX)) {
        e.preventDefault()
        el!.scrollLeft += e.deltaY
      }
    }
    el.addEventListener('wheel', onWheel, { passive: false })
    return () => el.removeEventListener('wheel', onWheel)
  }, [collapsed])

  // S4.F8: Drag to scroll
  const onMouseDown = useCallback((e: React.MouseEvent) => {
    setIsDragging(true)
    dragStartRef.current = { x: e.clientX, scrollLeft: scrollRef.current?.scrollLeft ?? 0 }
  }, [])

  const onMouseMove = useCallback((e: React.MouseEvent) => {
    if (!isDragging || !scrollRef.current) return
    const dx = e.clientX - dragStartRef.current.x
    scrollRef.current.scrollLeft = dragStartRef.current.scrollLeft - dx
  }, [isDragging])

  const onMouseUp = useCallback(() => setIsDragging(false), [])

  return (
    <div
      className="fixed bottom-0 left-0 right-0 z-40 border-t border-gray-700 bg-gray-900"
      data-testid="minimap"
    >
      {/* Header with collapse toggle */}
      <div className="flex items-center justify-between px-4 py-1">
        <button
          onClick={toggleCollapse}
          className="text-xs text-gray-400 hover:text-gray-200"
          data-testid="minimap-toggle"
        >
          {collapsed ? '▴' : '▾'} {cards.length} tasks
        </button>
        {!collapsed && (
          <span className="text-xs text-gray-500">
            ${totalCost.toFixed(2)} total
          </span>
        )}
      </div>

      {/* Card strip */}
      {!collapsed && (
        <div
          ref={scrollRef}
          className="flex gap-2 overflow-x-auto px-4 pb-3 scrollbar-thin scrollbar-track-gray-800 scrollbar-thumb-gray-600 cursor-grab select-none"
          onMouseDown={onMouseDown}
          onMouseMove={onMouseMove}
          onMouseUp={onMouseUp}
          onMouseLeave={onMouseUp}
          style={{ cursor: isDragging ? 'grabbing' : 'grab' }}
          data-testid="minimap-cards"
        >
          {cards.length === 0 ? (
            <div className="py-3 text-xs text-gray-500">No active tasks</div>
          ) : (
            cards.map((card) => {
              const stageConfig = PIPELINE_STAGES.find((s) => s.id === card.stage)
              const isActive = card.taskId === activeTaskId
              const statusColor = STATUS_COLORS[card.status as keyof typeof STATUS_COLORS] ?? STATUS_COLORS.idle

              return (
                <button
                  key={card.taskId}
                  onClick={() => onTaskClick(card.taskId)}
                  className={`shrink-0 rounded-lg border px-3 py-2 text-left transition-colors ${
                    isActive
                      ? 'border-blue-500 bg-blue-900/30'
                      : 'border-gray-700 bg-gray-800 hover:border-gray-600'
                  }`}
                  style={{ minWidth: '180px' }}
                  data-testid="minimap-card"
                >
                  <div className="flex items-center gap-2">
                    {/* Status dot */}
                    <div
                      className="h-2 w-2 rounded-full"
                      style={{ backgroundColor: statusColor }}
                    />
                    {/* Task ID */}
                    <span className="text-xs font-mono text-gray-300 truncate" style={{ maxWidth: '90px' }}>
                      {card.taskId.slice(0, 8)}…
                    </span>
                  </div>
                  <div className="mt-1 flex items-center gap-2 text-xs text-gray-400">
                    <span style={{ color: stageConfig?.color }}>{stageConfig?.label}</span>
                    <span>{Math.round(card.progress)}%</span>
                  </div>
                  {/* Mini progress bar */}
                  <div className="mt-1 h-0.5 w-full rounded-full bg-gray-700">
                    <div
                      className="h-0.5 rounded-full transition-all"
                      style={{ width: `${card.progress}%`, backgroundColor: stageConfig?.color }}
                    />
                  </div>
                </button>
              )
            })
          )}
        </div>
      )}
    </div>
  )
}
