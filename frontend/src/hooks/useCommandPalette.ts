/**
 * Global keyboard shortcut hook for the Command Palette (Epic 56.2).
 *
 * Registers Ctrl+K / Cmd+K to toggle the palette open/closed.
 * Returns open state plus open/close/toggle helpers.
 */

import { useState, useEffect, useCallback } from 'react'

export interface UseCommandPaletteReturn {
  isOpen: boolean
  open: () => void
  close: () => void
  toggle: () => void
}

export function useCommandPalette(): UseCommandPaletteReturn {
  const [isOpen, setIsOpen] = useState(false)

  const open = useCallback(() => setIsOpen(true), [])
  const close = useCallback(() => setIsOpen(false), [])
  const toggle = useCallback(() => setIsOpen((prev) => !prev), [])

  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      // Ctrl+K (Windows/Linux) or Cmd+K (macOS)
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault()
        setIsOpen((prev) => !prev)
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [])

  return { isOpen, open, close, toggle }
}
