import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

vi.mock('@scalar/api-reference-react', () => ({
  ApiReferenceReact: () => <div data-testid="scalar-api-reference-mock">Scalar</div>,
}))

import { ApiReference } from '../components/ApiReference'

describe('ApiReference', () => {
  it('mounts the API reference container', () => {
    render(<ApiReference />)
    expect(screen.getByTestId('api-reference-root')).toBeInTheDocument()
    expect(screen.getByTestId('scalar-api-reference-mock')).toBeInTheDocument()
  })
})
