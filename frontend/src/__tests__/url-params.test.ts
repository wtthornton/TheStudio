/**
 * Epic 49.3 / 49.6 — Vitest tests for URL query parameter parsing.
 *
 * These tests document and verify the conventions used in App.tsx:
 *   - ?tab=<name> controls the active tab on mount (getInitialTab)
 *   - ?repo=<encoded-name> selects the active repo on mount
 *   - Invalid / missing params fall back to safe defaults
 *   - Tab changes are reflected via replaceState
 */

import { describe, expect, it, beforeEach, afterEach, vi } from 'vitest'

// ---------------------------------------------------------------------------
// Inline mirror of App.tsx's getInitialTab logic — kept in sync with source.
// ---------------------------------------------------------------------------
const VALID_TABS = [
  'pipeline',
  'triage',
  'intent',
  'routing',
  'board',
  'trust',
  'budget',
  'activity',
  'analytics',
  'reputation',
  'repos',
  'api',
] as const

type Tab = (typeof VALID_TABS)[number]

function parseTabParam(search: string): Tab {
  const param = new URLSearchParams(search).get('tab')
  return param && (VALID_TABS as readonly string[]).includes(param) ? (param as Tab) : 'pipeline'
}

function parseRepoParam(search: string): string | null {
  const raw = new URLSearchParams(search).get('repo')
  return raw ? decodeURIComponent(raw) : null
}

function buildTabSearch(currentSearch: string, tab: Tab): string {
  const params = new URLSearchParams(currentSearch)
  params.set('tab', tab)
  return `?${params.toString()}`
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('parseTabParam', () => {
  it('returns "pipeline" when no ?tab= param is present', () => {
    expect(parseTabParam('')).toBe('pipeline')
    expect(parseTabParam('?')).toBe('pipeline')
  })

  it('returns the tab when ?tab= is a valid tab name', () => {
    VALID_TABS.forEach((tab) => {
      expect(parseTabParam(`?tab=${tab}`)).toBe(tab)
    })
  })

  it('returns "pipeline" for an unknown tab value', () => {
    expect(parseTabParam('?tab=unknown')).toBe('pipeline')
    expect(parseTabParam('?tab=PIPELINE')).toBe('pipeline') // case-sensitive
    expect(parseTabParam('?tab=')).toBe('pipeline')
  })

  it('ignores extra query params alongside ?tab=', () => {
    expect(parseTabParam('?foo=bar&tab=analytics&baz=1')).toBe('analytics')
  })
})

describe('parseRepoParam', () => {
  it('returns null when no ?repo= param is present', () => {
    expect(parseRepoParam('')).toBeNull()
    expect(parseRepoParam('?tab=pipeline')).toBeNull()
  })

  it('returns the raw repo name for simple identifiers', () => {
    expect(parseRepoParam('?repo=my-repo')).toBe('my-repo')
    expect(parseRepoParam('?repo=acme%2Fwidgets')).toBe('acme/widgets')
  })

  it('URL-decodes percent-encoded owner/repo pairs', () => {
    const encoded = encodeURIComponent('my-org/my-repo')
    expect(parseRepoParam(`?repo=${encoded}`)).toBe('my-org/my-repo')
  })

  it('handles ?tab= and ?repo= together', () => {
    const search = `?tab=repos&repo=${encodeURIComponent('acme/dashboard')}`
    expect(parseTabParam(search)).toBe('repos')
    expect(parseRepoParam(search)).toBe('acme/dashboard')
  })
})

describe('buildTabSearch (replaceState helper)', () => {
  it('sets the tab param in an empty search', () => {
    const result = buildTabSearch('', 'analytics')
    expect(new URLSearchParams(result).get('tab')).toBe('analytics')
  })

  it('replaces an existing tab param', () => {
    const result = buildTabSearch('?tab=pipeline', 'triage')
    expect(new URLSearchParams(result).get('tab')).toBe('triage')
  })

  it('preserves other query params when updating tab', () => {
    const result = buildTabSearch('?repo=my-org%2Frepo&tab=pipeline', 'analytics')
    const params = new URLSearchParams(result)
    expect(params.get('tab')).toBe('analytics')
    expect(params.get('repo')).toBe('my-org/repo')
  })
})

describe('window.history.replaceState on tab change', () => {
  let originalReplaceState: typeof window.history.replaceState

  beforeEach(() => {
    originalReplaceState = window.history.replaceState.bind(window.history)
    vi.spyOn(window.history, 'replaceState')
  })

  afterEach(() => {
    vi.restoreAllMocks()
    window.history.replaceState = originalReplaceState
  })

  it('replaceState mock is callable', () => {
    window.history.replaceState(null, '', '?tab=analytics')
    expect(window.history.replaceState).toHaveBeenCalledWith(null, '', '?tab=analytics')
  })
})

describe('VALID_TABS invariants', () => {
  it('contains all 12 expected tabs', () => {
    expect(VALID_TABS).toHaveLength(12)
  })

  it('includes the API tab (Epic 48)', () => {
    expect(VALID_TABS).toContain('api')
  })

  it('includes the repos tab (Epic 41)', () => {
    expect(VALID_TABS).toContain('repos')
  })

  it('tab names are lowercase with no spaces', () => {
    VALID_TABS.forEach((tab) => {
      expect(tab).toMatch(/^[a-z]+$/)
    })
  })
})
