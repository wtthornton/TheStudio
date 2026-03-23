/** RepoContext — global selected repository state (Epic 41, Story 41.4).
 *
 * Provides the selected repo full_name (owner/repo) across all dashboard
 * tabs. A null value means "All Repos" (no filter applied).
 *
 * The context persists only within the current browser session — it is not
 * stored in localStorage because the dashboard SPA does not have URL-based
 * routing and the context resets on page reload anyway.
 */

import { createContext, useContext, useState } from 'react'
import type { ReactNode } from 'react'

export interface RepoContextValue {
  /** Currently selected repo full_name (e.g. "owner/repo"), or null for All Repos. */
  selectedRepo: string | null
  /** Update the selected repo. Pass null to select "All Repos". */
  setSelectedRepo: (repo: string | null) => void
}

const RepoContext = createContext<RepoContextValue>({
  selectedRepo: null,
  setSelectedRepo: () => {},
})

/** Wrap the application in this provider to enable repo filtering. */
export function RepoContextProvider({ children }: { children: ReactNode }) {
  const [selectedRepo, setSelectedRepo] = useState<string | null>(null)

  return (
    <RepoContext.Provider value={{ selectedRepo, setSelectedRepo }}>
      {children}
    </RepoContext.Provider>
  )
}

/** Hook to read and set the currently selected repository. */
export function useRepoContext(): RepoContextValue {
  return useContext(RepoContext)
}
