/**
 * HelpPanel — slide-in contextual help panel.
 * Epic 45.1: slide-in/out animation, close button, Escape key handler.
 * Epic 45.4: route-aware content loaded via react-markdown (extended in 45.4).
 * Epic 45.5: Fuse.js search (extended in 45.5).
 */

import { useEffect, useRef } from 'react'

interface HelpPanelProps {
  /** Whether the panel is currently open. */
  open: boolean
  /** Called when the user closes the panel. */
  onClose: () => void
  /** Optional title shown in the panel header. */
  title?: string
  /** Optional content to render inside the panel (will be replaced by MD in 45.4). */
  children?: React.ReactNode
}

export function HelpPanel({
  open,
  onClose,
  title = 'Help',
  children,
}: HelpPanelProps) {
  const panelRef = useRef<HTMLDivElement>(null)

  // Close on Escape key
  useEffect(() => {
    if (!open) return
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [open, onClose])

  // Trap focus inside panel when open
  useEffect(() => {
    if (open && panelRef.current) {
      panelRef.current.focus()
    }
  }, [open])

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
        aria-label={title}
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
          <h2 className="text-base font-semibold text-gray-100">{title}</h2>
          <button
            type="button"
            onClick={onClose}
            className="rounded p-1 text-gray-400 hover:bg-gray-700 hover:text-gray-100 focus:outline-none focus:ring-2 focus:ring-indigo-500"
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

        {/* Panel body — scrollable */}
        <div className="flex-1 overflow-y-auto px-5 py-4 text-sm text-gray-300">
          {children ?? (
            <p className="text-gray-500">
              No help content available for this page.
            </p>
          )}
        </div>
      </div>
    </>
  )
}
