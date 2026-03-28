/**
 * HelpPanel — slide-in contextual help panel.
 * Epic 45.1: slide-in/out animation, close button, Escape key handler.
 * Epic 45.4: route-aware content loaded via react-markdown + ?raw imports.
 * Epic 45.5: Fuse.js full-text search across all articles; click result switches tab.
 */

import { useEffect, useRef, useState, useMemo } from 'react'
import Fuse from 'fuse.js'
import ReactMarkdown from 'react-markdown'
import { HELP_CONTENT, HELP_TITLES } from '../../help/index'

interface SearchArticle {
  key: string
  title: string
  content: string
}

/** Build a flat list of all indexed articles once at module load time. */
const ARTICLES: SearchArticle[] = Object.keys(HELP_CONTENT).map((key) => ({
  key,
  title: HELP_TITLES[key] ?? key,
  content: HELP_CONTENT[key],
}))

const FUSE = new Fuse<SearchArticle>(ARTICLES, {
  keys: [
    { name: 'title', weight: 2 },
    { name: 'content', weight: 1 },
  ],
  threshold: 0.35,
  minMatchCharLength: 2,
  includeScore: true,
})

interface HelpPanelProps {
  /** Whether the panel is currently open. */
  open: boolean
  /** Called when the user closes the panel. */
  onClose: () => void
  /**
   * The active tab key (e.g. 'pipeline', 'triage').
   * When provided, the panel loads the matching help article.
   * When omitted, falls back to `children` or a generic message.
   */
  activeTab?: string
  /** Optional title shown in the panel header (overrides tab-derived title). */
  title?: string
  /** Optional content to render inside the panel (used when activeTab not provided). */
  children?: React.ReactNode
  /**
   * Called when the user clicks a search result that maps to a tab.
   * The caller (App.tsx) should switch to that tab.
   * Epic 45.5
   */
  onSwitchTab?: (tabKey: string) => void
}

export function HelpPanel({
  open,
  onClose,
  activeTab,
  title,
  children,
  onSwitchTab,
}: HelpPanelProps) {
  const panelRef = useRef<HTMLDivElement>(null)
  const searchRef = useRef<HTMLInputElement>(null)

  const [query, setQuery] = useState('')
  /** When the user clicks a search result, show its content in-panel. */
  const [searchTab, setSearchTab] = useState<string | null>(null)

  // Resolved display state: prefer searchTab override, then activeTab prop
  const displayTab = searchTab ?? activeTab
  const tabContent = displayTab ? (HELP_CONTENT[displayTab] ?? null) : null
  const resolvedTitle = title ?? (displayTab ? (HELP_TITLES[displayTab] ?? 'Help') : 'Help')

  // Fuse.js search results (only when query is non-empty)
  const searchResults = useMemo(() => {
    const q = query.trim()
    if (!q) return []
    return FUSE.search(q).slice(0, 6)
  }, [query])

  const isSearching = query.trim().length > 0

  // Reset search state when panel closes
  useEffect(() => {
    if (!open) {
      setQuery('')
      setSearchTab(null)
    }
  }, [open])

  // Close on Escape key; if searching, clear search first
  useEffect(() => {
    if (!open) return
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        if (query) {
          setQuery('')
          setSearchTab(null)
        } else {
          onClose()
        }
      }
    }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [open, onClose, query])

  // Trap focus inside panel when open; autofocus search box
  useEffect(() => {
    if (open) {
      // Small delay so CSS transition doesn't fight focus
      const id = setTimeout(() => searchRef.current?.focus(), 50)
      return () => clearTimeout(id)
    }
  }, [open])

  function handleResultClick(article: SearchArticle) {
    setQuery('')
    setSearchTab(article.key)
    // Also switch the main app tab so the user lands on the right page
    onSwitchTab?.(article.key)
  }

  return (
    <>
      {/* Backdrop overlay */}
      {open && (
        <div
          className="fixed inset-0 z-40 bg-black/40"
          onClick={onClose}
          aria-hidden="true"
          data-testid="help-panel-backdrop"
        />
      )}

      {/* Slide-in panel */}
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-label={resolvedTitle}
        tabIndex={-1}
        data-testid="help-panel"
        className={[
          'fixed right-0 top-0 z-50 flex h-full w-full max-w-md flex-col',
          'bg-gray-900 shadow-2xl',
          'transform transition-transform duration-300 ease-in-out',
          'focus:outline-none',
          open ? 'translate-x-0' : 'translate-x-full',
        ].join(' ')}
      >
        {/* Panel header */}
        <div className="flex items-center justify-between border-b border-gray-700 px-5 py-4">
          <h2 className="text-base font-semibold text-gray-100">{resolvedTitle}</h2>
          <button
            type="button"
            onClick={onClose}
            className="rounded p-1 text-gray-400 hover:bg-gray-700 hover:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
            aria-label="Close help panel"
            data-testid="help-panel-close"
          >
            {/* × icon */}
            <svg
              xmlns="http://www.w3.org/2000/svg"
              className="h-5 w-5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
              aria-hidden="true"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        {/* Search bar — Epic 45.5 */}
        <div className="border-b border-gray-700 px-5 py-3">
          <div className="relative">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              className="pointer-events-none absolute left-2.5 top-2.5 h-4 w-4 text-gray-500"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
              aria-hidden="true"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M21 21l-4.35-4.35M17 11A6 6 0 1 1 5 11a6 6 0 0 1 12 0z"
              />
            </svg>
            <input
              ref={searchRef}
              type="search"
              value={query}
              onChange={(e) => {
                setQuery(e.target.value)
                setSearchTab(null)
              }}
              placeholder="Search help articles…"
              aria-label="Search help articles"
              data-testid="help-search-input"
              className="w-full rounded border border-gray-700 bg-gray-800 py-2 pl-8 pr-3 text-sm text-gray-200 placeholder-gray-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>
        </div>

        {/* Panel body — scrollable only when open (closed panel stays off-screen but
            must not expose a scrollable region to axe while translated away). */}
        <div
          className={`flex-1 px-5 py-4 text-sm text-gray-300 ${open ? 'overflow-y-auto' : 'overflow-hidden'}`}
          tabIndex={open ? 0 : undefined}
        >
          {isSearching ? (
            /* Search results list */
            searchResults.length > 0 ? (
              <ul
                role="list"
                className="space-y-1"
                data-testid="help-search-results"
              >
                {searchResults.map(({ item }) => (
                  <li key={item.key}>
                    <button
                      type="button"
                      onClick={() => handleResultClick(item)}
                      className="w-full rounded px-3 py-2.5 text-left hover:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-500"
                      data-testid={`help-result-${item.key}`}
                    >
                      <span className="block font-medium text-gray-100">
                        {item.title}
                      </span>
                      <span className="mt-0.5 block line-clamp-2 text-xs text-gray-500">
                        {item.content.slice(0, 120).replace(/[#*`\n]/g, ' ')}…
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-gray-500" data-testid="help-search-empty">
                No articles match "<span className="text-gray-400">{query}</span>".
              </p>
            )
          ) : tabContent != null ? (
            <div
              className="prose prose-invert prose-sm max-w-none
                prose-headings:text-gray-100
                prose-p:text-gray-300
                prose-li:text-gray-300
                prose-a:text-indigo-400 prose-a:no-underline hover:prose-a:underline
                prose-strong:text-gray-100
                prose-code:text-indigo-300 prose-code:bg-gray-800 prose-code:px-1 prose-code:rounded
                prose-table:text-xs
                prose-th:text-gray-200 prose-td:text-gray-400
                prose-hr:border-gray-700"
              data-testid="help-panel-markdown"
            >
              <ReactMarkdown>{tabContent}</ReactMarkdown>
            </div>
          ) : children != null ? (
            children
          ) : (
            <p className="text-gray-500">
              No help content available for this page.
            </p>
          )}
        </div>
      </div>
    </>
  )
}
