import { ApiReferenceReact } from '@scalar/api-reference-react'
import '@scalar/api-reference-react/style.css'

/**
 * Embedded Scalar OpenAPI reference (React wrapper for @scalar/api-reference).
 * Loads spec from same-origin `/openapi.json` (proxied to the API in Vite dev).
 */
export function ApiReference() {
  return (
    <div
      className="h-[calc(100vh-7rem)] w-full min-h-[400px] overflow-hidden rounded-lg border border-gray-800 bg-gray-950"
      data-testid="api-reference-root"
    >
      <ApiReferenceReact
        configuration={{
          url: '/openapi.json',
          darkMode: true,
          forceDarkModeState: 'dark',
        }}
      />
    </div>
  )
}
