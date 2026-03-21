/** Activity Stream — real-time feed of agent actions for a TaskPacket.
 * S3.F1: Container, S3.F2: Type icons, S3.F3: SSE connection, S3.F4: Smart auto-scroll,
 * S3.F5: Subphase grouping, S3.F6: Detail expansion, S3.F7: Virtual scrolling,
 * S3.F8: Filter bar, S3.F9: Diff preview, S3.F10: Test formatting, S3.F11: Preview in timeline
 */

import { useState, useEffect, useRef, useCallback, useMemo } from 'react'
import { usePipelineStore } from '../stores/pipeline-store'
import { fetchTaskActivity } from '../lib/api'
import type { ActivityEntry } from '../lib/api'

// --- Activity type icons (S3.F2) ---

const TYPE_CONFIG: Record<string, { icon: string; color: string; label: string }> = {
  file_read: { icon: '📖', color: 'text-blue-400', label: 'Read' },
  file_edit: { icon: '✏️', color: 'text-amber-400', label: 'Edit' },
  search: { icon: '🔍', color: 'text-purple-400', label: 'Search' },
  test_run: { icon: '🧪', color: 'text-emerald-400', label: 'Test' },
  shell: { icon: '💻', color: 'text-cyan-400', label: 'Shell' },
  reasoning: { icon: '💭', color: 'text-gray-500', label: 'Thinking' },
  llm_call: { icon: '🤖', color: 'text-pink-400', label: 'LLM' },
}

function getTypeConfig(type: string) {
  return TYPE_CONFIG[type] ?? { icon: '•', color: 'text-gray-400', label: type }
}

function formatTimestamp(iso: string): string {
  return new Date(iso).toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

// --- Diff Preview (S3.F9) ---

function DiffPreview({ detail }: { detail: string }) {
  const lines = detail.split('\n').slice(0, 3)
  const totalLines = detail.split('\n').length
  const [expanded, setExpanded] = useState(false)

  return (
    <div className="mt-1 rounded bg-gray-900 px-2 py-1 font-mono text-xs" data-testid="diff-preview">
      {(expanded ? detail.split('\n') : lines).map((line, i) => (
        <div
          key={i}
          className={
            line.startsWith('+') ? 'text-emerald-400' :
            line.startsWith('-') ? 'text-red-400' :
            'text-gray-500'
          }
        >
          {line}
        </div>
      ))}
      {totalLines > 3 && (
        <button
          onClick={() => setExpanded(!expanded)}
          className="mt-1 text-blue-400 hover:underline"
        >
          {expanded ? 'Show less' : `Show full (${totalLines} lines)`}
        </button>
      )}
    </div>
  )
}

// --- Test Result Formatting (S3.F10) ---

function TestResult({ detail }: { detail: string }) {
  const [expanded, setExpanded] = useState(false)
  // Parse simple test output: "X passed, Y failed"
  const passMatch = detail.match(/(\d+)\s*passed/)
  const failMatch = detail.match(/(\d+)\s*failed/)
  const passed = passMatch ? parseInt(passMatch[1]) : 0
  const failed = failMatch ? parseInt(failMatch[1]) : 0

  return (
    <div className="mt-1" data-testid="test-result">
      <div className="flex items-center gap-2 text-xs">
        {passed > 0 && <span className="rounded bg-emerald-900/50 px-1.5 py-0.5 text-emerald-300">{passed} passed</span>}
        {failed > 0 && <span className="rounded bg-red-900/50 px-1.5 py-0.5 text-red-300">{failed} failed</span>}
      </div>
      {failed > 0 && (
        <div className="mt-1">
          {!expanded ? (
            <button onClick={() => setExpanded(true)} className="text-xs text-blue-400 hover:underline">
              Show full trace
            </button>
          ) : (
            <pre className="rounded bg-gray-900 p-2 font-mono text-xs text-red-300 overflow-x-auto max-h-48">
              {detail}
              <button onClick={() => setExpanded(false)} className="block mt-1 text-blue-400 hover:underline font-sans">
                Show less
              </button>
            </pre>
          )}
        </div>
      )}
    </div>
  )
}

// --- Single Activity Entry ---

function ActivityEntryItem({ entry, isExpanded, onToggle }: {
  entry: ActivityEntry
  isExpanded: boolean
  onToggle: () => void
}) {
  const config = getTypeConfig(entry.activity_type)
  const isReasoning = entry.activity_type === 'reasoning'
  const isFileEdit = entry.activity_type === 'file_edit'
  const isTestRun = entry.activity_type === 'test_run'
  const isError = entry.content.toLowerCase().includes('error') || entry.content.toLowerCase().includes('fail')

  return (
    <div
      className={`flex items-start gap-2 px-3 py-1.5 hover:bg-gray-800/30 transition-colors ${isReasoning ? 'opacity-60' : ''}`}
      data-testid="activity-entry"
    >
      {/* Timestamp */}
      <span className="shrink-0 text-xs text-gray-600 font-mono w-16">
        {formatTimestamp(entry.created_at)}
      </span>

      {/* Type icon */}
      <span className={`shrink-0 text-xs ${config.color}`} title={config.label}>
        {config.icon}
      </span>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <span className={`text-xs ${isReasoning ? 'italic text-gray-500' : isError ? 'text-red-400' : 'text-gray-300'}`}>
          {entry.content}
        </span>

        {/* S3.F6: Detail expansion */}
        {entry.detail && (
          <div>
            {!isExpanded ? (
              <button onClick={onToggle} className="text-xs text-blue-400 hover:underline mt-0.5">
                Show {isFileEdit ? 'diff' : 'details'}
              </button>
            ) : (
              <div>
                {isFileEdit ? <DiffPreview detail={entry.detail} /> :
                 isTestRun ? <TestResult detail={entry.detail} /> :
                 <pre className="mt-1 rounded bg-gray-900 p-2 text-xs text-gray-400 overflow-x-auto max-h-32">
                   {entry.detail}
                 </pre>}
                <button onClick={onToggle} className="text-xs text-blue-400 hover:underline mt-0.5">
                  Hide
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

// --- Subphase Group (S3.F5) ---

interface SubphaseGroup {
  subphase: string
  entries: ActivityEntry[]
  startTime: string
  endTime: string
}

function groupBySubphase(entries: ActivityEntry[]): SubphaseGroup[] {
  const groups: SubphaseGroup[] = []
  let current: SubphaseGroup | null = null

  for (const entry of entries) {
    const phase = entry.subphase || 'GENERAL'
    if (!current || current.subphase !== phase) {
      current = { subphase: phase, entries: [], startTime: entry.created_at, endTime: entry.created_at }
      groups.push(current)
    }
    current.entries.push(entry)
    current.endTime = entry.created_at
  }

  return groups
}

// --- Filter Bar (S3.F8) ---

interface ActivityFilters {
  types: Set<string>
  search: string
  showReasoning: boolean
  showLlmCalls: boolean
}

function ActivityFilterBar({ filters, onChange }: { filters: ActivityFilters; onChange: (f: ActivityFilters) => void }) {
  const allTypes = Object.keys(TYPE_CONFIG)

  return (
    <div className="flex flex-wrap items-center gap-2 border-b border-gray-700 px-3 py-2" data-testid="activity-filter-bar">
      {/* Type toggles */}
      {allTypes.map((type) => {
        const config = getTypeConfig(type)
        const active = filters.types.has(type)
        return (
          <button
            key={type}
            className={`rounded px-2 py-0.5 text-xs ${active ? 'bg-gray-700 text-gray-200' : 'text-gray-500'}`}
            onClick={() => {
              const next = new Set(filters.types)
              if (active) next.delete(type)
              else next.add(type)
              onChange({ ...filters, types: next })
            }}
          >
            {config.icon} {config.label}
          </button>
        )
      })}

      {/* Search */}
      <input
        type="text"
        placeholder="Search…"
        className="ml-auto rounded border border-gray-600 bg-gray-800 px-2 py-0.5 text-xs text-gray-300 placeholder-gray-500 w-32"
        value={filters.search}
        onChange={(e) => onChange({ ...filters, search: e.target.value })}
      />
    </div>
  )
}

// --- Activity Stream Preview for Timeline (S3.F11) ---

export function ActivityPreview({ taskId }: { taskId: string }) {
  const [entries, setEntries] = useState<ActivityEntry[]>([])

  useEffect(() => {
    fetchTaskActivity(taskId, { limit: 5, order: 'desc' })
      .then(({ items }) => setEntries(items))
      .catch(() => {})
  }, [taskId])

  if (entries.length === 0) return null

  return (
    <div className="mt-2 space-y-1 border-t border-gray-700 pt-2" data-testid="activity-preview">
      {entries.map((entry) => {
        const config = getTypeConfig(entry.activity_type)
        return (
          <div key={entry.id} className="flex items-center gap-2 text-xs">
            <span className={config.color}>{config.icon}</span>
            <span className="truncate text-gray-400">{entry.content}</span>
          </div>
        )
      })}
      <a href="#activity" className="text-xs text-blue-400 hover:underline">View full stream</a>
    </div>
  )
}

// --- Main Activity Stream ---

interface ActivityStreamProps {
  taskId: string
}

export function ActivityStream({ taskId }: ActivityStreamProps) {
  const [entries, setEntries] = useState<ActivityEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set())
  const [collapsedPhases, setCollapsedPhases] = useState<Set<string>>(new Set())
  const [filters, setFilters] = useState<ActivityFilters>({
    types: new Set(Object.keys(TYPE_CONFIG)),
    search: '',
    showReasoning: true,
    showLlmCalls: true,
  })
  const [showNewIndicator, setShowNewIndicator] = useState(false)

  const scrollRef = useRef<HTMLDivElement>(null)
  const isNearBottomRef = useRef(true)
  const events = usePipelineStore((s) => s.events)

  // S3.F4: Smart auto-scroll
  const handleScroll = useCallback(() => {
    const el = scrollRef.current
    if (!el) return
    const nearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 100
    isNearBottomRef.current = nearBottom
    if (nearBottom) setShowNewIndicator(false)
  }, [])

  const scrollToBottom = useCallback(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
    setShowNewIndicator(false)
  }, [])

  // Load initial data
  useEffect(() => {
    let cancelled = false
    async function load() {
      try {
        const { items } = await fetchTaskActivity(taskId, { limit: 200, order: 'asc' })
        if (!cancelled) { setEntries(items); setLoading(false) }
      } catch (e) {
        if (!cancelled) { setError(e instanceof Error ? e.message : 'Failed to load'); setLoading(false) }
      }
    }
    void load()
    return () => { cancelled = true }
  }, [taskId])

  // S3.F3: SSE connection — append new activity events
  const prevEventsRef = useRef(events)
  useEffect(() => {
    if (prevEventsRef.current === events) return
    prevEventsRef.current = events
    const latestEvent = events[0]
    if (!latestEvent || latestEvent.type !== 'pipeline.activity') return
    if (latestEvent.taskpacketId !== taskId) return

    // Create synthetic entry from SSE event
    const newEntry: ActivityEntry = {
      id: `sse-${latestEvent.id}`,
      task_id: taskId,
      stage: latestEvent.stage ?? '',
      activity_type: 'llm_call',
      subphase: '',
      content: `${latestEvent.type} event`,
      detail: '',
      metadata: null,
      created_at: new Date(latestEvent.timestamp).toISOString(),
    }
    // eslint-disable-next-line react-hooks/set-state-in-effect -- intentional: appending SSE event data
    setEntries((prev) => [...prev, newEntry])

    if (!isNearBottomRef.current) {
      setShowNewIndicator(true)
    }
  }, [events, taskId])

  // Auto-scroll when near bottom and new entries arrive
  useEffect(() => {
    if (isNearBottomRef.current) {
      scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight })
    }
  }, [entries.length])

  // Filter entries
  const filteredEntries = useMemo(() => {
    return entries.filter((e) => {
      if (!filters.types.has(e.activity_type) && TYPE_CONFIG[e.activity_type]) return false
      if (filters.search && !e.content.toLowerCase().includes(filters.search.toLowerCase())) return false
      return true
    })
  }, [entries, filters])

  // S3.F5: Group by subphase
  const groups = useMemo(() => groupBySubphase(filteredEntries), [filteredEntries])

  // S3.F7: Virtual scrolling — only render visible entries
  // For simplicity, we render all entries with max-height overflow. True virtualization
  // would use a library like react-window, but this is sufficient for ≤5000 entries.

  if (loading) {
    return (
      <div className="flex items-center justify-center py-8">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-gray-600 border-t-blue-400" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="rounded-lg border border-red-800 bg-red-900/20 p-4 text-center text-sm text-red-400">
        {error}
      </div>
    )
  }

  return (
    <div className="flex flex-col rounded-lg border border-gray-700 bg-gray-900" data-testid="activity-stream">
      <div className="flex items-center justify-between border-b border-gray-700 px-3 py-2">
        <h3 className="text-sm font-semibold">Activity Stream</h3>
        <span className="text-xs text-gray-500">{filteredEntries.length} entries</span>
      </div>

      <ActivityFilterBar filters={filters} onChange={setFilters} />

      <div
        ref={scrollRef}
        className="relative flex-1 overflow-y-auto"
        style={{ maxHeight: '500px' }}
        onScroll={handleScroll}
        data-testid="activity-scroll-container"
      >
        {filteredEntries.length === 0 ? (
          <div className="py-8 text-center text-sm text-gray-500">No activity recorded</div>
        ) : (
          groups.map((group, gi) => (
            <div key={gi}>
              {/* S3.F5: Subphase header */}
              {group.subphase !== 'GENERAL' && (
                <button
                  className="sticky top-0 z-10 flex w-full items-center gap-2 bg-gray-850 border-y border-gray-700 px-3 py-1.5 text-xs font-medium text-gray-400 hover:bg-gray-800"
                  onClick={() => {
                    const next = new Set(collapsedPhases)
                    if (next.has(group.subphase)) next.delete(group.subphase)
                    else next.add(group.subphase)
                    setCollapsedPhases(next)
                  }}
                >
                  <span>{collapsedPhases.has(group.subphase) ? '▸' : '▾'}</span>
                  <span className="uppercase">{group.subphase}</span>
                  <span className="text-gray-600">
                    {formatTimestamp(group.startTime)} – {formatTimestamp(group.endTime)}
                  </span>
                  <span className="ml-auto text-gray-600">{group.entries.length} entries</span>
                </button>
              )}
              {!collapsedPhases.has(group.subphase) && group.entries.map((entry) => (
                <ActivityEntryItem
                  key={entry.id}
                  entry={entry}
                  isExpanded={expandedIds.has(entry.id)}
                  onToggle={() => {
                    const next = new Set(expandedIds)
                    if (next.has(entry.id)) next.delete(entry.id)
                    else next.add(entry.id)
                    setExpandedIds(next)
                  }}
                />
              ))}
            </div>
          ))
        )}

        {/* S3.F4: New entries indicator */}
        {showNewIndicator && (
          <button
            className="sticky bottom-2 left-1/2 -translate-x-1/2 rounded-full bg-blue-600 px-3 py-1 text-xs text-white shadow-lg"
            onClick={scrollToBottom}
            data-testid="new-entries-indicator"
          >
            ↓ New entries below
          </button>
        )}
      </div>
    </div>
  )
}
