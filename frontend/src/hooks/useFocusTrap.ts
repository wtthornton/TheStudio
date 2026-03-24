/**
 * useFocusTrap — constrains keyboard focus within a container element while active.
 *
 * Usage:
 *   const dialogRef = useRef<HTMLDivElement>(null)
 *   useFocusTrap(dialogRef, isOpen)
 *   <div ref={dialogRef} role="dialog"> … </div>
 *
 * Behaviour:
 *   - Tab cycles forward through focusable children, wrapping at the last element.
 *   - Shift+Tab cycles backward, wrapping at the first element.
 *   - When focus escapes the container (e.g. via an external click) the trap is a
 *     soft trap — it does not force-return focus, it only redirects Tab traversal.
 *
 * Epic 54, Story 54.2 — SG §10.5 focus trap requirement for modal dialogs.
 */

import { useEffect } from 'react'

const FOCUSABLE_SELECTORS = [
  'a[href]:not([tabindex="-1"])',
  'button:not([disabled]):not([tabindex="-1"])',
  'input:not([disabled]):not([tabindex="-1"])',
  'select:not([disabled]):not([tabindex="-1"])',
  'textarea:not([disabled]):not([tabindex="-1"])',
  '[tabindex]:not([tabindex="-1"])',
].join(', ')

export function useFocusTrap(
  containerRef: React.RefObject<HTMLElement | null>,
  active: boolean,
): void {
  useEffect(() => {
    if (!active) return
    const container = containerRef.current
    if (!container) return

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key !== 'Tab') return

      const focusable = Array.from(
        container.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTORS),
      ).filter((el) => {
        // Skip elements hidden inside aria-hidden subtrees
        return !el.closest('[aria-hidden="true"]') && el.offsetParent !== null
      })

      if (focusable.length === 0) return

      const first = focusable[0]
      const last = focusable[focusable.length - 1]
      const currentFocus = document.activeElement as HTMLElement

      if (e.shiftKey) {
        // Shift+Tab — wrap backward
        if (!container.contains(currentFocus) || currentFocus === first) {
          e.preventDefault()
          last.focus()
        }
      } else {
        // Tab — wrap forward
        if (!container.contains(currentFocus) || currentFocus === last) {
          e.preventDefault()
          first.focus()
        }
      }
    }

    container.addEventListener('keydown', handleKeyDown)
    return () => container.removeEventListener('keydown', handleKeyDown)
  }, [containerRef, active])
}
