/**
 * Epic 49.6 — Vitest tests for AppSwitcher component.
 * Covers: render, dropdown open/close, link hrefs, keyboard and outside-click handling.
 */

import { render, screen, fireEvent } from '@testing-library/react'
import { beforeEach, describe, expect, it } from 'vitest'
import { AppSwitcher } from '../components/AppSwitcher'

describe('AppSwitcher', () => {
  beforeEach(() => {
    // Default path — Pipeline Dashboard is active
    Object.defineProperty(window, 'location', {
      value: { ...window.location, pathname: '/dashboard/' },
      writable: true,
    })
  })

  it('renders the trigger button', () => {
    render(<AppSwitcher />)
    expect(screen.getByTestId('app-switcher-trigger')).toBeInTheDocument()
  })

  it('shows "Pipeline Dashboard" label when on /dashboard/', () => {
    render(<AppSwitcher />)
    expect(screen.getByTestId('app-switcher-trigger')).toHaveTextContent('Pipeline Dashboard')
  })

  it('shows "Admin Console" label when on /admin/ path', () => {
    Object.defineProperty(window, 'location', {
      value: { ...window.location, pathname: '/admin/ui/' },
      writable: true,
    })
    render(<AppSwitcher />)
    expect(screen.getByTestId('app-switcher-trigger')).toHaveTextContent('Admin Console')
  })

  it('dropdown is hidden initially', () => {
    render(<AppSwitcher />)
    expect(screen.queryByTestId('app-switcher-menu')).not.toBeInTheDocument()
  })

  it('opens dropdown when trigger is clicked', () => {
    render(<AppSwitcher />)
    fireEvent.click(screen.getByTestId('app-switcher-trigger'))
    expect(screen.getByTestId('app-switcher-menu')).toBeInTheDocument()
  })

  it('closes dropdown when trigger is clicked again', () => {
    render(<AppSwitcher />)
    const trigger = screen.getByTestId('app-switcher-trigger')
    fireEvent.click(trigger)
    expect(screen.getByTestId('app-switcher-menu')).toBeInTheDocument()
    fireEvent.click(trigger)
    expect(screen.queryByTestId('app-switcher-menu')).not.toBeInTheDocument()
  })

  it('shows both app options when open', () => {
    render(<AppSwitcher />)
    fireEvent.click(screen.getByTestId('app-switcher-trigger'))
    expect(screen.getByTestId('app-switcher-option-pipeline')).toBeInTheDocument()
    expect(screen.getByTestId('app-switcher-option-admin')).toBeInTheDocument()
  })

  it('Admin Console option has correct href /admin/ui/', () => {
    render(<AppSwitcher />)
    fireEvent.click(screen.getByTestId('app-switcher-trigger'))
    const adminOption = screen.getByTestId('app-switcher-option-admin')
    // The admin option renders as an <a> tag with the correct href
    expect(adminOption.tagName).toBe('A')
    expect(adminOption).toHaveAttribute('href', '/admin/ui/')
  })

  it('Pipeline Dashboard option renders as non-link (current app)', () => {
    render(<AppSwitcher />)
    fireEvent.click(screen.getByTestId('app-switcher-trigger'))
    const pipelineOption = screen.getByTestId('app-switcher-option-pipeline')
    // Pipeline Dashboard is the current app — no navigation link
    expect(pipelineOption.tagName).toBe('SPAN')
    expect(pipelineOption).not.toHaveAttribute('href')
  })

  it('closes dropdown on Escape key', () => {
    render(<AppSwitcher />)
    fireEvent.click(screen.getByTestId('app-switcher-trigger'))
    expect(screen.getByTestId('app-switcher-menu')).toBeInTheDocument()
    fireEvent.keyDown(document, { key: 'Escape' })
    expect(screen.queryByTestId('app-switcher-menu')).not.toBeInTheDocument()
  })

  it('closes dropdown when clicking outside', () => {
    render(
      <div>
        <AppSwitcher />
        <div data-testid="outside">outside</div>
      </div>,
    )
    fireEvent.click(screen.getByTestId('app-switcher-trigger'))
    expect(screen.getByTestId('app-switcher-menu')).toBeInTheDocument()
    fireEvent.mouseDown(screen.getByTestId('outside'))
    expect(screen.queryByTestId('app-switcher-menu')).not.toBeInTheDocument()
  })

  it('sets aria-expanded correctly', () => {
    render(<AppSwitcher />)
    const trigger = screen.getByTestId('app-switcher-trigger')
    expect(trigger).toHaveAttribute('aria-expanded', 'false')
    fireEvent.click(trigger)
    expect(trigger).toHaveAttribute('aria-expanded', 'true')
  })

  it('menu has role="listbox" and items have role="option"', () => {
    render(<AppSwitcher />)
    fireEvent.click(screen.getByTestId('app-switcher-trigger'))
    const menu = screen.getByTestId('app-switcher-menu')
    expect(menu).toHaveAttribute('role', 'listbox')
    const options = screen.getAllByRole('option')
    expect(options).toHaveLength(2)
  })
})
