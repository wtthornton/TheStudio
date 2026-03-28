/** AppSwitcher — dropdown to navigate between Pipeline Dashboard and Admin Console.
 * Epic 49.1: Unified Navigation — app-level switcher in HeaderBar.
 */

import { useState, useRef, useEffect } from 'react'

const APPS = [
  {
    id: 'pipeline',
    label: 'Pipeline Dashboard',
    href: null, // current app — no navigation
    description: 'AI-augmented issue delivery',
  },
  {
    id: 'admin',
    label: 'Admin Console',
    href: '/admin/ui/',
    description: 'Repos, workflows, settings',
  },
] as const

/** Which app is currently active (determined by pathname). */
function currentAppId(): 'pipeline' | 'admin' {
  if (typeof window !== 'undefined' && window.location.pathname.startsWith('/admin')) {
    return 'admin'
  }
  return 'pipeline'
}

export function AppSwitcher() {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)
  const activeId = currentAppId()
  const activeApp = APPS.find((a) => a.id === activeId) ?? APPS[0]

  // Close on outside click
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    if (open) {
      document.addEventListener('mousedown', handleClickOutside)
    }
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [open])

  // Close on Escape
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === 'Escape') setOpen(false)
    }
    if (open) {
      document.addEventListener('keydown', handleKeyDown)
    }
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [open])

  return (
    <div ref={ref} className="relative" data-testid="app-switcher">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-haspopup="listbox"
        aria-expanded={open}
        className="flex items-center gap-1.5 rounded border border-gray-700 bg-gray-900 px-3 py-1.5 text-sm font-medium text-gray-200 hover:border-gray-500 hover:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:ring-offset-gray-950"
        data-testid="app-switcher-trigger"
      >
        <span className="h-2 w-2 rounded-full bg-indigo-400" aria-hidden="true" />
        {activeApp.label}
        <svg
          className={`h-3.5 w-3.5 text-gray-400 transition-transform ${open ? 'rotate-180' : ''}`}
          viewBox="0 0 16 16"
          fill="currentColor"
          aria-hidden="true"
        >
          <path d="M4.427 6.427a.75.75 0 0 1 1.06 0L8 8.94l2.513-2.513a.75.75 0 1 1 1.06 1.06l-3.043 3.044a.75.75 0 0 1-1.06 0L4.427 7.487a.75.75 0 0 1 0-1.06Z" />
        </svg>
      </button>

      {open && (
        <ul
          role="listbox"
          aria-label="Switch application"
          className="absolute left-0 top-full z-50 mt-1 min-w-[13rem] rounded-lg border border-gray-700 bg-gray-900 py-1 shadow-xl"
          data-testid="app-switcher-menu"
        >
          {APPS.map((app) => {
            const isActive = app.id === activeId
            return (
              <li key={app.id} role="option" aria-selected={isActive}>
                {app.href ? (
                  <a
                    href={app.href}
                    className="flex items-start gap-3 px-4 py-2.5 text-sm hover:bg-gray-800 focus:outline-none focus:bg-gray-800"
                    onClick={() => setOpen(false)}
                    data-testid={`app-switcher-option-${app.id}`}
                  >
                    <span className="mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center">
                      {/* empty spacer to align with active checkmark */}
                    </span>
                    <div>
                      <div className="font-medium text-gray-200">{app.label}</div>
                      <div className="text-xs text-gray-500">{app.description}</div>
                    </div>
                  </a>
                ) : (
                  <span
                    className="flex items-start gap-3 px-4 py-2.5 text-sm cursor-default"
                    data-testid={`app-switcher-option-${app.id}`}
                  >
                    <span className="mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center text-indigo-400">
                      {isActive && (
                        <svg viewBox="0 0 16 16" fill="currentColor" className="h-3.5 w-3.5" aria-hidden="true">
                          <path d="M12.78 4.22a.75.75 0 0 1 0 1.06l-6 6a.75.75 0 0 1-1.06 0l-3-3a.75.75 0 0 1 1.06-1.06L6.25 9.69l5.47-5.47a.75.75 0 0 1 1.06 0Z" />
                        </svg>
                      )}
                    </span>
                    <div>
                      <div className="font-medium text-gray-100">{app.label}</div>
                      <div className="text-xs text-gray-500">{app.description}</div>
                    </div>
                  </span>
                )}
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )
}
