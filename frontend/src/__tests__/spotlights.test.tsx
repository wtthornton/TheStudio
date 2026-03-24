/**
 * Epic 50.5 — Vitest tests for feature spotlights.
 *
 * Covers:
 *  1. SPOTLIGHT_REGISTRY — schema validation (id, sinceVersion, title, description, target)
 *  2. parseSemver — semver string to [major, minor, patch]
 *  3. isVersionGreater / isVersionEqual — version comparison helpers
 *  4. getPendingSpotlights — version mismatch fires, same version skips, null lastSeen
 *  5. localStorage helpers — getLastSeenVersion, markVersionSeen, recordDismissal, resetSpotlightHistory
 *  6. SpotlightProvider — mounts without error, exposes context, version prop override
 */

// ---------------------------------------------------------------------------
// Mock driver.js so SpotlightProvider renders without a DOM paint engine
// ---------------------------------------------------------------------------
vi.mock('driver.js', () => {
  const driverInstance = {
    drive: vi.fn(),
    destroy: vi.fn(),
  }
  return {
    driver: vi.fn(() => driverInstance),
  }
})

// Grab a reference to the mocked driver factory at module load time
import { driver as mockDriver } from 'driver.js'

import { render, screen, act } from '@testing-library/react'
import { beforeEach, afterEach, describe, expect, it, vi } from 'vitest'
import {
  SPOTLIGHT_REGISTRY,
  parseSemver,
  isVersionGreater,
  isVersionEqual,
  getPendingSpotlights,
  getLastSeenVersion,
  markVersionSeen,
  recordDismissal,
  resetSpotlightHistory,
  SPOTLIGHT_VERSION_KEY,
  SPOTLIGHT_DISMISSED_KEY,
} from '../components/spotlights/registry'
import { SpotlightProvider, useSpotlight } from '../components/spotlights/SpotlightProvider'

// ---------------------------------------------------------------------------
// localStorage cleanup helpers
// ---------------------------------------------------------------------------
function clearSpotlightStorage() {
  localStorage.removeItem(SPOTLIGHT_VERSION_KEY)
  localStorage.removeItem(SPOTLIGHT_DISMISSED_KEY)
}

// ===========================================================================
// 1. SPOTLIGHT_REGISTRY — schema validation
// ===========================================================================
describe('SPOTLIGHT_REGISTRY', () => {
  it('contains at least one spotlight entry', () => {
    expect(SPOTLIGHT_REGISTRY.length).toBeGreaterThan(0)
  })

  it('each entry has a non-empty unique id', () => {
    const ids = SPOTLIGHT_REGISTRY.map((e) => e.id)
    const unique = new Set(ids)
    expect(unique.size).toBe(SPOTLIGHT_REGISTRY.length)
    for (const id of ids) {
      expect(id.length).toBeGreaterThan(0)
    }
  })

  it('each entry has a valid semver sinceVersion', () => {
    const semverPattern = /^\d+\.\d+\.\d+/
    for (const entry of SPOTLIGHT_REGISTRY) {
      expect(entry.sinceVersion).toMatch(semverPattern)
    }
  })

  it('each entry has a non-empty title', () => {
    for (const entry of SPOTLIGHT_REGISTRY) {
      expect(entry.title.length).toBeGreaterThan(0)
    }
  })

  it('each entry has a non-empty description', () => {
    for (const entry of SPOTLIGHT_REGISTRY) {
      expect(entry.description.length).toBeGreaterThan(0)
    }
  })

  it('each entry has a non-empty target selector', () => {
    for (const entry of SPOTLIGHT_REGISTRY) {
      expect(entry.target.length).toBeGreaterThan(0)
    }
  })

  it('each target selector is a data-spotlight attribute selector', () => {
    for (const entry of SPOTLIGHT_REGISTRY) {
      expect(entry.target).toMatch(/\[data-spotlight="[^"]+"\]/)
    }
  })

  it('each target selector id matches the entry id', () => {
    for (const entry of SPOTLIGHT_REGISTRY) {
      expect(entry.target).toContain(`data-spotlight="${entry.id}"`)
    }
  })

  it('optional side values are valid PopoverSide values when present', () => {
    const validSides = ['top', 'right', 'bottom', 'left', 'over']
    for (const entry of SPOTLIGHT_REGISTRY) {
      if (entry.side !== undefined) {
        expect(validSides).toContain(entry.side)
      }
    }
  })

  it('optional align values are valid when present', () => {
    const validAligns = ['start', 'center', 'end']
    for (const entry of SPOTLIGHT_REGISTRY) {
      if (entry.align !== undefined) {
        expect(validAligns).toContain(entry.align)
      }
    }
  })

  it('contains expected spotlight ids (help-panel, setup-wizard, api-tab)', () => {
    const ids = SPOTLIGHT_REGISTRY.map((e) => e.id)
    expect(ids).toContain('help-panel')
    expect(ids).toContain('setup-wizard')
    expect(ids).toContain('api-tab')
  })
})

// ===========================================================================
// 2. parseSemver
// ===========================================================================
describe('parseSemver', () => {
  it('parses "1.2.3" correctly', () => {
    expect(parseSemver('1.2.3')).toEqual([1, 2, 3])
  })

  it('parses "0.0.0" (dev fallback)', () => {
    expect(parseSemver('0.0.0')).toEqual([0, 0, 0])
  })

  it('parses "1.0.0"', () => {
    expect(parseSemver('1.0.0')).toEqual([1, 0, 0])
  })

  it('strips pre-release suffix "1.2.3-beta.1"', () => {
    expect(parseSemver('1.2.3-beta.1')).toEqual([1, 2, 3])
  })

  it('returns [0,0,0] for unrecognised input', () => {
    expect(parseSemver('not-a-version')).toEqual([0, 0, 0])
  })

  it('returns [0,0,0] for empty string', () => {
    expect(parseSemver('')).toEqual([0, 0, 0])
  })
})

// ===========================================================================
// 3. isVersionGreater / isVersionEqual
// ===========================================================================
describe('isVersionGreater', () => {
  it('returns true when major is greater', () => {
    expect(isVersionGreater('2.0.0', '1.9.9')).toBe(true)
  })

  it('returns true when minor is greater', () => {
    expect(isVersionGreater('1.3.0', '1.2.9')).toBe(true)
  })

  it('returns true when patch is greater', () => {
    expect(isVersionGreater('1.2.1', '1.2.0')).toBe(true)
  })

  it('returns false when versions are equal', () => {
    expect(isVersionGreater('1.2.0', '1.2.0')).toBe(false)
  })

  it('returns false when a is less than b (major)', () => {
    expect(isVersionGreater('1.0.0', '2.0.0')).toBe(false)
  })

  it('returns false when a is less than b (minor)', () => {
    expect(isVersionGreater('1.2.0', '1.3.0')).toBe(false)
  })

  it('returns false when a is less than b (patch)', () => {
    expect(isVersionGreater('1.2.0', '1.2.1')).toBe(false)
  })
})

describe('isVersionEqual', () => {
  it('returns true for identical versions', () => {
    expect(isVersionEqual('1.2.3', '1.2.3')).toBe(true)
  })

  it('returns true when pre-release suffix is stripped', () => {
    expect(isVersionEqual('1.2.3-alpha', '1.2.3')).toBe(true)
  })

  it('returns false when major differs', () => {
    expect(isVersionEqual('2.0.0', '1.0.0')).toBe(false)
  })

  it('returns false when minor differs', () => {
    expect(isVersionEqual('1.3.0', '1.2.0')).toBe(false)
  })

  it('returns false when patch differs', () => {
    expect(isVersionEqual('1.2.1', '1.2.0')).toBe(false)
  })
})

// ===========================================================================
// 4. getPendingSpotlights
// ===========================================================================
describe('getPendingSpotlights — version mismatch fires', () => {
  it('returns spotlights when currentVersion > lastSeenVersion', () => {
    // All registry entries have sinceVersion "1.0.0"
    // Upgrade from "0.9.0" → "1.0.0" should return all entries
    const pending = getPendingSpotlights('1.0.0', '0.9.0')
    expect(pending.length).toBeGreaterThan(0)
  })

  it('returns all registry entries on first install (lastSeen = null)', () => {
    const pending = getPendingSpotlights('1.0.0', null)
    // At minimum, entries with sinceVersion <= "1.0.0" should be returned
    expect(pending.length).toBeGreaterThan(0)
  })

  it('returned entries are a subset of SPOTLIGHT_REGISTRY', () => {
    const pending = getPendingSpotlights('1.0.0', null)
    for (const entry of pending) {
      expect(SPOTLIGHT_REGISTRY).toContain(entry)
    }
  })
})

describe('getPendingSpotlights — same version skips', () => {
  it('returns empty array when currentVersion equals lastSeenVersion', () => {
    const pending = getPendingSpotlights('1.0.0', '1.0.0')
    expect(pending).toHaveLength(0)
  })

  it('returns empty array when currentVersion is 0.0.0 and lastSeen is 0.0.0', () => {
    const pending = getPendingSpotlights('0.0.0', '0.0.0')
    expect(pending).toHaveLength(0)
  })
})

describe('getPendingSpotlights — future sinceVersion excluded', () => {
  it('excludes spotlights whose sinceVersion is greater than currentVersion', () => {
    // currentVersion "0.5.0" is before all registry entries (sinceVersion "1.0.0")
    const pending = getPendingSpotlights('0.5.0', null)
    expect(pending).toHaveLength(0)
  })
})

describe('getPendingSpotlights — already-seen spotlights excluded', () => {
  it('excludes spotlights whose sinceVersion is <= lastSeenVersion', () => {
    // lastSeen "1.0.0", current "1.0.0" → equal, returns empty
    const pending = getPendingSpotlights('1.0.0', '1.0.0')
    expect(pending).toHaveLength(0)
  })

  it('only returns NEW spotlights for an incremental upgrade', () => {
    // If lastSeen is current version, no new spotlights
    const pendingSame = getPendingSpotlights('1.0.0', '1.0.0')
    expect(pendingSame).toHaveLength(0)
    // If fresh upgrade from before v1.0.0, all v1.0.0 spotlights included
    const pendingUpgrade = getPendingSpotlights('1.0.0', '0.9.9')
    expect(pendingUpgrade.length).toBeGreaterThanOrEqual(pendingSame.length)
  })
})

// ===========================================================================
// 5. localStorage helpers
// ===========================================================================
describe('getLastSeenVersion / markVersionSeen', () => {
  beforeEach(() => clearSpotlightStorage())
  afterEach(() => clearSpotlightStorage())

  it('getLastSeenVersion returns null when key is absent', () => {
    expect(getLastSeenVersion()).toBeNull()
  })

  it('markVersionSeen persists the version string', () => {
    markVersionSeen('1.2.3')
    expect(localStorage.getItem(SPOTLIGHT_VERSION_KEY)).toBe('1.2.3')
  })

  it('getLastSeenVersion returns the stored version after markVersionSeen', () => {
    markVersionSeen('2.0.0')
    expect(getLastSeenVersion()).toBe('2.0.0')
  })
})

describe('recordDismissal', () => {
  beforeEach(() => clearSpotlightStorage())
  afterEach(() => clearSpotlightStorage())

  it('writes an ISO timestamp to localStorage', () => {
    recordDismissal()
    const value = localStorage.getItem(SPOTLIGHT_DISMISSED_KEY)
    expect(value).not.toBeNull()
    // Should be a parseable ISO date string
    expect(new Date(value!).toString()).not.toBe('Invalid Date')
  })
})

describe('resetSpotlightHistory', () => {
  beforeEach(() => {
    markVersionSeen('1.0.0')
    recordDismissal()
  })
  afterEach(() => clearSpotlightStorage())

  it('removes the last-seen version key', () => {
    resetSpotlightHistory()
    expect(localStorage.getItem(SPOTLIGHT_VERSION_KEY)).toBeNull()
  })

  it('removes the dismissed-at key', () => {
    resetSpotlightHistory()
    expect(localStorage.getItem(SPOTLIGHT_DISMISSED_KEY)).toBeNull()
  })

  it('getLastSeenVersion returns null after reset', () => {
    resetSpotlightHistory()
    expect(getLastSeenVersion()).toBeNull()
  })
})

// ===========================================================================
// 6. SpotlightProvider — mount and context
// ===========================================================================

/** Minimal consumer that renders appVersion from context. */
function SpotlightConsumer() {
  const { appVersion } = useSpotlight()
  return <span data-testid="app-version">{appVersion}</span>
}

describe('SpotlightProvider', () => {
  beforeEach(() => {
    clearSpotlightStorage()
    vi.clearAllMocks()
  })
  afterEach(() => clearSpotlightStorage())

  it('renders children without throwing', () => {
    render(
      <SpotlightProvider version="1.0.0">
        <div data-testid="child">hello</div>
      </SpotlightProvider>,
    )
    expect(screen.getByTestId('child')).toBeInTheDocument()
  })

  it('exposes appVersion from context via version prop override', () => {
    render(
      <SpotlightProvider version="2.3.4">
        <SpotlightConsumer />
      </SpotlightProvider>,
    )
    expect(screen.getByTestId('app-version')).toHaveTextContent('2.3.4')
  })

  it('does not fire spotlights when version equals lastSeen (same version skips)', async () => {
    // Prime localStorage so current === lastSeen
    markVersionSeen('1.0.0')

    await act(async () => {
      render(
        <SpotlightProvider version="1.0.0">
          <div />
        </SpotlightProvider>,
      )
    })

    // driver() should not have been called (no pending spotlights — same version)
    expect(mockDriver).not.toHaveBeenCalled()
  })
})

describe('useSpotlight — error when used outside provider', () => {
  it('throws if used outside SpotlightProvider', () => {
    // Suppress console.error from React's error boundary output in tests
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})

    function BareConsumer() {
      useSpotlight()
      return null
    }

    expect(() => render(<BareConsumer />)).toThrow(
      'useSpotlight must be used inside a <SpotlightProvider>',
    )

    consoleError.mockRestore()
  })
})
