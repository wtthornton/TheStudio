/**
 * Locale-aware formatting utilities (Epic 56.3).
 *
 * All functions are pure with no side effects.
 * They rely on standard Intl APIs available in all modern browsers.
 */

/** Returns the user's preferred locale or 'en-US' as fallback. */
export function getLocale(): string {
  if (typeof navigator !== 'undefined' && navigator.language) {
    return navigator.language
  }
  return 'en-US'
}

/** Locale-aware date formatting via Intl.DateTimeFormat. */
export function formatDate(date: Date | string | number, locale?: string): string {
  const resolved = locale ?? getLocale()
  const d = date instanceof Date ? date : new Date(date)
  return new Intl.DateTimeFormat(resolved, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  }).format(d)
}

/** Locale-aware number formatting via Intl.NumberFormat. */
export function formatNumber(num: number, locale?: string): string {
  const resolved = locale ?? getLocale()
  return new Intl.NumberFormat(resolved).format(num)
}

/** Locale-aware currency formatting via Intl.NumberFormat. */
export function formatCurrency(
  amount: number,
  currency: string = 'USD',
  locale?: string,
): string {
  const resolved = locale ?? getLocale()
  return new Intl.NumberFormat(resolved, {
    style: 'currency',
    currency,
  }).format(amount)
}

/** Relative time formatting (e.g., "2 hours ago", "in 3 days"). */
export function formatRelativeTime(date: Date | string | number, locale?: string): string {
  const resolved = locale ?? getLocale()
  const d = date instanceof Date ? date : new Date(date)
  const now = Date.now()
  const diffMs = d.getTime() - now
  const absDiffMs = Math.abs(diffMs)

  // Choose the most appropriate unit
  const seconds = Math.round(absDiffMs / 1000)
  const minutes = Math.round(absDiffMs / 60_000)
  const hours = Math.round(absDiffMs / 3_600_000)
  const days = Math.round(absDiffMs / 86_400_000)

  const rtf = new Intl.RelativeTimeFormat(resolved, { numeric: 'auto' })
  const sign = diffMs < 0 ? -1 : 1

  if (seconds < 60) {
    return rtf.format(sign * seconds, 'second')
  }
  if (minutes < 60) {
    return rtf.format(sign * minutes, 'minute')
  }
  if (hours < 24) {
    return rtf.format(sign * hours, 'hour')
  }
  return rtf.format(sign * days, 'day')
}
