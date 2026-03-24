/**
 * CommandPalette — Epic 56.2
 *
 * Global command palette triggered by Ctrl+K / Cmd+K.
 * Provides navigation, actions, and recent commands with keyboard navigation.
 *
 * SG 8.5: Commands with side effects show a confirmation indicator and
 * are NOT executed without explicit Enter on the confirmation step.
 */

import { useState, useEffect, useRef, useCallback, useMemo } from 'react'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface PaletteCommand {
  id: string
  label: string
  category: 'Navigation' | 'Actions' | 'Recent'
  /** Commands with side effects show a warning indicator. */
  hasSideEffect?: boolean
}

export interface CommandPaletteProps {
  isOpen: boolean
  onClose: () => void
  onNavigate: (tab: string) => void
  onAction: (actionId: string) => void
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const RECENT_COMMANDS_KEY = 'thestudio_recent_commands'
const MAX_RECENT = 5

const NAVIGATION_COMMANDS: PaletteCommand[] = [
  { id: 'nav:pipeline', label: 'Pipeline', category: 'Navigation' },
  { id: 'nav:triage', label: 'Triage', category: 'Navigation' },
  { id: 'nav:intent', label: 'Intent Review', category: 'Navigation' },
  { id: 'nav:routing', label: 'Routing', category: 'Navigation' },
  { id: 'nav:board', label: 'Backlog', category: 'Navigation' },
  { id: 'nav:trust', label: 'Trust Tiers', category: 'Navigation' },
  { id: 'nav:budget', label: 'Budget', category: 'Navigation' },
  { id: 'nav:activity', label: 'Activity Log', category: 'Navigation' },
  { id: 'nav:analytics', label: 'Analytics', category: 'Navigation' },
  { id: 'nav:reputation', label: 'Reputation', category: 'Navigation' },
  { id: 'nav:repos', label: 'Repos', category: 'Navigation' },
  { id: 'nav:api', label: 'API', category: 'Navigation' },
]

const ACTION_COMMANDS: PaletteCommand[] = [
  { id: 'action:import', label: 'Import Issues', category: 'Actions', hasSideEffect: true },
  { id: 'action:wizard', label: 'Open Setup Wizard', category: 'Actions', hasSideEffect: true },
  { id: 'action:help', label: 'Open Help', category: 'Actions' },
]

// ---------------------------------------------------------------------------
// Recent-commands helpers
// ---------------------------------------------------------------------------

function loadRecentCommands(): PaletteCommand[] {
  try {
    const raw = localStorage.getItem(RECENT_COMMANDS_KEY)
    if (raw) {
      const parsed = JSON.parse(raw) as PaletteCommand[]
      if (Array.isArray(parsed)) return parsed.slice(0, MAX_RECENT)
    }
  } catch {
    /* ignore corrupt data */
  }
  return []
}

function persistRecentCommand(cmd: PaletteCommand): void {
  const existing = loadRecentCommands()
  // Remove duplicates, prepend, trim
  const updated = [
    { ...cmd, category: 'Recent' as const },
    ...existing.filter((c) => c.id !== cmd.id),
  ].slice(0, MAX_RECENT)
  localStorage.setItem(RECENT_COMMANDS_KEY, JSON.stringify(updated))
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function CommandPalette({ isOpen, onClose, onNavigate, onAction }: CommandPaletteProps) {
  const [query, setQuery] = useState('')
  const [selectedIndex, setSelectedIndex] = useState(0)
  const [confirmingIndex, setConfirmingIndex] = useState<number | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const recentCommands = useMemo(() => loadRecentCommands(), [])

  // Build the filtered command list
  const allCommands = useMemo(() => {
    const combined = [...NAVIGATION_COMMANDS, ...ACTION_COMMANDS]
    // Add recent items that aren't duplicates
    for (const recent of recentCommands) {
      if (!combined.some((c) => c.id === recent.id)) {
        combined.push(recent)
      }
    }
    return combined
  }, [recentCommands])

  const filtered = useMemo(() => {
    if (!query.trim()) {
      // Group: Recent first, then Navigation, then Actions
      const recent = recentCommands.map((r) => ({ ...r, category: 'Recent' as const }))
      return [...recent, ...NAVIGATION_COMMANDS, ...ACTION_COMMANDS]
    }
    const q = query.toLowerCase()
    return allCommands.filter(
      (cmd) =>
        cmd.label.toLowerCase().includes(q) ||
        cmd.id.toLowerCase().includes(q) ||
        cmd.category.toLowerCase().includes(q),
    )
  }, [query, allCommands, recentCommands])

  // Reset state when palette opens/closes
  useEffect(() => {
    if (isOpen) {
      setQuery('')
      setSelectedIndex(0)
      setConfirmingIndex(null)
      // Focus the input after a tick so the DOM has rendered
      requestAnimationFrame(() => inputRef.current?.focus())
    }
  }, [isOpen])

  // Keep selectedIndex in bounds
  useEffect(() => {
    if (selectedIndex >= filtered.length) {
      setSelectedIndex(Math.max(0, filtered.length - 1))
    }
  }, [filtered.length, selectedIndex])

  const executeCommand = useCallback(
    (cmd: PaletteCommand) => {
      persistRecentCommand(cmd)

      if (cmd.id.startsWith('nav:')) {
        const tab = cmd.id.replace('nav:', '')
        onNavigate(tab)
      } else {
        onAction(cmd.id)
      }
      onClose()
    },
    [onNavigate, onAction, onClose],
  )

  const handleSelect = useCallback(
    (idx: number) => {
      const cmd = filtered[idx]
      if (!cmd) return

      // SG 8.5: side-effect commands require confirmation
      if (cmd.hasSideEffect && confirmingIndex !== idx) {
        setConfirmingIndex(idx)
        return
      }

      executeCommand(cmd)
    },
    [filtered, confirmingIndex, executeCommand],
  )

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault()
        onClose()
        return
      }
      if (e.key === 'ArrowDown') {
        e.preventDefault()
        setSelectedIndex((prev) => Math.min(prev + 1, filtered.length - 1))
        setConfirmingIndex(null)
        return
      }
      if (e.key === 'ArrowUp') {
        e.preventDefault()
        setSelectedIndex((prev) => Math.max(prev - 1, 0))
        setConfirmingIndex(null)
        return
      }
      if (e.key === 'Enter') {
        e.preventDefault()
        handleSelect(selectedIndex)
      }
    },
    [onClose, filtered.length, selectedIndex, handleSelect],
  )

  if (!isOpen) return null

  // Group filtered commands by category for display
  const groups: Record<string, PaletteCommand[]> = {}
  for (const cmd of filtered) {
    const cat = cmd.category
    if (!groups[cat]) groups[cat] = []
    groups[cat].push(cmd)
  }

  // Maintain flat index mapping for keyboard navigation
  let flatIdx = 0

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center pt-[15vh]"
      data-testid="command-palette-overlay"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose()
      }}
      role="presentation"
    >
      {/* Backdrop */}
      <div className="fixed inset-0 bg-black/60 backdrop-blur-sm" aria-hidden="true" />

      {/* Palette */}
      <div
        className="relative z-10 w-full max-w-lg rounded-lg border border-gray-700 bg-gray-900 shadow-2xl"
        role="dialog"
        aria-modal="true"
        aria-label="Command Palette"
        data-testid="command-palette"
        onKeyDown={handleKeyDown}
      >
        {/* Search input */}
        <div className="border-b border-gray-800 px-4 py-3">
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value)
              setSelectedIndex(0)
              setConfirmingIndex(null)
            }}
            placeholder="Type a command..."
            className="w-full bg-transparent text-sm text-gray-100 placeholder:text-gray-500 focus:outline-none"
            data-testid="command-palette-input"
            aria-label="Search commands"
          />
        </div>

        {/* Command list */}
        <ul
          className="max-h-72 overflow-y-auto py-2"
          role="listbox"
          data-testid="command-list"
        >
          {filtered.length === 0 && (
            <li className="px-4 py-3 text-sm text-gray-500" role="option" aria-selected={false}>
              No matching commands
            </li>
          )}

          {Object.entries(groups).map(([category, commands]) => (
            <li key={category} role="group" aria-label={category}>
              <div className="px-4 pb-1 pt-2 text-xs font-semibold uppercase tracking-wider text-gray-500">
                {category}
              </div>
              <ul role="group">
                {commands.map((cmd) => {
                  const thisIdx = flatIdx++
                  const isSelected = thisIdx === selectedIndex
                  const isConfirming = confirmingIndex === thisIdx

                  return (
                    <li
                      key={cmd.id}
                      role="option"
                      aria-selected={isSelected}
                      className={`flex cursor-pointer items-center justify-between px-4 py-2 text-sm ${
                        isSelected
                          ? 'bg-indigo-900/50 text-gray-100'
                          : 'text-gray-300 hover:bg-gray-800'
                      }`}
                      onClick={() => handleSelect(thisIdx)}
                      data-testid={`command-item-${cmd.id}`}
                    >
                      <span>
                        {cmd.hasSideEffect && (
                          <span className="mr-1.5 text-amber-400" aria-label="Has side effect">
                            &#9888;
                          </span>
                        )}
                        {isConfirming ? `Confirm: ${cmd.label}?` : cmd.label}
                      </span>
                      {isSelected && (
                        <kbd className="ml-2 rounded border border-gray-700 bg-gray-800 px-1.5 py-0.5 text-xs text-gray-500">
                          Enter
                        </kbd>
                      )}
                    </li>
                  )
                })}
              </ul>
            </li>
          ))}
        </ul>

        {/* Footer hint */}
        <div className="flex items-center gap-3 border-t border-gray-800 px-4 py-2 text-xs text-gray-500">
          <span>
            <kbd className="rounded border border-gray-700 bg-gray-800 px-1 py-0.5">↑↓</kbd> navigate
          </span>
          <span>
            <kbd className="rounded border border-gray-700 bg-gray-800 px-1 py-0.5">Enter</kbd> select
          </span>
          <span>
            <kbd className="rounded border border-gray-700 bg-gray-800 px-1 py-0.5">Esc</kbd> close
          </span>
        </div>
      </div>
    </div>
  )
}
